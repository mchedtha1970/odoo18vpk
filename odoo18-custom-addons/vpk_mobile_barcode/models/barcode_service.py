import re
from datetime import datetime

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class VpkBarcodeService(models.AbstractModel):
    _name = "vpk.barcode.service"
    _description = "VPK mobile barcode"

    def _ensure_user(self):
        if not self.env.user.has_group("stock.group_stock_user"):
            raise AccessError(_("ต้องอยู่ในกลุ่มผู้ใช้สินค้าคงคลัง"))

    def _rounding(self, uom):
        return uom.rounding or 0.01

    def _fefo_key(self, line):
        lot = line.lot_id
        exp = False
        if lot and "expiration_date" in lot._fields:
            exp = lot.expiration_date
        return (exp or datetime.max, line.id)

    def menu_data(self):
        self._ensure_user()
        user = self.env.user
        types = self.env["stock.picking.type"].search([
            ("code", "in", ("incoming", "outgoing", "internal")),
        ])
        operations = []
        Picking = self.env["stock.picking"]
        for ptype in types:
            operations.append({
                "id": ptype.id,
                "name": ptype.name,
                "warehouse": ptype.warehouse_id.name or "",
                "code": ptype.code,
                "barcode": ptype.barcode or "",
                "color": ptype.color or 0,
                "count": Picking.search_count([
                    ("picking_type_id", "=", ptype.id),
                    ("state", "in", ("assigned", "confirmed", "waiting")),
                ]),
            })
        today = fields.Date.context_today(user)
        quant_count = self.env["stock.quant"].search_count([
            ("user_id", "=", user.id),
            ("location_id.usage", "in", ("internal", "transit")),
            ("inventory_date", "<=", today),
            ("inventory_quantity_set", "=", False),
        ])
        return {
            "user": user.name,
            "quant_count": quant_count,
            "operations": operations,
        }

    def list_pickings(self, picking_type_id):
        self._ensure_user()
        ptype = self.env["stock.picking.type"].browse(picking_type_id).exists()
        if not ptype:
            raise UserError(_("ไม่พบประเภทการปฏิบัติการ"))
        pickings = self.env["stock.picking"].search([
            ("picking_type_id", "=", ptype.id),
            ("state", "in", ("assigned", "confirmed", "waiting")),
        ], order="scheduled_date, id", limit=80)
        return {
            "type": {
                "id": ptype.id,
                "name": ptype.display_name,
                "code": ptype.code,
            },
            "pickings": [self._picking_card(p) for p in pickings],
        }

    def _picking_card(self, picking):
        labels = {
            "assigned": "พร้อม",
            "confirmed": "รอสินค้า",
            "waiting": "กำลังรอ",
            "done": "เสร็จสิ้น",
            "cancel": "ยกเลิก",
            "draft": "ฉบับร่าง",
        }
        return {
            "id": picking.id,
            "name": picking.name,
            "origin": picking.origin or "",
            "partner": picking.partner_id.name or "",
            "state": picking.state,
            "state_label": labels.get(picking.state, picking.state),
            "scheduled": fields.Datetime.to_string(picking.scheduled_date) if picking.scheduled_date else "",
            "line_count": len(picking.move_ids),
        }

    def get_picking(self, picking_id):
        self._ensure_user()
        return {"picking": self._picking_payload(self._picking(picking_id))}

    def _picking(self, picking_id):
        picking = self.env["stock.picking"].browse(picking_id).exists()
        if not picking:
            raise UserError(_("ไม่พบใบงาน"))
        return picking

    def _picking_payload(self, picking):
        lines = picking.move_line_ids.filtered(lambda line: line.state != "cancel")
        lines = lines.sorted(key=lambda line: (
            line.location_id.complete_name or "",
            line.product_id.default_code or "",
            line.lot_id.name or "",
            line.id,
        ))
        done_count = 0
        for line in lines:
            if line.picked and not float_is_zero(line.quantity, precision_rounding=self._rounding(line.product_uom_id)):
                done_count += 1
        return {
            "id": picking.id,
            "name": picking.name,
            "origin": picking.origin or "",
            "partner": picking.partner_id.name or "",
            "state": picking.state,
            "note": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", picking.note or "")).strip(),
            "can_validate": picking.state not in ("done", "cancel") and done_count > 0,
            "lines": [self._line_dict(line) for line in lines],
        }

    def _line_dict(self, line):
        product = line.product_id
        done = line.quantity if line.picked else 0.0
        demand = line.quantity if not line.picked else line.quantity
        return {
            "id": line.id,
            "product_id": product.id,
            "default_code": product.default_code or "",
            "product_name": product.name or product.display_name,
            "tracking": product.tracking,
            "lot_id": line.lot_id.id or False,
            "lot_name": line.lot_id.name or line.lot_name or "",
            "location_id": line.location_id.id,
            "location_name": line.location_id.display_name,
            "dest_name": line.location_dest_id.display_name,
            "qty_done": done,
            "qty_demand": demand,
            "uom": line.product_uom_id.name or "",
            "picked": bool(line.picked),
        }

    def scan_menu(self, barcode):
        self._ensure_user()
        barcode = (barcode or "").strip()
        if not barcode:
            raise UserError(_("ไม่มีบาร์โค้ด"))
        picking = self.env["stock.picking"].search([
            ("name", "=", barcode),
            ("state", "not in", ("done", "cancel")),
        ], limit=1)
        if picking:
            return {"action": "picking", "picking_id": picking.id, "message": picking.name}
        ptype = self.env["stock.picking.type"].search([("barcode", "=", barcode)], limit=1)
        if ptype:
            return {
                "action": "picking_type",
                "picking_type_id": ptype.id,
                "message": ptype.display_name,
            }
        location = self.env["stock.location"].search([
            ("barcode", "=", barcode),
            ("usage", "in", ("internal", "transit")),
        ], limit=1)
        if location:
            return {
                "action": "inventory",
                "location_id": location.id,
                "location_name": location.display_name,
                "message": location.display_name,
            }
        product = self._find_product(barcode)
        if product:
            return {
                "action": "product",
                "message": product.display_name,
                **self._product_locations(product),
            }
        lot = self.env["stock.lot"].search([("name", "=", barcode)], limit=1)
        if lot:
            return {
                "action": "product",
                "message": "%s · %s" % (lot.product_id.display_name, lot.name),
                "lot_name": lot.name,
                **self._product_locations(lot.product_id, lot),
            }
        return {
            "action": "warning",
            "warning": True,
            "message": _("ไม่พบใบงาน สินค้า ตำแหน่ง หรือล็อตของบาร์โค้ด %s", barcode),
        }

    def _find_product(self, barcode):
        return self.env["product.product"].search([
            "|", ("barcode", "=", barcode), ("default_code", "=", barcode),
        ], limit=1)

    def _product_locations(self, product, lot=None):
        domain = [
            ("product_id", "=", product.id),
            ("location_id.usage", "=", "internal"),
            ("quantity", ">", 0),
        ]
        if lot:
            domain.append(("lot_id", "=", lot.id))
        quants = self.env["stock.quant"].search(domain, limit=30)
        return {
            "product": {
                "id": product.id,
                "default_code": product.default_code or "",
                "name": product.name,
                "uom": product.uom_id.name or "",
                "tracking": product.tracking,
            },
            "quants": [{
                "id": quant.id,
                "location": quant.location_id.display_name,
                "lot": quant.lot_id.name or "",
                "qty": quant.quantity,
                "uom": quant.product_uom_id.name or "",
            } for quant in quants],
        }

    def scan_picking(self, picking_id, barcode, location_id=False, line_id=False, pending_product_id=False):
        self._ensure_user()
        picking = self._picking(picking_id)
        if picking.state in ("done", "cancel"):
            raise UserError(_("ใบงานนี้ปิดแล้ว"))
        barcode = (barcode or "").strip()
        if not barcode:
            raise UserError(_("ไม่มีบาร์โค้ด"))

        location = self.env["stock.location"].search([
            ("barcode", "=", barcode),
            ("usage", "in", ("internal", "transit")),
        ], limit=1)
        if location:
            return self._scan_result(
                picking,
                action="location",
                message=_("ตำแหน่ง %s — สแกนสินค้า", location.display_name),
                location_id=location.id,
                location_name=location.display_name,
            )

        product = self._find_product(barcode)
        if product:
            return self._scan_product(picking, product, location_id, line_id)

        lot = self.env["stock.lot"].search([("name", "=", barcode)], limit=1)
        if lot or pending_product_id:
            return self._scan_lot(picking, barcode, lot, location_id, line_id, pending_product_id)

        return self._scan_result(
            picking,
            action="warning",
            warning=True,
            message=_("ไม่พบบาร์โค้ด %s ในใบนี้", barcode),
        )

    def _scan_result(self, picking, message, action="ok", warning=False, **extra):
        payload = {
            "action": action,
            "warning": warning,
            "message": message,
            "picking": self._picking_payload(picking),
        }
        payload.update(extra)
        return payload

    def _candidate_lines(self, picking, product, location_id=False, line_id=False):
        lines = picking.move_line_ids.filtered(
            lambda line: line.product_id == product and line.state not in ("done", "cancel")
        )
        if line_id:
            chosen = lines.filtered(lambda line: line.id == line_id)
            if chosen:
                lines = chosen
        if location_id:
            here = lines.filtered(lambda line: line.location_id.id == location_id)
            if here:
                lines = here
        return lines

    def _scan_product(self, picking, product, location_id, line_id):
        lines = self._candidate_lines(picking, product, location_id, line_id)
        if not lines:
            moves = picking.move_ids.filtered(
                lambda move: move.product_id == product and move.state not in ("done", "cancel")
            )
            if not moves:
                return self._scan_result(
                    picking,
                    action="warning",
                    warning=True,
                    message=_("สินค้า %s ไม่อยู่ในใบงานนี้", product.display_name),
                )
            if product.tracking != "none":
                return self._scan_result(
                    picking,
                    action="need_lot",
                    message=_("สแกนหมายเลขล็อตของ %s", product.display_name),
                    pending_product_id=product.id,
                )
            move = moves[0]
            loc = self.env["stock.location"].browse(location_id) if location_id else move.location_id
            line = self._create_picked_line(move, loc, 1.0, move.product_uom)
            return self._scan_result(
                picking,
                action="product",
                message=self._done_message(line),
                selected_line_id=line.id,
            )

        unpicked = lines.filtered(lambda line: not line.picked)
        pool = (unpicked or lines).sorted(key=self._fefo_key)
        line = pool[0]
        if product.tracking != "none" and not line.lot_id and not line.lot_name:
            return self._scan_result(
                picking,
                action="need_lot",
                message=_("สแกนหมายเลขล็อตของ %s", product.display_name),
                pending_product_id=product.id,
                selected_line_id=line.id,
            )
        target = self._take_qty(line, 1.0)
        return self._scan_result(
            picking,
            action="product",
            message=self._done_message(target),
            selected_line_id=target.id,
        )

    def _scan_lot(self, picking, barcode, lot, location_id, line_id, pending_product_id):
        if lot:
            lines = picking.move_line_ids.filtered(
                lambda line: line.lot_id == lot and line.state not in ("done", "cancel")
            )
            if location_id:
                here = lines.filtered(lambda line: line.location_id.id == location_id)
                if here:
                    lines = here
            if lines:
                unpicked = lines.filtered(lambda line: not line.picked)
                target = self._take_qty((unpicked or lines)[0], 1.0)
                return self._scan_result(
                    picking,
                    action="lot",
                    message=self._done_message(target),
                    selected_line_id=target.id,
                )

        product = lot.product_id if lot else self.env["product.product"].browse(pending_product_id).exists()
        if not product:
            return self._scan_result(
                picking,
                action="warning",
                warning=True,
                message=_("ไม่พบล็อต %s", barcode),
            )
        if lot and pending_product_id and lot.product_id.id != pending_product_id:
            raise UserError(_("ล็อต %s ไม่ใช่ของสินค้าที่เลือก", lot.name))
        moves = picking.move_ids.filtered(
            lambda move: move.product_id == product and move.state not in ("done", "cancel")
        )
        if not moves and not picking.move_line_ids.filtered(lambda line: line.product_id == product):
            raise UserError(_("สินค้าของล็อตนี้ไม่อยู่ในใบงาน"))
        if not lot and not picking.picking_type_id.use_create_lots:
            raise UserError(_("ไม่พบล็อต %s ในระบบ", barcode))

        lines = self._candidate_lines(picking, product, location_id, line_id)
        bare = lines.filtered(lambda line: not line.picked and not line.lot_id and not line.lot_name)
        host = bare[:1] or lines.filtered(lambda line: not line.picked)[:1]
        if host:
            target = self._take_qty(host, 1.0, lot=lot, lot_name=False if lot else barcode)
        else:
            move = moves[:1] or lines[:1].move_id
            loc = self.env["stock.location"].browse(location_id) if location_id else move.location_id
            target = self._create_picked_line(
                move, loc, 1.0, move.product_uom, lot=lot, lot_name=False if lot else barcode,
            )
        return self._scan_result(
            picking,
            action="lot",
            message=self._done_message(target),
            selected_line_id=target.id,
        )

    def _done_message(self, line):
        code = line.product_id.default_code or line.product_id.name
        lot = line.lot_id.name or line.lot_name or ""
        label = "%s · %s" % (code, lot) if lot else code
        return _("%s  จำนวน %s %s", label, self._format_qty(line.quantity), line.product_uom_id.name or "")

    def _format_qty(self, qty):
        rounded = float_round(qty, precision_digits=2)
        if float_is_zero(rounded - int(rounded), precision_digits=2):
            return str(int(rounded))
        return ("%.2f" % rounded).rstrip("0").rstrip(".")

    def set_line_qty(self, line_id, qty):
        self._ensure_user()
        line = self.env["stock.move.line"].browse(line_id).exists()
        if not line:
            raise UserError(_("ไม่พบบรรทัด"))
        picking = line.picking_id
        if picking.state in ("done", "cancel"):
            raise UserError(_("ใบงานนี้ปิดแล้ว"))
        rounding = self._rounding(line.product_uom_id)
        qty = float_round(qty, precision_rounding=rounding)
        if float_compare(qty, 0.0, precision_rounding=rounding) < 0:
            raise UserError(_("จำนวนต้องไม่ติดลบ"))
        current = line.quantity if line.picked else 0.0
        selected = line.id
        if float_compare(qty, current, precision_rounding=rounding) > 0:
            target = self._take_qty(line, qty - current)
            selected = target.id
        elif float_compare(qty, current, precision_rounding=rounding) < 0 and line.picked:
            self._give_back(line, current - qty)
            selected = line.id if line.exists() else False
        return self._scan_result(
            picking,
            action="qty",
            message=_("ปรับจำนวนแล้ว"),
            selected_line_id=selected,
        )

    def _take_qty(self, line, qty, lot=None, lot_name=None):
        rounding = self._rounding(line.product_uom_id)
        qty = float_round(qty, precision_rounding=rounding)
        if float_compare(qty, 0.0, precision_rounding=rounding) <= 0:
            return line
        if line.picked:
            self._steal_qty(line, qty)
            if lot:
                line.lot_id = lot.id
            elif lot_name and not line.lot_id:
                line.lot_name = lot_name
            line.quantity = float_round(line.quantity + qty, precision_rounding=rounding)
            return line
        reserved = line.quantity
        if float_compare(qty, reserved, precision_rounding=rounding) < 0:
            line.quantity = float_round(reserved - qty, precision_rounding=rounding)
            return self._create_picked_line(
                line.move_id,
                line.location_id,
                qty,
                line.product_uom_id,
                lot=lot or line.lot_id,
                lot_name=lot_name or (False if (lot or line.lot_id) else line.lot_name),
                dest=line.location_dest_id,
                package=line.package_id,
            )
        if lot:
            line.lot_id = lot.id
            line.lot_name = False
        elif lot_name:
            line.lot_name = lot_name
        extra = float_round(qty - reserved, precision_rounding=rounding)
        line.quantity = qty
        line.picked = True
        if float_compare(extra, 0.0, precision_rounding=rounding) > 0:
            self._steal_qty(line, extra)
        return line

    def _steal_qty(self, picked_line, qty):
        rounding = self._rounding(picked_line.product_uom_id)
        remaining = qty
        siblings = picked_line.move_id.move_line_ids.filtered(
            lambda line: line.id != picked_line.id
            and not line.picked
            and line.product_id == picked_line.product_id
            and line.location_id == picked_line.location_id
            and line.lot_id == picked_line.lot_id
        )
        for sibling in siblings:
            if float_compare(remaining, 0.0, precision_rounding=rounding) <= 0:
                break
            take = min(sibling.quantity, remaining)
            sibling.quantity = float_round(sibling.quantity - take, precision_rounding=rounding)
            remaining = float_round(remaining - take, precision_rounding=rounding)
            if float_is_zero(sibling.quantity, precision_rounding=rounding):
                sibling.unlink()

    def _give_back(self, line, qty):
        rounding = self._rounding(line.product_uom_id)
        qty = float_round(qty, precision_rounding=rounding)
        sibling = line.move_id.move_line_ids.filtered(
            lambda other: other.id != line.id
            and not other.picked
            and other.product_id == line.product_id
            and other.location_id == line.location_id
            and other.lot_id == line.lot_id
        )[:1]
        if sibling:
            sibling.quantity = float_round(sibling.quantity + qty, precision_rounding=rounding)
        else:
            self.env["stock.move.line"].create(self._line_vals(
                line.move_id, line.location_id, qty, line.product_uom_id,
                lot=line.lot_id, lot_name=line.lot_name, dest=line.location_dest_id,
                package=line.package_id, picked=False,
            ))
        left = float_round(line.quantity - qty, precision_rounding=rounding)
        if float_is_zero(left, precision_rounding=rounding):
            line.unlink()
        else:
            line.quantity = left

    def _create_picked_line(self, move, location, qty, uom, lot=None, lot_name=None, dest=None, package=None):
        return self.env["stock.move.line"].create(self._line_vals(
            move, location, qty, uom, lot=lot, lot_name=lot_name, dest=dest, package=package, picked=True,
        ))

    def _line_vals(self, move, location, qty, uom, lot=None, lot_name=None, dest=None, package=None, picked=True):
        lot_id = lot.id if lot else False
        return {
            "picking_id": move.picking_id.id,
            "move_id": move.id,
            "product_id": move.product_id.id,
            "product_uom_id": uom.id,
            "location_id": location.id,
            "location_dest_id": (dest or move.location_dest_id).id,
            "package_id": package.id if package else False,
            "lot_id": lot_id,
            "lot_name": False if lot_id else (lot_name or False),
            "quantity": qty,
            "picked": picked,
        }

    def put_in_pack(self, picking_id):
        self._ensure_user()
        picking = self._picking(picking_id)
        result = picking.action_put_in_pack()
        if isinstance(result, dict):
            return self._scan_result(
                picking,
                action="warning",
                warning=True,
                message=_("เลือกสินค้าที่จะใส่แพ็กให้ครบ แล้วลองอีกครั้ง"),
            )
        return self._scan_result(picking, action="pack", message=_("ใส่แพ็กแล้ว"))

    def validate_picking(self, picking_id, backorder=None):
        self._ensure_user()
        picking = self._picking(picking_id)
        if picking.state in ("done", "cancel"):
            raise UserError(_("ใบงานนี้ปิดแล้ว"))
        ctx = dict(self.env.context, button_validate_picking_ids=picking.ids)
        if backorder is None:
            result = picking.with_context(**ctx).button_validate()
            if isinstance(result, dict):
                if result.get("res_model") == "stock.backorder.confirmation":
                    return {"need_backorder": True, "name": picking.name}
                return {
                    "blocked": True,
                    "message": result.get("name") or _("ต้องทำขั้นตอนนี้ต่อในระบบหลังบ้าน"),
                }
            return self._done_result(picking)
        wizard = self.env["stock.backorder.confirmation"].with_context(**ctx).create({
            "pick_ids": [(6, 0, picking.ids)],
            "backorder_confirmation_line_ids": [(0, 0, {
                "picking_id": picking.id,
                "to_backorder": bool(backorder),
            })],
        })
        if backorder:
            wizard.process()
        else:
            wizard.process_cancel_backorder()
        return self._done_result(picking)

    def _done_result(self, picking):
        picking.invalidate_recordset()
        names = picking.backorder_ids.mapped("name")
        return {
            "done": picking.state == "done",
            "name": picking.name,
            "state": picking.state,
            "backorders": names,
            "message": _("ยืนยัน %s แล้ว", picking.name) if picking.state == "done" else _("บันทึกแล้ว"),
        }

    def inventory_data(self, location_id=False):
        self._ensure_user()
        location = self.env["stock.location"].browse(location_id).exists() if location_id else self.env["stock.location"]
        if not location:
            return {"location": False, "lines": []}
        if location.usage not in ("internal", "transit"):
            raise UserError(_("ตำแหน่งนี้ไม่ใช่ที่เก็บภายใน"))
        return {
            "location": {"id": location.id, "name": location.display_name},
            "lines": self._inventory_lines(location),
        }

    def _inventory_lines(self, location):
        quants = self.env["stock.quant"].search([
            ("location_id", "=", location.id),
            "|", ("quantity", "!=", 0), ("inventory_quantity_set", "=", True),
        ], limit=200, order="product_id")
        rows = []
        for quant in quants:
            product = quant.product_id
            rows.append({
                "id": quant.id,
                "product_id": product.id,
                "default_code": product.default_code or "",
                "product_name": product.name,
                "tracking": product.tracking,
                "lot_name": quant.lot_id.name or "",
                "on_hand": quant.quantity,
                "counted": quant.inventory_quantity if quant.inventory_quantity_set else False,
                "counted_set": bool(quant.inventory_quantity_set),
                "uom": quant.product_uom_id.name or "",
            })
        rows.sort(key=lambda row: ((row["default_code"] or row["product_name"]), row["lot_name"], row["id"]))
        return rows

    def inventory_scan(self, barcode, location_id=False, pending_product_id=False):
        self._ensure_user()
        barcode = (barcode or "").strip()
        if not barcode:
            raise UserError(_("ไม่มีบาร์โค้ด"))
        location = self.env["stock.location"].search([
            ("barcode", "=", barcode),
            ("usage", "in", ("internal", "transit")),
        ], limit=1)
        if location:
            data = self.inventory_data(location.id)
            data.update({
                "action": "location",
                "message": _("ตำแหน่ง %s — สแกนสินค้า", location.display_name),
                "warning": False,
            })
            return data
        current = self.env["stock.location"].browse(location_id).exists() if location_id else self.env["stock.location"]
        if not current:
            return {"action": "warning", "warning": True, "message": _("สแกนตำแหน่งจัดเก็บก่อน"), "location": False, "lines": []}

        product = self._find_product(barcode)
        lot = self.env["stock.lot"].search([("name", "=", barcode)], limit=1) if not product else self.env["stock.lot"]
        if product:
            return self._inventory_add_product(current, product, lot=None)
        if not lot and pending_product_id:
            product = self.env["product.product"].browse(pending_product_id).exists()
            if product and product.tracking != "none":
                if not current:
                    raise UserError(_("สแกนตำแหน่งจัดเก็บก่อน"))
                existing = self.env["stock.lot"].search([
                    ("name", "=", barcode), ("product_id", "=", product.id),
                ], limit=1)
                return self._inventory_add_product(current, product, lot=existing, lot_name=barcode)
        if lot:
            return self._inventory_add_product(current, lot.product_id, lot=lot)
        return {
            "action": "warning",
            "warning": True,
            "message": _("ไม่พบสินค้า ล็อต หรือตำแหน่งของบาร์โค้ด %s", barcode),
            "location": {"id": current.id, "name": current.display_name},
            "lines": self._inventory_lines(current),
        }

    def _inventory_add_product(self, location, product, lot=None, lot_name=None):
        if product.tracking != "none" and not lot and not lot_name:
            quants = self.env["stock.quant"].search([
                ("location_id", "=", location.id),
                ("product_id", "=", product.id),
            ])
            lotted = quants.filtered(lambda quant: quant.lot_id)
            if len(lotted) == 1:
                lot = lotted.lot_id
            elif len(lotted) > 1:
                return {
                    "action": "need_lot",
                    "warning": False,
                    "message": _("สแกนหมายเลขล็อตของ %s", product.display_name),
                    "pending_product_id": product.id,
                    "location": {"id": location.id, "name": location.display_name},
                    "lines": self._inventory_lines(location),
                }
            else:
                return {
                    "action": "need_lot",
                    "warning": False,
                    "message": _("สแกนหมายเลขล็อตของ %s", product.display_name),
                    "pending_product_id": product.id,
                    "location": {"id": location.id, "name": location.display_name},
                    "lines": self._inventory_lines(location),
                }
        if lot_name and not lot:
            lot = self.env["stock.lot"].search([
                ("name", "=", lot_name), ("product_id", "=", product.id),
            ], limit=1)
            if not lot:
                lot = self.env["stock.lot"].create({
                    "name": lot_name,
                    "product_id": product.id,
                    "company_id": self.env.company.id,
                })
        domain = [
            ("product_id", "=", product.id),
            ("location_id", "=", location.id),
            ("lot_id", "=", lot.id if lot else False),
        ]
        quant = self.env["stock.quant"].search(domain, limit=1)
        if quant and quant.inventory_quantity_set:
            counted = quant.inventory_quantity + 1
        else:
            counted = 1
        if quant:
            quant.with_context(inventory_mode=True).write({
                "inventory_quantity": counted,
                "user_id": self.env.user.id,
            })
        else:
            quant = self.env["stock.quant"].with_context(inventory_mode=True).create({
                "product_id": product.id,
                "location_id": location.id,
                "lot_id": lot.id if lot else False,
                "inventory_quantity": counted,
                "user_id": self.env.user.id,
            })
        label = product.default_code or product.name
        if lot:
            label = "%s · %s" % (label, lot.name)
        return {
            "action": "product",
            "warning": False,
            "message": _("%s  นับได้ %s", label, self._format_qty(counted)),
            "selected_quant_id": quant.id,
            "location": {"id": location.id, "name": location.display_name},
            "lines": self._inventory_lines(location),
        }

    def inventory_set_qty(self, quant_id, qty):
        self._ensure_user()
        quant = self.env["stock.quant"].browse(quant_id).exists()
        if not quant:
            raise UserError(_("ไม่พบรายการสต็อก"))
        rounding = self._rounding(quant.product_uom_id)
        qty = float_round(qty, precision_rounding=rounding)
        if float_compare(qty, 0.0, precision_rounding=rounding) < 0:
            raise UserError(_("จำนวนต้องไม่ติดลบ"))
        quant.with_context(inventory_mode=True).write({
            "inventory_quantity": qty,
            "user_id": self.env.user.id,
        })
        return self.inventory_data(quant.location_id.id) | {
            "action": "qty",
            "message": _("ปรับจำนวนที่นับแล้ว"),
            "selected_quant_id": quant.id,
            "warning": False,
        }

    def inventory_apply(self, location_id, reason=None):
        self._ensure_user()
        location = self.env["stock.location"].browse(location_id).exists()
        if not location:
            raise UserError(_("สแกนตำแหน่งจัดเก็บก่อน"))
        quants = self.env["stock.quant"].search([
            ("location_id", "=", location.id),
            ("user_id", "=", self.env.user.id),
            ("inventory_quantity_set", "=", True),
        ])
        todo = quants.filtered(
            lambda quant: not float_is_zero(
                quant.inventory_diff_quantity,
                precision_rounding=self._rounding(quant.product_uom_id),
            )
        )
        if not todo:
            raise UserError(_("ไม่มียอดที่ต่างจากในระบบ"))
        result = todo.with_context(inventory_name=reason or _("นับจากแอปสแกน")).action_apply_inventory()
        if isinstance(result, dict):
            return {
                "blocked": True,
                "message": result.get("name") or _("ต้องยืนยันขั้นตอนนี้ในระบบหลังบ้าน"),
                "location": {"id": location.id, "name": location.display_name},
                "lines": self._inventory_lines(location),
            }
        return {
            "done": True,
            "message": _("ปรับยอด %s รายการแล้ว", len(todo)),
            "location": {"id": location.id, "name": location.display_name},
            "lines": self._inventory_lines(location),
        }
