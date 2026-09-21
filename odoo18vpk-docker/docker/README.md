# odoo18vpk-docker

โครงสร้างเดียวกับ `odoo15apexth-docker`:

```
odoo18vpk-docker/
├── VPK_S1/                 # dump + filestore (เทียบ APEXTH_LIVE)
├── docker/                 # Dockerfile, odoo.conf
├── docker-compose.yml
└── odoo18-custom-addons/   # โมดูล VPK + OCA
```

## รันบนเครื่อง local

```bash
git clone https://github.com/mchedtha1970/odoo18vpk.git odoo18vpk
cd odoo18vpk/odoo18vpk-docker
./docker/clone-oca-addons.sh
cp .env.example .env
docker compose up -d --build
```

เปิด http://localhost:8069 — master password คือ `admin`

ไม่ต้อง clone `odoo/odoo` ใช้ image `odoo:18.0`

## คำสั่งที่ใช้บ่อย

```bash
docker compose ps
docker compose logs -f odoo
docker compose down          # เก็บ volume ไว้
docker compose down -v       # ลบ DB + filestore

docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d VPK-S1 -u vpk_sidebar_menu --stop-after-init
docker compose restart odoo
```

OCA ที่ยังไม่มีใน `odoo18-custom-addons/`:

```bash
./docker/clone-oca-addons.sh
```

## Restore ข้อมูลจากเซิร์ฟเวอร์

Dump + filestore **ไม่ได้อยู่ใน git** ต้องโหลดจากเซิร์ฟเวอร์แยก:

```bash
scp odoo18vpk@<server>:/opt/odoo18vpk/odoo18vpk-docker/VPK_S1/VPK-S1-backup-*.tar.gz .
cd odoo18vpk-docker
tar -xzf ../VPK-S1-backup-*.tar.gz -C VPK_S1
./docker/restore-vpk-s1.sh
```

หรือถ้า copy ทั้งโฟลเดอร์ `VPK_S1/` มาแล้ว:

```bash
cd odoo18vpk-docker
./docker/restore-vpk-s1.sh
```

Filestore ถูก mount ที่ `./VPK_S1/filestore` → `/var/lib/odoo/filestore` อัตโนมัติ
เปิด http://localhost:8069 แล้วเลือก database `VPK-S1`
