# © 2019 Eficent Business and IT Consulting Services S.L.
# - Jordi Ballester Alomar
# © 2019 Serpent Consulting Services Pvt. Ltd. - Sudhir Arya
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import _, exceptions, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _generate_valuation_lines_data(
        self,
        partner_id,
        qty,
        debit_value,
        credit_value,
        debit_account_id,
        credit_account_id,
        svl_id,
        description,
    ):
        res = super(StockMove, self)._generate_valuation_lines_data(
            partner_id,
            qty,
            debit_value,
            credit_value,
            debit_account_id,
            credit_account_id,
            svl_id,
            description,
        )
        if res:
            debit_line_vals = res.get("debit_line_vals")
            credit_line_vals = res.get("credit_line_vals")
            price_diff_line_vals = res.get("price_diff_line_vals", {})

            if (
                self.operating_unit_id
                and self.operating_unit_dest_id
                and self.operating_unit_id != self.operating_unit_dest_id
                and debit_line_vals["account_id"] != credit_line_vals["account_id"]
            ):
                raise exceptions.UserError(
                    _(
                        "You cannot create stock moves involving separate source"
                        " and destination accounts related to different "
                        "operating units."
                    )
                )

            if not self.operating_unit_dest_id and not self.operating_unit_id:
                ou_id = (
                    self.picking_id.picking_type_id.warehouse_id.operating_unit_id.id
                )
            else:
                ou_id = False

            debit_line_vals["operating_unit_id"] = (
                ou_id or self.operating_unit_dest_id.id or self.operating_unit_id.id
            )
            credit_line_vals["operating_unit_id"] = (
                ou_id or self.operating_unit_id.id or self.operating_unit_dest_id.id
            )
            rslt = {
                "credit_line_vals": credit_line_vals,
                "debit_line_vals": debit_line_vals,
            }
            if price_diff_line_vals:
                price_diff_line_vals["operating_unit_id"] = (
                    ou_id or self.operating_unit_id.id or self.operating_unit_dest_id.id
                )
                rslt["price_diff_line_vals"] = price_diff_line_vals
            return rslt
        return res


    def _action_done(self, cancel_backorder=False):
        """
        Generate accounting moves if the product being moved is subject
        to real_time valuation tracking,
        and the source or destination location are
        a transit location or is outside of the company or the source or
        destination locations belong to different operating units.
        """
        res = super(StockMove, self)._action_done(cancel_backorder)
        for move in self:
            if move.product_id.valuation == "real_time":
                print ("move_line",move)

        for move in self:
            print ("move",move)

            if move.product_id.valuation == "real_time":
                # Inter-operating unit moves do not accept to
                # from/to non-internal location
                if (
                    move.location_id.company_id
                    and move.location_id.company_id == move.location_dest_id.company_id
                    and move.operating_unit_id != move.operating_unit_dest_id
                ):
                    (
                        journal_id,
                        acc_src,
                        acc_dest,
                        acc_valuation,
                    ) = move._get_accounting_data_for_valuation()

                    # search from svl_id
                    svl_id = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id),('product_id', '=', move.product_id.id)])
 

                    move_lines = move._prepare_account_move_line(
                        move.product_qty,
                        move.product_id.standard_price,
                        acc_valuation,
                        acc_valuation,
                        svl_id,
                        _("%s - OU Move") % move.product_id.display_name,
                    )

                    
                    print ("move_lines",move_lines)
                    #move_lines.update({'operating_unit_id':move.operating_unit_dest_id})
                    
                    ## update move_lines
                    new_move_lines = []
                    for mvline in move_lines:
                        #print("mvline[2]",mvline[2])
                        new_line = mvline[2]
                        new_line["balance"] = new_line["balance"] * new_line["quantity"]
                        print ("new_line[balance]",new_line["balance"])
                        if new_line["balance"] <0 :
                            new_line["operating_unit_id"] = move.operating_unit_id.id
                        if new_line["balance"] > 0 :
                            new_line["operating_unit_id"] = move.operating_unit_dest_id.id
                        
                        new_move_lines.append((0, 0, new_line))
                    
                    print ("new_move_lines",new_move_lines)

                    am = (
                        self.env["account.move"]
                        .with_context(
                            company_id=move.company_id.id,
                        )
                        .create(
                            {
                                "journal_id": journal_id,
                                "line_ids": move_lines,
                                "company_id": move.company_id.id,
                                "ref": move.picking_id and move.picking_id.name,
                                "stock_move_id": move.id,
                            }
                        )
                        .with_company(move.location_id.company_id.id)
                    )
                    am.action_post()
        #print ("",ghb)
        return res


    # def _action_done(self, cancel_backorder=False):
    #     """
    #     Generate accounting moves if the product being moved is subject
    #     to real_time valuation tracking,
    #     and the source or destination location are
    #     a transit location or is outside of the company or the source or
    #     destination locations belong to different operating units.
    #     """
    #     res = super(StockMove, self)._action_done(cancel_backorder)
    #     for move in self:

    #         if move.product_id.valuation == "real_time":
    #             # Inter-operating unit moves do not accept to
    #             # from/to non-internal location
    #             if (
    #                 move.location_id.company_id
    #                 and move.location_id.company_id == move.location_dest_id.company_id
    #                 and move.operating_unit_id != move.operating_unit_dest_id
    #             ):
    #                 (
    #                     journal_id,
    #                     acc_src,
    #                     acc_dest,
    #                     acc_valuation,
    #                 ) = move._get_accounting_data_for_valuation()

    #                 move_lines = move._prepare_account_move_line(
    #                     move.product_qty,
    #                     move.product_id.standard_price,
    #                     acc_valuation,
    #                     acc_valuation,
    #                     _("%s - OU Move") % move.product_id.display_name,
    #                 )
    #                 am = (
    #                     self.env["account.move"]
    #                     .with_context(
    #                         company_id=move.company_id.id,
    #                     )
    #                     .create(
    #                         {
    #                             "journal_id": journal_id,
    #                             "line_ids": move_lines,
    #                             "company_id": move.company_id.id,
    #                             "ref": move.picking_id and move.picking_id.name,
    #                             "stock_move_id": move.id,
    #                         }
    #                     )
    #                     .with_company(move.location_id.company_id.id)
    #                 )
    #                 am.action_post()
    #         return res
