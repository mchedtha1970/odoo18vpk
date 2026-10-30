def migrate(cr, version):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'purchase_requisition_egp_bid_line'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        ALTER TABLE purchase_requisition_egp_bid_line
        ADD COLUMN IF NOT EXISTS partner_id INTEGER
        """
    )
    cr.execute(
        """
        ALTER TABLE purchase_requisition_egp_bid_line
        ADD COLUMN IF NOT EXISTS requisition_id INTEGER
        """
    )
    cr.execute(
        """
        UPDATE purchase_requisition_egp_bid_line line
           SET partner_id = bid.partner_id
          FROM purchase_requisition_egp_bid bid
         WHERE line.bid_id = bid.id
           AND line.partner_id IS NULL
        """
    )
    cr.execute(
        """
        UPDATE purchase_requisition_egp_bid_line line
           SET requisition_id = bid.requisition_id
          FROM purchase_requisition_egp_bid bid
         WHERE line.bid_id = bid.id
           AND line.requisition_id IS NULL
        """
    )
