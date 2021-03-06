"""
Classes representing an abstract query result or
a concrete position or region result.
"""

from collections import defaultdict

from ichnaea.api.locate.constants import DataAccuracy
from ichnaea.constants import DEGREE_DECIMAL_PLACES

try:
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    from ordereddict import OrderedDict


class Result(object):
    """An empty query result."""

    _required = ()  #: The list of required attributes.

    def __init__(self, accuracy=None, region_code=None, region_name=None,
                 fallback=None, lat=None, lon=None, source=None, score=0.0):
        self.accuracy = self._round(accuracy)
        self.fallback = fallback
        self.lat = self._round(lat)
        self.lon = self._round(lon)
        self.region_code = region_code
        self.region_name = region_name
        self.score = score
        self.source = source

    def __repr__(self):
        values = []
        for field in self._required:
            values.append('%s:%s' % (field, getattr(self, field, '')))
        return '{klass}<{values}>'.format(
            klass=self.__class__.__name__,
            values=', '.join(values),
        )

    def _round(self, value):
        if value is not None:
            value = round(value, DEGREE_DECIMAL_PLACES)
        return value

    @property
    def data_accuracy(self):
        """Return the accuracy class of this result."""
        if self.empty():
            return DataAccuracy.none
        return DataAccuracy.from_number(self.accuracy)

    def empty(self):
        """Does this result include any data?"""
        if not self._required:
            return True
        all_fields = []
        for field in self._required:
            all_fields.append(getattr(self, field, None))
        return None in all_fields

    def as_list(self):
        """Return a new result list including this result."""
        raise NotImplementedError()

    def new_list(self):
        """Return a new empty result list."""
        raise NotImplementedError()

    def satisfies(self, query):
        """Does this result match the expected query accuracy?"""
        return False


class Position(Result):
    """The position returned by a position query."""

    _required = ('lat', 'lon', 'accuracy', 'score')  #:

    def as_list(self):
        """Return a new position result list including this result."""
        return PositionResultList(self)

    def new_list(self):
        """Return a new empty result list."""
        return PositionResultList()

    def satisfies(self, query):
        if self.data_accuracy <= query.expected_accuracy:
            return True
        return False


class Region(Result):
    """The region returned by a region query."""

    _required = ('region_code', 'region_name', 'accuracy', 'score')  #:

    def as_list(self):
        """Return a new region result list including this result."""
        return RegionResultList(self)

    def new_list(self):
        """Return a new empty result list."""
        return RegionResultList()

    def satisfies(self, query):
        return not self.empty()


class ResultList(object):
    """A collection of query results."""

    result_type = None  #:

    def __init__(self, result=None):
        self._results = []
        if result is not None:
            self.add(result)

    def add(self, results):
        """Add one or more results to the collection."""
        if isinstance(results, Result):
            self._results.append(results)
        else:
            self._results.extend(list(results))

    def __getitem__(self, index):
        return self._results[index]

    def __len__(self):
        return len(self._results)

    def __repr__(self):
        return 'ResultList: %s' % ', '.join([repr(res) for res in self])

    def satisfies(self, query):
        """
        Is one of the results in the collection good enough to satisfy
        the expected query data accuracy?
        """
        for result in self:
            if result.satisfies(query):
                return True
        return False

    def best(self, expected_accuracy):
        """Return the best result in the collection."""
        raise NotImplementedError()


class PositionResultList(ResultList):
    """A collection of position results."""

    result_type = Position  #:

    def best(self, expected_accuracy):
        """Return the best result in the collection."""
        accurate_results = OrderedDict(matches=[], misses=[], empty=[])
        # Group the results by whether or not they match the expected
        # accuracy of the query.
        for result in self:
            if result.empty():
                accurate_results['empty'].append(result)
            elif result.data_accuracy <= expected_accuracy:
                accurate_results['matches'].append(result)
            else:
                accurate_results['misses'].append(result)

        if accurate_results['matches']:
            most_accurate_results = accurate_results['matches']
        elif accurate_results['misses']:
            most_accurate_results = accurate_results['misses']
        elif accurate_results['empty']:
            # only empty results, they are all equal
            return accurate_results['empty'][0]
        else:
            # totally empty result list, return new empty result
            return self.result_type()

        if len(most_accurate_results) == 1:
            return most_accurate_results[0]

        def best_result(result):
            # sort descending, take higher score and
            # break tie by using the smaller accuracy/radius
            return (result.score, (result.accuracy or 0.0) * -1)

        sorted_results = sorted(
            most_accurate_results, key=best_result, reverse=True)
        return sorted_results[0]


class RegionResultList(ResultList):
    """A collection of region results."""

    result_type = Region  #:

    def best(self, expected_accuracy):
        """Return the best result in the collection."""
        # group by region code
        grouped = defaultdict(list)
        for result in self:
            if not result.empty():
                grouped[result.region_code].append(result)

        regions = []
        for code, values in grouped.items():
            # Pick the first found value, this determines the source
            # and possible fallback flag on the end result.
            region = values[0]
            regions.append((
                sum([value.score for value in values]),
                region.accuracy,
                region))

        if not regions:
            return self.result_type()

        # pick the region with the highest combined score,
        # break tie by region with the largest radius
        sorted_regions = sorted(regions, reverse=True)
        return sorted_regions[0][2]
