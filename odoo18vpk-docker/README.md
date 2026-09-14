# odoo18vpk-docker

Odoo 18 VPK สำหรับรันบน Docker เครื่อง local

```
odoo18vpk-docker/
├── VPK_S1/                   # dump + filestore
├── docker/                   # Dockerfile, odoo.conf
├── docker-compose.yml
└── odoo18-custom-addons/     # โมดูล VPK + OCA
```

## รันบนเครื่อง local

```bash
git clone <url> odoo18vpk
cd odoo18vpk/odoo18vpk-docker
./docker/clone-oca-addons.sh
cp .env.example .env
docker compose up -d --build
```

เปิด http://localhost:8069 — master password คือ `admin`

รายละเอียดเพิ่มเติมอยู่ที่ `docker/README.md`
