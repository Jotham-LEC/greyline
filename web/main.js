// Live demo driver: set up the canvas, load the map data once, cache the static base
// layer, and re-render the terminator + clocks on a ticking loop.
import { makeProjection } from "./geo.js";
import { loadGeo, buildBase } from "./vectormap.js";
import { overlayNight, drawClocks } from "./render.js";
import { THEMES, THEME_LABELS, THEME_ORDER, DARKNESS_ALPHA, CITIES, tzOffsetHours, labelLines }
  from "./config.js";

const canvas = document.getElementById("wt");
const ctx = canvas.getContext("2d");
const viewerTz = Intl.DateTimeFormat().resolvedOptions().timeZone;

// nightAlpha null = whatever the theme sets; homeTz starts as the viewer's own zone.
const state = {
  theme: "modus", fmt: "24h", bands: true, darkness: "subtle",
  fontScale: 1, labelBgAlpha: 130, labelBackground: true, nightAlpha: null,
  columnHighlight: true, homeTz: viewerTz, homeColor: null,
  cities: CITIES.map((c) => ({ ...c })),
};
let geo = null, proj = null, base = null, baseKey = "", W = 0, H = 0, dpr = 1;

function resize() {
  dpr = Math.min(2, window.devicePixelRatio || 1);
  W = Math.round(window.innerWidth);
  H = Math.round(window.innerHeight);
  canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
  canvas.style.width = W + "px"; canvas.style.height = H + "px";
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  proj = makeProjection(W, H);
  base = null;
  render();
}

const hexToRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));

function render() {
  showConfig();
  if (!geo || !proj) return;
  const now = new Date();
  const theme = state.homeColor
    ? { ...THEMES[state.theme], home: hexToRgb(state.homeColor) } : THEMES[state.theme];
  const scale = proj.scale;
  const homeOffset = tzOffsetHours(state.homeTz, now);
  const alpha = state.nightAlpha ?? theme.night_alpha ?? DARKNESS_ALPHA[state.darkness];

  const key = `${W}x${H}:${state.theme}:${homeOffset}:${state.columnHighlight}`;
  if (key !== baseKey || !base) {
    base = document.createElement("canvas");
    base.width = Math.round(W * dpr); base.height = Math.round(H * dpr);
    const bctx = base.getContext("2d");
    bctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    buildBase(bctx, W, H, theme, proj, geo, state.columnHighlight ? homeOffset : null, Math.max(8, Math.round(11 * scale)));
    baseKey = key;
  }

  ctx.clearRect(0, 0, W, H);
  ctx.drawImage(base, 0, 0, W, H);
  overlayNight(ctx, now, theme, state.bands, alpha, proj, W, H);
  const isHome = (c) => Math.abs(tzOffsetHours(c.tz, now) - homeOffset) < 0.01;
  drawClocks(ctx, W, H, {
    date: now, theme, fmt: state.fmt, cities: state.cities, scale, proj,
    labelBgAlpha: state.labelBackground ? state.labelBgAlpha : 0, fontScale: state.fontScale, obstacles: [], isHome,
  });
  describe(now);
}

// The canvas is the entire page. Its label has to carry what the picture says — the
// clocks and which one is home — or a screen reader gets a heading and nothing else.
function describe(now) {
  const times = state.cities.map((c) => labelLines(c, now, state.fmt).join(" ")).join(", ");
  canvas.setAttribute(
    "aria-label",
    `World map with the day and night terminator. Local times: ${times}. ` +
    `Your timezone, ${state.homeTz}, is highlighted.`,
  );
}

// The config.toml that reproduces the current view — only the keys the demo lets you
// change, as the same names `greyline config set` accepts.
// Options the demo cannot show — they act on a desktop wallpaper, a logo or raster map
// art, none of which exist in a browser. Listed commented-out, as in default-config.toml,
// so the copied file is a complete template.
const UNSUPPORTED_HEAD = [
  "",
  "# Not used by this demo — set these for your desktop:",
  '# backend = "auto"            # auto | sway | swww | hyprpaper | x11 | windows | macos | command',
  "# command = 'plasma-apply-wallpaperimage {path}'   # backend = \"command\": GNOME/KDE/XFCE, see `greyline help desktops`",
  '# resolution = "2560x1440"   # size of the rendered image (else largest xrandr output, else 1920x1080)',
  '# map_style = "vector"        # vector | raster (raster needs your own map art, see NOTICE)',
  "# desaturate = false         # grey out the raster map art (map_style = \"raster\" only)",
  '# font_family = "Aporetic Sans"  # label font: a fontconfig family name or a font-file path',
  "# logo = true                 # bottom-left corner logo (bundled default: Tux)",
  '# logo_path = "/path/to/your/logo.png"   # your own logo (PNG with transparency)',
  "# logo_invert = false        # recolour a dark logo's near-black pixels to light",
  '# logo_color = "#ffffff"     # recolour the whole logo to one flat colour',
  "# logo_scale = 1.0           # size the corner logo (0.5 = half)",
  "# logo_max_height = 0.0      # cap logo height to this fraction of screen height (0 = no cap)",
  "# bar_height = 0              # px reserved at the bottom for a status bar (lifts the logo)",
];

function configText() {
  const out = [`theme = "${state.theme}"`, `format = "${state.fmt}"`];
  // Only what differs from default-config.toml, so the file stays as short as the view allows.
  if (state.fontScale !== 1) out.push(`font_scale = ${state.fontScale}`);
  if (!state.labelBackground) out.push("label_background = false");
  else if (state.labelBgAlpha !== 130) out.push(`label_bg_alpha = ${state.labelBgAlpha}`);
  out.push(...UNSUPPORTED_HEAD);
  if (state.nightAlpha !== null) out.push("", "[colors]", `night_alpha = ${state.nightAlpha}`);
  out.push("", "[twilight]", `bands = ${state.bands}`,
    '# darkness = "subtle"      # subtle | medium | dramatic (a theme\'s night_alpha wins)');
  out.push("", "[home]", ...homeTzLines(new Date()));
  if (state.homeColor) out.push(`color = "${state.homeColor}"`);
  if (!state.columnHighlight) out.push("column_highlight = false");
  for (const c of state.cities) {
    out.push("", "[[city]]", `name = ${JSON.stringify(c.name)}`, `lat = ${c.lat}`, `lon = ${c.lon}`,
      `tz = "${c.tz}"`);
    if (c.label_side) out.push(`label_side = "${c.label_side}"`);
  }
  return out.join("\n") + "\n";
}

// greyline marks a city as home only when its tz is exactly home.tz (config.py), while
// the demo highlights any city on the home zone's UTC offset. So name the city the demo
// actually highlights, or the copied file would highlight nothing.
function homeTzLines(now) {
  const tz = state.homeTz;
  if (state.cities.some((c) => c.tz === tz)) return [`tz = "${tz}"`];
  const off = tzOffsetHours(tz, now);
  const twin = state.cities.find((c) => Math.abs(tzOffsetHours(c.tz, now) - off) < 0.01);
  if (twin) return [`tz = "${twin.tz}"`,
    `# ${tz} has no city below; ${twin.name} is on the same offset, so it is home.`];
  return [`tz = "${tz}"`,
    `# No city below is in ${tz}, so greyline highlights nothing: add a [[city]] with this tz.`];
}

// render() runs every minute; only touch the (aria-live) text when it changes, or a
// screen reader re-reads the whole file each tick.
function showConfig() {
  const pre = document.getElementById("config-text"), text = configText();
  if (pre.textContent !== text) pre.textContent = text;
}

function drawCityList() {
  const list = document.getElementById("city-list");
  list.replaceChildren(...state.cities.map((c, i) => {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = c.name;
    const side = document.createElement("select");
    side.setAttribute("aria-label", `Label side for ${c.name}`);
    side.append(...["", "left", "right", "above", "below"].map((v) => new Option(v || "auto", v)));
    side.value = c.label_side || "";
    side.addEventListener("change", () => {
      if (side.value) c.label_side = side.value; else delete c.label_side;
      render();
    });
    const del = document.createElement("button");
    del.type = "button"; del.textContent = "×"; del.setAttribute("aria-label", `Remove ${c.name}`);
    del.addEventListener("click", () => { state.cities.splice(i, 1); drawCityList(); render(); });
    li.append(name, side, del);
    return li;
  }));
}

function bindCities() {
  drawCityList();
  const form = document.getElementById("city-form");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const f = new FormData(form);
    const name = String(f.get("name")).trim(), lat = parseFloat(f.get("lat")), lon = parseFloat(f.get("lon"));
    if (!name || !(Math.abs(lat) <= 90) || !(Math.abs(lon) <= 180)) return;
    state.cities.push({ name, lat, lon, tz: String(f.get("tz")) });
    form.reset();
    document.getElementById("city-tz").value = viewerTz;
    drawCityList();
    render();
  });
  document.getElementById("city-reset").addEventListener("click", () => {
    state.cities = CITIES.map((c) => ({ ...c }));
    drawCityList();
    render();
  });
}

const SLIDERS = [["font-scale", "fontScale"], ["label-bg", "labelBgAlpha"], ["night-alpha", "nightAlpha"]];

// Keep each slider and its read-out on the value render() will use; the night slider
// shows the theme's own darkness until it is moved.
function syncSliders() {
  const theme = THEMES[state.theme];
  const night = state.nightAlpha ?? theme.night_alpha ?? DARKNESS_ALPHA[state.darkness];
  const shown = { fontScale: state.fontScale, labelBgAlpha: state.labelBgAlpha, nightAlpha: night };
  for (const [id, key] of SLIDERS) {
    document.getElementById(id).value = shown[key];
    document.getElementById(id + "-out").textContent = shown[key];
  }
}

function bindControls() {
  // One collapsible side panel; start folded on a phone, where it would cover the map.
  const toggle = document.getElementById("toggle"), body = document.getElementById("side-body");
  const fold = (open) => {
    body.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "Hide" : "Show";
  };
  fold(!window.matchMedia("(max-width: 560px)").matches);
  toggle.addEventListener("click", () => fold(body.hidden));

  document.getElementById("copy").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    try {
      await navigator.clipboard.writeText(configText());
      btn.textContent = "Copied";
    } catch {
      btn.textContent = "Copy failed";
    }
    setTimeout(() => { btn.textContent = "Copy"; }, 1500);
  });

  // The theme list is generated (three dozen palettes), so the picker is filled in
  // here rather than spelled out in the markup.
  const picker = document.getElementById("theme");
  picker.append(...THEME_ORDER.map((name) => new Option(THEME_LABELS[name], name)));
  picker.value = state.theme;
  picker.addEventListener("change", () => {
    state.theme = picker.value;
    state.nightAlpha = null;  // a new theme brings its own night darkness
    syncSliders();
    base = null;
    render();
  });

  const zones = typeof Intl.supportedValuesOf === "function"
    ? Intl.supportedValuesOf("timeZone") : CITIES.map((c) => c.tz);
  state.zones = [...new Set([viewerTz, ...zones])];
  const tzPicker = document.getElementById("home-tz");
  tzPicker.append(...state.zones.map((z) => new Option(z, z)));
  document.getElementById("city-tz").append(...state.zones.map((z) => new Option(z, z)));
  document.getElementById("city-tz").value = viewerTz;
  tzPicker.value = state.homeTz;
  tzPicker.addEventListener("change", () => { state.homeTz = tzPicker.value; render(); });

  // Sliders: [id, state key, shown value]. Moving one is an override; render() reads it.
  for (const [id, key] of SLIDERS) {
    const el = document.getElementById(id);
    el.addEventListener("input", () => {
      state[key] = +el.value;
      syncSliders();
      render();
    });
  }
  const plate = document.getElementById("label-background");
  plate.addEventListener("change", () => {
    state.labelBackground = plate.checked;
    document.getElementById("label-bg").disabled = !plate.checked;
    render();
  });
  const color = document.getElementById("home-color"), reset = document.getElementById("home-color-reset");
  color.addEventListener("input", () => { state.homeColor = color.value; reset.hidden = false; render(); });
  reset.addEventListener("click", () => { state.homeColor = null; reset.hidden = true; render(); });
  bindCities();
  const highlight = document.getElementById("column-highlight");
  highlight.addEventListener("change", () => { state.columnHighlight = highlight.checked; render(); });
  syncSliders();

  document.querySelectorAll("[data-set]").forEach((el) => {
    el.addEventListener("click", () => {
      const [k, v] = el.dataset.set.split(":");
      state[k] = v === "true" ? true : v === "false" ? false : v;
      const group = el.dataset.group;
      if (group) document.querySelectorAll(`[data-group="${group}"]`).forEach((b) => {
        b.classList.toggle("on", b === el);
        b.setAttribute("aria-pressed", String(b === el));
      });
      base = null;  // theme/darkness change invalidates the cached base
      render();
    });
  });
}

// A clock accurate to the minute is the contract greyline makes, on the desktop and
// here — so redraw on the minute boundary rather than every second. Rebuilding the
// overlay and the clocks 60x more often than the display can change costs battery and
// buys nothing anyone can read.
function scheduleTick() {
  // +50ms of slack so a timer that fires a hair early still lands in the new minute.
  setTimeout(() => { render(); scheduleTick(); }, 60000 - (Date.now() % 60000) + 50);
}

// Every resize throws away the cached base and redraws the map, which is ~110ms of
// main thread. Dragging a window edge fires it continuously, and on a phone so does
// the URL bar sliding away; wait for it to settle instead.
let resizePending = null;
function onResize() {
  clearTimeout(resizePending);
  resizePending = setTimeout(resize, 150);
}

async function start() {
  bindControls();
  window.addEventListener("resize", onResize);
  resize();
  try {
    geo = await loadGeo();
    document.getElementById("loading").remove();
    resize();
    scheduleTick();
  } catch (e) {
    document.getElementById("loading").textContent = "Failed to load map data: " + e.message;
  }
}
start();
