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
    'Marketplace ID',
    'Subscription ID',
    'CBC Subscription ID',
    'CBC Customer ID',
    'Customer Name',
    'Transaction Type',
    'Domain',
    'Offer ID',
    'Offer Name',
    'CBC Status',
    'Microsoft Status',
    'Microsoft Auto Renew',
    'CBC Creation Date',
    'Microsoft Creation Date',
    'Microsoft Commitment End Date',
    'CBC Licenses',
    'Microsoft Licenses',
    'Error details',
]

# This report is only valid for the NCE Commercial product in development and production environments.
NCE_COMMERCIAL_PRODUCTS = ['PRD-183-233-565', 'PRD-814-505-018']
MICROSOFT_SAAS = 'MICROSOFT_SAAS'
SERVICE_IDS = ['SRVC-7117-4970', 'SRVC-7374-6941']

active_subscriptions_not_processed = {}


def generate(
        client=None,
        parameters=None,
        progress_callback=None,
        renderer_type=None,
        extra_context_callback=None,
):
    validate_parameters(parameters)
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
                enumerate(_process_line(request, parameters, mms_client))
            }
        else:
            yield _process_line(request, parameters, mms_client)

        progress += 1
        progress_callback(progress, total)


def validate_parameters(parameters: dict):
    # Validate date range
    if not parameters.get('date').get('after') or not parameters.get('date').get('before'):
        raise ValueError('The date range is required.')

    # Validate date range is not greater than 2 months
    date_after = convert_to_datetime(parameters.get('date').get('after').replace('Z', ''))
    date_before = convert_to_datetime(parameters.get('date').get('before').replace('Z', ''))
    difference_months = (date_after.year - date_before.year) * 12 + date_after.month - date_before.month
    if difference_months > 2:
        raise ValueError('The date range cannot be greater than 2 months.')

    # Validate marketplace is just one
    if parameters.get('mkp'):
        if parameters['mkp']['all'] is True:
            raise ValueError('Only one marketplace can be selected.')
        if len(parameters.get('mkp').get('choices')) != 1:
            raise ValueError('Only one marketplace can be selected.')

    if parameters.get('connection_type'):
        if parameters['connection_type']['all'] is True:
            raise ValueError('Only one connection type can be selected.')
        if len(parameters.get('connection_type').get('choices')) != 1:
            raise ValueError('Only one connection type can be selected.')


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
    query &= R().product.id.oneof(NCE_COMMERCIAL_PRODUCTS)

    if parameters.get('connection_type') and parameters['connection_type']['all'] is False:
        query &= R().connection.type.eq(parameters['connection_type']['choices'][0])

    if parameters.get('mkp') and parameters['mkp']['all'] is False:
        query &= R().marketplace.id.eq(parameters['mkp']['choices'][0])

    query &= R().created.gt(parameters['date']['after'])
    query &= R().created.lt(parameters['date']['before'])
    return client.assets.filter(query)


def _process_line(request, parameters, mms_client):
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


def obtain_values_from_request(request):
    values = {}
    params = get_value(request, ['params'])
    item = get_value(request, ['items', 0])

    values['asset_id'] = get_value(request, ['id'])
    values['provider_name'] = get_value(request, ['connection', 'provider', 'name'])
    values['provider_id'] = get_value(request, ['connection', 'provider', 'id'])
    values['marketplace_id'] = get_value(request, ['marketplace', 'id'])
    values['subscription_id'] = parameter_value('subscription_id', params)
    values['cbc_subscription_id'] = get_value(request, ['external_id'])
    values['cbc_customer_id'] = parameter_value('ms_customer_id', params)
    values['customer_name'] = get_value(request, ['tiers', 'customer', 'name'])
    values['transaction_type'] = get_value(request, ['connection', 'type'])
    values['domain'] = parameter_value('microsoft_domain', params)
    values['offer_id'] = item['mpn']
    values['offer_name'] = item['display_name']
    values['cbc_status'] = get_value(request, ['status'])
    values['cbc_creation_date'] = get_value(request, ['events', 'created', 'at'])
    values['cbc_licenses'] = item['quantity']
    return values


def process_row(subscription, request, error=None):
    if error:
        return process_row_error(request, error)

    values = obtain_values_from_request(request)

    microsoft_status = subscription.get('status', None)
    microsoft_auto_renew = subscription.get('autoRenewEnabled', None)
    microsoft_creation_date = subscription.get('creationDate', None)
    microsoft_commitment_end_date = subscription.get('commitmentEndDate', None)
    microsoft_licenses = subscription.get('quantity', None)

    row = (
        values['asset_id'],
        values['provider_name'],
        values['provider_id'],
        values['marketplace_id'],
        values['subscription_id'],
        values['cbc_subscription_id'],
        values['cbc_customer_id'],
        values['customer_name'],
        values['transaction_type'],
        values['domain'],
        values['offer_id'],
        values['offer_name'],
        values['cbc_status'],
        microsoft_status,
        microsoft_auto_renew,
        values['cbc_creation_date'],
        microsoft_creation_date,
        microsoft_commitment_end_date,
        values['cbc_licenses'],
        microsoft_licenses,
        '-'
    )
    return row


def process_row_error(request, error):
    values = obtain_values_from_request(request)
    row = (
        values['asset_id'],
        values['provider_name'],
        values['provider_id'],
        values['marketplace_id'],
        values['subscription_id'],
        values['cbc_subscription_id'],
        values['cbc_customer_id'],
        values['customer_name'],
        values['transaction_type'],
        values['domain'],
        values['offer_id'],
        values['offer_name'],
        values['cbc_status'],
        '-',
        '-',
        values['cbc_creation_date'],
        '-',
        '-',
        values['cbc_licenses'],
        '-',
        error
    )
    return row


class StopProcessingReport(Exception):
    pass
