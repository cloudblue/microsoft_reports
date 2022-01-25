# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Ingram Micro
# All rights reserved.
from connect.client import R

from reports.utils import get_value, parameter_value, convert_to_datetime

HEADERS = (
    'Request Type', 'Request ID', 'Request Created At', 'Subscription ID',
    'Subscription External ID', 'Promotion ID',
    'Promotion Applied (PercentDiscount)', 'Promotion Expire Date',
    'Microsoft Tenant ID', 'Microsoft Domain', 'Microsoft Subscription ID',
    'Microsoft Order ID', 'Item MPN', 'Item Name', 'Item Period',
    'Item Quantity', 'Marketplace Name', 'Microsoft Tier1 MPN (if any)',
    'Customer ID'
)

# This report is only valid for the NCE Commercial product in development
# and production environments.
NCE_COMMERCIAL_PRODUCTS = ['PRD-814-505-018', 'PRD-183-233-565']

TIER_CONFIGS = {}


def generate(
        client=None,
        parameters=None,
        progress_callback=None,
        renderer_type=None,
        extra_context_callback=None,
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
        item = _get_purchased_item(get_value(request, ['asset', 'items'], []))
        promotion = _get_promo_applied(
            item,
            parameter_value('nce_promo_final',
                            get_value(request, ['asset', 'params'], []))
        )
        if promotion:
            if renderer_type == 'json':
                yield {
                    HEADERS[idx].replace(' ', '_').lower(): value
                    for idx, value in
                    enumerate(_process_line(client, request, item, promotion))
                }
            else:
                yield _process_line(client, request, item, promotion)
            progress += 1
            progress_callback(progress, total)


def _get_request_list(client, parameters):
    query = R()
    query &= R().updated.ge(parameters['date']['after'])
    query &= R().updated.le(parameters['date']['before'])
    query &= R().status.eq('approved')
    query &= R().asset.params.id.eq('nce_promo_final')
    query &= R().type.oneof(['purchase', 'change'])
    query &= R().asset.product.id.oneof(NCE_COMMERCIAL_PRODUCTS)
    if parameters.get('mkp') and parameters['mkp']['all'] is False:
        query &= R().marketplace.id.oneof(parameters['mkp']['choices'])
    if parameters.get('connection_type') and parameters['connection_type'][
            'all'] is False:
        query &= R().asset.connection.type.oneof(
            parameters['connection_type']['choices'])
    else:
        query &= R().asset.connection.type.oneof(['test', 'production'])

    return client.requests.filter(query).order_by("created")


def _get_tier1_mpn(client, product_id, account_id):
    if product_id not in TIER_CONFIGS:
        TIER_CONFIGS[product_id] = {}

    if account_id not in TIER_CONFIGS[product_id]:
        TIER_CONFIGS[product_id][account_id] = "-"
        query = R()
        query &= R().product.id.eq(product_id)
        query &= R().account.id.eq(account_id)
        config = client.ns('tier').collection('configs').filter(query).first()
        TIER_CONFIGS[product_id][account_id] = parameter_value(
            'tier1_mpn',
            get_value(
                config,
                ['params'],
                []))

    return TIER_CONFIGS[product_id][account_id]


def _get_promo_applied(item, promo_final):
    item_mpn = item['mpn'].split('_')[0] if "_" in item['mpn'] else item['mpn']
    if promo_final and promo_final != "-" and promo_final['promotions'][0][
            'mpn'] == item_mpn:
        return promo_final['promotions'][0]
    return None


def _get_purchased_item(item_list):
    return list(filter(lambda item: int(item['quantity']) > 0, item_list))[0]


def _get_item_quantity(request_type, item):
    quantity = get_value(item, ['quantity'])
    if request_type == "change":
        quantity = int(quantity) - int(get_value(item, ['old_quantity']))
        return "+" + str(quantity) if quantity > 0 else "-" + str(quantity)

    return quantity


def _process_line(client, request, item, promotion):
    tier1_mpn = _get_tier1_mpn(
        client,
        get_value(request, ['asset', 'product', 'id']),
        get_value(request, ['asset', 'tiers', 'tier1', 'id']),
    )

    return (
        get_value(request, ['type']),
        get_value(request, ['id']),
        convert_to_datetime(
            get_value(request, ['asset', 'events', 'created', 'at'])),
        get_value(request, ['asset', 'id']),
        get_value(request, ['asset', 'external_id']),
        get_value(promotion, ['promotion_id']),
        get_value(promotion, ['discount_percent']),
        convert_to_datetime(get_value(promotion, ['end_date'])),
        parameter_value('ms_customer_id',
                        get_value(request, ['asset', 'params'], [])),
        parameter_value('microsoft_domain',
                        get_value(request, ['asset', 'params'], [])),
        parameter_value('subscription_id',
                        get_value(request, ['asset', 'params'], [])),
        parameter_value('csp_order_id',
                        get_value(request, ['asset', 'params'], [])),
        get_value(item, ['mpn']),
        get_value(item, ['display_name']),
        get_value(item, ['period']),
        _get_item_quantity(get_value(request, ['type']), item),
        get_value(request, ['asset', 'marketplace', 'name']),
        tier1_mpn,
        get_value(request, ['asset', 'tiers', 'customer', 'id']),
    )
