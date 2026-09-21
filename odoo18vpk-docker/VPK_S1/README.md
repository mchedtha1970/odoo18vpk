ข้อมูลสำรอง VPK-S1 (อย่า commit ขึ้น git)

| ไฟล์ | รายละเอียด |
|------|-------------|
| `VPK-S1-backup-YYYYMMDD-HHMM.tar.gz` | โหลดไฟล์เดียว (dump + filestore) |
| `VPK_S1.dump` | pg_dump -Fc |
| `filestore/VPK-S1/` | ไฟล์แนบ Odoo |
| `MANIFEST.txt` | วันที่และขนาด |

Download จากเซิร์ฟเวอร์:

```bash
scp odoo18vpk@<server>:/opt/odoo18vpk/odoo18vpk-docker/VPK_S1/VPK-S1-backup-*.tar.gz .
```

Restore ใน local docker:

```bash
cd odoo18vpk-docker
tar -xzf VPK-S1-backup-*.tar.gz -C VPK_S1
./docker/restore-vpk-s1.sh
```
