วาง dump / filestore ของ database VPK-S1 ไว้ที่นี่ (เทียบกับ APEXTH_LIVE)

ตัวอย่าง:

    VPK_S1.dump          # pg_dump -Fc
    filestore/VPK-S1/    # จาก /var/lib/odoo/filestore หรือ data_dir

Restore หลัง docker compose up:

    docker compose exec -T db pg_restore -U odoo -C -d postgres < VPK_S1.dump
