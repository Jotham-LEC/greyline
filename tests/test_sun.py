"""Day/night terminator math against known solar geometry."""

import math
from datetime import UTC, datetime

import pytest

from greyline import sun

LEVELS = (0.0, -6.0, -12.0, -18.0)


def _utc(y, m, d, h=12):
    return datetime(y, m, d, h, tzinfo=UTC)


def _sin_elevation(lat, sublat, sublon, lon):
    """sin(solar elevation) from first principles, independent of sun.py's solver."""
    a, d = math.radians(lat), math.radians(sublat)
    return math.sin(a) * math.sin(d) + math.cos(a) * math.cos(d) * math.cos(
        math.radians(lon - sublon)
    )


def test_solstice_declinations():
    june, _ = sun.subsolar_point(_utc(2024, 6, 20))
    dec, _ = sun.subsolar_point(_utc(2024, 12, 21))
    assert june == pytest.approx(23.4, abs=0.6)
    assert dec == pytest.approx(-23.4, abs=0.6)


def test_equinox_declination_near_zero():
    lat, _ = sun.subsolar_point(_utc(2024, 3, 20))
    assert abs(lat) < 1.5


def test_subsolar_longitude_near_prime_meridian_at_noon_utc():
    _lat, lon = sun.subsolar_point(_utc(2024, 3, 20))
    assert abs(lon) < 5.0


@pytest.mark.parametrize(
    "when",
    [
        _utc(2024, 6, 20, 9),  # june solstice
        _utc(2024, 12, 21, 18),  # december solstice
        _utc(2026, 3, 20, 12),  # march equinox — near-zero declination
        _utc(2026, 9, 9, 7),  # the instant from #17
    ],
)
def test_dark_lat_bounds_is_exactly_the_dark_latitudes(when):
    """Inside the returned band it is darker than the level, and outside it is not.

    The second half is the half that matters. Solving for a single boundary
    latitude also puts the dark latitudes inside its answer — what it got wrong was
    everything OUTSIDE, which it went on shading all the way to the pole. So this
    walks the whole meridian and checks membership both ways, against an elevation
    computed here rather than by the code under test.
    """
    sublat, sublon = sun.subsolar_point(when)
    for lon in range(-180, 181, 15):
        for level in LEVELS:
            target = math.sin(math.radians(level))
            band = sun.dark_lat_bounds(lon, sublat, sublon, level)
            if band is not None:
                lo, hi = band
                assert -90.0 <= lo <= hi <= 90.0
            for i in range(721):
                lat = -90.0 + i * 0.25
                elev = _sin_elevation(lat, sublat, sublon, lon)
                if abs(elev - target) < 1e-3:
                    continue  # sitting on the boundary; either answer is right
                if band is None:
                    assert elev > target, f"unreported dark latitude at {lon},{lat}"
                elif band[0] < lat < band[1]:
                    assert elev < target, f"band is too wide at {lon},{lat}"
                elif not band[0] <= lat <= band[1]:
                    assert elev > target, f"dark latitude outside the band at {lon},{lat}"


def test_dark_lat_bounds_closes_the_midnight_oval():
    """The deepest band is a closed oval around the midnight point, not a wedge.

    Regression pin for #17: near the equinoxes the astronomical band used to spill
    out of its oval and shade everything to the winter pole, swallowing the civil
    and nautical bands on the way.
    """
    sublat, sublon = sun.subsolar_point(datetime(2026, 9, 9, 7, 44, tzinfo=UTC))
    midnight_lon = (sublon - 180.0 + 540.0) % 360.0 - 180.0

    deepest = sun.dark_lat_bounds(midnight_lon, sublat, sublon, -18.0)
    assert deepest is not None
    lo, hi = deepest
    assert lo < -sublat < hi  # the oval covers the midnight point
    assert lo > -80.0  # and closes short of the pole instead of fanning to it

    # It is also nested inside the shallower bands rather than cutting through them.
    for shallower in (-12.0, -6.0, 0.0):
        outer = sun.dark_lat_bounds(midnight_lon, sublat, sublon, shallower)
        assert outer is not None
        outer_lo, outer_hi = outer
        assert outer_lo < lo and hi < outer_hi

    # A quarter turn away, on the sunward side, it never gets that dark at all.
    sunward = (midnight_lon + 90.0 + 540.0) % 360.0 - 180.0
    assert sun.dark_lat_bounds(sunward, sublat, sublon, -18.0) is None


def test_dark_lat_bounds_saturates_to_the_whole_meridian_or_to_nothing():
    """The two levels a meridian cannot bracket answer "all of it" and "none of it".

    Not levels greyline draws — a meridian a quarter turn from the subsolar point
    only swings between +-|declination| — but they are the branches that keep the
    return type a plain interval, so they are worth holding still.
    """
    sublat, sublon = sun.subsolar_point(_utc(2024, 12, 21, 18))
    quarter = (sublon + 90.0 + 540.0) % 360.0 - 180.0
    assert abs(sublat) < 30.0  # the sun on this meridian never leaves +-|dec|
    assert sun.dark_lat_bounds(quarter, sublat, sublon, 30.0) == (-90.0, 90.0)
    assert sun.dark_lat_bounds(quarter, sublat, sublon, -30.0) is None
