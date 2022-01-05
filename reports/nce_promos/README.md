# New Commerce Promotions Report

This template allows you to create a report containing the NCE commercial subscriptions to which an NCE Promotional
discount was applied by Microsoft. You can create a report for a particular date, Microsoft NCE product, marketplace or
environment. For each subscription, the report will display the promotional discount percentage that was applied.
Additional details on how to configure this report can be found in the Distributor Portal Configuration Guide. Please
take into account the following:

* The report will display the list of subscriptions in approved purchase and change requests that have an NCE promotion applied
  in a particular date range.
* In the case of change requests, the report includes an “item seats” column that contains changes in the seat quantity
  that require billing adjustments. For example, if “item seats” is “+2” it means that 2 seats were added to which the
  NCE Promotion discount was applied by Microsoft. If “item seats” includes a negative number, it means that a seat
  downsize has been done.
* In the case of a plan switch, the report will not include information about NCE discounts, as such discounts will not
  be applicable to the new plan.
* The report will not provide information on renewal events. The report contains an “end date” column with the date on
  which a promotion ends for new sales orders or renewal events. This means that if a subscription is renewed before the
  promotion end date, the promotion will be applied for the whole term. Otherwise, it will be renewed with the regular
  price.

You can configure the report according to the following:

* Request creation date range.
* List of transaction types (test, production).
* List of marketplaces.

