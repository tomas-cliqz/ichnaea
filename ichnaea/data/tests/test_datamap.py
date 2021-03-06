from collections import defaultdict
from datetime import timedelta

from ichnaea.data.tasks import update_datamap
from ichnaea.models.content import (
    DataMap,
    encode_datamap_grid,
)
from ichnaea.tests.base import CeleryTestCase
from ichnaea import util


class TestDataMap(CeleryTestCase):

    def setUp(self):
        super(TestDataMap, self).setUp()
        self.today = util.utcnow().date()
        self.yesterday = self.today - timedelta(days=1)

    def _add(self, entries):
        for lat, lon, time in entries:
            lat, lon = DataMap.scale(lat, lon)
            self.session.add(DataMap.shard_model(lat, lon)(
                grid=(lat, lon), created=time, modified=time))
        self.session.flush()

    def _check_position(self, stat, lat, lon):
        self.assertEqual(stat.grid, DataMap.scale(lat, lon))

    def _queue(self, pairs):
        grids = defaultdict(list)
        for lat, lon in pairs:
            lat, lon = DataMap.scale(lat, lon)
            shard_id = DataMap.shard_id(lat, lon)
            grids[shard_id].append(encode_datamap_grid(lat, lon))

        for shard_id, values in grids.items():
            queue = self.celery_app.data_queues['update_datamap_' + shard_id]
            queue.enqueue(list(values), json=False)

    def test_empty(self):
        for shard_id, shard in DataMap.shards().items():
            update_datamap.delay(shard_id=shard_id).get()
            self.assertEqual(self.session.query(shard).count(), 0)

    def test_one(self):
        lat = 1.234567
        lon = 2.345678
        shard_id = DataMap.shard_id(*DataMap.scale(lat, lon))
        self._queue([(lat, lon)])
        update_datamap.delay(shard_id=shard_id).get()

        grids = self.session.query(DataMap.shards()[shard_id]).all()
        self.assertEqual(len(grids), 1)
        self._check_position(grids[0], 1.235, 2.346)
        self.assertEqual(grids[0].created, self.today)
        self.assertEqual(grids[0].modified, self.today)

    def test_update(self):
        lat = 1.0
        lon = 2.0
        shard_id = DataMap.shard_id(*DataMap.scale(lat, lon))
        self._add([(lat, lon, self.yesterday)])
        self._queue([(lat, lon)])
        update_datamap.delay(shard_id=shard_id).get()

        grids = self.session.query(DataMap.shards()[shard_id]).all()
        self.assertEqual(len(grids), 1)
        self._check_position(grids[0], 1.0, 2.0)
        self.assertEqual(grids[0].created, self.yesterday)
        self.assertEqual(grids[0].modified, self.today)

    def test_multiple(self):
        self._add([
            (1.0, 2.0, self.yesterday),
            (-10.0, 40.0, self.yesterday),
        ])
        self._queue([
            (1.0, 2.0), (1.0, 2.0),
            (40.0011, 3.0011), (40.0012, 3.0012), (40.0013, 3.0013),
            (0.0, 0.0),
            (1.0, 2.0),
            (1.00001, 2.00001),
        ])
        for shard_id in DataMap.shards():
            update_datamap.delay(batch=2, shard_id=shard_id).get()

        rows = []
        for shard in DataMap.shards().values():
            rows.extend(self.session.query(shard).all())

        self.assertEqual(len(rows), 4)
        created = set()
        modified = set()
        positions = set()
        for row in rows:
            lat, lon = row.grid
            created.add(row.created)
            modified.add(row.modified)
            positions.add((lat / 1000.0, lon / 1000.0))

        self.assertEqual(created, set([self.today, self.yesterday]))
        self.assertEqual(modified, set([self.today, self.yesterday]))
        self.assertEqual(
            positions,
            set([(1.0, 2.0), (-10.0, 40.0), (0.0, 0.0), (40.001, 3.001)]))
