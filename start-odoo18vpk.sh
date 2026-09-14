#!/bin/bash
# Bind this instance to VPK-S1 so REST /vpk/api/v1/mobile is reachable
# without a prior web session (fixes 404 from the mobile app).
exec /opt/odoo18vpk/odoo18vpk-venv/bin/python3 /opt/odoo18vpk/odoo18/odoo-bin \
  -c /etc/odoo18vpk.conf -d VPK-S1 "$@"
