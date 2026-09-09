"""Day/night terminator math (PORTABLE CORE, stdlib only).

Computes the subsolar point (where the sun is directly overhead) for a given UTC
instant, then the terminator latitude for any longitude. The terminator is the
great circle 90 degrees from the subsolar point; a point (lat, lon) is in daylight
when the solar elevation is positive:

    sin(lat)*sin(dec) + cos(lat)*cos(dec)*cos(lon - sublon) > 0

Solving elevation = 0 for the boundary latitude at a given longitude gives:

    tan(lat_term) = -cos(lon - sublon) / tan(dec)

This is seasonally accurate (declination changes the tilt), unlike the original
wallpaper's single sliding shadow image.
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


def boundary_lat(lon: float, sublat: float, sublon: float, elevation: float = 0.0) -> float:
    """Latitude (deg) where the solar elevation equals `elevation`, clamped [-90, 90].

    Solving  sin(elev) = sin(lat)*sin(dec) + cos(lat)*cos(dec)*cos(H)  for lat:
    write the RHS as R*sin(lat + phi) with R = hypot(sin dec, cos dec cos H) and
    phi = atan2(cos dec cos H, sin dec); then lat = asin(sin(elev)/R) - phi.

    elevation = 0 is the day/night terminator; -6 / -12 / -18 are the civil /
    nautical / astronomical twilight boundaries. When there is no crossing in a
    column (|sin(elev)/R| > 1: that band's whole column is lit or dark), the value
    saturates to a pole, which clamps correctly for polygon filling.
    """
    dec = math.radians(sublat)
    h = math.radians(lon - sublon)
    e = math.radians(elevation)
    a = math.sin(dec)
    b = math.cos(dec) * math.cos(h)
    r = math.hypot(a, b)
    if r < 1e-9:
        return 0.0
    arg = max(-1.0, min(1.0, math.sin(e) / r))
    phi = math.atan2(b, a)
    lat = math.degrees(math.asin(arg) - phi)
    return max(-90.0, min(90.0, lat))


def dark_lat_bounds(
    lon: float, sublat: float, sublon: float, elevation: float = 0.0
) -> tuple[float, ...]:
    """Latitudes (deg) on this meridian where solar elevation < `elevation`.

    Along a meridian, sin(elevation) is a single-humped sinusoid,
    a*sin(lat) + b*cos(lat) with a = sin(dec), b = cos(dec)*cos(lon - sublon),
    so a horizon level is crossed by a column at UP TO TWO latitudes: once on the
    way down toward the midnight point and once on the way back up toward the
    pole.  ``boundary_lat`` keeps only the shallow root, which over-shades
    everything poleward of it (e.g. in southern spring the deepest twilight band
    fanned out from Brazil all the way to the south pole, cutting through the
    nautical and astronomical bands).  This returns the exact dark interval.

    Returns an empty tuple when the level is never reached on that meridian,
    ``(-91.0,)`` when the whole meridian is darker than it (a sentinel latitude
    that translates to "the full column"), or ``(lo, hi)`` with lo <= hi, the
    latitudes between which the elevation stays below the level (a zero-width
    interval marks a tangent that pinches the band off).
    """
    dec = math.radians(sublat)
    h = math.radians(lon - sublon)
    a = math.sin(dec)
    b = math.cos(dec) * math.cos(h)
    r = math.hypot(a, b)
    sin_elev = math.sin(math.radians(elevation))
    if r < 1e-9:
        return (-91.0,) if sin_elev > 0 else ()

    # Meridian extrema: the endpoints, plus the interior extremum latitudes when
    # they fall on the meridian (atan2(a, b) is the max, atan2(-a, -b) the min).
    cands = [(-90.0, -a), (90.0, a)]
    for t in (math.degrees(math.atan2(a, b)), math.degrees(math.atan2(-a, -b))):
        if -90.0 <= t <= 90.0:
            rad = math.radians(t)
            cands.append((t, a * math.sin(rad) + b * math.cos(rad)))
    th_min, emin = min(cands, key=lambda p: p[1])
    emax = max(e for _, e in cands)
    if sin_elev <= emin:
        return ()
    if sin_elev >= emax:
        return (-91.0,)

    # Two crossings.  sin(lat + phi) = sin_elev/r with phi = atan2(b, a); in
    # latitude space the roots sit at asin(c) - phi and pi - asin(c) - phi,
    # wrapped back onto the meridian.
    phi = math.atan2(b, a)
    alpha = math.asin(max(-1.0, min(1.0, sin_elev / r)))
    crossings = []
    for u in (alpha, math.pi - alpha):
        for k in (-1, 0, 1):
            th = math.degrees(u + 2.0 * math.pi * k - phi)
            if -90.0 <= th <= 90.0 and all(abs(th - x) > 1e-6 for x in crossings):
                crossings.append(th)
    crossings.sort()
    if len(crossings) == 2:
        return (crossings[0], crossings[1])
    if len(crossings) == 1:
        t = crossings[0]
        # The dark side is the segment toward the meridian's minimum.
        return (t, 90.0) if th_min > t else (-90.0, t)
    return ()


def terminator_lat(lon: float, sublat: float, sublon: float) -> float:
    """Day/night terminator latitude (solar elevation 0) at the given longitude."""
    return boundary_lat(lon, sublat, sublon, 0.0)


def night_is_south(sublat: float) -> bool:
    """True when the night (dark) hemisphere is south of the terminator.

    The north pole is lit exactly when the sun's declination is positive, so the
    dark region lies to the south then, and to the north otherwise.
    """
    return sublat > 0
