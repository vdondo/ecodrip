# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import datetime, dateutil

class AccountMove(models.Model):
    _inherit = 'account.move'

    # migrate some of the fields from data files here
    x_invoice_id = fields.Many2one('account.move', ondelete='set null', string='Main Invoice', readonly=True)
    x_apr_ids = fields.One2many('account.move', 'x_invoice_id', string='Related APRs', readonly=True)
    x_apr_count = fields.Integer('# of APRs', readonly=True, compute="_compute_apr_count")
    last_apr_id = fields.Many2one('account.move', ondelete='set null', string='Last APR', readonly=True, compute='_compute_last_apr_id', store=True)
    x_last_apr_date_due = fields.Date('Last APR Date Due', related='last_apr_id.invoice_date_due', store=True, readonly=True, compute='_compute_last_apr_id')

    def _get_last_sequence(self, relaxed=False):
        """Retrieve the previous sequence.

        This is done by taking the number with the greatest alphabetical value within
        the domain of _get_last_sequence_domain. This means that the prefix has a
        huge importance.
        For instance, if you have INV/2019/0001 and INV/2019/0002, when you rename the
        last one to FACT/2019/0001, one might expect the next number to be
        FACT/2019/0002 but it will be INV/2019/0002 (again) because INV > FACT.
        Therefore, changing the prefix might not be convenient during a period, and
        would only work when the numbering makes a new start (domain returns by
        _get_last_sequence_domain is [], i.e: a new year).

        :param field_name: the field that contains the sequence.
        :param relaxed: this should be set to True when a previous request didn't find
            something without. This allows to find a pattern from a previous period, and
            try to adapt it for the new period.

        :return: the string of the previous sequence or None if there wasn't any.
        """
        self.ensure_one()
        if self._sequence_field not in self._fields or not self._fields[self._sequence_field].store:
            raise ValidationError(_('%s is not a stored field', self._sequence_field))
        where_string, param = self._get_last_sequence_domain(relaxed)
        if self.id or self.id.origin:
            where_string += " AND id != %(id)s "
            param['id'] = self.id or self.id.origin

        # CUSTOM CODE
        # add to where string to ignore apr invoices
        where_string += "AND x_invoice_id is null"

        query = """
            UPDATE {table} SET write_date = write_date WHERE id = (
                SELECT id FROM {table}
                {where_string}
                AND sequence_prefix = (SELECT sequence_prefix FROM {table} {where_string} ORDER BY id DESC LIMIT 1)
                ORDER BY sequence_number DESC
                LIMIT 1
            )
            RETURNING {field};
        """.format(
            table=self._table,
            where_string=where_string,
            field=self._sequence_field,
        )

        self.flush([self._sequence_field, 'sequence_number', 'sequence_prefix'])
        self.env.cr.execute(query, param)
        return (self.env.cr.fetchone() or [None])[0]

    def _compute_apr_count(self):
        for inv in self:
            inv.x_apr_count = len(inv.x_apr_ids)
    
    def action_open_apr_tree_view(self):
        # depending on which user group this current user is
        # let's open different objects
        self.ensure_one()
        action_data = self.env.ref('account.action_move_out_invoice_type').read()[0]
        
        action_data.update({
            'domain': [('x_invoice_id', '=', self.id)],
            'context': {'company_id': self.company_id.id,
                        'move_type':'out_invoice',
                        'journal_type': 'sale'}
        })

        return action_data
    
    @api.depends('x_apr_ids', 'x_apr_ids.state', 'x_apr_ids.invoice_date_due')
    def _compute_last_apr_id(self):
        for record in self:
            if not record.x_invoice_id:
                apr_ids = record.x_apr_ids.filtered(lambda apr: apr.state != 'cancel' and apr.invoice_date_due)
                # if there is no last apr, then our record is the last apr
                record.last_apr_id = apr_ids.sorted(key=lambda apr: apr.invoice_date_due)[-1].id if apr_ids else record.id  
            else:
                record.last_apr_id = False
            if record.last_apr_id:
                record.x_last_apr_date_due = record.last_apr_id.invoice_date_due
            else:
                record.x_last_apr_date_due = False

    # https://stackoverflow.com/questions/42950/get-last-day-of-the-month-in-python
    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)

    def action_generate_apr(self, date=None, batch_size=50):
        if not date:
            date = datetime.date.today()
            
        invoices = self.env['account.move'].search([('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'in_payment', 'partial']), ('x_invoice_id', '=', False), ('x_last_apr_date_due', '!=', False), ('x_last_apr_date_due', '<', date)], limit=batch_size)

        invoices.generate_apr(date=date, safe=True)
    
    def generate_apr(self, date=None, safe=False):
        if not date:
            date = datetime.date.today()

        invoices = self
        # do a filter when it is not safe
        if not safe:
            invoices = self.filtered(lambda inv:inv.move_type == 'out_invoice' and not inv.x_invoice_id and inv.payment_state in ['not_paid', 'in_payment', 'partial'] and inv.x_last_apr_date_due and inv.x_last_apr_date_due < date)
            
        if not invoices:
            raise ValidationError(_('No open, past due invoices or aprs.'))

        for inv in invoices:
            # since customer is using multi company, we need to make sure apr related settings exist in current invoice company
            if not inv.company_id.x_apr_payment_term_id or not inv.company_id.x_apr_product_id or (not inv.company_id.x_apr_account_id and not inv.company_id.x_apr_product_id.property_account_income_id):
                raise ValidationError(_('APR product or payment term or account is not set for company: {}.'.format(inv.company_id.display_name)))
    
            # find the last active invoice, it could be the invoice itself or the last apr of this invoice
            last_apr_id = inv.last_apr_id or inv

            # we want to create all missing APRs, based on the date this action is being run
            while last_apr_id.invoice_date_due < date:
                # create a new apr with the invoice_date setting to the end of the same month of the current due date
                first_day = last_apr_id.invoice_date_due if last_apr_id == inv else last_apr_id.invoice_date  # technical first day

                new_apr_id = self.env['account.move'].create({
                    'company_id': inv.company_id.id,
                    'partner_id': inv.partner_id.id,
                    'move_type': 'out_invoice',
                    'x_invoice_id': inv.id,
                    'invoice_payment_term_id': inv.company_id.x_apr_payment_term_id.id,
                    'invoice_date': self.last_day_of_month(last_apr_id.invoice_date_due),
                    'invoice_line_ids': [(0,0,{
                    'product_id': inv.company_id.x_apr_product_id.id,
                    'price_unit': inv.amount_residual * ((self.last_day_of_month(last_apr_id.invoice_date_due) - first_day).days/365.0*0.18),
                    'quantity': 1.00,
                    'name': inv.company_id.x_apr_product_id.description_sale or 'Finance Charges',
                    'account_id': inv.company_id.x_apr_product_id.property_account_income_id.id or inv.company_id.x_apr_account_id.id
                    })],
                })

                # this is to show to human since the real first day is one day before
                # display_first_day = first_day + dateutil.relativedelta.relativedelta(days=+1)  

                # validate invoice
                new_apr_id.action_post()
                # change the invoice move's name to display APR
                new_apr_id.sudo().write({'name': '{}-{}/APR/{:03d}'.format(new_apr_id.name, inv.name, len(inv.x_apr_ids))})
                # loop on
                last_apr_id = new_apr_id
