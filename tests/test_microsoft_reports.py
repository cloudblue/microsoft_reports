# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Ingram Micro
# All rights reserved.
#
import reports.nce_promos.entrypoint as nce_promos
import reports.nce_migrations.entrypoint as nce_migrations

from tests.test_utils import data_migration_requests

TIER_RQL_TA_2 = 'and(eq(product.id,PRD-814-505-018),eq(account.id,TA-2))'
TIER_RQL_TA_1 = 'and(eq(product.id,PRD-814-505-018),eq(account.id,TA-1))'
AFTER_DATE = '2021-12-01T00:00:00'
BEFORE_DATE = '2021-12-20T00:00:00'


def test_nce_promos(progress, client_factory, response_factory, ff_request, tc_request):
    parameters = {
        'date': {
            'after': AFTER_DATE,
            'before': BEFORE_DATE,
        },
        'connection_type': {
            'all': False,
            'choices': ["test"]},
        'mkp': {
            'all': True,
            'choices': [],
        }
    }
    responses = [response_factory(
        count=2,
    ), response_factory(
        query='and(ge(updated,2021-12-01T00:00:00),'
              'le(updated,2021-12-20T00:00:00),'
              'eq(status,approved),'
              'in(type,(purchase,change)),'
              'in(asset.product.id,(PRD-814-505-018,PRD-183-233-565)),'
              'in(asset.connection.type,(test)))',
        value=ff_request,
    ), response_factory(
        query=TIER_RQL_TA_1,
        value=tc_request
    ), response_factory(
        query=TIER_RQL_TA_2,
        value=tc_request
    )]

    client = client_factory(responses)
    result = list(nce_promos.generate(client, parameters, progress))

    assert len(result) == 2


def test_generate_csv_rendered(progress, client_factory, response_factory, ff_request, tc_request):
    parameters = {
        'date': {
            'after': AFTER_DATE,
            'before': BEFORE_DATE,
        },
        'connection_type': {
            'all': False,
            'choices': ["test"]},
        'mkp': {
            'all': False,
            'choices': ['MP-123']
        }
    }
    responses = [response_factory(
        count=2,
    ), response_factory(
        query='and(ge(updated,2021-12-01T00:00:00),'
              'le(updated,2021-12-20T00:00:00),'
              'eq(status,approved),'
              'in(type,(purchase,change)),'
              'in(asset.product.id,(PRD-814-505-018,PRD-183-233-565)),'
              'in(marketplace.id,(MP-123)),'
              'in(asset.connection.type,(test)))',

        value=ff_request,
    ), response_factory(
        query=TIER_RQL_TA_1,
        value=tc_request
    ), response_factory(
        query=TIER_RQL_TA_2,
        value=tc_request
    )]

    client = client_factory(responses)
    result = list(nce_promos.generate(client, parameters, progress, renderer_type='csv'))

    assert len(result) == 3
    assert result[0] == nce_promos.HEADERS


def test_generate_json_render(progress, client_factory, response_factory, ff_request, tc_request):
    parameters = {
        'date': {
            'after': AFTER_DATE,
            'before': BEFORE_DATE,
        },
        'connection_type': {
            'all': True,
            'choices': ["test"]},
        'mkp': {
            'all': False,
            'choices': ['MP-123']
        }
    }

    responses = [response_factory(
        count=2,
    ), response_factory(
        query='and(ge(updated,2021-12-01T00:00:00),'
              'le(updated,2021-12-20T00:00:00),'
              'eq(status,approved),'
              'in(type,(purchase,change)),'
              'in(asset.product.id,(PRD-814-505-018,PRD-183-233-565)),'
              'in(marketplace.id,(MP-123)))',
        value=ff_request,
    ), response_factory(
        query=TIER_RQL_TA_1,
        value=tc_request
    ), response_factory(
        query=TIER_RQL_TA_2,
        value=tc_request
    )]

    client = client_factory(responses)
    result = list(nce_promos.generate(client, parameters, progress, renderer_type='json'))

    assert len(result) == 2
    assert result[0]['request_id'] == 'PR-2'


def test_nce_promos_direct_sales_model(progress, client_factory, response_factory, ff_request_direct,
                                       tc_request_direct):
    parameters = {
        'date': {
            'after': AFTER_DATE,
            'before': BEFORE_DATE,
        },
        'connection_type': {
            'all': False,
            'choices': ["production"]},
        'mkp': {
            'all': False,
            'choices': ['MP-DIRECT']
        }
    }
    responses = [response_factory(
        count=2,
    ), response_factory(
        query='and(ge(updated,2021-12-01T00:00:00),'
              'le(updated,2021-12-20T00:00:00),'
              'eq(status,approved),'
              'in(type,(purchase,change)),'
              'in(asset.product.id,(PRD-814-505-018,PRD-183-233-565)),'
              'in(marketplace.id,(MP-DIRECT)),'
              'in(asset.connection.type,(production)))',
        value=ff_request_direct,
    ), response_factory(
        query='and(eq(product.id,PRD-183-233-565),eq(account.id,'
              'TA-DIRECT))',
        value=tc_request_direct
    )]

    client = client_factory(responses)
    result = list(nce_promos.generate(client, parameters, progress))

    assert len(result) == 1



def test_nce_migrations(progress, client_factory, response_factory):
    parameters = {
        'date': {
            'after': AFTER_DATE,
            'before': BEFORE_DATE,
        },
        'connection_type': {
            'all': False,
            'choices': ["test"]},
        'marketplaces': {
            'all': True,
            'choices': [],
        }
    }

    responses = [response_factory(count=1),
        response_factory(query='and(eq(type,purchase),'
               'eq(status,approved),'
               'in(asset.product.id,(PRD-183-233-565,PRD-814-505-018)),'
               'in(asset.connection.type,(test)),'
               f'ge(updated,{AFTER_DATE}),'
               f'le(updated,{BEFORE_DATE}))',
            value=data_migration_requests())
    ]

    client = client_factory(responses)
    result = list(nce_migrations.generate(client, parameters, progress))

    assert len(result) == 1


def test_nce_migrations_csv_rendered(progress, client_factory, response_factory):
    parameters = {
        'date': {
            'after': AFTER_DATE,
            'before': BEFORE_DATE,
        },
        'connection_type': {
            'all': False,
            'choices': ["test"]},
        'marketplaces': {
            'all': True,
            'choices': [],
        }
    }

    responses = [response_factory(count=1),
        response_factory(query='and(eq(type,purchase),'
               'eq(status,approved),'
               'in(asset.product.id,(PRD-183-233-565,PRD-814-505-018)),'
               'in(asset.connection.type,(test)),'
               f'ge(updated,{AFTER_DATE}),'
               f'le(updated,{BEFORE_DATE}))',
            value=data_migration_requests())
    ]

    client = client_factory(responses)
    result = list(nce_migrations.generate(client, parameters, progress, renderer_type='csv'))

    assert len(result) == 2
    assert result[0] == nce_migrations.HEADERS


def test_nce_migrations_json_rendered(progress, client_factory, response_factory):
    parameters = {
        'date': {
            'after': AFTER_DATE,
            'before': BEFORE_DATE,
        },
        'connection_type': {
            'all': False,
            'choices': ["test"]},
        'marketplaces': {
            'all': True,
            'choices': [],
        }
    }

    responses = [response_factory(count=1),
        response_factory(query='and(eq(type,purchase),'
               'eq(status,approved),'
               'in(asset.product.id,(PRD-183-233-565,PRD-814-505-018)),'
               'in(asset.connection.type,(test)),'
               f'ge(updated,{AFTER_DATE}),'
               f'le(updated,{BEFORE_DATE}))',
            value=data_migration_requests())
    ]

    client = client_factory(responses)
    result = list(nce_migrations.generate(client, parameters, progress, renderer_type='json'))

    assert len(result) == 1
    