from ichnaea.api.locate.internal import InternalRegionSource
from ichnaea.api.locate.tests.base import BaseSourceTest
from ichnaea.geocode import GEOCODER
from ichnaea.tests.factories import (
    CellAreaFactory,
    WifiShardFactory,
)
from ichnaea import util


class TestRegionSource(BaseSourceTest):

    TestSource = InternalRegionSource
    api_type = 'region'

    def test_from_mcc(self):
        region = GEOCODER.regions_for_mcc(235, metadata=True)[0]
        cell = CellAreaFactory(mcc=235, num_cells=10)
        self.session.flush()

        query = self.model_query(cells=[cell])
        results = self.source.search(query)
        self.check_model_result(results, region)
        self.assertAlmostEqual(results[0].score, 1.0, 4)
        self.check_stats(counter=[
            (self.api_type + '.source',
                ['key:test', 'region:none', 'source:internal',
                 'accuracy:low', 'status:hit']),
        ])

    def test_ambiguous_mcc(self):
        now = util.utcnow()
        regions = GEOCODER.regions_for_mcc(234, metadata=True)
        cell = CellAreaFactory(mcc=234, num_cells=10)
        self.session.flush()

        query = self.model_query(cells=[cell])
        results = self.source.search(query)
        self.check_model_result(results, regions)
        best_result = results.best(query.expected_accuracy)
        self.assertEqual(best_result.region_code, 'GB')
        for result in results:
            score = 0.25
            if result.region_code == 'GB':
                score += cell.score(now)
            self.assertAlmostEqual(result.score, score, 4)
        self.check_stats(counter=[
            (self.api_type + '.source',
                ['key:test', 'region:none', 'source:internal',
                 'accuracy:low', 'status:hit']),
        ])

    def test_multiple_mcc(self):
        now = util.utcnow()
        region = GEOCODER.regions_for_mcc(235, metadata=True)[0]
        cell = CellAreaFactory(mcc=234, num_cells=6)
        cell2 = CellAreaFactory(mcc=235, num_cells=8)
        self.session.flush()

        query = self.model_query(cells=[cell, cell2])
        results = self.source.search(query)
        self.assertTrue(len(results) > 2)
        best_result = results.best(query.expected_accuracy)
        self.assertEqual(best_result.region_code, region.code)
        self.assertAlmostEqual(best_result.score, 1.25 + cell.score(now), 4)

    def test_invalid_mcc(self):
        cell = CellAreaFactory.build(mcc=235, num_cells=10)
        cell.mcc = 999
        query = self.model_query(cells=[cell])
        results = self.source.search(query)
        self.check_model_result(results, None)

    def test_wifi(self):
        wifis = WifiShardFactory.create_batch(2)
        self.session.flush()

        query = self.model_query(wifis=wifis)
        results = self.source.search(query)
        self.check_model_result(results, None)
