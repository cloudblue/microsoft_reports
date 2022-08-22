import json
import os

MIGRATION_REQUESTS = '/fixtures/migration_requests.json'

def get_json(path: str) -> dict:
    with open(os.path.dirname(__file__) + path) as json_file:
        return json.load(json_file)

def data_migration_requests() -> dict:
    return get_json(MIGRATION_REQUESTS)
