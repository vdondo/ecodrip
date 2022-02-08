# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools.misc import formatLang, format_date

INV_LINES_PER_STUB = 9

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _check_build_page_info(self, i, p):
        page = super(AccountPayment, self)._check_build_page_info(i, p)
        page.update(company=self.company_id)
        return page

    def _check_make_stub_pages(self):
        """ The stub is the summary of paid invoices. It may spill on several pages, in which case only the check on
            first page is valid. This function returns a list of stub lines per page.
        """
        self.ensure_one()

        def prepare_vals(invoice, partials):
            number = ' - '.join([invoice.name, invoice.ref] if invoice.ref else [invoice.name])
            stub_line = {}

            if invoice.is_outbound():
                invoice_sign = 1
                partial_field = 'debit_amount_currency'
            else:
                invoice_sign = -1
                partial_field = 'credit_amount_currency'

            if invoice.currency_id.is_zero(invoice.amount_residual):
                amount_residual_str = '-'
            else:
                amount_residual_str = formatLang(self.env, invoice_sign * invoice.amount_residual, currency_obj=invoice.currency_id)

            if invoice.payment_state == 'in_payment' and invoice.move_type == 'in_invoice':
                last_payment_date = max([date for date in self.env['account.payment'].search([('reconciled_bill_ids', 'in', invoice.ids)]).mapped('date') if date], default=None)
                if last_payment_date and invoice.early_payment_deadline and self.date == last_payment_date and self.date <= invoice.early_payment_deadline:
                    discount = invoice.early_payment_discount
                else:
                    discount = 0
                invoice_payment_reconcile = invoice.line_ids.mapped('matched_debit_ids').filtered(lambda r: r.debit_move_id in self.line_ids)

                if self.currency_id != self.journal_id.company_id.currency_id:
                    payment = abs(sum(invoice_payment_reconcile.mapped('amount_currency'))) - discount
                else:
                    payment = abs(sum(invoice_payment_reconcile.mapped('amount'))) - discount
                amount_paid = formatLang(self.env, payment, currency_obj=invoice.currency_id)
                stub_line.update(discount=discount, amount_paid=amount_paid)
            else:
                stub_line.update(discount=0, amount_paid=formatLang(self.env, invoice_sign * sum(partials.mapped(partial_field)), currency_obj=self.currency_id))
            stub_line.update(memo=invoice.ref)

            stub_line.update({
                'due_date': format_date(self.env, invoice.invoice_date_due),
                'number': number,
                'amount_total': formatLang(self.env, invoice_sign * invoice.amount_total, currency_obj=invoice.currency_id),
                'amount_residual': amount_residual_str,
                'currency': invoice.currency_id,
            })
            return stub_line

        # Decode the reconciliation to keep only invoices.
        term_lines = self.line_ids.filtered(lambda line: line.account_id.internal_type in ('receivable', 'payable'))
        invoices = (term_lines.matched_debit_ids.debit_move_id.move_id + term_lines.matched_credit_ids.credit_move_id.move_id)\
            .filtered(lambda x: x.is_outbound())
        invoices = invoices.sorted(lambda x: x.invoice_date_due or x.date)

        # Group partials by invoices.
        invoice_map = {invoice: self.env['account.partial.reconcile'] for invoice in invoices}
        for partial in term_lines.matched_debit_ids:
            invoice = partial.debit_move_id.move_id
            if invoice in invoice_map:
                invoice_map[invoice] |= partial
        for partial in term_lines.matched_credit_ids:
            invoice = partial.credit_move_id.move_id
            if invoice in invoice_map:
                invoice_map[invoice] |= partial

        # Prepare stub_lines.
        if 'out_refund' in invoices.mapped('move_type'):
            stub_lines = [{'header': True, 'name': "Bills"}]
            stub_lines += [prepare_vals(invoice, partials)
                           for invoice, partials in invoice_map.items()
                           if invoice.move_type == 'in_invoice']
            stub_lines += [{'header': True, 'name': "Refunds"}]
            stub_lines += [prepare_vals(invoice, partials)
                           for invoice, partials in invoice_map.items()
                           if invoice.move_type == 'out_refund']
        else:
            stub_lines = [prepare_vals(invoice, partials)
                          for invoice, partials in invoice_map.items()
                          if invoice.move_type == 'in_invoice']

        # Crop the stub lines or split them on multiple pages
        if not self.company_id.account_check_printing_multi_stub:
            # If we need to crop the stub, leave place for an ellipsis line
            num_stub_lines = len(stub_lines) > INV_LINES_PER_STUB and INV_LINES_PER_STUB - 1 or INV_LINES_PER_STUB
            stub_pages = [stub_lines[:num_stub_lines]]
        else:
            stub_pages = []
            i = 0
            while i < len(stub_lines):
                # Make sure we don't start the credit section at the end of a page
                if len(stub_lines) >= i + INV_LINES_PER_STUB and stub_lines[i + INV_LINES_PER_STUB - 1].get('header'):
                    num_stub_lines = INV_LINES_PER_STUB - 1 or INV_LINES_PER_STUB
                else:
                    num_stub_lines = INV_LINES_PER_STUB
                stub_pages.append(stub_lines[i:i + num_stub_lines])
                i += num_stub_lines

        return stub_pages

    # def _check_make_stub_line(self, invoice):
    #     stub_line = super(AccountPayment, self)._check_make_stub_line(invoice)
    #     print("\n")
    #     print(stub_line)
    #     if invoice.payment_state == 'in_payment' and invoice.move_type == 'in_invoice':
    #         last_payment_date = max([payment_date for payment_date in invoice.payment_ids.mapped('payment_date') if payment_date], default=None)
    #         if last_payment_date and invoice.early_payment_deadline and self.payment_date == last_payment_date and self.payment_date <= invoice.early_payment_deadline:
    #             discount = invoice.early_payment_discount
    #         else:
    #             discount = 0
    #         invoice_payment_reconcile = invoice.line_ids.mapped('matched_debit_ids').filtered(lambda r: r.debit_move_id in self.move_line_ids)

    #         if self.currency_id != self.journal_id.company_id.currency_id:
    #             payment = abs(sum(invoice_payment_reconcile.mapped('amount_currency'))) - discount
    #         else:
    #             payment = abs(sum(invoice_payment_reconcile.mapped('amount'))) - discount
    #         amount_paid = formatLang(self.env, payment, currency_obj=invoice.currency_id)
    #         stub_line.update(discount=discount, amount_paid=amount_paid)
    #     else:
    #         stub_line.update(discount=0)
    #     stub_line.update(memo=invoice.reference)
    #     print(stub_line)
    #     print("\n")
    #     return stub_line
