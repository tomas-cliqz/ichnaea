import logging

from cornice import Service
from pyramid.httpexceptions import HTTPError
from pyramid.response import Response

from ichnaea.decimaljson import dumps
from ichnaea.schema import SearchSchema
from ichnaea.service.search.search import search_request

logger = logging.getLogger('ichnaea')


def configure_search(config):
    config.scan('ichnaea.service.search.views')


class _JSONError(HTTPError):
    def __init__(self, errors, status=400):
        body = {'errors': errors}
        Response.__init__(self, dumps(body))
        self.status = status
        self.content_type = 'application/json'


def error_handler(errors):
    logger.debug('error_handler' + repr(errors))
    return _JSONError(errors, errors.status)


MSG_ONE_OF = 'You need to provide a mapping with least one cell or wifi entry.'


def check_cell_or_wifi(data, request):
    cell = data.get('cell', ())
    wifi = data.get('wifi', ())
    if not any(wifi) and not any(cell):
        request.errors.add('body', 'body', MSG_ONE_OF)


def search_validator(request):
    if len(request.errors):
        return
    check_cell_or_wifi(request.validated, request)


search = Service(
    name='search',
    path='/v1/search',
    description="Search for your current location.",
)


@search.post(renderer='json', accept="application/json",
             schema=SearchSchema, error_handler=error_handler,
             validators=search_validator)
def search_post(request):
    """
    Determine the current location based on provided data about
    nearby cell towers or wifi base stations.

    The request body is a nested JSON mapping, for example:

    .. code-block:: javascript

        {
            "radio": "gsm",
            "cell": [
                {
                    "radio": "umts",
                    "mcc": 123,
                    "mnc": 123,
                    "lac": 12345,
                    "cid": 12345,
                    "signal": -61,
                    "asu": 26
                }
            ],
            "wifi": [
                {
                    "key": "3680873e9b83738eb72946d19e971e023e51fd01",
                    "channel": 11,
                    "frequency": 2412,
                    "signal": -50
                }
            ]
        }

    The mapping can contain zero to many entries per category. At least for one
    category an entry has to be provided. Empty categories can be omitted
    entirely.

    The top-level radio type must be one of "gsm", "cdma" or be omitted (for
    example for tablets or laptops without a cell radio).

    The cell specific radio entry must be one of "gsm", "cdma", "umts" or
    "lte".

    See :ref:`cell_records` for a detailed explanation of the cell record
    fields for the different network standards.

    For `wifi` entries, the `key` field is required. The client must check the
    Wifi SSID for a `_nomap` suffix. Wifi's with such a suffix must not be
    submitted to the server. Wifi's with a hidden SSID should not be submitted
    to the server either.

    The `key` is a the BSSID or MAC address of the wifi network. So for example
    a valid key would look similar to `01:23:45:67:89:ab`.

    A successful result will be:

    .. code-block:: javascript

        {
            "status": "ok",
            "lat": -22.7539192,
            "lon": -43.4371081,
            "accuracy": 1000
        }

    The latitude and longitude are numbers, with seven decimal places of
    actual precision. The coordinate reference system is WGS 84. The accuracy
    is an integer measured in meters and defines a circle around the location.

    If no position can be determined, you instead get:

    .. code-block:: javascript

        {
            "status": "not_found"
        }

    If the request couldn't be processed or a validation error occurred, you
    get a HTTP status code of 400 and a JSON body:

    .. code-block:: javascript

        {
            "errors": {}
        }

    The errors mapping contains detailed information about the errors.
    """
    return search_request(request)


submit = Service(
    name='submit',
    path='/v1/submit',
    description="Submit a measurement result for a location.",
)