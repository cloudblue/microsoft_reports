from connect.client import ConnectClient

from reports.utils import convert_to_datetime


def check_if_only_one_marketplace_is_available(client: ConnectClient):
    marketplaces = client.marketplaces.all()
    if marketplaces.count() != 1:
        raise ValueError('Only one marketplace can be selected.')


def validate_date(parameters: dict, limit_in_months: int):
    # Validate date range
    if not parameters.get('date').get('after') or not parameters.get('date').get('before'):
        raise ValueError('The date range is required.')

    date_after = convert_to_datetime(parameters.get('date').get('after').replace('Z', ''))
    date_before = convert_to_datetime(parameters.get('date').get('before').replace('Z', ''))
    difference_months = (date_before.year - date_after.year) * 12 + date_before.month - date_after.month
    if difference_months > limit_in_months:
        raise ValueError(
            f'The date range cannot be greater than {limit_in_months} month{"s" if limit_in_months > 1 else ""}.')
