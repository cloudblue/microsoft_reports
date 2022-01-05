# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Ingram Micro
# All rights reserved.
#

from reports.nce_promos.entrypoint import generate, HEADERS

PARAMETERS = {
    'date': {
        'after': '2021-12-01T00:00:00',
        'before': '2021-12-20T00:00:00',
    },
    'connection_type': {
        'all': False,
        'choices': ["test"]},
    'mkp': {
        'all': True,
        'choices': [],
    }
}


def test_nce_promos(progress, client_factory, response_factory, ff_request, tc_request):
    responses = []

    responses.append(
        response_factory(
            count=2,
        ),
    )
    responses.append(
        response_factory(
            query='and(ge(created,2021-12-01T00:00:00),'
                  'le(created,2021-12-20T00:00:00),'
                  'eq(status,approved),'
                  'eq(asset.params.id,nce_promo_final),'
                  'in(type,(purchase,change)),'
                  'in(asset.product.id,(PRD-814-505-018,PRD-183-233-565)),'
                  'in(asset.connection.type,(test)))',
            value=ff_request,
        ),
    )
    responses.append(
        response_factory(
            query='and(eq(product.id,PRD-814-505-018),eq(account.id,TA-2))',
            value=tc_request
        ),
    )

    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress))

    assert len(result) == 1


def test_generate_csv_rendered(progress, client_factory, response_factory, ff_request,tc_request):
    responses = []

    PARAMETERS['mkp'] = {
        'all': False,
        'choices': ['MP-123'],
    }

    responses.append(
        response_factory(
            count=2,
        ),
    )
    responses.append(
        response_factory(
            query='and(ge(created,2021-12-01T00:00:00),'
                  'le(created,2021-12-20T00:00:00),'
                  'eq(status,approved),'
                  'eq(asset.params.id,nce_promo_final),'
                  'in(type,(purchase,change)),'
                  'in(asset.product.id,(PRD-814-505-018,PRD-183-233-565)),'
                  'in(marketplace.id,(MP-123)),'
                  'in(asset.connection.type,(test)))',


            value=ff_request,
        ),
    )
    responses.append(
        response_factory(
            query='and(eq(product.id,PRD-814-505-018),eq(account.id,TA-2))',
            value=tc_request
        ),
    )
    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='csv'))

    assert len(result) == 2
    assert result[0] == HEADERS


def test_generate_json_render(progress, client_factory, response_factory, ff_request,tc_request):
    responses = []

    PARAMETERS['mkp'] = {
        'all': False,
        'choices': ['MP-123'],
    }

    responses.append(
        response_factory(
            count=2,
        ),
    )
    responses.append(
        response_factory(
            query='and(ge(created,2021-12-01T00:00:00),'
                  'le(created,2021-12-20T00:00:00),'
                  'eq(status,approved),'
                  'eq(asset.params.id,nce_promo_final),'
                  'in(type,(purchase,change)),'
                  'in(asset.product.id,(PRD-814-505-018,PRD-183-233-565)),'
                  'in(marketplace.id,(MP-123)),'
                  'in(asset.connection.type,(test)))',
            value=ff_request,
        ),
    )

    responses.append(
        response_factory(
            query='and(eq(product.id,PRD-814-505-018),eq(account.id,TA-2))',
            value=tc_request
        ),
    )
    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 1
    assert result[0]['request_id'] == 'PR-3'
