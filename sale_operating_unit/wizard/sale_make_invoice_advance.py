from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoices(self, sale_orders):
        res = super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders)
        if self.advance_payment_method != "delivered":
            res.operating_unit_id = sale_orders.operating_unit_id.id
        return res
