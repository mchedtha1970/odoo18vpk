ข้อมูลสำรอง VPK-S1 (อย่า commit ขึ้น git)

| ไฟล์ | รายละเอียด |
|------|-------------|
| `VPK-S1-backup-YYYYMMDD-HHMM.tar.gz` | โหลดไฟล์เดียว (dump + filestore) |
| `VPK_S1.dump` | pg_dump -Fc |
| `filestore/VPK-S1/` | ไฟล์แนบ Odoo |
| `MANIFEST.txt` | วันที่และขนาด |

Backup จาก Docker เครื่องนี้:

```bash
cd odoo18vpk-docker
./docker/backup-vpk-s1.sh
scp VPK_S1/VPK-S1-backup-*.tar.gz user@other-host:
```

Restore ใน local docker:

```bash
cd odoo18vpk-docker
tar -xzf VPK-S1-backup-*.tar.gz -C VPK_S1
./docker/restore-vpk-s1.sh
```
