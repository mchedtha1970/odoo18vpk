# VPK Odoo 18 — โครงสร้างการพัฒนา

## โฟลเดอร์หลัก

| โฟลเดอร์ | 用途 |
|----------|------|
| `odoo18-custom-addons/` | **พัฒนาและติดตั้ง module ทั้งหมด** (เช่น `vpk_sidebar_menu`, `vpk_tier_validation`) |
| `odoo18/addons/` | Odoo core + standard addons |
| `work/spiffy_theme_backend/` | **อ้างอิงเท่านั้น** — เปรียบเทียบ UI/UX กับ Spiffy ไม่ติดตั้ง ไม่อยู่ใน `addons_path` |

## สิ่งที่เลิกใช้

- ~~`odoo18-custom-addons-clean/`~~ — ลบแล้ว (เคยเป็น symlink ทำให้สับสนกับ path จริง)
- ~~`odoo18-custom-addons/spiffy_theme_backend/`~~ — ย้ายออกจาก addons path แล้ว ใช้ copy ใน `work/` แทน

## Odoo config

ไฟล์จริง: `/etc/odoo18vpk.conf`  
ตัวอย่างใน repo: `odoo18vpk.conf.example`

`addons_path` ต้องมี `/opt/odoo18vpk/odoo18-custom-addons` และ **ไม่** มี `odoo18-custom-addons-clean`

## อัปเกรด module หลังแก้โค้ด

```bash
/opt/odoo18vpk/odoo18vpk-venv/bin/python /opt/odoo18vpk/odoo18/odoo-bin \
  -c /etc/odoo18vpk.conf -d VPK-S1 -u vpk_sidebar_menu --stop-after-init
```

หลังเปลี่ยน config ให้ restart Odoo แล้ว hard refresh browser (Ctrl+Shift+R)

## รันบน Docker (เครื่อง local)

โครงสร้างอยู่ที่ `odoo18vpk-docker/` แบบเดียวกับ `odoo15apexth-docker`:

```
odoo18vpk-docker/
├── VPK_S1/
├── docker/
├── docker-compose.yml
└── odoo18-custom-addons/
```

```bash
git clone https://github.com/mchedtha1970/odoo18vpk.git odoo18vpk
cd odoo18vpk/odoo18vpk-docker
./docker/clone-oca-addons.sh
cp .env.example .env
docker compose up -d --build
```

เปิด http://localhost:8069 (master password: `admin`)

รายละเอียดอยู่ที่ `odoo18vpk-docker/docker/README.md`
