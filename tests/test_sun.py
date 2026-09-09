"""Day/night terminator math against known solar geometry."""

import math
from datetime import UTC, datetime

import pytest

from greyline import sun


def _utc(y, m, d, h=12):
    return datetime(y, m, d, h, tzinfo=UTC)


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


def test_boundary_lat_is_clamped():
    sublat, sublon = sun.subsolar_point(_utc(2024, 6, 20))
    for lon in range(-180, 181, 30):
        for elev in (0.0, -6.0, -12.0, -18.0):
            lat = sun.boundary_lat(lon, sublat, sublon, elev)
            assert -90.0 <= lat <= 90.0


def test_night_hemisphere_follows_declination():
    assert sun.night_is_south(10.0) is True
    assert sun.night_is_south(-10.0) is False


def test_dark_lat_bounds_encloses_the_true_dark_region():
    """The interval endpoints sit on the level, and its inside is darker than it.

    The old single-root solver drew every deep band as a wedge to the pole; this
    regression-pins the two-crossing geometry: wherever a level is reached, the
    returned interval is exactly the set of latitudes with elevation below it.
    """
    sublat, sublon = sun.subsolar_point(_utc(2024, 6, 20))
    s = math.radians(sublat)
    for lon in range(-180, 181, 15):
        h = math.radians(lon - sublon)
        for elev in (0.0, -6.0, -12.0, -18.0):
            iv = sun.dark_lat_bounds(lon, sublat, sublon, elev)
            if not iv or iv[0] == -91.0:
                continue
            lo, hi = iv
            assert -90.0 - 1e-9 <= lo <= hi <= 90.0 + 1e-9

            def sun_alt(lat):
                rad = math.radians(lat)
                return (
                    math.sin(rad) * math.sin(s)
                    + math.cos(rad) * math.cos(s) * math.cos(h)
                )

            target = math.sin(math.radians(elev))
            step = max(0.5, (hi - lo) / 40)
            lat = lo + 0.25 * (hi - lo)  # inside, away from the ends
            assert sun_alt(lat) < target + 1e-9
            if hi - lo > 2.0:  # a real band has a proper poleward edge
                assert sun_alt(hi) > target - 1e-9 or sun_alt(lo) > target - 1e-9


def test_dark_lat_bounds_finds_the_midnight_oval():
    """In the equinoctial seasons the deepest band is a closed oval around the
    anti-subsolar point — not a wedge fanned out to the pole, which is the bug
    this replaced (the user saw it at the -3 timezone column in Brazil)."""
    sublat, sublon = sun.subsolar_point(datetime(2026, 9, 9, 7, 44, tzinfo=UTC))  # dec ~ +5.7
    wrap = lambda lon: (lon + 540.0) % 360.0 - 180.0
    midnight_lon = wrap(sublon - 180.0)
    lo, hi = sun.dark_lat_bounds(midnight_lon, sublat, sublon, -18.0)
    assert lo < -sublat < hi  # the oval covers the midnight point
    assert lo > -80.0  # and it is closed: it does NOT touch the south pole
    # A quarter globe around, on the sunward side, the level is never reached.
    assert sun.dark_lat_bounds(wrap(midnight_lon + 90.0), sublat, sublon, -18.0) == ()

