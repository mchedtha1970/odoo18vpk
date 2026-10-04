from pathlib import Path

from odoo import http
from odoo.http import request
from odoo.tools.misc import file_path


class VpkBarcodeController(http.Controller):

    def _service(self):
        return request.env["vpk.barcode.service"]

    @http.route("/vpk/barcode", type="http", auth="user", website=False)
    def app_index(self, **kwargs):
        index = file_path("vpk_mobile_barcode/static/app/index.html", filter_ext=(".html",))
        return request.make_response(
            Path(index).read_bytes(),
            headers=[("Content-Type", "text/html; charset=utf-8")],
        )

    @http.route("/vpk_barcode/menu", type="json", auth="user")
    def menu(self):
        return self._service().menu_data()

    @http.route("/vpk_barcode/scan_menu", type="json", auth="user")
    def scan_menu(self, barcode):
        return self._service().scan_menu(barcode)

    @http.route("/vpk_barcode/pickings", type="json", auth="user")
    def pickings(self, picking_type_id):
        return self._service().list_pickings(picking_type_id)

    @http.route("/vpk_barcode/picking", type="json", auth="user")
    def picking(self, picking_id):
        return self._service().get_picking(picking_id)

    @http.route("/vpk_barcode/scan", type="json", auth="user")
    def scan(self, picking_id, barcode, location_id=False, line_id=False, pending_product_id=False):
        return self._service().scan_picking(
            picking_id, barcode,
            location_id=location_id or False,
            line_id=line_id or False,
            pending_product_id=pending_product_id or False,
        )

    @http.route("/vpk_barcode/set_qty", type="json", auth="user")
    def set_qty(self, line_id, qty):
        return self._service().set_line_qty(line_id, qty)

    @http.route("/vpk_barcode/validate", type="json", auth="user")
    def validate(self, picking_id, backorder=None):
        return self._service().validate_picking(picking_id, backorder=backorder)

    @http.route("/vpk_barcode/put_in_pack", type="json", auth="user")
    def put_in_pack(self, picking_id):
        return self._service().put_in_pack(picking_id)

    @http.route("/vpk_barcode/inventory", type="json", auth="user")
    def inventory(self, location_id=False):
        return self._service().inventory_data(location_id or False)

    @http.route("/vpk_barcode/inventory_scan", type="json", auth="user")
    def inventory_scan(self, barcode, location_id=False, pending_product_id=False):
        return self._service().inventory_scan(
            barcode,
            location_id=location_id or False,
            pending_product_id=pending_product_id or False,
        )

    @http.route("/vpk_barcode/inventory_set", type="json", auth="user")
    def inventory_set(self, quant_id, qty):
        return self._service().inventory_set_qty(quant_id, qty)

    @http.route("/vpk_barcode/inventory_apply", type="json", auth="user")
    def inventory_apply(self, location_id, reason=None):
        return self._service().inventory_apply(location_id, reason=reason)
