# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Ingram Micro
# All rights reserved.

from connect.client import R

from reports.audit_tool.http import MMSClientAPI, MMSClientAPIError, SubscriptionCantBeObtained
from reports.utils import get_value, parameter_value, convert_to_datetime

HEADERS = [
    'Asset ID',
    'Provider Name',
    'Provider ID',
    'Marketplace Name',
    'Subscription ID',
    'External Subscription ID',
    'External Customer ID',
    'Customer Name',
    'Connection Type',
    'Domain',
    'Offer ID',
    'Offer Name',
    'Status',
    'Microsoft Status',
    'Microsoft Auto Renew',
    'CBC Creation Date',
    'Microsoft Creation Date',
    'Microsoft Commitment End Date',
    'Licenses',
    'Microsoft Licenses',
    'Error details',
]

# This report is only valid for the NCE Commercial product in development and production environments.
MICROSOFT_SAAS = 'MICROSOFT_SAAS'
SERVICE_IDS = ['SRVC-7117-4970', 'SRVC-7374-6941']
VENDORS_IDS = ['VA-888-104', 'VA-610-138']
active_subscriptions_not_processed = {}


def generate(
        client=None,
        parameters=None,
        progress_callback=None,
        renderer_type=None,
        extra_context_callback=None,
):
    try:
        validate_parameters(parameters, client)
        service_url = obtain_url_for_service(client)
        requests = _get_request_list(client, parameters)
        mms_client = MMSClientAPI(client, service_url)

        progress = 0
        total = requests.count()
        if renderer_type == 'csv':
            yield HEADERS

        for request in requests:
            # Filtering the parameter value directly as the client query returns timeout error
            if renderer_type == 'json':
                yield {
                    HEADERS[idx].replace(' ', '_').lower(): value
                    for idx, value in
                    enumerate(_process_line(request, parameters, mms_client, progress))
                }
            else:
                yield _process_line(request, parameters, mms_client, progress)

            progress += 1
            progress_callback(progress, total)

    except Exception as error:
        error_str = str(error)
        if renderer_type == 'csv':
            yield HEADERS

        if renderer_type == 'json':
            yield {
                HEADERS[idx].replace(' ', '_').lower(): value
                for idx, value in
                enumerate(process_row_error({}, error_str))
            }
        else:
            yield process_row_error({}, error_str)
        progress_callback(1, 1)
        return


def validate_parameters(parameters: dict, client):
    validate_date(parameters)

    # Validate marketplace is just one
    if parameters.get('mkp'):
        if parameters['mkp']['all'] is True:
            check_if_only_one_marketplace_is_available(client)
        if len(parameters.get('mkp').get('choices')) != 1:
            raise ValueError('Only one marketplace can be selected.')

    if parameters.get('connection_type'):
        if parameters['connection_type']['all'] is True:
            raise ValueError('Only one connection type can be selected.')
        if len(parameters.get('connection_type').get('choices')) != 1:
            raise ValueError('Only one connection type can be selected.')

    if parameters.get('product'):
        if parameters['product']['all'] is True:
            raise ValueError('Only one product can be selected.')
        if len(parameters.get('product').get('choices')) != 1:
            raise ValueError('Only one product can be selected.')
        check_if_product_is_valid(parameters['product']['choices'][0], client)


def check_if_only_one_marketplace_is_available(client):
    marketplaces = client.marketplaces.all()
    if marketplaces.count() != 1:
        raise ValueError('Only one marketplace can be selected.')


def check_if_product_is_valid(product_id, client):
    query = R()
    query &= R().id.eq(product_id)
    query &= R().owner.id.oneof(VENDORS_IDS)
    products = client.products.filter(query)
    if products.count() != 1:
        raise ValueError('The product selected is not valid. Please select a valid product from Microsoft products.')


def validate_date(parameters: dict):
    # Validate date range
    if not parameters.get('date').get('after') or not parameters.get('date').get('before'):
        raise ValueError('The date range is required.')

    # Validate date range is not greater than 2 months
    date_after = convert_to_datetime(parameters.get('date').get('after').replace('Z', ''))
    date_before = convert_to_datetime(parameters.get('date').get('before').replace('Z', ''))
    difference_months = (date_before.year - date_after.year) * 12 + date_before.month - date_after.month
    if difference_months > 2:
        raise ValueError('The date range cannot be greater than 2 months.')


def obtain_url_for_service(client):
    query = R()
    query &= R().status.eq('installed')
    query &= R().environment.extension.id.oneof(SERVICE_IDS)
    installation = client.ns('devops').collection('installations').filter(query).first()
    if not installation:
        raise StopProcessingReport('The service for the MMS was not found.')

    hostname = get_value(installation, ['environment', 'hostname'])
    domain = get_value(installation, ['environment', 'domain'])
    url = 'https://' + hostname + '.' + domain
    return url


def _get_request_list(client, parameters):
    query = R()
    query &= R().status.eq('active')

    if parameters.get('product') and parameters['product']['all'] is False:
        query &= R().product.id.oneof(parameters['product']['choices'])

    if parameters.get('connection_type') and parameters['connection_type']['all'] is False:
        query &= R().connection.type.eq(parameters['connection_type']['choices'][0])

    if parameters.get('mkp') and parameters['mkp']['all'] is False:
        query &= R().marketplace.id.eq(parameters['mkp']['choices'][0])

    query &= R().created.gt(parameters['date']['after'])
    query &= R().created.lt(parameters['date']['before'])
    return client.assets.filter(query)


def _process_line(request, parameters, mms_client, progress):
    environment = parameters.get('connection_type').get('choices')[0]
    params = get_value(request, ['params'])
    customer_tenant = parameter_value('ms_customer_id', params)
    marketplace_id = get_value(request, ['marketplace', 'id'])
    subscription_id = parameter_value('subscription_id', params)
    subscription_to_process = find_and_remove_subscription(subscription_id, customer_tenant)

    if not subscription_to_process:
        try:

            subscriptions = mms_client.get_ms_customer_subscriptions(product_type=MICROSOFT_SAAS,
                                                                     marketplace_id=marketplace_id,
                                                                     environment=environment,
                                                                     ms_customer_id=customer_tenant)
            active_subscriptions_not_processed[customer_tenant] = prepare_subscriptions_to_save(subscriptions)
            subscription_to_process = find_and_remove_subscription(subscription_id, customer_tenant)
        except SubscriptionCantBeObtained as error:
            if progress == 0:
                raise StopProcessingReport(f"There is an error with the Microsoft Management Settings: {str(error)}")
            return process_row({}, request, error=str(error))
        except MMSClientAPIError as error:
            raise StopProcessingReport(f"There is an error with the Microsoft Management Settings: {str(error)}")

    if not subscription_to_process:
        return process_row({}, request, error=f'The subscription {subscription_id} was not found in Microsoft for the '
                                              f'customer {customer_tenant}')
    return process_row(subscription_to_process, request)


def prepare_subscriptions_to_save(subscriptions):
    subscriptions_to_save = {}
    for subscription in subscriptions:
        subscriptions_to_save[subscription['id']] = subscription
    return subscriptions_to_save


def find_and_remove_subscription(subscription_id, customer_tenant):
    if customer_tenant in active_subscriptions_not_processed.keys():
        subscription_to_process = active_subscriptions_not_processed[customer_tenant].get(subscription_id, None)
        if subscription_to_process:
            active_subscriptions_not_processed[customer_tenant].pop(subscription_id)
            return subscription_to_process
    return None


def process_asset_values(request) -> dict:
    values = {}
    params = get_value(request, ['params'], {})

    values['asset_id'] = get_value(request, ['id'])
    values['provider_name'] = get_value(request, ['connection', 'provider', 'name'])
    values['provider_id'] = get_value(request, ['connection', 'provider', 'id'])
    values['marketplace_name'] = get_value(request, ['marketplace', 'name'])
    values['subscription_id'] = parameter_value('subscription_id', params)
    values['external_subscription_id'] = get_value(request, ['external_id'])
    values['external_customer_id'] = get_value(request, ['tiers', 'customer', 'external_id'])
    values['customer_name'] = get_value(request, ['tiers', 'customer', 'name'])
    values['transaction_type'] = get_value(request, ['connection', 'type'])
    values['domain'] = parameter_value('microsoft_domain', params)
    values['status'] = get_value(request, ['status'])
    values['creation_date'] = get_value(request, ['events', 'created', 'at'])

    return values


def process_item_values(values, item) -> dict:
    values['offer_id'] = item.get('mpn', '-')
    values['offer_name'] = item.get('display_name', '-')
    values['licenses'] = item.get('quantity', '-')

    return values


def process_item_list(values, items, subscription):
    items = list(filter(lambda item_to_process: int(item_to_process.get('quantity')) > 0, items))
    if len(items) > 1:
        for item in items:
            if item.get('mpn') == subscription.get('offerId'):
                values = process_item_values(values, item)
                break
    else:
        values = process_item_values(values, items[0])

    return values


def process_row(subscription, request, error=None) -> tuple:
    if error:
        return process_row_error(request, error)
    values_request = process_asset_values(request)

    items = get_value(request, ['items'], [])
    values_request = process_item_list(values_request, items, subscription)

    microsoft_status = subscription.get('status', None)
    microsoft_auto_renew = subscription.get('autoRenewEnabled', None)
    microsoft_creation_date = subscription.get('creationDate', None)
    microsoft_commitment_end_date = subscription.get('commitmentEndDate', None)
    microsoft_licenses = subscription.get('quantity', None)

    row = (
        values_request['asset_id'],
        values_request['provider_name'],
        values_request['provider_id'],
        values_request['marketplace_name'],
        values_request['subscription_id'],
        values_request['external_subscription_id'],
        values_request['external_customer_id'],
        values_request['customer_name'],
        values_request['transaction_type'],
        values_request['domain'],
        values_request.get('offer_id', '-'),
        values_request.get('offer_name', '-'),
        values_request['status'],
        microsoft_status,
        microsoft_auto_renew,
        values_request['creation_date'],
        microsoft_creation_date,
        microsoft_commitment_end_date,
        values_request.get('licenses', '-'),
        microsoft_licenses,
        '-'
    )
    return row


def process_row_error(request, error) -> tuple:
    values_request = process_asset_values(request)
    row = (
        values_request['asset_id'],
        values_request['provider_name'],
        values_request['provider_id'],
        values_request['marketplace_name'],
        values_request['subscription_id'],
        values_request['external_subscription_id'],
        values_request['external_customer_id'],
        values_request['customer_name'],
        values_request['transaction_type'],
        values_request['domain'],
        values_request.get('offer_id', '-'),
        values_request.get('offer_name', '-'),
        values_request['status'],
        '-',
        '-',
        values_request['creation_date'],
        '-',
        '-',
        values_request.get('licenses', '-'),
        '-',
        error
    )
    return row


class StopProcessingReport(Exception):
    pass
