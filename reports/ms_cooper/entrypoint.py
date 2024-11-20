from cnct import R
from reports.utils import (
    convert_to_datetime,
    get_sub_parameter,
    get_sub_ta_parameter,
)
from datetime import datetime
from reports.validation import validate_date

HEADERS = (
    'Subscription ID', 'Subscription External ID', 'Subscription Status', 'Subscription Created At',
    'Subscription Updated At', 'Subscription Type', 'Contract Type', 'Product ID', 'Product Name',
    'Billing Period', 'Anniversary Day', 'Anniversary Month', 'Item ID', 'Item MPN',
    'Item Description', 'Item Period', 'Item Quantity', 'Customer ID', 'Customer Name',
    'Customer external id', 'Customer Country', 'Tier 1 ID', 'Tier 1 Company name',
    'Tier 1 External Id', 'Tier 1 Country location', 'Tier 2 ID', 'Tier 2 Company name',
    'Tier 2 External Id', 'Tier 2 Country location', 'Provider ID', 'Provider Name',
    'Source MKP', 'MKP Name', 'Vendor ID', 'Vendor Name', 'Microsoft Domain (if any)',
    'Microsoft Sub ID (if any)', 'Microsoft Customer ID (if any)', 'Microsoft Order ID (if any)',
    'Microsoft Plan Sub ID (if any)', 'Microsoft Tier1 MPN'
)

TC_CACHE = {}
ASSET_ITEM = []

PRODUCTS = []

# Microsoft Vendor ID
VENDOR = "VA-888-104"

def generate(
        client=None,
        parameters=None,
        progress_callback=None,
        renderer_type=None,
        extra_context_callback=None,
):
    try:
        populate_products(client)
        if len(PRODUCTS) == 0:
            return
        init_tc_cache(client)
        client.default_limit = 1000

        last_day_of_prev_month = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0,
        )
        today = datetime.utcnow()
        month, year = (today.month - 1, today.year) if today.month != 1 else (12, today.year - 1)
        start_day_of_prev_month = today.replace(day=1, month=month, year=year)

        # If date_after and date_before are provided, override the default values
        if parameters.get('date') and parameters['date'].get('after') and parameters['date'].get('before'):
            date_after = convert_to_datetime(parameters['date']['after'].replace('Z', ''))
            date_before = convert_to_datetime(parameters['date']['before'].replace('Z', ''))

            last_day_of_prev_month = date_before
            start_day_of_prev_month = date_after

        # Handling Active first
        rqlactive = R().status.oneof(['active', 'suspended']) & R().product.id.oneof(PRODUCTS)
        rqlactive &= R().events.created.at.lt(last_day_of_prev_month)
        sub_active_suspended = (
            client.ns('subscriptions')
            .collection('assets')
            .filter(rqlactive)
            .order_by("-events.created.at")
        )
        # For terminated, termination must be in last month
        rql = R().status.oneof(['terminated', 'terminating']) & R().product.id.oneof(PRODUCTS)
        rql &= R().events.updated.at.ge(start_day_of_prev_month)
        rql &= R().events.updated.at.lt(last_day_of_prev_month)
        sub_terminated = (
            client.ns('subscriptions')
            .collection('assets')
            .filter(rql)
            .order_by("-events.created.at")
        )
        total_subscriptions = sub_active_suspended.count() + sub_terminated.count()
        progress = 0

        progress_callback(progress, total_subscriptions)

        if renderer_type == 'csv':
            yield HEADERS

        for subscription in sub_active_suspended:
            result = process_subscription(client, subscription)
            for res in result:
                if renderer_type == 'json':
                    yield {
                        HEADERS[idx].replace(' ', '_').lower(): value
                        for idx, value in enumerate(res)
                    }
                else:
                    yield res
            progress += 1
            progress_callback(progress, total_subscriptions)

        for subscription in sub_terminated:
            result = process_subscription(client, subscription)
            for res in result:
                if renderer_type == 'json':
                    yield {
                        HEADERS[idx].replace(' ', '_').lower(): value
                        for idx, value in enumerate(res)
                    }
                else:
                    yield res
            progress += 1
            progress_callback(progress, total_subscriptions)

    except Exception as error:
        error_str = str(error)
        if renderer_type == 'csv':
            yield HEADERS

        yield _render_row(renderer_type, _process_error, error_str)

        progress_callback(1, 1)
        return


def process_subscription(client, subscription):
    param_values = get_product_specifics(subscription, client)
    output = []
    for item in subscription["items"]:
        try:
            if int(item["quantity"]) == 0:
                continue
            if subscription['id'] + '_' + item['id'] in ASSET_ITEM:
                continue
            output.append(
                (
                    subscription["id"],
                    subscription["external_id"] if subscription["external_id"] else subscription["external_uid"],
                    subscription["status"].capitalize(),
                    convert_to_datetime(subscription["events"]["created"]["at"]),
                    convert_to_datetime(subscription["events"]["updated"]["at"]) if 'updated' in subscription['events'] else '-',
                    subscription["connection"]["type"].capitalize(),
                    get_contract_type(subscription.get("contract",{}).get('id','Distribution')),
                    subscription['product']['id'],
                    subscription['product']['name'],
                    str(subscription.get('billing', {}).get('period', {}).get('delta','')) + " " + subscription.get('billing', {}).get('period', {}).get('uom', 'Perpetual').capitalize(),
                    subscription.get('billing', {}).get('anniversary', {}).get('day', 'Perpetual'),
                    subscription.get('billing', {}).get('anniversary', {}).get('month', 'Perpetual'),
                    item['id'],
                    item['mpn'],
                    item['display_name'],
                    item['period'],
                    (
                        "unlimited" if item["quantity"] == -1 else item["quantity"]
                    ),
                    subscription["tiers"]["customer"]["id"],
                    subscription["tiers"]["customer"]["name"],
                    (
                        subscription["tiers"]["customer"]["external_id"]
                        if "external_id" in subscription["tiers"]["customer"]
                        else subscription["tiers"]["customer"]["external_uid"]
                    ),
                    subscription["tiers"]["customer"]["contact_info"]["country"].upper(),
                    subscription["tiers"]["tier1"]["id"],
                    subscription["tiers"]["tier1"]["name"],
                    (
                        subscription["tiers"]["tier1"]["external_id"]
                        if "external_id" in subscription["tiers"]["tier1"]
                        else subscription["tiers"]["tier1"]["external_uid"]
                    ),
                    subscription["tiers"]["tier1"]["contact_info"]["country"].upper(),
                    (
                        subscription["tiers"]["tier2"]["id"]
                        if "tier2" in subscription["tiers"] and 'id' in subscription["tiers"]['tier2']
                        else "-"
                    ),
                    (
                        subscription["tiers"]["tier2"]["name"]
                        if "tier2" in subscription["tiers"] and "name" in subscription["tiers"]["tier2"]
                        else "-"
                    ),
                    (
                        subscription["tiers"]["tier2"]["external_id"]
                        if "tier2" in subscription["tiers"] and "external_id" in subscription["tiers"]["tier2"]
                        else "-"
                    ),
                    (
                        subscription["tiers"]["tier2"]["contact_info"]["country"]
                        if "tier2" in subscription["tiers"] and "country" in subscription["tiers"]["tier2"]["contact_info"]
                        else "-"
                    ),
                    subscription['connection']['provider']['id'] if 'provider' in subscription['connection'] else '-',
                    subscription['connection']['provider']['name'] if 'provider' in subscription['connection'] else '-',
                    subscription['marketplace']['id'],
                    subscription['marketplace']['name'],
                    subscription['connection']['vendor']['id'],
                    subscription['connection']['vendor']['name'],
                    param_values["microsoft_domain"],
                    param_values["subscription_id"],
                    param_values["ms_customer_id"],
                    param_values["microsoft_order_id"],
                    param_values["microsoft_plan_subscription_id"],
                    param_values["microsoft_tier1_mpn"],
                )
            )
            ASSET_ITEM.append(subscription['id'] + '_' + item['id'])
        except Exception as e:
            print(f"Error in {subscription['id']}: {e}")
    return output

def get_product_specifics(subscription, client):
    values = {
        "microsoft_domain": "-",
        "subscription_id": "-",
        "ms_customer_id": "-",
        "microsoft_order_id": "-",
        "microsoft_plan_subscription_id": "-",
        "microsoft_tier1_mpn": "-",
    }
    if subscription["connection"]["vendor"]["id"] == "VA-888-104":
        values["microsoft_domain"] = get_sub_parameter(subscription, "microsoft_domain")
        sub_id = get_sub_parameter(subscription, "subscription_id")
        if sub_id == "-":
            sub_id = get_sub_parameter(subscription, "microsoft_subscription_id")
        values["subscription_id"] = sub_id
        cust_id = get_sub_parameter(subscription, "ms_customer_id")
        if cust_id == "-":
            cust_id = get_sub_parameter(subscription, "customer_id")
        values["ms_customer_id"] = cust_id
        order_id = get_sub_parameter(subscription, "microsoft_order_id")
        if order_id == "-":
            order_id = get_sub_parameter(subscription, "csp_order_id")
        values["microsoft_plan_subscription_id"] = get_sub_parameter(
            subscription,
            "microsoft_plan_subscription_id",
        )
        values["microsoft_order_id"] = order_id
        values["microsoft_tier1_mpn"] = get_param_mpn(subscription, client)
    return values

def init_tc_cache(client):
    for product in PRODUCTS:
        TC_CACHE[product] = {}
        init_product_tc_cache(product, client)
        print(f'Length of cache for product {product} is {len(TC_CACHE[product])}')

def get_param_mpn(subscription, client):
    if subscription['tiers']['tier1']['id'] in TC_CACHE[subscription['product']['id']]:
        return TC_CACHE[subscription['product']['id']][subscription['tiers']['tier1']['id']]
    mpn = get_sub_ta_parameter(subscription, 'tier1', 'tier1_mpn', client)
    TC_CACHE[subscription['product']['id']][subscription['tiers']['tier1']['id']] = mpn
    return mpn

def populate_ta_cache(parameters, client):
    rql = R()
    rql &= R().product.id.oneof(PRODUCTS)
    if parameters.get('mkp') and parameters['mkp']['all'] is False:
        rql &= R().marketplace.id.oneof(parameters['mkp']['choices'])
    tcs = client.ns('tier').collection('configs').filter(rql)
    for tc in tcs:
        if tc['product']['id'] not in TC_CACHE:
            TC_CACHE[tc['product']['id']] = {}
        TC_CACHE[tc['product']['id']][tc['account']['id']] = get_param_value(tc['params'], 'tier1_mpn')

def get_param_value(params, param_id):
    for param in params:
        if param_id == param['id']:
            return param['value'] if 'value' in param else '-'
    return '-'


def init_product_tc_cache(product, client):
    rql = R().product.id.eq(product) & R().status.eq('active') & R().tier_level.eq(1) & R().connection.type.ne('null()')
    tcs = client.ns('tier').collection('configs').filter(rql).select(
        '-configuration',
        '-connection',
        '-contract',
        '-marketplace'
    )
    print(f'Obtaining {tcs.count()} for product {product}')
    for tc in tcs:
        mpn = get_param_value(tc['params'], 'tier1_mpn')
        TC_CACHE[product][tc['account']['id']] = mpn


def populate_products(client):
    rql = R().owner.id.eq(VENDOR)
    rql2 = R().visibility.listing.eq(True) | R().visibility.syndication.eq(True)
    rql &= rql2
    products = client.products.filter(rql)
    for product in products:
        PRODUCTS.append(product['id'])
    # Empty print due CLI Execution
    print("")
    print(f"Amount of products from microsoft to include in report {len(PRODUCTS)}")

def get_contract_type(contract):
    if contract.startswith("CRD-"):
        return "Distribution"
    return "Syndication"
