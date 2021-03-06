"""
Contains helper functions for various geo related calculations.

These are implemented in Cython / C using NumPy.
"""

from libc.math cimport asin, cos, fmax, fmin, M_PI, pow, sin, sqrt
from numpy cimport double_t, ndarray

import numpy

cdef double EARTH_RADIUS = 6371.0  #: Earth radius in km.
cdef double MAX_LAT = 85.051  #: Max Web Mercator latitude
cdef double MIN_LAT = -85.051  #: Min Web Mercator latitude
cdef double MAX_LON = 180.0  #: Max Web Mercator longitude
cdef double MIN_LON = -180.0  #: Min Web Mercator longitude

cdef double* RANDOM_LAT = [
    0.8218, 0.1382, 0.8746, 0.0961, 0.8159, 0.2876, 0.6191, 0.0897,
    0.3755, 0.9412, 0.3231, 0.5353, 0.225, 0.0555, 0.1591, 0.3871,
    0.8714, 0.2496, 0.7499, 0.0279, 0.3794, 0.8224, 0.1459, 0.5992,
    0.3004, 0.5599, 0.8807, 0.1546, 0.7401, 0.834, 0.7581, 0.2057,
    0.4496, 0.1683, 0.3266, 0.1515, 0.9731, 0.4078, 0.9517, 0.6511,
    0.9287, 0.8405, 0.4579, 0.9462, 0.2645, 0.7315, 0.458, 0.3744,
    0.4637, 0.3643, 0.5599, 0.815, 0.8971, 0.6997, 0.1595, 0.0066,
    0.8548, 0.6805, 0.9786, 0.8293, 0.0041, 0.5027, 0.6556, 0.0273,
    0.0949, 0.6407, 0.0867, 0.2891, 0.9741, 0.2599, 0.3148, 0.8786,
    0.6432, 0.2424, 0.195, 0.4672, 0.3097, 0.0697, 0.493, 0.5484,
    0.7611, 0.2611, 0.6947, 0.632, 0.466, 0.1275, 0.4001, 0.7947,
    0.8693, 0.8536, 0.686, 0.9742, 0.8517, 0.6809, 0.0395, 0.7739,
    0.4133, 0.5117, 0.9562, 0.7003, 0.261, 0.9772, 0.1694, 0.2982,
    0.3459, 0.3611, 0.7994, 0.6209, 0.2771, 0.8388, 0.9764, 0.698,
    0.1615, 0.3205, 0.0766, 0.0832, 0.3695, 0.4471, 0.8077, 0.4343,
    0.716, 0.6502, 0.351, 0.1502, 0.9186, 0.3677, 0.8139, 0.6609,
    0.2635, 0.1418, 0.4809, 0.15, 0.1809, 0.1874, 0.0272, 0.6513,
    0.6073, 0.5867, 0.8034, 0.744, 0.3532, 0.2124, 0.2574, 0.0536,
    0.2066, 0.4326, 0.4771, 0.5265, 0.1183, 0.0778, 0.7552, 0.9647,
    0.4392, 0.3256, 0.4935, 0.8999, 0.1643, 0.4203, 0.8042, 0.8463,
    0.1369, 0.0638, 0.7694, 0.9243, 0.3213, 0.1072, 0.8301, 0.4133,
    0.731, 0.5625, 0.3609, 0.1266, 0.8004, 0.5228, 0.5915, 0.533,
    0.8568, 0.9744, 0.1226, 0.2214, 0.8163, 0.3973, 0.0492, 0.0257,
    0.4362, 0.6687, 0.7528, 0.1546, 0.8486, 0.1903, 0.3155, 0.4483,
    0.2951, 0.625, 0.1373, 0.3942, 0.7765, 0.1284, 0.3895, 0.0197,
]

cdef double* RANDOM_LON = [
    0.3366, 0.9381, 0.9013, 0.7668, 0.4397, 0.0931, 0.4599, 0.7187,
    0.2778, 0.9749, 0.8002, 0.867, 0.6856, 0.5892, 0.0715, 0.1547,
    0.6151, 0.8931, 0.0535, 0.0219, 0.669, 0.7393, 0.3453, 0.2699,
    0.2595, 0.3468, 0.5989, 0.5349, 0.6499, 0.973, 0.1924, 0.6981,
    0.0049, 0.7285, 0.2222, 0.907, 0.2086, 0.6255, 0.438, 0.7481,
    0.3976, 0.8766, 0.0788, 0.072, 0.4321, 0.7367, 0.5851, 0.7282,
    0.4919, 0.7602, 0.8871, 0.6833, 0.7713, 0.7626, 0.1701, 0.2766,
    0.7929, 0.9612, 0.5676, 0.0297, 0.1039, 0.1106, 0.3217, 0.7889,
    0.9967, 0.4868, 0.1648, 0.9118, 0.5572, 0.2365, 0.2466, 0.4317,
    0.2269, 0.107, 0.359, 0.8855, 0.8001, 0.6695, 0.659, 0.9648,
    0.3251, 0.7101, 0.5131, 0.693, 0.7862, 0.5623, 0.3496, 0.3707,
    0.4111, 0.5193, 0.4851, 0.5421, 0.7793, 0.163, 0.4101, 0.5883,
    0.7102, 0.7474, 0.1109, 0.4315, 0.2044, 0.0695, 0.9451, 0.8879,
    0.349, 0.7498, 0.7603, 0.2392, 0.6879, 0.8437, 0.8868, 0.5658,
    0.2767, 0.6489, 0.1796, 0.3364, 0.7185, 0.966, 0.4197, 0.0102,
    0.8892, 0.2361, 0.9872, 0.5313, 0.9641, 0.8675, 0.8401, 0.253,
    0.8521, 0.3932, 0.9406, 0.1951, 0.2688, 0.5872, 0.0671, 0.5138,
    0.4509, 0.0914, 0.8911, 0.2342, 0.2115, 0.4977, 0.0297, 0.3052,
    0.5143, 0.5642, 0.0268, 0.8893, 0.9661, 0.0796, 0.5527, 0.8903,
    0.3143, 0.7346, 0.0573, 0.3421, 0.4941, 0.4112, 0.6782, 0.8287,
    0.5729, 0.6492, 0.2224, 0.8022, 0.9722, 0.5225, 0.5149, 0.092,
    0.4232, 0.6636, 0.7266, 0.5325, 0.4495, 0.8719, 0.9192, 0.2562,
    0.327, 0.3825, 0.1051, 0.4907, 0.167, 0.9088, 0.3463, 0.511,
    0.0884, 0.071, 0.1059, 0.0939, 0.5202, 0.6005, 0.9173, 0.5957,
    0.8279, 0.7611, 0.8101, 0.9157, 0.004, 0.9844, 0.3872, 0.7046,
]

cdef inline double deg2rad(double degrees):
    return degrees * M_PI / 180.0


cpdef tuple aggregate_position(ndarray[double_t, ndim=2] circles,
                               double minimum_accuracy):
    """
    Calculate the aggregate position based on a number of circles
    (numpy 3-column arrays of lat/lon/radius).

    Return the position and an accuracy estimate, but at least
    use the minimum_accuracy.
    """
    cdef ndarray[double_t, ndim=2] points
    cdef double lat, lon, radius
    cdef double p_dist, p_lat, p_lon, p_radius

    if len(circles) == 1:
        lat = circles[0][0]
        lon = circles[0][1]
        radius = circles[0][2]
        radius = fmax(radius, minimum_accuracy)
        return (lat, lon, radius)

    points, _ = numpy.hsplit(circles, [2])
    lat, lon = centroid(points)

    # Given the centroid of all the circles, calculate the distance
    # between that point and and all the centers of the provided
    # circles. Add the radius of each of the circles to the distance,
    # to account for the area / uncertainty range of those circles.

    radius = 0.0
    for p_lat, p_lon, p_radius in circles:
        p_dist = distance(lat, lon, p_lat, p_lon) + p_radius
        radius = fmax(radius, p_dist)

    radius = fmax(radius, minimum_accuracy)
    return (lat, lon, radius)


cpdef tuple bbox(double lat, double lon, double meters):
    """
    Return a bounding box around the passed in lat/lon position.
    """
    cdef double max_lat, min_lat, max_lon, min_lon

    max_lat = latitude_add(lat, lon, meters)
    min_lat = latitude_add(lat, lon, -meters)
    max_lon = longitude_add(lat, lon, meters)
    min_lon = longitude_add(lat, lon, -meters)
    return (max_lat, min_lat, max_lon, min_lon)


cpdef tuple centroid(ndarray[double_t, ndim=2] points):
    """
    Compute the centroid (average lat and lon) from a set of points
    (two-dimensional lat/lon array).
    """
    cdef ndarray[double_t, ndim=1] center
    cdef double avg_lat, avg_lon

    center = points.mean(axis=0)
    avg_lat = center[0]
    avg_lon = center[1]
    return (avg_lat, avg_lon)


cpdef int circle_radius(double lat, double lon,
                        double max_lat, double max_lon,
                        double min_lat, double min_lon):
    """
    Compute the maximum distance, in meters, from a (lat, lon) point
    to any of the extreme points of a bounding box.
    """
    cdef ndarray[double_t, ndim=2] points
    cdef double radius

    points = numpy.array([
        (min_lat, min_lon),
        (min_lat, max_lon),
        (max_lat, min_lon),
        (max_lat, max_lon),
    ], dtype=numpy.double)

    radius = max_distance(lat, lon, points)
    return round(radius)


cpdef double distance(double lat1, double lon1, double lat2, double lon2):
    """
    Compute the distance between a pair of lat/longs in meters using
    the haversine calculation. The output distance is in meters.

    References:
      * http://en.wikipedia.org/wiki/Haversine_formula
      * http://www.movable-type.co.uk/scripts/latlong.html

    Accuracy: since the earth is not quite a sphere, there are small
    errors in using spherical geometry; the earth is actually roughly
    ellipsoidal (or more precisely, oblate spheroidal) with a radius
    varying between about 6378km (equatorial) and 6357km (polar),
    and local radius of curvature varying from 6336km (equatorial
    meridian) to 6399km (polar). 6371 km is the generally accepted
    value for the Earth's mean radius. This means that errors from
    assuming spherical geometry might be up to 0.55% crossing the
    equator, though generally below 0.3%, depending on latitude and
    direction of travel. An accuracy of better than 3m in 1km is
    mostly good enough for me, but if you want greater accuracy, you
    could use the Vincenty formula for calculating geodesic distances
    on ellipsoids, which gives results accurate to within 1mm.
    """
    cdef double a, c, dLat, dLon

    dLat = deg2rad(lat2 - lat1) / 2.0
    dLon = deg2rad(lon2 - lon1) / 2.0

    lat1 = deg2rad(lat1)
    lat2 = deg2rad(lat2)

    a = pow(sin(dLat), 2) + cos(lat1) * cos(lat2) * pow(sin(dLon), 2)
    c = asin(fmin(1, sqrt(a)))
    return 1000 * 2 * EARTH_RADIUS * c


cpdef double latitude_add(double lat, double lon, double meters):
    """
    Return a latitude in degrees which is shifted by
    distance in meters.

    The new latitude is bounded by our globally defined
    :data:`ichnaea.constants.MIN_LAT` and
    :data:`ichnaea.constants.MAX_LAT`.

    A suitable estimate for surface level calculations is
    111,111m = 1 degree latitude
    """
    return fmax(MIN_LAT, fmin(lat + (meters / 111111.0), MAX_LAT))


cpdef double longitude_add(double lat, double lon, double meters):
    """
    Return a longitude in degrees which is shifted by
    distance in meters.

    The new longitude is bounded by our globally defined
    :data:`ichnaea.constants.MIN_LON` and
    :data:`ichnaea.constants.MAX_LON`.
    """
    return fmax(MIN_LON, fmin(lon + (meters / (cos(lat) * 111111.0)), MAX_LON))


cpdef double max_distance(double lat, double lon,
                          ndarray[double_t, ndim=2] points):
    """
    Returns the maximum distance from the given lat/lon point to any of
    the provided points in the points array.
    """
    cdef double dist, p_lat, p_lon, result

    result = 0.0
    for p_lat, p_lon in points:
        dist = distance(lat, lon, p_lat, p_lon)
        result = fmax(result, dist)
    return result


cpdef list random_points(long lat, long lon, int num):
    """
    Given a row from the datamap table, return a list of
    pseudo-randomized but stable points for the datamap grid.

    The points look random, but their position only depends on the
    passed in latitude and longitude. This ensures that on consecutive
    calls with the same input data, the exact same output data is
    returned, and the generated image tiles showing these points don't
    change. The randomness needs to be good enough to not show clear
    visual patterns for adjacent grid cells, so a change in one of
    the input arguments by 1 needs to result in a large change in
    the pattern.
    """
    cdef str pattern = '%.6f,%.6f\n'
    cdef list result = []
    cdef int i, lat_random, lon_random, multiplier
    cdef double lat_d, lon_d

    lat_d = float(lat)
    lon_d = float(lon)
    lat_random = int((lon * (lat * 17) % 1021) % 179)
    lon_random = int((lat * (lon * 11) % 1913) % 181)

    multiplier = min(max(6 - num, 1), 6) * 2

    for i in range(multiplier):
        result.append(pattern % (
            (lat_d + RANDOM_LAT[lat_random + i]) / 1000.0,
            (lon_d + RANDOM_LON[lon_random + i]) / 1000.0))

    return result
