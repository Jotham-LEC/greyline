// Day/night terminator math — near-verbatim port of sun.py (NOAA approximation).
const D2R = Math.PI / 180, R2D = 180 / Math.PI;

export function subsolarPoint(date) {
  // `date` is a JS Date; we read its UTC fields.
  const y = date.getUTCFullYear();
  const doy = Math.floor((Date.UTC(y, date.getUTCMonth(), date.getUTCDate())
                          - Date.UTC(y, 0, 0)) / 86400000);  // 1-based day of year
  const hour = date.getUTCHours() + date.getUTCMinutes() / 60 + date.getUTCSeconds() / 3600;
  const g = 2 * Math.PI / 365 * (doy - 1 + (hour - 12) / 24);

  const dec = 0.006918 - 0.399912 * Math.cos(g) + 0.070257 * Math.sin(g)
    - 0.006758 * Math.cos(2 * g) + 0.000907 * Math.sin(2 * g)
    - 0.002697 * Math.cos(3 * g) + 0.001480 * Math.sin(3 * g);
  const sublat = dec * R2D;

  const eot = 229.18 * (0.000075 + 0.001868 * Math.cos(g) - 0.032077 * Math.sin(g)
    - 0.014615 * Math.cos(2 * g) - 0.040849 * Math.sin(2 * g));
  const minutesUtc = date.getUTCHours() * 60 + date.getUTCMinutes() + date.getUTCSeconds() / 60;
  let sublon = (720 - (minutesUtc + eot)) / 4;
  sublon = (((sublon + 180) % 360) + 360) % 360 - 180;
  return [sublat, sublon];
}

export function darkLatBounds(lon, sublat, sublon, elevation = 0) {
  // The latitudes on this meridian where the sun is below `elevation`, as [lo, hi],
  // or null where it never gets that dark — port of sun.py:dark_lat_bounds.  Down a
  // meridian the elevation is a single-humped sinusoid, so a meridian that reaches a
  // level reaches it TWICE (once sinking toward the midnight point, once climbing
  // back out); solving for one root finds only the shallow crossing and leaves
  // everything poleward of it looking dark.
  const dec = sublat * D2R, h = (lon - sublon) * D2R;
  const a = Math.sin(dec), b = Math.cos(dec) * Math.cos(h);
  const r = Math.hypot(a, b);
  const sinElev = Math.sin(elevation * D2R);
  if (sinElev > r) return [-90, 90];   // never climbs to the level: dark all the way down
  if (sinElev <= -r) return null;      // and never sinks to it: no band here at all

  // R*sin(u) < sin(elev) on (pi - asin(c), 2*pi + asin(c)), one interval per turn:
  // shift it by whole turns until it meets this meridian, then clip it to the poles.
  const phi = Math.atan2(b, a);
  const alpha = Math.asin(Math.max(-1, Math.min(1, sinElev / r)));
  const lo = (Math.PI - alpha - phi) * R2D;
  const hi = (2 * Math.PI + alpha - phi) * R2D;
  for (const turn of [-360, 0, 360]) {
    const top = Math.max(-90, lo + turn), bottom = Math.min(90, hi + turn);
    if (top <= bottom) return [top, bottom];
  }
  return null;
}
