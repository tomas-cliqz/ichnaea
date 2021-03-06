"""
Implementation of submit specific HTTP service views.
"""

from redis import RedisError

from ichnaea.api.exceptions import (
    ParseError,
    ServiceUnavailable,
    UploadSuccess,
    UploadSuccessV0,
)
from ichnaea.api.submit.schema_v0 import SUBMIT_V0_SCHEMA
from ichnaea.api.submit.schema_v1 import SUBMIT_V1_SCHEMA
from ichnaea.api.submit.schema_v2 import SUBMIT_V2_SCHEMA

from ichnaea.api.views import BaseAPIView
from ichnaea.data.tasks import queue_reports


class BaseSubmitView(BaseAPIView):
    """Common base class for all submit related views."""

    error_on_invalidkey = False  #:
    view_type = 'submit'  #:

    #: :exc:`ichnaea.api.exceptions.UploadSuccess`
    success = UploadSuccess

    def __init__(self, request):
        super(BaseSubmitView, self).__init__(request)
        self.nickname = self.decode_request_header('X-Nickname')

    def decode_request_header(self, header_name):
        value = self.request.headers.get(header_name, None)
        if isinstance(value, str):  # pragma: no cover
            value = value.decode('utf-8', 'ignore')
        return value

    def emit_upload_metrics(self, value, api_key):
        tags = None
        if api_key.should_log('submit'):
            tags = ['key:%s' % api_key.name]
        self.stats_client.incr('data.batch.upload', tags=tags)

    def preprocess(self):
        try:
            request_data, errors = self.preprocess_request()

            if not request_data:
                # don't allow completely empty submit request
                raise self.prepare_exception(ParseError())

        except ParseError:
            # capture JSON exceptions for submit calls
            self.raven_client.captureException()
            raise

        return request_data

    def submit(self, api_key):
        # may raise HTTP error
        request_data = self.preprocess()

        # data pipeline using new internal data format
        reports = request_data['items']
        batch_size = 50
        for i in range(0, len(reports), batch_size):
            batch = reports[i:i + batch_size]
            # insert reports, expire the task if it wasn't processed
            # after six hours to avoid queue overload
            queue_reports.apply_async(
                kwargs={
                    'api_key': api_key.valid_key,
                    'nickname': self.nickname,
                    'reports': batch,
                },
                expires=21600)

        self.emit_upload_metrics(len(reports), api_key)

    def view(self, api_key):
        """
        Execute the view code and return a response.
        """
        try:
            self.submit(api_key)
        except RedisError:
            raise self.prepare_exception(ServiceUnavailable())

        return self.prepare_exception(self.success())


class SubmitV0View(BaseSubmitView):
    """"Submit version 0 view for `/v1/submit`."""

    metric_path = 'v1.submit'  #:
    route = '/v1/submit'  #:
    schema = SUBMIT_V0_SCHEMA  #:

    #: :exc:`ichnaea.api.exceptions.UploadSuccessV0`
    success = UploadSuccessV0


class SubmitV1View(BaseSubmitView):
    """"Submit version 1 view for `/v1/geosubmit`."""

    metric_path = 'v1.geosubmit'  #:
    route = '/v1/geosubmit'  #:
    schema = SUBMIT_V1_SCHEMA  #:


class SubmitV2View(BaseSubmitView):
    """"Submit version 2 view for `/v2/geosubmit`."""

    metric_path = 'v2.geosubmit'  #:
    route = '/v2/geosubmit'  #:
    schema = SUBMIT_V2_SCHEMA  #:
