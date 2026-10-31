def migrate(cr, version):
    cr.execute(
        """
        UPDATE procurement_guarantee g
           SET egp_contract_control_no = COALESCE(g.egp_contract_control_no, c.egp_contract_control_no),
               contract_po_number = COALESCE(g.contract_po_number, c.contract_po_number)
          FROM purchase_contract c
         WHERE g.contract_id = c.id
           AND (g.egp_contract_control_no IS NULL OR g.contract_po_number IS NULL)
        """
    )
