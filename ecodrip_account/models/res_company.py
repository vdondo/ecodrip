# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_check_signature_image = fields.Binary('Signature')

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        if vals.get('account_check_signature_image'):
            for company in self:
                report = self.env.ref('%s' % company.account_check_printing_layout)
                if report.attachment:
                    checks = self.env['ir.attachment'].search(['&', ('company_id', '=', company.id), ('res_model', '=', 'account.payment')])
                    for check in checks:
                        record = self.env['account.payment'].browse(check.res_id)
                        check.sudo().unlink()
                        pdf = report.render_qweb_pdf(res_ids=[record.id])[0]
        return res
