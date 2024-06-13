# Microsoft Audit Tool Report

This template allows you to create a report containing detailed information for Microsoft subscriptions with information from Connect and Microsoft to be able to compare it. 
Additional details on how to configure this report can be found in the Distributor Portal Configuration Guide

Please take into account the following:
- To avoid API throttling, the report will only allow one product to be selected

You can configure the report according to the following:
- List of products to be selected (Only one can be selected, else the report will fail)
- Request creation date range (The range must be less than 2 months, anything else will fail the report)
- List of statuses of subscriptions (active, suspended, terminated, terminating. default all)
- List of transaction types (test, production. Only one can be selected, else the report will fail)
- List of marketplaces (Only one can be selected, else the report will fail)