"""
Colander schemata describing the public v2/geosubmit HTTP API.
"""

import colander

from ichnaea.api.schema import (
    OptionalIntNode,
    OptionalMappingSchema,
    OptionalSequenceSchema,
)
from ichnaea.api.submit.schema import (
    BluetoothBeaconsSchema,
    CellTowerSchema,
    PositionSchema,
    ReportSchema,
)


class CellTowersV2Schema(OptionalSequenceSchema):

    @colander.instantiate()
    class SequenceItem(CellTowerSchema):

        primaryScramblingCode = OptionalIntNode()


class SubmitV2Schema(OptionalMappingSchema):

    @colander.instantiate()
    class items(OptionalSequenceSchema):  # NOQA

        @colander.instantiate()
        class SequenceItem(ReportSchema):

            bluetoothBeacons = BluetoothBeaconsSchema(missing=())
            cellTowers = CellTowersV2Schema(missing=())
            position = PositionSchema(missing=None)

            # connection is not mapped on purpose
            # connection = ConnectionSchema(missing=None)


SUBMIT_V2_SCHEMA = SubmitV2Schema()
