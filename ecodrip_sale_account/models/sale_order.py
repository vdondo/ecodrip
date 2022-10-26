from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import datetime, dateutil


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def action_confirm(self):
        for sol in self.order_line:
            if (sol.product_id.standard_price > sol.price_unit) and self.env.ref('sales_team.group_sale_manager') not in self.env.user.groups_id:
                raise UserError('Only manager can validate this SO since at least one product is being sold with a price that is lower than its cost.')
        result = super(SaleOrder, self).action_confirm()
        return result
        