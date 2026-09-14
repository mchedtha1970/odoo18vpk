#!/usr/bin/env bash
# Clone OCA addon repos into odoo18-custom-addons/. Safe to re-run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ADDONS="${ROOT}/odoo18-custom-addons"
BRANCH="${OCA_BRANCH:-18.0}"

mkdir -p "${ADDONS}"

clone_repo() {
  local dest_name="$1"
  local url="$2"
  local dest="${ADDONS}/${dest_name}"
  if [ -d "${dest}/.git" ] || [ -d "${dest}" ]; then
    echo "skip  ${dest_name} (already present)"
    return 0
  fi
  echo "clone ${dest_name}"
  git clone --depth 1 --branch "${BRANCH}" "${url}" "${dest}"
}

clone_repo account-financial-tools-18.0 https://github.com/OCA/account-financial-tools.git
clone_repo account-invoicing-18.0 https://github.com/OCA/account-invoicing.git
clone_repo account-payment-18.0 https://github.com/OCA/account-payment.git
clone_repo hr-expense-18.0 https://github.com/OCA/hr-expense.git
clone_repo l10n-thailand-18.0 https://github.com/OCA/l10n-thailand.git
clone_repo partner-contact-18.0 https://github.com/OCA/partner-contact.git
clone_repo purchase-workflow-18.0 https://github.com/OCA/purchase-workflow.git
clone_repo reporting-engine-18.0 https://github.com/OCA/reporting-engine.git
clone_repo server-tools-18.0 https://github.com/OCA/server-tools.git
clone_repo server-ux-18.0 https://github.com/OCA/server-ux.git
clone_repo stock-logistics-workflow-18.0 https://github.com/OCA/stock-logistics-workflow.git

echo "done. Next: cp .env.example .env && docker compose up -d --build"
