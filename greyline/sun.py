"""Day/night terminator math (PORTABLE CORE, stdlib only).

Computes the subsolar point (where the sun is directly overhead) for a given UTC
instant, then, for any meridian, the band of latitudes darker than a given solar
elevation. A point (lat, lon) is in daylight when the solar elevation is positive:

    sin(elev) = sin(lat)*sin(dec) + cos(lat)*cos(dec)*cos(lon - sublon)

Read down a meridian with lon fixed, the right-hand side is a single-humped
sinusoid in lat, so a level is reached over one contiguous band of latitudes and
`dark_lat_bounds` returns its two edges. This is seasonally accurate (declination
changes the tilt), unlike the original wallpaper's single sliding shadow image.
"""

import math
from datetime import UTC, datetime


def subsolar_point(dt_utc: datetime) -> tuple[float, float]:
    """Return (sublat, sublon) in degrees for the given UTC time.

    sublat is the solar declination; sublon is the longitude where it is solar
    noon. Uses the NOAA approximation (good to a fraction of a degree).
    """
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=UTC)
    dt_utc = dt_utc.astimezone(UTC)

    doy = dt_utc.timetuple().tm_yday
    hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0

    gamma = 2.0 * math.pi / 365.0 * (doy - 1 + (hour - 12) / 24.0)

    dec = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.001480 * math.sin(3 * gamma)
    )
    sublat = math.degrees(dec)

    eot = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )

    minutes_utc = dt_utc.hour * 60 + dt_utc.minute + dt_utc.second / 60.0
    sublon = (720.0 - (minutes_utc + eot)) / 4.0
    sublon = (sublon + 180.0) % 360.0 - 180.0
    return sublat, sublon


def dark_lat_bounds(
    lon: float, sublat: float, sublon: float, elevation: float = 0.0
) -> tuple[float, float] | None:
    """The latitudes on this meridian where the sun is below `elevation`.

    Down a meridian the solar elevation is a single-humped sinusoid in latitude,

        sin(elev) = sin(lat)*sin(dec) + cos(lat)*cos(dec)*cos(H)
                  = R * sin(lat + phi)

    with R = hypot(sin dec, cos dec cos H) and phi = atan2(cos dec cos H, sin dec).
    The sun sinks toward the midnight point and climbs again beyond it, so a
    meridian that reaches a level like -18 degrees reaches it TWICE: once going
    down and once coming back up. Solving for a single root finds only the
    shallow crossing, which leaves everything poleward of it looking dark, and
    the deepest band then fans out to a pole instead of closing into an oval
    around the midnight point.

    So rather than a boundary latitude, this returns the whole dark interval:
    `(lo, hi)` with lo <= hi, or None where the meridian never gets that dark.
    Bands that never reach the level end there instead of spreading. elevation 0
    is the day/night terminator; -6 / -12 / -18 are the civil / nautical /
    astronomical twilight boundaries.

    Only levels at or below the horizon are answered as a single band, which is
    all greyline draws. Above the horizon the dark region can split into two
    caps, one at each pole, and this reports the southern one.
    """
    dec = math.radians(sublat)
    h = math.radians(lon - sublon)
    a = math.sin(dec)
    b = math.cos(dec) * math.cos(h)
    r = math.hypot(a, b)
    sin_elev = math.sin(math.radians(elevation))
    if sin_elev > r:  # the sun never climbs to the level: dark the whole way down
        return -90.0, 90.0
    if sin_elev <= -r:  # and never sinks to it: no band on this meridian at all
        return None

    # R*sin(u) < sin(elev) holds on u in (pi - asin(c), 2*pi + asin(c)), one such
    # interval per turn. Shift it by whole turns until it meets this meridian's
    # latitudes, then clip it to the poles -- which is also what makes a band that
    # runs off the top or bottom of the globe come back as a half-open one.
    phi = math.atan2(b, a)
    alpha = math.asin(max(-1.0, min(1.0, sin_elev / r)))
    lo = math.degrees(math.pi - alpha - phi)
    hi = math.degrees(2.0 * math.pi + alpha - phi)
    for turn in (-360.0, 0.0, 360.0):
        top, bottom = max(-90.0, lo + turn), min(90.0, hi + turn)
        if top <= bottom:
            return top, bottom
    return None
