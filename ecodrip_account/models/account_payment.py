# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.misc import formatLang


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _check_build_page_info(self, i, p):
        page = super(AccountPayment, self)._check_build_page_info(i, p)
        page.update(company=self.company_id)
        return page

    def _check_make_stub_line(self, invoice):
        stub_line = super(AccountPayment, self)._check_make_stub_line(invoice)
        if invoice.state == 'paid' and invoice.type == 'in_invoice':
            last_payment_date = max([payment_date for payment_date in invoice.payment_ids.mapped('payment_date') if payment_date], default=None)
            if last_payment_date and invoice.early_payment_deadline and self.payment_date == last_payment_date and self.payment_date <= invoice.early_payment_deadline:
                discount = invoice.early_payment_discount
            else:
                discount = 0
            invoice_payment_reconcile = invoice.move_id.line_ids.mapped('matched_debit_ids').filtered(lambda r: r.debit_move_id in self.move_line_ids)

            if self.currency_id != self.journal_id.company_id.currency_id:
                payment = abs(sum(invoice_payment_reconcile.mapped('amount_currency'))) - discount
            else:
                payment = abs(sum(invoice_payment_reconcile.mapped('amount'))) - discount
            amount_paid = formatLang(self.env, payment, currency_obj=invoice.currency_id)
            stub_line.update(discount=discount, amount_paid=amount_paid)
        else:
            stub_line.update(discount=0)
        stub_line.update(memo=invoice.reference)
        return stub_line
