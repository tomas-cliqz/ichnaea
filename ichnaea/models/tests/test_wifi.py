from sqlalchemy.exc import (
    SQLAlchemyError,
)

from ichnaea.models import StationSource
from ichnaea.models.wifi import (
    decode_mac,
    encode_mac,
    WifiShard,
    WifiShard0,
    WifiShardF,
)
from ichnaea.tests.base import (
    TestCase,
    DBTestCase,
    GB_LAT,
    GB_LON,
)
from ichnaea import util


class TestMacCodec(TestCase):

    def test_decode(self):
        value = decode_mac(b'\xab\xcd\xed\x124V')
        self.assertEqual(value, 'abcded123456')

        value = decode_mac(b'q83tEjRW', codec='base64')
        self.assertEqual(value, 'abcded123456')

    def test_encode(self):
        value = encode_mac('abcded123456')
        self.assertEqual(len(value), 6)
        self.assertEqual(value, b'\xab\xcd\xed\x124V')

        value = encode_mac('abcded123456', codec='base64')
        self.assertEqual(value, b'q83tEjRW')

    def test_max(self):
        value = encode_mac('ffffffffffff')
        self.assertEqual(len(value), 6)
        self.assertEqual(value, b'\xff\xff\xff\xff\xff\xff')

        value = encode_mac('ffffffffffff', codec='base64')
        self.assertEqual(value, b'////////')

    def test_min(self):
        value = encode_mac('000000000000')
        self.assertEqual(len(value), 6)
        self.assertEqual(value, b'\x00\x00\x00\x00\x00\x00')

        value = encode_mac('000000000000', codec='base64')
        self.assertEqual(value, b'AAAAAAAA')


class TestWifiShard(DBTestCase):

    def test_shard_id(self):
        self.assertEqual(WifiShard.shard_id('111101123456'), '0')
        self.assertEqual(WifiShard.shard_id('0000f0123456'), 'f')
        self.assertEqual(WifiShard.shard_id(''), None)
        self.assertEqual(WifiShard.shard_id(None), None)

        mac = encode_mac('0000f0123456')
        self.assertEqual(WifiShard.shard_id(mac), 'f')

    def test_shard_model(self):
        self.assertIs(WifiShard.shard_model('111101123456'), WifiShard0)
        self.assertIs(WifiShard.shard_model('0000f0123456'), WifiShardF)
        self.assertIs(WifiShard.shard_model(''), None)
        self.assertIs(WifiShard.shard_model(None), None)

        mac = encode_mac('0000f0123456')
        self.assertEqual(WifiShard.shard_model(mac), WifiShardF)

    def test_init(self):
        wifi = WifiShard0(mac='111101123456')
        self.session.add(wifi)
        self.session.flush()

        wifis = (self.session.query(WifiShard0)
                             .filter(WifiShard0.mac == '111101123456')).all()
        self.assertEqual(wifis[0].mac, '111101123456')

    def test_init_empty(self):
        wifi = WifiShard0()
        self.session.add(wifi)
        with self.assertRaises(SQLAlchemyError):
            self.session.flush()

    def test_init_fail(self):
        wifi = WifiShard0(mac='abc')
        self.session.add(wifi)
        with self.assertRaises(SQLAlchemyError):
            self.session.flush()

    def test_fields(self):
        now = util.utcnow()
        today = now.date()
        self.session.add(WifiShard.create(
            mac='111101123456', created=now, modified=now,
            lat=GB_LAT, max_lat=GB_LAT, min_lat=GB_LAT,
            lon=GB_LON, max_lon=GB_LON, min_lon=GB_LON,
            radius=200, region='GB', samples=10, source=StationSource.gnss,
            block_first=today, block_last=today, block_count=1,
            _raise_invalid=True,
        ))
        self.session.flush()

        wifi = self.session.query(WifiShard0).first()
        self.assertEqual(wifi.mac, '111101123456')
        self.assertEqual(wifi.created, now)
        self.assertEqual(wifi.modified, now)
        self.assertEqual(wifi.lat, GB_LAT)
        self.assertEqual(wifi.max_lat, GB_LAT)
        self.assertEqual(wifi.min_lat, GB_LAT)
        self.assertEqual(wifi.lon, GB_LON)
        self.assertEqual(wifi.max_lon, GB_LON)
        self.assertEqual(wifi.min_lon, GB_LON)
        self.assertEqual(wifi.radius, 200)
        self.assertEqual(wifi.region, 'GB')
        self.assertEqual(wifi.samples, 10)
        self.assertEqual(wifi.source, StationSource.gnss)
        self.assertEqual(wifi.block_first, today)
        self.assertEqual(wifi.block_last, today)
        self.assertEqual(wifi.block_count, 1)

    def test_mac_unhex(self):
        stmt = 'insert into wifi_shard_0 (mac) values (unhex("111101123456"))'
        self.session.execute(stmt)
        self.session.flush()
        wifi = self.session.query(WifiShard0).one()
        self.assertEqual(wifi.mac, '111101123456')

    def test_mac_hex(self):
        self.session.add(WifiShard0(mac='111101123456'))
        self.session.flush()
        stmt = 'select hex(`mac`) from wifi_shard_0'
        row = self.session.execute(stmt).fetchone()
        self.assertEqual(row, ('111101123456', ))

    def test_score(self):
        now = util.utcnow()
        wifi = WifiShard.create(
            mac='111101123456', created=now, modified=now,
            radius=10, samples=2,
        )
        self.assertAlmostEqual(wifi.score(now), 0.1, 2)
