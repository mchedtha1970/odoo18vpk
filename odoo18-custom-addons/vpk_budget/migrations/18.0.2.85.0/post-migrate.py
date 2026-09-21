def migrate(cr, version):
    """Link budget groups to matching product categories under กลุ่มวัสดุ."""
    cr.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'vpk_budget_group'
              AND column_name = 'product_categ_id'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    cr.execute(
        """
        SELECT id
        FROM product_category
        WHERE name = 'กลุ่มวัสดุ' AND parent_id IS NULL
        LIMIT 1
        """
    )
    root = cr.fetchone()
    if not root:
        return
    root_id = root[0]

    cr.execute(
        """
        SELECT id, name
        FROM product_category
        WHERE parent_id = %s
        """,
        (root_id,),
    )
    children = cr.fetchall()

    def strip_prefix(name):
        text = (name or "").strip()
        if "." in text:
            text = text.split(".", 1)[-1].strip()
        return text

    aliases = {
        "TECHNICIAN": ["ช่าง", "วัสดุช่าง"],
        "FUEL": ["เชื้อเพลิง"],
    }

    cr.execute(
        """
        SELECT id, code, name
        FROM vpk_budget_group
        WHERE product_categ_id IS NULL
        """
    )
    for group_id, code, name in cr.fetchall():
        needles = [strip_prefix(name)]
        needles.extend(aliases.get(code or "", []))
        matched_id = None
        for categ_id, categ_name in children:
            short = strip_prefix(categ_name)
            for needle in needles:
                if not needle:
                    continue
                if short == needle or needle in short or short in needle:
                    matched_id = categ_id
                    break
            if matched_id:
                break
        if matched_id:
            cr.execute(
                """
                UPDATE vpk_budget_group
                SET product_categ_id = %s
                WHERE id = %s
                """,
                (matched_id, group_id),
            )
