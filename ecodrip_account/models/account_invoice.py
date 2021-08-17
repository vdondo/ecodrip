# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    early_payment_discount = fields.Monetary(string='Early Payment Discount', currency_field='currency_id')
    early_payment_deadline = fields.Date(string='Early Payment Deadline')
