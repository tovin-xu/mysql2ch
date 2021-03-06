import datetime
import json
import logging

import dateutil.parser
from decimal import Decimal

from kafka import KafkaAdminClient
from kafka.admin import NewPartitions

from mysql2ch import settings

logger = logging.getLogger('mysql2ch.common')

CONVERTERS = {
    'date': dateutil.parser.parse,
    'datetime': dateutil.parser.parse,
    'decimal': Decimal,
}


def complex_decode(xs):
    if isinstance(xs, dict):
        ret = {}
        for k in xs:
            ret[k.decode()] = complex_decode(xs[k])
        return ret
    elif isinstance(xs, list):
        ret = []
        for x in xs:
            ret.append(complex_decode(x))
        return ret
    elif isinstance(xs, bytes):
        return xs.decode()
    else:
        return xs


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return {'val': obj.strftime('%Y-%m-%d %H:%M:%S'), '_spec_type': 'datetime'}
        elif isinstance(obj, datetime.date):
            return {'val': obj.strftime('%Y-%m-%d'), '_spec_type': 'date'}
        elif isinstance(obj, Decimal):
            return {'val': str(obj), '_spec_type': 'decimal'}
        else:
            return super().default(obj)


def object_hook(obj):
    _spec_type = obj.get('_spec_type')
    if not _spec_type:
        return obj

    if _spec_type in CONVERTERS:
        return CONVERTERS[_spec_type](obj['val'])
    else:
        raise TypeError('Unknown {}'.format(_spec_type))


def init_partitions():
    client = KafkaAdminClient(
        bootstrap_servers=settings.KAFKA_SERVER,
    )
    try:
        client.create_partitions(topic_partitions={
            settings.KAFKA_TOPIC: NewPartitions(total_count=len(settings.PARTITIONS.keys()))
        })
    except Exception as e:
        logger.warning(f'init_partitions error:{e}')
