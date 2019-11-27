# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import datetime, dateutil

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # migrate some of the fields from data files here
    x_invoice_id = fields.Many2one('account.invoice', ondelete='set null', string='Main Invoice', readonly=True)
    x_apr_ids = fields.One2many('account.invoice', 'x_invoice_id', string='Related APRs', readonly=True)
    x_apr_count = fields.Integer('# of APRs', readonly=True, compute="_compute_apr_count")
    last_apr_id = fields.Many2one('account.invoice', ondelete='set null', string='Last APR', readonly=True, compute='_compute_last_apr_id', store=True)
    x_last_apr_date_due = fields.Date('Last APR Date Due', related='last_apr_id.date_due', store=True, readonly=True, compute='_compute_last_apr_id')

    def _compute_apr_count(self):
        for inv in self:
            inv.x_apr_count = len(inv.x_apr_ids)
    
    def action_open_apr_tree_view(self):
        # depending on which user group this current user is
        # let's open different objects
        self.ensure_one()
        action_data = self.env.ref('account.action_invoice_tree1').read()[0]
        
        action_data.update({
            'domain': [('x_invoice_id', '=', self.id)],
            'context': {'company_id': self.company_id.id,
                        'type':'out_invoice',
                        'journal_type': 'sale'}
        })

        return action_data
    
    @api.depends('x_apr_ids', 'x_apr_ids.state', 'x_apr_ids.date_due')
    def _compute_last_apr_id(self):
        for record in self:
            if not record.x_invoice_id:
                apr_ids = record.x_apr_ids.filtered(lambda apr: apr.state != 'cancel' and apr.date_due)
                # if there is no last apr, then our record is the last apr
                record.last_apr_id = apr_ids.sorted(key=lambda apr: apr.date_due)[-1].id if apr_ids else record.id  
            else:
                record.last_apr_id = False
            if record.last_apr_id:
                record.x_last_apr_date_due = record.last_apr_id.date_due
            else:
                record.x_last_apr_date_due = False

    # https://stackoverflow.com/questions/42950/get-last-day-of-the-month-in-python
    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)

    def action_generate_apr(self, date=None, batch_size=50):
        if not date:
            date = datetime.date.today()
            
        invoices = self.env['account.invoice'].search([('type', '=', 'out_invoice'), ('state', '=', 'open'), ('x_invoice_id', '=', False), ('x_last_apr_date_due', '!=', False), ('x_last_apr_date_due', '<', date)], limit=batch_size)

        invoices.generate_apr(date=date, safe=True)
    
    def generate_apr(self, date=None, safe=False):
        if not date:
            date = datetime.date.today()

        invoices = self
        # do a filter when it is not safe
        if not safe:
            invoices = self.filtered(lambda inv:inv.type == 'out_invoice' and not inv.x_invoice_id and inv.state == 'open' and inv.x_last_apr_date_due and inv.x_last_apr_date_due < date)
            
        if not invoices:
            raise ValidationError(_('No open, past due invoices or aprs.'))

        for inv in invoices:
            # since customer is using multi company, we need to make sure apr related settings exist in current invoice company
            if not inv.company_id.x_apr_payment_term_id or not inv.company_id.x_apr_product_id or (not inv.company_id.x_apr_account_id and not inv.company_id.x_apr_product_id.property_account_income_id):
                raise ValidationError(_('APR product or payment term or account is not set for company: {}.'.format(inv.company_id.display_name)))
    
            # find the last active invoice, it could be the invoice itself or the last apr of this invoice
            last_apr_id = inv.last_apr_id or inv

            # we want to create all missing APRs, based on the date this action is being run
            while last_apr_id.date_due < date:
                # create a new apr with the invoice_date setting to the end of the same month of the current due date
                new_apr_id = self.env['account.invoice'].create({
                    'company_id': inv.company_id.id,
                    'partner_id': inv.partner_id.id,
                    'type': 'out_invoice',
                    'x_invoice_id': inv.id,
                    'payment_term_id': inv.company_id.x_apr_payment_term_id.id,
                    'date_invoice': self.last_day_of_month(last_apr_id.date_due)})

                # explicitly calling payment_term and date_invoice onchange here to calculate date_due
                new_apr_id._onchange_payment_term_date_invoice()
        
                # if this apr is the first apr of the invoice, we know we need to subtract the first n days from the number of days
                first_day = last_apr_id.date_due if last_apr_id == inv else last_apr_id.date_invoice  # technical first day
                number_of_days = (new_apr_id.date_invoice - first_day).days

                # this is to show to human since the real first day is one day before
                display_first_day = first_day + dateutil.relativedelta.relativedelta(days=+1)  
        
                new_apr_line_id = self.env['account.invoice.line'].create({
                    'invoice_id': new_apr_id.id,
                    'product_id': inv.company_id.x_apr_product_id.id,
                    'price_unit': inv.residual * (number_of_days/365.0*0.18),
                    'quantity': 1.00,
                    'name': inv.company_id.x_apr_product_id.description_sale or 'Finance Charges',
                    'account_id': inv.company_id.x_apr_product_id.property_account_income_id.id or inv.company_id.x_apr_account_id.id})

                # validate invoice
                #new_apr_id.action_invoice_open()
                new_apr_id.action_invoice_draft()
                # change the invoice move's name to display APR
                new_apr_id.move_id.sudo().write({'name': '{}-{}/APR/{:03d}'.format(new_apr_id.move_id.name, inv.number, len(inv.x_apr_ids))})
                # loop on
                last_apr_id = new_apr_id
