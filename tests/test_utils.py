import json
import os
import responses

MIGRATION_REQUESTS = '/fixtures/migration_requests.json'
CUSTOMER_SUBSCRIPTIONS = '/fixtures/customer_subscriptions.json'


def get_json(path: str) -> dict:
    with open(os.path.dirname(__file__) + path) as json_file:
        return json.load(json_file)


def data_migration_requests() -> dict:
    return get_json(MIGRATION_REQUESTS)


def customer_subscriptions_from_service():
    return get_json(CUSTOMER_SUBSCRIPTIONS)
