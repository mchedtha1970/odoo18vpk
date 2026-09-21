#!/usr/bin/env bash
# Restore VPK-S1 dump + filestore into local docker compose.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DUMP="${ROOT}/VPK_S1/VPK_S1.dump"
cd "${ROOT}"

if [ ! -f "${DUMP}" ]; then
  echo "missing ${DUMP}" >&2
  exit 1
fi

docker compose up -d db
for _ in $(seq 1 30); do
  if docker compose exec -T db pg_isready -U odoo -d postgres >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker compose exec -T db psql -U odoo -d postgres -v ON_ERROR_STOP=1 <<'SQL'
SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
 WHERE datname = 'VPK-S1' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "VPK-S1";
CREATE DATABASE "VPK-S1" OWNER odoo;
SQL

docker compose exec -T db pg_restore -U odoo --no-owner --no-acl --role=odoo --dbname=VPK-S1 < "${DUMP}"
docker compose up -d odoo
echo "restored VPK-S1. Open http://localhost:8069"
