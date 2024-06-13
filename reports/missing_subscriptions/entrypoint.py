# -*- coding: utf-8 -*-
#
# Copyright (c) 2024, Ingram Micro
# All rights reserved.

from connect.client import R

from reports.utils import get_value, parameter_value
from reports.http import MMSClientAPI, obtain_url_for_service
from reports.validation import validate_date, check_if_only_one_marketplace_is_available

HEADERS = [
    'Microsoft Subscription ID',
    'Customer ID',
    'Customer External ID',
    'Microsoft Customer ID',
    'Customer Domain',
    'Reseller MPN ID',
    'Product Name',
    'Product ID',
    'Product SKU ID',
    'Quantity Of Licenses',
    'Microsoft Subscription Status',
    'Auto-renewal Status',
    'Subscription Commitment End Date',
    'Subscription Creation Date',
    'Error Details',
]

NCE_PRODUCTS = ['PRD-183-233-565', 'PRD-814-505-018', 'PRD-361-551-319', 'PRD-750-410-786', 'PRD-108-206-764',
                'PRD-561-716-033', 'PRD-814-505-01', 'PRD-275-843-418']
MICROSOFT_SAAS = 'MICROSOFT_SAAS'


def generate(
        client=None,
        parameters=None,
        progress_callback=None,
        renderer_type=None,
        extra_context_callback=None,
):
    try:
        _validate_parameters(parameters, client)
        service_url = obtain_url_for_service(client)
        mms_client = MMSClientAPI(client, service_url)
        customers = _get_filtered_customers_list(client, parameters)

        progress = 0
        total = len(customers)
        progress_callback(progress, total)

        if renderer_type == 'csv':
            yield HEADERS

        for customer in customers:
            connect_subscriptions = _get_connect_subscriptions_dict(client, parameters, customer.id)
            ms_subscriptions = []
            try:
                ms_subscriptions = _get_microsoft_subscriptions(mms_client, parameters, customer.microsoft_id)
            except CannotObtainMSSubscriptionsError as error:
                yield _render_row(renderer_type, _process_error, str(error))
            missing_subscriptions = _find_missing_subscriptions(connect_subscriptions, ms_subscriptions)

            for subscription in missing_subscriptions:
                yield _render_row(renderer_type, _process_line, subscription, customer)

            progress += 1
            progress_callback(progress, total)
    except Exception as error:
        error_str = str(error)
        if renderer_type == 'csv':
            yield HEADERS

        yield _render_row(renderer_type, _process_error, error_str)

        progress_callback(1, 1)
        return


def _validate_parameters(parameters, client):
    validate_date(parameters, limit_in_months=2)

    if parameters.get('connection_type'):
        if parameters['connection_type']['all'] is True:
            raise ValueError('Only one connection type can be selected.')
        if len(parameters.get('connection_type').get('choices')) != 1:
            raise ValueError('Only one connection type can be selected.')

    if parameters.get('mkp'):
        if parameters['mkp']['all'] is True:
            check_if_only_one_marketplace_is_available(client)
        if len(parameters.get('mkp').get('choices')) != 1:
            raise ValueError('Only one marketplace can be selected.')


def _find_missing_subscriptions(connect_subscriptions, ms_subscriptions):
    missing_subscriptions = []
    for subscription in ms_subscriptions:
        sub_id = subscription['id']
        if sub_id in connect_subscriptions:
            if connect_subscriptions[sub_id]['status'] == 'active':
                continue
            if subscription['status'] == connect_subscriptions[sub_id]['status']:
                continue
        missing_subscriptions.append(subscription)

    return missing_subscriptions


def _extract_subscription_id(request):
    params = get_value(request, ['params'], {})
    subscription_id = parameter_value('subscription_id', params)
    return subscription_id


def _get_filters(parameters):
    domain_names, ms_customer_ids = [], []

    if parameters.get('domain_names'):
        domain_names = parameters['domain_names'].split(',')
    if parameters.get('ms_customer_ids'):
        ms_customer_ids = parameters['ms_customer_ids'].split(',')

    return domain_names, ms_customer_ids


def _get_customers(client, parameters):
    query = R()
    query &= R().type.eq('customer')

    query &= R().events.created.at.ge(parameters['date']['after'])
    query &= R().events.created.at.le(parameters['date']['before'])

    return client.ns('tier').collection('accounts').filter(query)


def _get_filtered_customers_list(client, parameters):
    customers_unfiltered = _get_customers(client, parameters)
    customers = []
    domain_names, ms_customer_ids = _get_filters(parameters)

    for customer in customers_unfiltered:
        ms_customer_id, domain = _get_customer_microsoft_domain_and_id(client, parameters, customer['id'])
        if not ms_customer_id:
            continue
        if domain_names and domain not in domain_names:
            continue
        if ms_customer_ids and ms_customer_id not in ms_customer_ids:
            continue
        customers.append(CustomerInfo(customer['id'], customer['external_id'], domain, ms_customer_id))

    return customers


def _get_customer_microsoft_domain_and_id(client, parameters, customer_id):
    query = R()
    query &= R().asset.tiers.customer.id.eq(customer_id)
    query &= R().status.eq('approved')
    if parameters.get('mkp') and parameters['mkp']['all'] is False:
        query &= R().marketplace.id.eq(parameters['mkp']['choices'][0])
    request = client.requests.filter(query).order_by('-created').first()

    params = get_value(request, ['asset', 'params'], {})
    domain = parameter_value('microsoft_domain', params, None)
    ms_customer_id = parameter_value('ms_customer_id', params, None)

    return ms_customer_id, domain


def _get_microsoft_subscriptions(mms_client, parameters, customer_id):
    marketplace_id = parameters.get('mkp').get('choices')[0]
    environment = parameters.get('connection_type').get('choices')[0]
    try:
        ms_subscriptions = mms_client.get_ms_customer_subscriptions(product_type=MICROSOFT_SAAS,
                                                                    marketplace_id=marketplace_id,
                                                                    environment=environment,
                                                                    ms_customer_id=customer_id)
    except Exception as error:
        raise CannotObtainMSSubscriptionsError(
            f'Failed to obtain microsoft subscriptions for customer with id:{customer_id}.'
            f'Error message: {str(error)}')

    statuses = parameters.get('status').get('choices')
    if not statuses:
        statuses = ['active']

    return filter(lambda subscription: subscription.get('status') in statuses, ms_subscriptions)


def _get_connect_subscriptions_dict(client, parameters, customer_id):
    query = R()
    query &= R().status.oneof(['active', 'terminated', 'terminating', 'suspended'])
    query &= R().product.id.oneof(NCE_PRODUCTS)
    query &= R().tiers.customer.id.eq(customer_id)

    if parameters.get('mkp') and parameters['mkp']['all'] is False:
        query &= R().marketplace.id.eq(parameters['mkp']['choices'][0])

    if parameters.get('connection_type') and parameters['connection_type']['all'] is False:
        query &= R().connection.type.eq(parameters['connection_type']['choices'][0])

    subscriptions = client.assets.filter(query)
    sub_dict = {}
    for subscription in subscriptions:
        s_id = _extract_subscription_id(subscription)
        sub_dict[s_id] = subscription

    return sub_dict


def _extract_product_and_sku_id(subscription):
    offer_id = subscription.get('offer_id')
    if not offer_id:
        return '-', '-'

    offer_parts = offer_id.split(':')
    prod_id = offer_parts[0]
    sku_id = offer_parts[1]
    return prod_id, sku_id


def _process_line(subscription, customer):
    subscription_id = subscription.get('id', '-')
    product_name = subscription.get('offer_name', '-')
    reseller_mpn_id = subscription.get('partner_id', '-')
    product_id, product_sku_id = _extract_product_and_sku_id(subscription)
    license_quantity = subscription.get('quantity', '-')
    subscription_status = subscription.get('status', '-')
    auto_renewal_status = subscription.get('auto_renew_enabled', '-')
    subscription_commitment_end_date = subscription.get('commitment_end_date', '-')
    subscription_creation_date = subscription.get('creation_date', '-')

    return (
        subscription_id,
        customer.id,
        customer.external_id,
        customer.microsoft_id,
        customer.domain,
        reseller_mpn_id,
        product_name,
        product_id,
        product_sku_id,
        license_quantity,
        subscription_status,
        auto_renewal_status,
        subscription_commitment_end_date,
        subscription_creation_date,
    )


def _process_error(error):
    error_row = ['-' for _ in HEADERS]
    error_row[-1] = error
    return tuple(error_row)


def _render_row(renderer_type, process_func, *args):
    if renderer_type == 'json':
        return {
            HEADERS[idx].replace(' ', '_').lower(): value
            for idx, value in
            enumerate(process_func(*args))
        }
    else:
        return process_func(*args)


class CannotObtainMSSubscriptionsError(Exception):
    pass


class CustomerInfo:
    def __init__(self, customer_id, customer_external_id, domain, microsoft_id):
        self.id = customer_id
        self.external_id = customer_external_id
        self.domain = domain
        self.microsoft_id = microsoft_id
