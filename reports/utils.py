# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, CloudBlue
# All rights reserved.
#

from datetime import datetime
from functools import reduce
from operator import getitem


def convert_to_datetime(value):
    if value == "" or value == "-":
        return "-"

    return datetime.strptime(
        value.replace("T", " ").replace("+00:00", "").split('.')[0],
        "%Y-%m-%d %H:%M:%S",
    )


def get_value(base, path, default="-"):
    try:
        return reduce(lambda value, path_elem: getitem(value, path_elem), path, base)
    except (IndexError, KeyError, TypeError):
        return default


def parameter_value(parameter_id, parameter_list, default="-"):
    try:
        parameter = list(filter(lambda param: param['id'] == parameter_id, parameter_list))[0]
    except IndexError:
        return default
    
    if 'structured_value' in parameter:
        return parameter['structured_value']
    if 'value' in parameter:
        return parameter['value']
    return default
