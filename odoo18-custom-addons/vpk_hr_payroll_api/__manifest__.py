# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK HR Payroll Interface",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "รับชุดเงินเดือนจากระบบ HR แล้วกดผ่านเพื่อสร้างสมุดรายวัน",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": ["account", "mail"],
    "data": [
        "security/hr_payroll_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ir_config_parameter_data.xml",
        "data/payroll_component_data.xml",
        "views/payroll_batch_views.xml",
        "views/payroll_component_map_views.xml",
        "views/payroll_log_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
}
