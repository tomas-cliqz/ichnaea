from ichnaea.api.locate.cell import (
    CellPositionSource,
    OCIDPositionSource,
)
from ichnaea.api.locate.constants import (
    CELL_MAX_ACCURACY,
    CELLAREA_MIN_ACCURACY,
)
from ichnaea.api.locate.tests.base import BaseSourceTest
from ichnaea.tests.factories import (
    CellAreaFactory,
    CellAreaOCIDFactory,
    CellShardFactory,
    CellOCIDFactory,
)
from ichnaea import util


class TestCellPosition(BaseSourceTest):

    TestSource = CellPositionSource

    def test_check_empty(self):
        query = self.model_query()
        results = self.source.result_type().new_list()
        self.assertFalse(self.source.should_search(query, results))

    def test_empty(self):
        query = self.model_query()
        with self.db_call_checker() as check_db_calls:
            results = self.source.search(query)
            self.check_model_results(results, None)
            check_db_calls(rw=0, ro=0)

    def test_cell(self):
        now = util.utcnow()
        cell = CellShardFactory(samples=10)
        self.session.flush()

        query = self.model_query(cells=[cell])
        results = self.source.search(query)
        self.check_model_results(results, [cell])
        self.assertAlmostEqual(
            results.best(query.expected_accuracy).score, cell.score(now), 4)

    def test_cell_wrong_cid(self):
        cell = CellShardFactory()
        self.session.flush()
        cell.cid += 1

        query = self.model_query(cells=[cell])
        results = self.source.search(query)
        self.check_model_results(results, None)

    def test_multiple_cells(self):
        now = util.utcnow()
        cell = CellShardFactory(samples=20)
        cell2 = CellShardFactory(radio=cell.radio, mcc=cell.mcc, mnc=cell.mnc,
                                 lac=cell.lac, cid=cell.cid + 1,
                                 lat=cell.lat + 1.0, lon=cell.lon + 1.0,
                                 samples=10)
        self.session.flush()

        query = self.model_query(cells=[cell, cell2])
        results = self.source.search(query)
        self.check_model_results(
            results, [cell],
            lat=cell.lat + 0.5, lon=cell.lon + 0.5,
            accuracy=CELL_MAX_ACCURACY)
        self.assertAlmostEqual(
            results.best(query.expected_accuracy).score,
            cell.score(now) + cell2.score(now), 4)

    def test_incomplete_keys(self):
        cells = CellAreaFactory.build_batch(4)
        cells[0].radio = None
        cells[1].mcc = None
        cells[2].mnc = None
        cells[3].lac = None

        with self.db_call_checker() as check_db_calls:
            query = self.model_query(cells=cells)
            results = self.source.result_type().new_list()
            self.assertFalse(self.source.should_search(query, results))
            check_db_calls(rw=0, ro=0)

    def test_smallest_area(self):
        now = util.utcnow()
        area = CellAreaFactory(radius=25000, num_cells=8)
        area2 = CellAreaFactory(radius=30000, lat=area.lat + 0.2, num_cells=6)
        self.session.flush()

        query = self.model_query(cells=[area, area2])
        results = self.source.search(query)
        self.check_model_results(results, [area])
        self.assertAlmostEqual(
            results.best(query.expected_accuracy).score, area.score(now), 4)

    def test_minimum_radius(self):
        areas = CellAreaFactory.create_batch(2)
        areas[0].radius = CELLAREA_MIN_ACCURACY - 2000
        areas[1].radius = CELLAREA_MIN_ACCURACY + 3000
        areas[1].lat = areas[0].lat + 0.2
        self.session.flush()

        query = self.model_query(cells=areas)
        results = self.source.search(query)
        self.check_model_results(
            results, [areas[0]], accuracy=CELLAREA_MIN_ACCURACY)


class TestOCIDPositionSource(BaseSourceTest):

    TestSource = OCIDPositionSource

    def test_check_empty(self):
        query = self.model_query()
        results = self.source.result_type().new_list()
        self.assertFalse(self.source.should_search(query, results))

    def test_empty(self):
        query = self.model_query()
        with self.db_call_checker() as check_db_calls:
            results = self.source.search(query)
            self.check_model_results(results, None)
            check_db_calls(rw=0, ro=0)

    def test_cell(self):
        now = util.utcnow()
        cell = CellOCIDFactory(samples=10)
        self.session.flush()
        query = self.model_query(cells=[cell])
        results = self.source.search(query)
        self.check_model_results(results, [cell])
        self.assertAlmostEqual(
            results.best(query.expected_accuracy).score, cell.score(now), 4)

    def test_cell_area(self):
        now = util.utcnow()
        area = CellAreaOCIDFactory(num_cells=8)
        self.session.flush()
        query = self.model_query(cells=[area])
        results = self.source.search(query)
        self.check_model_results(results, [area])
        self.assertAlmostEqual(
            results.best(query.expected_accuracy).score, area.score(now), 4)
