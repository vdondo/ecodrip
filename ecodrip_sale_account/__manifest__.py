# -*- coding: utf-8 -*-
{
    'name': 'Eco-Drip: Custom Sale Account',
    'summary': 'Eco-Drip: Blocking message for sales margins / Calculate APR',
    'description':"""
TASK ID: 1825668
Dev Request 1
The warning would be based on the cost field on the sale order line. The warning should appear when the unit price value is lower than the cost value on the sale order line
1. Blocking message when confimring sales orders if product unit price is lower than cost price on sale.order line
2. Allow sale order to remain in draft status, if cost price is higher than unit price
3. User can edit sale.order line to update the unit price and then confirm the sale order
4. User Group Sale/Manager only can confirm the sale order if the unit price is lower than the cost price 
Dev Request 2
1. Create 18% annual APR charge to invoices with outstanding balances.
2. The calculation for APR is based on 18% per year eg: ((31/365 x 0.18) x 1,532.27
3. The first APR charge is applied on the following month based on the date of the invoice.
a. At the end of the following month the APR charge is applied to the invoice balance -10 to account for the invoice due date (10th of every month).
b. The first charge is a prorated amount
eg: Invoice total $67.27 due date April 10th – APR incurs as of May 31st . Formula  ((31-10)/365) x 0.18) x 67.27
4. APR will apply to any outstanding amount on each customer invoice every month until they pay off the total balance
5. APR charges should only be generated once per month per invoice with outstanding balance.
6. Create new invoice with APR charges.
a. Use APR product in database __export__.product_product_986_7688880a APR to create invoice with appropriate amount.
b. Product has been configured with correct income account.
7. Generated APR invoice should be automatically validated.
8. Create button that will run the action to generate APR charges on outstanding invoices and created new invoices.
a. Client will manually click on the button to run the action.
b. Button should appear in “Customer” menu in Accounting application See attached PDF
9. The invoices should appear on the Partner Ledger report for each client. 
10. The action should ignore any lock dates set for Journal entries""",
    'license': 'OEEL-1',
    'author': 'Odoo Inc',
    'version': '0.1',
    'depends': ['sale_management', 'account_accountant', 'sale_stock', 'base_automation'],
    'data': [
        'data/data.xml',
        'data/actions.xml',
        'views/res_company_views.xml',
        'views/account_move_views.xml'
    ],
}
