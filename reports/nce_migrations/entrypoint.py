# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Ingram Micro
# All rights reserved.
from connect.client import R

from reports.utils import get_value, parameter_value, convert_to_datetime

HEADERS = [
    'Date of Migration',
    'Customer Domain',
    'Customer Tenant ID',
    'Customer Name',
    'Product Name',
    'Product ID',
    'SKU ID',
    'Number of Licenses',
    'Subscription ID',
    'Provider Name',
]

# This report is only valid for the NCE Commercial product in development and production environments.
NCE_COMMERCIAL_PRODUCTS = ['PRD-183-233-565', 'PRD-814-505-018']
MIGRATION_TYPE_VALUE = 'CSPNCEMIGRATION'


def generate(
        client=None,
        parameters=None,
        progress_callback=None,
        renderer_type=None,
        extra_cntext_callback=None,
):
    requests = _get_request_list(client, parameters)

    progress = 0
    total = requests.count()
    if renderer_type == 'csv':
        yield HEADERS
        progress += 1
        total += 1
        progress_callback(progress, total)

    for request in requests:
        # Filtering the parameter value directly as the client query returns timeout error
        params = get_value(request, ['asset', 'params'])
        migration_type = parameter_value('migration_type', params, None)
        if not migration_type:
            continue

        if renderer_type == 'json':
            yield {
                HEADERS[idx].replace(' ', '_').lower(): value
                for idx, value in
                enumerate(_process_line(request))
            }
        else:
            yield _process_line(request)
        progress += 1
        progress_callback(progress, total)


def _get_request_list(client, parameters):
    query = R()
    query &= R().type.eq('purchase')
    query &= R().status.eq('approved')
    query &= R().asset.product.id.oneof(NCE_COMMERCIAL_PRODUCTS)

    if parameters.get('connection_type') and parameters['connection_type']['all'] is False:
        query &= R().asset.connection.type.oneof(parameters['connection_type']['choices'])
    else:
        query &= R().asset.connection.type.oneof(['test', 'production'])

    if parameters.get('marketplaces') and parameters['marketplaces']['all'] is False:
        query &= R().marketplace.id.oneof(parameters['marketplaces']['choices'])

    query &= R().updated.ge(parameters['date']['after'])
    query &= R().updated.le(parameters['date']['before'])

    return client.requests.filter(query).order_by("created")


def _process_line(request):
    params = get_value(request, ['asset', 'params'])
    item = get_value(request, ['asset', 'items', 0])
    # Split MPN like ABC222C0LH1S:0001_P1Y:Annual
    mpn = item['mpn'].split('_')[0].split(':')

    migration_date = convert_to_datetime(request['effective_date'])
    customer_domain = parameter_value('microsoft_domain', params)
    customer_tenant = parameter_value('ms_customer_id', params)
    customer_name = get_value(request, ['asset', 'tiers', 'customer', 'name'])
    product_name = item['display_name']
    product_id = mpn[0]
    product_sku = mpn[1]
    num_licenses = item['quantity']
    subscription_id = parameter_value('subscription_id', params)
    provider_name = get_value(request, ['asset', 'connection', 'provider', 'name'])

    row = (
        migration_date,
        customer_domain,
        customer_tenant,
        customer_name,
        product_name,
        product_id,
        product_sku,
        num_licenses,
        subscription_id,
        provider_name,
    )
    return row
