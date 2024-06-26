import requests
from connect.client import ConnectClient, R

from reports.utils import get_value

SERVICE_IDS = ['SRVC-7117-4970', 'SRVC-7374-6941']


class MMSClientAPI(object):  # pragma: no cover
    """ Microsoft Management Settings client API """
    api_url = ""

    def __init__(self, client: ConnectClient, service_url):
        """ Constructor of MMSClient """
        self.client = client
        self.api_url = service_url

    def _get_headers(self):
        headers = {
            "Accept": "application/json",
            "Authorization": self.client.api_key,
        }
        headers.update({"X-APP-ID-MICROSOFT-EAAS": "unique_application_id"})
        return headers

    def get_ms_customer_subscriptions(
            self, product_type, marketplace_id, environment, ms_customer_id) -> (dict, int):
        headers = self._get_headers()
        response = requests.get(
            '{}/api/customer-subscriptions?product_type={}&marketplace_id={}&environment={}&ms_tenant_id={}'.format(
                self.api_url,
                product_type.upper(),
                marketplace_id.upper(),
                environment.upper(),
                ms_customer_id
            ), headers=headers
        )
        if response.status_code == 200:
            subscriptions = response.json()
            return subscriptions
        if response.status_code == 400:
            self.handle_response_error_codes(response)
        raise MMSClientAPIError(response.json()['error_message'])

    def handle_response_error_codes(self, response):
        if response.json()['error_code'] == 1000:
            raise SubscriptionCantBeObtained(response.json()['error_message'])
        elif response.json()['error_code'] == 1001:
            raise MMSClientAPIError(response.json()['error_message'])


class MMSClientAPIError(Exception):
    """ Base class for exceptions in this module. """
    pass


class SubscriptionCantBeObtained(MMSClientAPIError):
    pass


def obtain_url_for_service(client):
    query = R()
    query &= R().status.eq('installed')
    query &= R().environment.extension.id.oneof(SERVICE_IDS)
    installation = client.ns('devops').collection('installations').filter(query).first()
    if not installation:
        raise ValueError('The service for the MMS was not found.')

    hostname = get_value(installation, ['environment', 'hostname'])
    domain = get_value(installation, ['environment', 'domain'])
    url = 'https://' + hostname + '.' + domain
    return url
