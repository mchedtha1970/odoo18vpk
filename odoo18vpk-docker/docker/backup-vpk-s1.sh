#!/usr/bin/env bash
# Backup VPK-S1 dump + filestore to VPK_S1/VPK-S1-backup-YYYYMMDD-HHMM.tar.gz
# Do not commit the archive; copy it to the other host and run restore-vpk-s1.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

PGUSER="${POSTGRES_USER:-odoo}"
DBNAME="VPK-S1"
BACKUP_DIR="${ROOT}/VPK_S1"
DUMP="${BACKUP_DIR}/VPK_S1.dump"
FILESTORE="${BACKUP_DIR}/filestore"
STAMP="$(date -u +%Y%m%d-%H%M)"
ARCHIVE="${BACKUP_DIR}/VPK-S1-backup-${STAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}" "${FILESTORE}"

echo "waiting for postgres..."
docker compose up -d db
ready=0
for _ in $(seq 1 30); do
  if docker compose exec -T db pg_isready -U "${PGUSER}" -d postgres >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "${ready}" != 1 ]; then
  echo "postgres is not ready" >&2
  exit 1
fi

if ! docker compose exec -T db psql -U "${PGUSER}" -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname = '${DBNAME}'" | grep -q 1; then
  echo "database ${DBNAME} does not exist" >&2
  exit 1
fi

odoo_was_up=0
if docker compose ps --format '{{.Service}} {{.State}}' 2>/dev/null | grep -Eq '^odoo running$'; then
  odoo_was_up=1
elif docker compose ps odoo 2>/dev/null | grep -q ' Up '; then
  odoo_was_up=1
fi
if [ "${odoo_was_up}" = 1 ]; then
  echo "stopping odoo for a consistent backup..."
  docker compose stop odoo
fi

echo "dumping ${DBNAME}..."
docker compose exec -T db pg_dump -U "${PGUSER}" -Fc --no-owner --no-acl -d "${DBNAME}" > "${DUMP}"

echo "collecting filestore..."
odoo_cid="$(docker compose ps -aq odoo 2>/dev/null || true)"
if [ -n "${odoo_cid}" ]; then
  tmp_fs="${FILESTORE}/.vpk-s1-copy"
  rm -rf "${tmp_fs}"
  if docker cp "${odoo_cid}:/var/lib/odoo/filestore/VPK-S1" "${tmp_fs}" 2>/dev/null; then
    rm -rf "${FILESTORE}/VPK-S1"
    mv "${tmp_fs}" "${FILESTORE}/VPK-S1"
  else
    rm -rf "${tmp_fs}"
  fi
fi
if [ ! -d "${FILESTORE}/VPK-S1" ]; then
  echo "warning: no filestore/VPK-S1 found (attachments will be missing on restore)" >&2
fi

dump_size="$(du -h "${DUMP}" | awk '{print $1}')"
fs_size="0"
fs_files="0"
if [ -d "${FILESTORE}/VPK-S1" ]; then
  fs_size="$(du -sh "${FILESTORE}/VPK-S1" | awk '{print $1}')"
  fs_files="$(find "${FILESTORE}/VPK-S1" -type f | wc -l | tr -d ' ')"
fi
db_size="$(docker compose exec -T db psql -U "${PGUSER}" -d postgres -tAc \
  "SELECT pg_size_pretty(pg_database_size('${DBNAME}'))" | tr -d '[:space:]')"
pg_version="$(docker compose exec -T db psql -U "${PGUSER}" -d postgres -tAc 'SHOW server_version' | tr -d '[:space:]')"
host_name="$(hostname -s 2>/dev/null || hostname)"

cat > "${BACKUP_DIR}/MANIFEST.txt" <<EOF
database: ${DBNAME}
created: ${STAMP}
source_host: ${host_name}
postgres: ${pg_version}
db_size: ${db_size}
dump: VPK_S1.dump (${dump_size})
filestore: filestore/VPK-S1 (${fs_size}) files=${fs_files}
EOF

echo "creating ${ARCHIVE}..."
tar -C "${BACKUP_DIR}" -czf "${ARCHIVE}" VPK_S1.dump MANIFEST.txt filestore

if [ "${odoo_was_up}" = 1 ]; then
  docker compose start odoo
fi

echo "backup ready: ${ARCHIVE}"
echo
echo "copy to another host:"
echo "  scp ${ARCHIVE} user@other-host:"
echo
echo "restore on the other host:"
echo "  tar -xzf VPK-S1-backup-${STAMP}.tar.gz -C odoo18vpk-docker/VPK_S1"
echo "  cd odoo18vpk-docker && ./docker/restore-vpk-s1.sh"
