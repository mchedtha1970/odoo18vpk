# -*- coding: utf-8 -*-


def migrate(cr, version):
    cr.execute(
        """
        UPDATE purchase_requisition AS req
           SET purchase_request_amount_total = line.amount_total
          FROM ebidding_plan_line AS line
         WHERE req.ebidding_plan_line_id = line.id
           AND COALESCE(req.purchase_request_amount_total, 0) = 0
           AND COALESCE(line.amount_total, 0) <> 0
        """
    )
