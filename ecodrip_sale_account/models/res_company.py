# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    x_apr_account_id = fields.Many2one('account.account', string='APR Account')
    x_apr_payment_term_id = fields.Many2one('account.payment.term', string='APR Payment Term')
    x_apr_product_id = fields.Many2one('product.product', string='APR Product')