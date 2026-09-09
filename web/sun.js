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

export function boundaryLat(lon, sublat, sublon, elevation = 0) {
  const dec = sublat * D2R, h = (lon - sublon) * D2R, e = elevation * D2R;
  const a = Math.sin(dec), b = Math.cos(dec) * Math.cos(h);
  const r = Math.hypot(a, b);
  if (r < 1e-9) return 0;
  const arg = Math.max(-1, Math.min(1, Math.sin(e) / r));
  const lat = (Math.asin(arg) - Math.atan2(b, a)) * R2D;
  return Math.max(-90, Math.min(90, lat));
}

export const nightIsSouth = (sublat) => sublat > 0;

export function darkLatBounds(lon, sublat, sublon, elevation = 0) {
  // Latitudes (deg) on this meridian where the solar elevation is below `elevation`
  // — port of sun.py:dark_lat_bounds.  Along a meridian the elevation is a single-
  // humped sinusoid, so a level is crossed at UP TO TWO latitudes (once down
  // toward the midnight point, once back up toward the pole); boundaryLat only
  // keeps the shallow root, which over-shades everything poleward of it.  Returns
  // [] when the level is never reached, [-91] when the whole meridian is darker
  // than it, or [lo, hi] with lo <= hi (a zero-width interval is a tangent).
  const dec = sublat * D2R, h = (lon - sublon) * D2R;
  const a = Math.sin(dec), b = Math.cos(dec) * Math.cos(h);
  const r = Math.hypot(a, b);
  const sinL = Math.sin(elevation * D2R);
  if (r < 1e-9) return sinL > 0 ? [-91] : [];

  let cands = [[-90, -a], [90, a]];  // e(-90) = -a, e(90) = +a
  for (const t of [Math.atan2(a, b) * R2D, Math.atan2(-a, -b) * R2D]) {
    if (t >= -90 && t <= 90) {
      const rad = t * D2R;
      cands.push([t, a * Math.sin(rad) + b * Math.cos(rad)]);
    }
  }
  let thMin = cands[0][0], emin = cands[0][1], emax = cands[0][1];
  for (const [th, e] of cands) {
    if (e < emin) { emin = e; thMin = th; }
    if (e > emax) emax = e;
  }
  if (sinL <= emin) return [];
  if (sinL >= emax) return [-91];

  const phi = Math.atan2(b, a);
  const alpha = Math.asin(Math.max(-1, Math.min(1, sinL / r)));
  const crossings = [];
  for (const u of [alpha, Math.PI - alpha]) {
    for (const k of [-1, 0, 1]) {
      const th = (u + 2 * Math.PI * k - phi) * R2D;
      if (th >= -90 && th <= 90 && !crossings.some((x) => Math.abs(th - x) < 1e-6)) crossings.push(th);
    }
  }
  crossings.sort((p, q) => p - q);
  if (crossings.length === 2) return [crossings[0], crossings[1]];
  if (crossings.length === 1) {
    const t = crossings[0];
    return thMin > t ? [t, 90] : [-90, t];
  }
  return [];
}
