# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    account_check_signature_image = fields.Binary(string='Signature', related='company_id.account_check_signature_image', readonly=False)
