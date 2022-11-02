from odoo.upgrade import util

def migrate(cr, version):
    util.uninstall_module(cr, 'account_banking_reconciliation')
    util.uninstall_module(cr, 'account_reconciliation_widget_partial')
    util.uninstall_module(cr, 'sale_order_price_recalculation')
