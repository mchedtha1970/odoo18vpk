{
    "name": "VPK Vendor Security - กำหนดสิทธิ์ฐานข้อมูลผู้จำหน่าย",
    "version": "18.0.1.0.0",
    "category": "Contacts",
    "summary": "กำหนดสิทธิ์เพิ่ม/แก้ไข/ลบฐานข้อมูลผู้จำหน่ายตามบทบาท",
    "depends": ["base", "purchase", "account", "partner_readonly_security"],
    "data": [
        "security/vendor_security_groups.xml",
        "security/ir.model.access.csv",
        "data/fiscal_position_data.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
