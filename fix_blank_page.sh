#!/bin/bash
# Fix blank Odoo page caused by spiffy_theme_backend_old_15 invalid manifest
set -euo pipefail

echo "1. Removing old module backup from addons path..."
sudo rm -rf /opt/odoo18vpk/odoo18-custom-addons/spiffy_theme_backend_old_15

echo "2. Updating Odoo config to use clean addons path..."
sudo cp /opt/odoo18vpk/odoo18vpk-fixed.conf /etc/odoo18vpk.conf

echo "3. Upgrading spiffy_theme_backend..."
/opt/odoo18vpk/odoo18vpk-venv/bin/python /opt/odoo18vpk/odoo18/odoo-bin \
  -c /etc/odoo18vpk.conf -d VPK-S1 -u spiffy_theme_backend --stop-after-init

echo "4. Restarting Odoo..."
sudo systemctl restart odoo18vpk

echo "Done. Please hard-refresh browser (Ctrl+Shift+R)."
