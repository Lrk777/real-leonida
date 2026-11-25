const $ = s => document.querySelector(s);
const fmt = (v, dp) => v == null ? "–" : Number(v).toLocaleString("en-CA", {minimumFractionDigits: dp, maximumFractionDigits: dp});
const money = v => v == null ? "–" : "$" + Math.round(v / 1000).toLocaleString("en-CA") + "k";
const layerBy = Object.fromEntries(D.layers.map(l => [l.key, l]));
const byFips = Object.fromEntries(D.counties.map(c => [c.fips, c]));
const YEARS = 76; // 1950-2025 inclusive
const RAMPS = {night: D.ramp, day: ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]};
const CATCOL = ["#ffe066", "#ffb347", "#ff7a45", "#ff3d6e", "#d63cff"];
let layer = "chaos_score", selected = null, regionOn = null, theme = "night";
try { theme = localStorage.getItem("rl-theme") || "night"; } catch (e) {}

// Wanted level and verdict
const nstars = s => s == null ? 0 : Math.max(1, Math.min(5, Math.ceil(s / 20)));
const stars = s => { const n = nstars(s); return `<span class="stars" aria-label="Wanted level ${n} of 5">${"★".repeat(n)}<span class="off">${"★".repeat(5 - n)}</span></span>`; };
function verdict(s) { return s >= 60 ? ["Not exaggerated", "v-wild"] : s >= 45 ? ["Fair", "v-fair"] : ["Exaggerated", "v-exag"]; }
function cat(kt) { return kt >= 137 ? 5 : kt >= 113 ? 4 : kt >= 96 ? 3 : kt >= 83 ? 2 : kt >= 64 ? 1 : 0; }
const catName = kt => "Cat " + cat(kt);

// Theme
function setTheme(t) { theme = t; document.documentElement.dataset.theme = t; $("#themebtn").textContent = t === "night" ? "☀" : "☾";
  try { localStorage.setItem("rl-theme", t); } catch (e) {} if (selected) paint(); }
$("#themebtn").addEventListener("click", () => setTheme(theme === "night" ? "day" : "night"));

// Headlines
$("#headlines").innerHTML = D.headlines.map(h => `<div class="hl"><b>${h.big}</b><span>${h.text}</span></div>`).join("");

// Region cards: drawn by drawRegions() in the v4 block below
const short = {hurricanes_per_decade:"Hurricanes", sinkholes_per_1000km2:"Sinkholes", gators_per_10k_obs:"Alligators", homicide_per_100k:"Homicide", crash_deaths_per_100k:"Road deaths"};

// Layer controls (the finder adds "Your match" further down)
D.layers.push({key: "match", label: "Your match", unit: "match score (0-100, higher = calmer for you)", dp: 0, chaos: false});
layerBy.match = D.layers[D.layers.length - 1];
function drawControls() { $("#controls").innerHTML = D.layers.map(l => `<button type="button" class="pill" data-k="${l.key}" aria-pressed="${l.key === layer}">${l.label}</button>`).join(""); }
drawControls();
$("#controls").addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return; layer = b.dataset.k; drawControls(); paint(); });

const DESC = {
  chaos_score: "Real-world difficulty: the five hazard layers, each ranked against all 67 counties and averaged. ★ for every 20 points; 100 = the hardest county in Florida.",
  hurricanes_per_decade: "Hurricanes whose eye passed within 60 nautical miles of the county centre, 1950-2025, per decade. Central counties get storms from both coasts.",
  sinkholes_per_1000km2: "Sinkhole and ground-collapse reports to the Florida Geological Survey, per 1,000 km². Reports, not all verified.",
  gators_per_10k_obs: "Out of every 10,000 wildlife photos people logged on iNaturalist in the county, how many were alligators. Small counties have few photos, so read with care.",
  homicide_per_100k: "Homicide deaths per 100,000 residents per year (CDC death records via County Health Rankings 2025). Grey = too few deaths to publish.",
  crash_deaths_per_100k: "Motor-vehicle crash deaths per 100,000 residents per year (CDC via County Health Rankings 2025). Rural counties with long, fast roads lead.",
  home_value: "Typical home value, mid-tier homes (Zillow Home Value Index, latest month). Context only, not part of the score.",
  danger: "Road deaths plus homicides per 100,000 residents a year: where real Floridians actually die. Studios draw the same kind of map for where players die.",
  story_missions: "How many of GTA 6's 91 story missions are set in each real county (by chapter). Grey = no story chapter is set there.",
  biome: "Data-driven zones: k-means clustering groups the 67 counties by what threatens them most, like an open-world map's biomes. Flip to Dev Mode to see how.",
  match: "Your match score from the finder below: 100 = calmest county on what you said you care about. Grey = over your budget."
};
const sorted = [...D.counties].sort((a, b) => a.name.localeCompare(b.name));
$("#countylist").innerHTML = sorted.map(c => `<option value="${c.name}">`).join("");
$("#search").addEventListener("change", e => { const q = e.target.value.trim().toLowerCase();
  const c = D.counties.find(x => x.name.toLowerCase() === q) || D.counties.find(x => x.name.toLowerCase().startsWith(q));
  if (c) { select(c.fips); e.target.value = ""; } });

// Map
const svg = $("#map");
svg.setAttribute("viewBox", `0 0 ${D.W} ${D.H}`);
const tracks = D.tracks || [];
svg.innerHTML = D.counties.map(c => `<path class="c" d="${c.path}" data-f="${c.fips}"><title>${c.name}</title></path>`).join("") +
  `<g id="tracks">${tracks.map((t, i) => `<g class="trk off" data-i="${i}"><path class="base" d="M${t.pts.map(p => p[0] + "," + p[1]).join("L")}"></path>` +
     t.pts.filter(p => p[2] >= 64).map(p => `<circle class="p" cx="${p[0]}" cy="${p[1]}" r="3.2" fill="${CATCOL[cat(p[2]) - 1]}"></circle>`).join("") +
     (t.lf || []).map(p => `<circle class="lf" cx="${p[0]}" cy="${p[1]}" r="6"></circle>`).join("") + `</g>`).join("")}</g>` +
  `<text id="yearbadge" class="yearbadge" x="${D.W - 20}" y="64" text-anchor="end"></text>`;
const tip = $("#tip");
svg.addEventListener("mousemove", e => { const p = e.target.closest("path.c"); if (!p) { tip.style.opacity = 0; return; }
  const c = byFips[p.dataset.f], L = layerBy[layer], v = c[layer];
  tip.innerHTML = `<b>${c.name}</b> ${"★".repeat(nstars(c.chaos_score))} · ${layer === "biome" ? bioName(c) : layer === "home_value" ? money(v) : layer === "chaos_score" ? diffOf(v) : fmt(v, L.dp)}`;
  const box = $("#mapbox").getBoundingClientRect(); tip.style.left = Math.min(e.clientX - box.left + 12, box.width - 190) + "px"; tip.style.top = (e.clientY - box.top + 12) + "px"; tip.style.opacity = 1; });
svg.addEventListener("mouseleave", () => tip.style.opacity = 0);
svg.addEventListener("click", e => { const p = e.target.closest("path.c"); if (p) select(p.dataset.f); });

function breaks(vals) { const s = vals.filter(v => v != null).sort((a, b) => a - b); return [0.2, 0.4, 0.6, 0.8].map(q => s[Math.floor(q * (s.length - 1))]); }
function paint() {
  if (layer === "biome") return paintBiomes();
  const ramp = RAMPS[theme], vals = D.counties.map(c => c[layer]), br = layer === "story_missions" ? [0, 10, 20, 30] : breaks(vals), L = layerBy[layer];
  $("#layerdesc").textContent = DESC[layer] || "";
  if (selected) history.replaceState(null, "", `#county=${selected}&layer=${layer}`);
  const regF = regionOn ? D.regions.find(r => r.region === regionOn).fips : D.regions.flatMap(r => r.fips);
  svg.querySelectorAll("path.c").forEach(p => { const c = byFips[p.dataset.f], v = c[layer];
    p.classList.toggle("na", v == null);
    p.style.fill = v == null ? "" : ramp[br.filter(b => v > b).length];
    p.classList.toggle("reg", regF.includes(c.fips)); p.classList.toggle("sel", c.fips === selected); });
  const f = v => layer === "home_value" ? money(v) : fmt(v, L.dp);
  const lab = i => i === 0 ? `≤ ${f(br[0])}` : i === 4 ? `> ${f(br[3])}` : `${f(br[i - 1])}–${f(br[i])}`;
  $("#legend").innerHTML = ramp.map((col, i) => `<span style="display:inline-flex;flex-direction:column;gap:3px;min-width:72px"><span style="height:10px;border-radius:2px;background:${col}"></span><span>${lab(i)}</span></span>`).join("") +
    `<div class="unit">${L.unit} · 5 groups of ~13 counties · grey = no data</div>`;
}

function rankOf(key, fips) { const s = D.counties.filter(c => c[key] != null).sort((a, b) => b[key] - a[key]); const i = s.findIndex(c => c.fips === fips); return i < 0 ? null : i + 1; }
function select(f) { selected = f; const c = byFips[f]; const n = D.counties.length;
  const row = (label, txt, key) => `<tr><td>${label}</td><td>${txt}</td><td>${key && rankOf(key, f) ? "#" + rankOf(key, f) + " of " + D.counties.filter(x => x[key] != null).length : ""}</td></tr>`;
  $("#panel").innerHTML = `<h3>${c.name}</h3>
    <div class="meta">${Number(c.population).toLocaleString("en-CA")} residents · Difficulty rank #${c.chaos_rank} of ${n}</div>
    ${stars(c.chaos_score)} ${c.regions.map(r => `<span class="tag">GTA 6: ${r}</span>`).join("")}
    <table>
      ${row("Difficulty", stars(c.chaos_score) + " " + diffOf(c.chaos_score), "chaos_score")}
      ${row("Biome", bioName(c), null)}
      ${row("Hurricanes within 60 nm, 1950-2025", fmt(c.hurricanes_1950_2025, 0) + " (" + fmt(c.major_hurricanes_1950_2025, 0) + " major)", "hurricanes_per_decade")}
      ${row("Hurricane landfalls since 1851", fmt(c.landfalls_since_1851, 0), "landfalls_since_1851")}
      ${row("Sinkhole reports", fmt(c.sinkholes, 0) + " (" + fmt(c.sinkholes_per_1000km2, 1) + " per 1,000 km²)", "sinkholes_per_1000km2")}
      ${row("Alligators per 10k sightings", fmt(c.gators_per_10k_obs, 0) + " (" + fmt(c.alligator_obs, 0) + " gators)", "gators_per_10k_obs")}
      ${row("Homicides per 100k", fmt(c.homicide_per_100k, 1), "homicide_per_100k")}
      ${row("Road deaths per 100k", fmt(c.crash_deaths_per_100k, 1), "crash_deaths_per_100k")}
      ${row("Typical home value", money(c.home_value) + (c.home_value_change_pct == null ? "" : " (" + (c.home_value_change_pct >= 0 ? "+" : "") + fmt(c.home_value_change_pct, 0) + "% in 5 yrs)"), "home_value")}
    </table>
    ${c.landfalls.length ? `<div class="storms"><b>Strongest hurricanes to make landfall here:</b> ${c.landfalls.slice(0, 4).map(s => `${s[0]} ${s[1]} (${catName(s[2])})`).join(" · ")}</div>` : `<div class="storms">No hurricane has made landfall in this county since 1851 (storms can still pass nearby).</div>`}
    <div class="btnrow"><button type="button" class="btn hot" id="idcard">⬇ Download ID card</button><button type="button" class="btn" id="copylink">Copy link</button><button type="button" class="btn" id="tofight">Use in face-off</button></div>`;
  $("#copylink").onclick = () => { const u = location.href.split("#")[0] + `#county=${f}&layer=${layer}`;
    (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(() => $("#copylink").textContent = "Link copied", () => $("#copylink").textContent = u); };
  $("#idcard").onclick = () => idCard(c);
  $("#tofight").onclick = () => { $("#fa").value = f; fight(); $("#s7").scrollIntoView({behavior: "smooth"}); };
  paint(); }

// Hurricane replay
const tg = [...svg.querySelectorAll("g.trk")];
const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
$("#trackSel").innerHTML = `<option value="none">Off</option><option value="all">All ${tracks.length} major landfalls since 1950</option>` +
  tracks.map((t, i) => `<option value="${i}">${t.name} ${t.year} (${catName(t.landfall_kt)} at landfall)</option>`).join("");
let playing = null;
function stopPlay() { if (playing) { clearTimeout(playing); playing = null; } $("#play").textContent = "▶ Replay 1950-2025"; $("#yearbadge").textContent = ""; }
function describe(t) { return `${t.name} ${t.year}: ${catName(t.landfall_kt)} at landfall (${t.landfall_kt} kt) in ${t.counties.join(", ")}`; }
function draw(g, dur) { const el = g.querySelector(".base"); if (reduce || !el.getTotalLength) return; const L = el.getTotalLength();
  el.style.transition = "none"; el.style.strokeDasharray = L; el.style.strokeDashoffset = L; el.getBoundingClientRect();
  el.style.transition = `stroke-dashoffset ${dur}s ease-out`; el.style.strokeDashoffset = 0; }
function showTracks(v) {
  $("#catlegend").classList.toggle("show", v !== "none");
  tg.forEach(g => { g.classList.remove("on", "dim"); g.querySelector(".base").style.strokeDasharray = ""; g.classList.toggle("off", v === "none"); });
  if (v === "none") { $("#stormInfo").textContent = ""; return; }
  if (v === "all") { tg.forEach(g => g.classList.add("dim")); $("#stormInfo").textContent = `${tracks.length} major hurricanes made landfall in Florida, 1950-2025. Pick one or press Replay.`; return; }
  const i = +v; tg.forEach((g, j) => g.classList.toggle("off", j !== i)); tg[i].classList.add("on"); draw(tg[i], 1.4);
  $("#stormInfo").textContent = describe(tracks[i]);
}
$("#trackSel").addEventListener("change", e => { stopPlay(); showTracks(e.target.value); });
$("#play").disabled = !tracks.length;
$("#play").addEventListener("click", () => {
  if (playing) { stopPlay(); showTracks("all"); return; }
  $("#trackSel").value = "all"; $("#catlegend").classList.add("show"); tg.forEach(g => { g.classList.add("off"); g.classList.remove("on", "dim"); });
  $("#play").textContent = "■ Stop"; let i = 0; const k = +$("#speed").value;
  const step = () => { if (i > 0) { tg[i - 1].classList.remove("on"); tg[i - 1].classList.add("dim"); }
    if (i >= tracks.length) { playing = null; $("#play").textContent = "▶ Replay 1950-2025"; showTracks("all"); $("#yearbadge").textContent = ""; return; }
    const g = tg[i]; g.classList.remove("off", "dim"); g.classList.add("on"); draw(g, 1.1 * k);
    $("#yearbadge").textContent = tracks[i].year; $("#stormInfo").textContent = describe(tracks[i]); i++; playing = setTimeout(step, (reduce ? 600 : 1600) * k); };
  step();
});
showTracks("none");

// Face-off
const ROUNDS = [["hurricanes_per_decade", "Hurricanes / decade", 1], ["sinkholes_per_1000km2", "Sinkholes / 1k km²", 1], ["gators_per_10k_obs", "Gators / 10k sightings", 0],
  ["homicide_per_100k", "Homicides / 100k", 1], ["crash_deaths_per_100k", "Road deaths / 100k", 1], ["home_value", "Home price", -1]];
const opts = sorted.map(c => `<option value="${c.fips}">${c.name}</option>`).join("");
$("#fa").innerHTML = opts; $("#fb").innerHTML = opts; $("#fa").value = "12086"; $("#fb").value = "12087";
function fight() {
  const a = byFips[$("#fa").value], b = byFips[$("#fb").value]; let wa = 0, wb = 0;
  $("#rounds").innerHTML = ROUNDS.map(([k, label, dp]) => { const x = a[k], y = b[k]; let ca = "", cb = "";
    if (x != null && y != null && x !== y) { if (x < y) { ca = "win"; wa++; } else { cb = "win"; wb++; } }
    const f = v => dp === -1 ? money(v) : fmt(v, dp);
    const t = abTest(k, a, b);
    return `<div class="round"><span class="l ${ca}">${f(x)}</span><span class="m">${label}${t}</span><span class="${cb}">${f(y)}</span></div>`; }).join("");
  $("#fightverdict").innerHTML = a.fips === b.fips ? "Pick two different counties." :
    wa === wb ? `It's a draw, ${wa}–${wb}.` : `${wa > wb ? a.name : b.name} wins ${Math.max(wa, wb)}–${Math.min(wa, wb)}: the calmer place to live.`;
}
$("#fa").addEventListener("change", fight); $("#fb").addEventListener("change", fight);

// Survive Leonida
$("#sv").innerHTML = opts; $("#sv").value = "12087";
function survive() { surviveMC(); }
$("#sv").addEventListener("change", survive); $("#yrs").addEventListener("input", survive);

// ID card (canvas, original design, downloads as PNG)
function idCard(c) {
  const W = 1080, H = 1350, cv = document.createElement("canvas"); cv.width = W; cv.height = H; const g = cv.getContext("2d");
  const bg = g.createLinearGradient(0, 0, 0, H); bg.addColorStop(0, "#1a0b3a"); bg.addColorStop(.55, "#3b0d4f"); bg.addColorStop(1, "#0d0a1f"); g.fillStyle = bg; g.fillRect(0, 0, W, H);
  const sun = g.createLinearGradient(0, 120, 0, 520); sun.addColorStop(0, "#ffe066"); sun.addColorStop(.6, "#ff8a3d"); sun.addColorStop(1, "#ff3ea5");
  g.save(); g.beginPath(); g.arc(820, 330, 190, 0, Math.PI * 2); g.clip(); g.fillStyle = sun; g.fillRect(600, 120, 440, 420);
  g.fillStyle = "rgba(59,13,79,.55)"; [[360, 10], [395, 14], [432, 18], [474, 24]].forEach(([y, h]) => g.fillRect(600, y, 440, h)); g.restore();
  g.fillStyle = "#ffffff"; g.font = "800 30px system-ui, sans-serif"; g.fillText("REAL LEONIDA · COUNTY ID", 70, 110);
  g.font = "italic 900 96px system-ui, sans-serif"; g.fillStyle = "#ffe3f3"; g.fillText(c.name.toUpperCase(), 70, 640, W - 140);
  g.font = "700 36px system-ui, sans-serif"; g.fillStyle = "#c3b8e6";
  g.fillText((c.regions.length ? "GTA 6: " + c.regions.join(" / ") : "Florida county") + " · " + DIFF[nstars(c.chaos_score) - 1].toUpperCase(), 70, 700, W - 140);
  if (state.persona) { g.font = "700 30px system-ui, sans-serif"; g.fillStyle = "#ffd23f"; g.fillText("Character: " + PERSONAS.find(p => p.id === state.persona).name + (state.match === c.fips ? " · best match" : ""), 70, 560, W - 140); }
  g.font = "900 60px system-ui, sans-serif"; const n = nstars(c.chaos_score); g.fillStyle = "#ffd23f"; g.fillText("★".repeat(n), 70, 790); g.fillStyle = "#3a2f68"; g.fillText("★".repeat(5 - n), 70 + g.measureText("★".repeat(n)).width, 790);
  g.fillStyle = "#ffffff"; g.font = "900 120px system-ui, sans-serif"; g.textAlign = "right"; g.fillText(Math.round(c.chaos_score), W - 70, 800);
  g.font = "700 28px system-ui, sans-serif"; g.fillStyle = "#c3b8e6"; g.fillText("Difficulty / 100", W - 70, 840); g.textAlign = "left";
  const rows = [["Hurricanes", "hurricanes_per_decade_pct"], ["Sinkholes", "sinkholes_per_1000km2_pct"], ["Alligators", "gators_per_10k_obs_pct"], ["Homicide", "homicide_per_100k_pct"], ["Road deaths", "crash_deaths_per_100k_pct"]];
  rows.forEach(([lab, k], i) => { const y = 920 + i * 66, v = c[k];
    g.fillStyle = "#f4efff"; g.font = "700 32px system-ui, sans-serif"; g.fillText(lab, 70, y + 26);
    g.fillStyle = "#221a47"; g.fillRect(330, y, 560, 30);
    const gr = g.createLinearGradient(330, 0, 890, 0); gr.addColorStop(0, "#2ee6ff"); gr.addColorStop(1, "#ff3ea5"); g.fillStyle = gr; g.fillRect(330, y, 560 * (v == null ? 0 : v / 100), 30);
    g.fillStyle = "#f4efff"; g.textAlign = "right"; g.fillText(v == null ? "–" : Math.round(v), W - 70, y + 26); g.textAlign = "left"; });
  g.fillStyle = "#c3b8e6"; g.font = "600 28px system-ui, sans-serif";
  g.fillText(`Typical home ${money(c.home_value)} · ${c.landfalls_since_1851} hurricane landfalls since 1851`, 70, 1275 - 30);
  g.fillStyle = "#8f84b5"; g.font = "500 24px system-ui, sans-serif"; g.fillText("lrk777.github.io/real-leonida · NOAA, FGS, GBIF, CDC/CHR, Census, Zillow · fan analysis", 70, 1300);
  const a = document.createElement("a"); a.download = `real-leonida-${c.name.toLowerCase().replace(/[^a-z]+/g, "-")}.png`; a.href = cv.toDataURL("image/png"); document.body.appendChild(a); a.click(); a.remove();
}

// Table
const tcols = [["name","County",null],["chaos_score","Difficulty",0],["hurricanes_1950_2025","Hurricanes",0],["landfalls_since_1851","Landfalls",0],["sinkholes_per_1000km2","Sinkholes/1k km²",1],["gators_per_10k_obs","Gators/10k obs",0],["homicide_per_100k","Homicide/100k",1],["crash_deaths_per_100k","Road deaths/100k",1],["home_value","Home value",-1]];
let sortK = "chaos_score", sortD = -1;
function table() { const rows = [...D.counties].sort((a, b) => sortK === "name" ? a.name.localeCompare(b.name) * -sortD : ((a[sortK] ?? -1e9) - (b[sortK] ?? -1e9)) * sortD);
  $("#table").innerHTML = `<thead><tr>${tcols.map(([k, l]) => `<th data-k="${k}" aria-sort="${k === sortK ? (sortD < 0 ? "descending" : "ascending") : "none"}">${l}</th>`).join("")}</tr></thead><tbody>` +
    rows.map(c => `<tr>${tcols.map(([k, l, dp]) => `<td>${k === "name" ? c.name : dp === -1 ? money(c[k]) : fmt(c[k], dp)}</td>`).join("")}</tr>`).join("") + "</tbody>"; }
$("#table").addEventListener("click", e => { const th = e.target.closest("th"); if (!th) return; const k = th.dataset.k; sortD = k === sortK ? -sortD : -1; sortK = k; table(); });

// Finder
const RISKS = [["hurricanes_per_decade", "Hurricanes"], ["sinkholes_per_1000km2", "Sinkholes"], ["gators_per_10k_obs", "Alligators"], ["homicide_per_100k", "Crime"], ["crash_deaths_per_100k", "Road safety"]];
const LVL = ["Don't care", "A little", "Matters", "Top worry"];
const W = {hurricanes_per_decade: 2, sinkholes_per_1000km2: 1, gators_per_10k_obs: 1, homicide_per_100k: 2, crash_deaths_per_100k: 1};
let budget = 0, invert = false;
$("#prefs").innerHTML = `<b>What worries you?</b>` + RISKS.map(([k, l]) =>
  `<div class="slider"><label for="w_${k}">${l}</label><input type="range" id="w_${k}" min="0" max="3" step="1" value="${W[k]}"><output id="o_${k}">${LVL[W[k]]}</output></div>`).join("") +
  `<div class="slider"><label for="budget">Budget</label><select class="sel" id="budget"><option value="0">Any price</option><option value="250000">Under $250k</option><option value="300000">Under $300k</option><option value="400000">Under $400k</option><option value="500000">Under $500k</option></select><span></span></div>`;
RISKS.forEach(([k]) => $("#w_" + k).addEventListener("input", e => { W[k] = +e.target.value; $("#o_" + k).textContent = LVL[W[k]]; setPersona(null); rank(true); }));
$("#budget").addEventListener("change", e => { budget = +e.target.value; setPersona(null); rank(true); });
function rank(show) {
  const tot = Object.values(W).reduce((a, b) => a + b, 0);
  D.counties.forEach(c => {
    if (budget && (c.home_value == null || c.home_value > budget)) { c.match = null; return; }
    let s = 0, w = 0;
    // a layer the source suppressed (e.g. homicide in tiny counties) counts as a typical county (50), not as calm
    RISKS.forEach(([k]) => { const p = c[k + "_pct"] ?? 50; if (W[k]) { s += (invert ? p : 100 - p) * W[k]; w += W[k]; } });
    c.match = tot === 0 ? null : w ? s / w : null;
  });
  const top = D.counties.filter(c => c.match != null).sort((a, b) => b.match - a.match).slice(0, 8);
  $("#results").innerHTML = top.map((c, i) => { const best = RISKS.filter(([k]) => W[k] && c[k + "_pct"] != null).sort((a, b) => (invert ? -1 : 1) * (c[a[0] + "_pct"] - c[b[0] + "_pct"])).slice(0, 2).map(x => x[1].toLowerCase());
    return `<li tabindex="0" data-f="${c.fips}"><span class="n">${i + 1}</span><span><b>${c.name}</b>${c.regions.length ? ` <span class="tag">${c.regions[0]}</span>` : ""}<br><span class="why">${invert ? "Wild on" : "Calm on"} ${best.join(" and ")} · ${money(c.home_value)} typical home</span></span><span class="m">${Math.round(c.match)}</span></li>`; }).join("");
  $("#hint").textContent = tot === 0 ? "Move at least one slider to rank counties." : top.length ? "Click a county to see it on the map. Match = 100 means calmest in Florida on everything you picked. Missing data counts as average." : "No county fits that budget. Try a higher one.";
  if (show) { layer = "match"; drawControls(); }
  state.match = top.length ? top[0].fips : null;
  paint(); drawResults();
}
$("#results").addEventListener("click", e => { const li = e.target.closest("li"); if (li) { select(li.dataset.f); $("#mapbox").scrollIntoView({behavior: "smooth", block: "center"}); } });
$("#results").addEventListener("keydown", e => { const li = e.target.closest("li"); if (li && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); select(li.dataset.f); } });

// Story mode: GTA 6 chapters -> real counties, with stats computed from the data on every build
const CH = D.chapters || [];
let cleared = new Set();
try { cleared = new Set(JSON.parse(localStorage.getItem("rl-cleared") || "[]")); } catch (e) {}
const rk = (k, f) => { const r = rankOf(k, f), n = D.counties.filter(x => x[k] != null).length; return r ? `#${r} of ${n} in Florida` : ""; };
const STAT = {
  landfalls_since_1851: c => [`${fmt(c.landfalls_since_1851, 0)} hurricanes made landfall here since 1851`, rk("landfalls_since_1851", c.fips)],
  major_hurricanes_1950_2025: c => [`${fmt(c.major_hurricanes_1950_2025, 0)} major (Cat 3+) hurricanes passed within 60 nm since 1950`, rk("major_hurricanes_1950_2025", c.fips)],
  hurricanes_1950_2025: c => [`${fmt(c.hurricanes_1950_2025, 0)} hurricanes passed within 60 nm since 1950`, rk("hurricanes_1950_2025", c.fips)],
  gators_per_10k_obs: c => [`1 in ${c.gators_per_10k_obs ? Math.round(10000 / c.gators_per_10k_obs) : "–"} wildlife sightings is an alligator`, rk("gators_per_10k_obs", c.fips)],
  alligator_obs: c => [`${fmt(c.alligator_obs, 0)} alligator sightings logged on iNaturalist`, rk("alligator_obs", c.fips)],
  strongest_landfall: c => c.landfalls.length ? [`Strongest landfall: ${c.landfalls[0][0]} ${c.landfalls[0][1]} (${catName(c.landfalls[0][2])})`, ""] : ["No hurricane landfall recorded here since 1851", ""],
  crash_deaths_per_100k: c => [`${fmt(c.crash_deaths_per_100k, 1)} road deaths per 100,000 residents a year`, rk("crash_deaths_per_100k", c.fips)],
  homicide_per_100k: c => [`${fmt(c.homicide_per_100k, 1)} homicides per 100,000 residents a year`, rk("homicide_per_100k", c.fips)],
  home_value: c => [`Typical home: ${money(c.home_value)}`, rk("home_value", c.fips)],
  chaos_score: c => [`Difficulty ${diffOf(c.chaos_score)} (${fmt(c.chaos_score, 0)} / 100)`, rk("chaos_score", c.fips)],
};
function drawChapters() {
  $("#chapters").innerHTML = CH.map(ch => `<button type="button" class="ch${cleared.has(ch.n) ? " cleared" : ""}" data-n="${ch.n}" aria-label="Chapter ${ch.n}${cleared.has(ch.n) ? ", cleared" : ""}">
    <span class="done">✓ CLEARED</span><span class="no">CHAPTER ${ch.n}</span><b>${ch.title}</b>
    <small>${ch.region || "Statewide finale"} · ${ch.missions} missions</small></button>`).join("");
  $("#progtxt").textContent = `${cleared.size} / ${CH.length} chapters cleared`;
  $("#progbar").style.width = (CH.length ? cleared.size / CH.length * 100 : 0) + "%";
}
function playChapter(n) {
  const ch = CH.find(x => x.n === n); if (!ch) return;
  document.querySelectorAll(".ch").forEach(b => b.classList.toggle("on", +b.dataset.n === n));
  let body;
  if (ch.fips) {
    const c = byFips[ch.fips], v = verdict(c.chaos_score);
    body = `<div><div class="no" style="font-size:11px;font-weight:800;letter-spacing:.14em;color:var(--pink)">CHAPTER ${ch.n} · ${ch.missions} MISSIONS · ${ch.region.toUpperCase()}</div>
      <h3>Real ${ch.region} = ${c.name} County</h3><p class="hook">${ch.hook}</p>
      ${stars(c.chaos_score)} <span class="verdict ${v[1]}">${v[0]}</span>
      <ul class="rcheck">${ch.stats.map(k => { const [t, r] = STAT[k](c); return `<li>${t}${r ? `<span>${r}</span>` : ""}</li>`; }).join("")}
      <li>${tallyText(ch.n)}</li></ul>
      <div class="btnrow"><button type="button" class="btn" id="chmap">See it on the map</button><button type="button" class="btn" id="chlist">See its ${ch.missions} missions</button><button type="button" class="btn hot" id="chcard">⬇ ${c.name} ID card</button></div></div>`;
    regionOn = ch.region; document.querySelectorAll(".rc").forEach(x => x.classList.toggle("on", x.dataset.region === regionOn));
    select(ch.fips);
  } else {
    const top = [...D.counties].sort((a, b) => b.chaos_score - a.chaos_score)[0], vc = byFips["12086"];
    const regs = [...D.regions].sort((a, b) => b.reality_score - a.reality_score);
    body = `<div><div class="no" style="font-size:11px;font-weight:800;letter-spacing:.14em;color:var(--pink)">CHAPTER ${ch.n} · ${ch.missions} MISSIONS · FINALE</div>
      <h3>Final boss: the real most chaotic county</h3><p class="hook">${ch.hook}</p>
      <ul class="rcheck"><li>${top.name} County tops all 67 counties with a difficulty score of ${fmt(top.chaos_score, 0)} ${top.regions.length ? `(GTA 6: ${top.regions.join(" / ")})` : "(not in any GTA 6 region)"}</li>
      <li>Real Vice City (${vc.name}) ends at #${vc.chaos_rank} of ${D.counties.length}, score ${fmt(vc.chaos_score, 0)}</li>
      <li>Most chaotic region overall: ${regs[0].region} (${Math.round(regs[0].reality_score)}). Calmest: ${regs[regs.length - 1].region} (${Math.round(regs[regs.length - 1].reality_score)})</li></ul>
      <div class="btnrow"><button type="button" class="btn" id="chmap">See ${top.name} on the map</button><button type="button" class="btn hot" id="chcard">⬇ ${top.name} ID card</button></div></div>`;
    regionOn = null; document.querySelectorAll(".rc").forEach(x => x.classList.remove("on"));
    select(top.fips);
  }
  const first = !cleared.has(n); cleared.add(n);
  try { localStorage.setItem("rl-cleared", JSON.stringify([...cleared])); } catch (e) {}
  const all = cleared.size === CH.length;
  $("#brief").innerHTML = body + `<div class="stamp${first ? " pop" : ""}">${all ? "100% Reality<br>checked" : "Chapter<br>cleared"}</div>`;
  $("#chmap").onclick = () => $("#mapbox").scrollIntoView({behavior: "smooth", block: "center"});
  $("#chcard").onclick = () => idCard(byFips[selected]);
  if ($("#chlist")) $("#chlist").onclick = () => { mgCh = n; drawMissions(); $("#missions-h").scrollIntoView({behavior: "smooth"}); };
  drawChapters(); document.querySelectorAll(".ch").forEach(b => b.classList.toggle("on", +b.dataset.n === n));
}
$("#chapters").addEventListener("click", e => { const b = e.target.closest(".ch"); if (b) playChapter(+b.dataset.n); });
drawChapters();

// Mission guide: every story mission, its region's real county, and a data check where there's something to measure
const MS = (D.missions || []).map((m, i) => ({...m, i: i + 1}));
const THEME_LABEL = {driving: "Driving", violence: "Violence", coast: "Coast", swamp: "Swamp", money: "Money", story: "Story beat"};
const THEME_CHECK = {driving: "road deaths per 100k", violence: "homicides per 100k", coast: "hurricanes per decade", swamp: "alligators per 10k sightings", money: "home prices"};
function pctOf(key, f) { const n = D.counties.filter(x => x[key] != null).length, r = rankOf(key, f); return r && n > 1 ? (n - r) / (n - 1) * 100 : null; }
function missionCheck(m) {
  const ch = CH.find(x => x.n === m.ch), key = (D.themes || {})[m.theme];
  if (!ch || !ch.fips) return {where: "Not given", check: "Location not given in the lists", v: null};
  const c = byFips[ch.fips], where = `${ch.region} → ${c.name}`;
  if (!key) return {where, check: "Story beat: nothing to measure", v: null};
  const p = pctOf(key, ch.fips), r = rankOf(key, ch.fips), n = D.counties.filter(x => x[key] != null).length;
  if (p == null) return {where, check: `No ${THEME_CHECK[m.theme]} data for ${c.name}`, v: null};
  return {where, check: `${c.name}: ${THEME_CHECK[m.theme]} #${r} of ${n}`, v: verdict(p)};
}
MS.forEach(m => Object.assign(m, missionCheck(m), {d: missionDiff(m)}));
function tallyText(n) { const t = {"Not exaggerated": 0, Fair: 0, Exaggerated: 0}, ms = MS.filter(m => m.ch === n); let s = 0;
  ms.forEach(m => m.v ? t[m.v[0]]++ : s++);
  return `Its ${ms.length} missions: <b>${t["Not exaggerated"]}</b> not exaggerated · <b>${t.Fair}</b> fair · <b>${t.Exaggerated}</b> exaggerated · ${s} story beats`; }
let mgCh = 0, spoil = false;
function drawMissions() {
  $("#mgch").innerHTML = [0, ...CH.map(c => c.n)].map(n => `<button type="button" class="pill" data-n="${n}" aria-pressed="${n === mgCh}">${n ? "Chapter " + n : "All chapters"}</button>`).join("");
  const th = $("#mgtheme").value, vd = $("#mgverdict").value, q = $("#mgq").value.trim().toLowerCase();
  const list = MS.filter(m => (!mgCh || m.ch === mgCh) && (!th || m.theme === th) && (!vd || (m.v && m.v[0] === vd)) && (!q || (m.name + " " + m.what).toLowerCase().includes(q)));
  const shown = list.filter(m => m.ch !== 5 || spoil);
  const t = {"Not exaggerated": 0, Fair: 0, Exaggerated: 0}; let beats = 0; shown.forEach(m => m.v ? t[m.v[0]]++ : beats++);
  $("#mgsum").innerHTML = `Showing <b>${shown.length}</b> missions${list.length > shown.length ? ` (${list.length - shown.length} chapter 5 missions hidden)` : ""} · <b>${t["Not exaggerated"]}</b> not exaggerated · <b>${t.Fair}</b> fair · <b>${t.Exaggerated}</b> exaggerated · ${beats} with nothing to measure`;
  let html = `<thead><tr><th>#</th><th>Mission</th><th>Where (real county)</th><th>Real-world check</th><th>Difficulty</th><th>Verdict</th></tr></thead><tbody>`, last = 0;
  list.forEach(m => {
    if (m.ch !== last) { last = m.ch; const c = CH.find(x => x.n === m.ch);
      html += `<tr class="chrow"><td colspan="6">Chapter ${m.ch}: ${c ? c.title : ""} · ${c && c.region ? c.region : "location not given"}${m.ch === 5 && !spoil ? ` · <button type="button" class="spoil" data-spoil="1">Show ${list.filter(x => x.ch === 5).length} hidden missions</button>` : ""}</td></tr>`; }
    if (m.ch === 5 && !spoil) return;
    html += `<tr class="row" data-ch="${m.ch}" tabindex="0"><td class="n">${m.i}</td><td class="nm"><b>${m.name}</b><small>${m.what}</small></td><td class="w">${m.where}</td>
      <td class="ck"><span class="theme">${THEME_LABEL[m.theme]}</span><br><small>${m.check}</small></td><td class="st">${m.d == null ? "–" : stars(m.d)}</td><td class="vd">${m.v ? `<span class="verdict ${m.v[1]}">${m.v[0]}</span>` : `<small style="color:var(--muted)">–</small>`}</td></tr>`;
  });
  $("#mgtable").innerHTML = html + "</tbody>";
  $("#mgspoil").textContent = spoil ? "Hide chapter 5" : "Show chapter 5 (spoilers)";
}
$("#mgch").addEventListener("click", e => { const b = e.target.closest("button"); if (b) { mgCh = +b.dataset.n; drawMissions(); } });
["#mgtheme", "#mgverdict"].forEach(id => $(id).addEventListener("change", drawMissions));
$("#mgq").addEventListener("input", drawMissions);
$("#mgspoil").addEventListener("click", () => { spoil = !spoil; drawMissions(); });
$("#mgtable").addEventListener("click", e => { if (e.target.closest("[data-spoil]")) { spoil = true; drawMissions(); return; }
  const tr = e.target.closest("tr.row"); if (!tr) return; const c = CH.find(x => x.n === +tr.dataset.ch); if (c && c.fips) select(c.fips); });
drawMissions();

// ===================== v4: game loop, Player/Dev mode, game-analytics features =====================
const DIFF = ["Easy", "Normal", "Hard", "Very hard", "Insane"];
const diffOf = s => s == null ? "–" : DIFF[nstars(s) - 1];
const state = {persona: null, match: null, roll: null, steps: new Set(), spike: null};
let mode = "player";
try { mode = localStorage.getItem("rl-mode") || "player"; } catch (e) {}
function setMode(m) { mode = m; document.body.classList.toggle("dev", m === "dev");
  $("#mPlayer").setAttribute("aria-pressed", String(m !== "dev")); $("#mDev").setAttribute("aria-pressed", String(m === "dev"));
  try { localStorage.setItem("rl-mode", m); } catch (e) {} }
$("#mPlayer").onclick = () => setMode("player");
$("#mDev").onclick = () => setMode("dev");
$("#heroDev").onclick = () => { setMode("dev"); $("#s1").scrollIntoView({behavior: "smooth"}); };
const sk = (...xs) => xs.map(x => `<span class="skill">${x}</span>`).join("");

// Game loop stepper: a step lights up once you interact with its section
const STEPS = [["s1", "Character"], ["s2", "World"], ["s3", "Difficulty"], ["s4", "Missions"], ["s5", "Heatmaps"], ["s6", "Survive"], ["s7", "PvP"], ["s8", "Seasons"], ["s9", "Results"]];
function drawLoop() { $("#loop").innerHTML = STEPS.map(([id, l], i) => `<li class="${state.steps.has(id) ? "done" : ""}"><a href="#${id}">${state.steps.has(id) ? "✓" : i + 1} ${l}</a></li>`).join(""); }
function mark(id) { if (!state.steps.has(id)) { state.steps.add(id); drawLoop(); } }
["click", "change", "input"].forEach(ev => document.addEventListener(ev, e => { const sec = e.target.closest && e.target.closest("section"); if (sec && e.target.closest("button,.rc,li,path,select,input,tr")) mark(sec.id); }));

// 1. Character select: personas = player segments; matching = weighted similarity
const K = {h: "hurricanes_per_decade", s: "sinkholes_per_1000km2", g: "gators_per_10k_obs", m: "homicide_per_100k", r: "crash_deaths_per_100k"};
const w = (h, s, g, m, r) => ({[K.h]: h, [K.s]: s, [K.g]: g, [K.m]: m, [K.r]: r});
const PERSONAS = [
  {id: "retiree", ic: "🏖️", name: "Retiree", blurb: "Calm weather, safe streets, solid ground. Budget under $400k.", w: w(3, 2, 0, 2, 1), budget: 400000},
  {id: "family", ic: "👨‍👩‍👧", name: "Young family", blurb: "Safe roads and streets first, then storms. Under $400k.", w: w(2, 1, 1, 3, 3), budget: 400000},
  {id: "commuter", ic: "🚗", name: "Commuter", blurb: "Long drives every day, so road safety is everything.", w: w(1, 0, 0, 1, 3), budget: 0},
  {id: "budget", ic: "💸", name: "Budget mover", blurb: "Under $250k, a little careful about everything.", w: w(1, 1, 1, 1, 1), budget: 250000},
  {id: "chaos", ic: "🔥", name: "Chaos seeker", blurb: "Wants the full GTA experience: max wanted level.", w: w(2, 2, 2, 2, 2), budget: 0, invert: true},
];
function setPersona(id) {
  state.persona = id; const p = PERSONAS.find(x => x.id === id);
  if (p) { Object.assign(W, p.w); budget = p.budget; invert = !!p.invert;
    RISKS.forEach(([k]) => { $("#w_" + k).value = W[k]; $("#o_" + k).textContent = LVL[W[k]]; }); $("#budget").value = String(p.budget); }
  else invert = false;
  drawPersonas();
}
function drawPersonas() {
  $("#personas").innerHTML = PERSONAS.map(p => `<button type="button" class="pc" data-id="${p.id}" aria-pressed="${state.persona === p.id}"><span class="ic">${p.ic}</span><b>${p.name}</b><small>${p.blurb}</small></button>`).join("") +
    `<button type="button" class="pc" data-id="" aria-pressed="${!state.persona}"><span class="ic">🎛️</span><b>Custom</b><small>Set your own worries and budget with the sliders.</small></button>`;
}
$("#personas").addEventListener("click", e => { const b = e.target.closest(".pc"); if (!b) return; setPersona(b.dataset.id || null); rank(true); });

// 2. Biomes: k-means zones computed in the build
const BIO = D.biomes || {clusters: [], k: 0, silhouette: {}, features: []};
const BIOCOL = ["#2ee6ff", "#ff3ea5", "#ffd23f", "#9b8cff", "#5be37d", "#ff8a3d"];
const bioName = c => c.biome == null || !BIO.clusters[c.biome] ? "–" : BIO.clusters[c.biome].name;
function paintBiomes() {
  $("#layerdesc").textContent = DESC.biome;
  if (selected) history.replaceState(null, "", `#county=${selected}&layer=${layer}`);
  const regF = regionOn ? D.regions.find(r => r.region === regionOn).fips : D.regions.flatMap(r => r.fips);
  svg.querySelectorAll("path.c").forEach(p => { const c = byFips[p.dataset.f];
    p.classList.toggle("na", c.biome == null); p.style.fill = c.biome == null ? "" : BIOCOL[c.biome % BIOCOL.length];
    p.classList.toggle("reg", regF.includes(c.fips)); p.classList.toggle("sel", c.fips === selected); });
  $("#legend").innerHTML = BIO.clusters.map(b => `<span style="display:inline-flex;align-items:center;gap:6px;margin-right:12px"><i style="width:12px;height:12px;border-radius:3px;background:${BIOCOL[b.id % BIOCOL.length]};display:inline-block"></i>${b.name} (${b.size})</span>`).join("") +
    `<div class="unit">${BIO.k} biomes found by k-means on the five hazard percentiles · colour = zone, not "more" or "less"</div>`;
}

// 3. Difficulty select: region cards with stars and a spawn table
function regionAgg(r) {
  const cs = r.fips.map(f => byFips[f]), sum = k => cs.reduce((a, c) => a + (c[k] || 0), 0);
  const wavg = k => { const v = cs.filter(c => c[k] != null), p = v.reduce((a, c) => a + c.population, 0); return p ? v.reduce((a, c) => a + c[k] * c.population, 0) / p : null; };
  return {cs, hur: sum("hurricanes_1950_2025") / cs.length, maj: sum("major_hurricanes_1950_2025") / cs.length, lf: Math.max(...cs.map(c => c.landfalls_since_1851 || 0)),
    gator: sum("all_obs") ? sum("alligator_obs") / sum("all_obs") : null, road: wavg("crash_deaths_per_100k"), hom: wavg("homicide_per_100k"),
    sink: sum("sinkholes_per_1000km2") / cs.length};
}
const every = (n, yrs) => n > 0 ? `1 every ${fmt(yrs / n, yrs / n < 10 ? 1 : 0)} yrs` : "none on record";
const oneIn = p => p > 0 ? `1 in ${Math.round(1 / p).toLocaleString("en-CA")}` : "–";
function spawnRows(a) {
  return [["🌀 Hurricane passes", every(a.hur, YEARS)], ["🌪️ Major (Cat 3+)", every(a.maj, YEARS)], ["🏝️ Landfall (since 1851)", every(a.lf, 175)],
    ["🐊 Gator", a.gator ? oneIn(a.gator) + " sightings" : "–"], ["🚗 Road death", a.road ? oneIn(a.road / 1e5) + " people/yr" : "–"],
    ["🚨 Homicide", a.hom ? oneIn(a.hom / 1e5) + " people/yr" : "–"], ["🕳️ Sinkholes", fmt(a.sink, 1) + " per 1,000 km²"]];
}
function drawRegions() {
  $("#regions").innerHTML = D.regions.map(r => { const a = regionAgg(r), v = verdict(r.reality_score);
    return `<div class="rc" tabindex="0" role="button" data-region="${r.region}" aria-label="${r.region}: difficulty ${diffOf(r.reality_score)}, ${nstars(r.reality_score)} of 5 stars">
      <span class="conf">${r.confidence} match</span><h3>${r.region}</h3>
      <div class="insp">${r.inspiration} · ${r.counties}</div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">${stars(r.reality_score)} <span class="diff">${diffOf(r.reality_score)}</span> <span class="verdict ${v[1]}">${v[0]}</span></div>
      <table class="spawn">${spawnRows(a).map(([k, x]) => `<tr><td>${k}</td><td>${x}</td></tr>`).join("")}</table>
      <div class="bars devin">${Object.keys(short).map(k => { const p = r[k + "_pct"]; return `<div class="bar"><span>${short[k]}</span><i><em style="width:${p == null ? 0 : p}%"></em></i><span>${p == null ? "–" : Math.round(p)}</span></div>`; }).join("")}<span class="ab">difficulty score ${Math.round(r.reality_score)} / 100 = mean of these percentiles</span></div>
    </div>`; }).join("");
  document.querySelectorAll(".rc").forEach(el => {
    const act = () => { const r = D.regions.find(x => x.region === el.dataset.region); regionOn = regionOn === r.region ? null : r.region;
      document.querySelectorAll(".rc").forEach(x => x.classList.toggle("on", x.dataset.region === regionOn));
      if (regionOn) { select(r.fips[0]); $("#mapbox").scrollIntoView({behavior: "smooth", block: "center"}); } paint(); };
    el.addEventListener("click", act); el.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); act(); } });
  });
}

// 4. Mission difficulty and the difficulty curve
function missionDiff(m) {
  const ch = CH.find(x => x.n === m.ch); if (!ch || !ch.fips) return null;
  const c = byFips[ch.fips], key = (D.themes || {})[m.theme], p = key ? pctOf(key, ch.fips) : null;
  return p == null ? c.chaos_score : 0.7 * p + 0.3 * c.chaos_score;
}
const CHCOL = ["#2ee6ff", "#ffd23f", "#ff3ea5", "#9b8cff", "#8f84b5"];
function drawCurve() {
  const Wd = 900, Hd = 250, l = 64, r = 10, t = 26, b = 30, n = MS.length;
  const x = i => l + i / (n - 1) * (Wd - l - r), y = d => t + (1 - d / 100) * (Hd - t - b);
  let g = "";
  CH.forEach((ch, j) => { const ms = MS.filter(m => m.ch === ch.n); if (!ms.length) return; const x0 = x(ms[0].i - 1) - 4, x1 = x(ms[ms.length - 1].i - 1) + 4;
    g += `<rect x="${x0}" y="${t}" width="${x1 - x0}" height="${Hd - t - b}" fill="${CHCOL[j]}" opacity=".07"></rect><text x="${(x0 + x1) / 2}" y="${t - 8}" text-anchor="middle" class="lbl">Ch ${ch.n}</text>`; });
  [20, 40, 60, 80].forEach((v, i) => { g += `<line class="grid" x1="${l}" x2="${Wd - r}" y1="${y(v)}" y2="${y(v)}"></line><text x="${l - 4}" y="${y(v) + 4}" text-anchor="end">${"★".repeat(i + 1)}</text>`; });
  const pts = MS.filter(m => m.d != null);
  g += `<polyline fill="none" stroke="var(--ink2)" stroke-width="1.2" stroke-opacity=".5" points="${pts.map(m => x(m.i - 1) + "," + y(m.d)).join(" ")}"></polyline>`;
  g += pts.map(m => `<circle cx="${x(m.i - 1)}" cy="${y(m.d)}" r="${m.theme === "story" ? 2.5 : 4.5}" fill="${CHCOL[m.ch - 1]}"><title>#${m.i} ${m.name}: ${diffOf(m.d)} (${Math.round(m.d)}) · ${THEME_LABEL[m.theme]}</title></circle>`).join("");
  g += `<text x="${l}" y="${Hd - 8}">Mission 1</text><text x="${Wd - r}" y="${Hd - 8}" text-anchor="end">Mission ${n}</text>`;
  $("#curve").innerHTML = `<svg class="chart" viewBox="0 0 ${Wd} ${Hd}" role="img" aria-label="Real-world difficulty of each mission in story order">${g}</svg><p class="hint">Big dots = missions about something measurable (driving, violence, coast, swamp, money); small dots = story beats, which take their region's overall difficulty. Hover a dot for the mission.</p>`;
  let best = null; for (let i = 1; i < pts.length; i++) { const dlt = pts[i].d - pts[i - 1].d; if (!best || dlt > best.dlt) best = {dlt, a: pts[i - 1], b: pts[i]}; }
  state.spike = best;
}

// 5. Heatmaps: where the story sends you vs where Florida is deadly
function miniMap(el, key, ramp, br) {
  el.setAttribute("viewBox", `0 0 ${D.W} ${D.H}`);
  el.innerHTML = D.counties.map(c => { const v = c[key]; return `<path class="c${v == null ? " na" : ""}" d="${c.path}" style="${v == null ? "" : "fill:" + ramp[br.filter(q => v > q).length]}"><title>${c.name}: ${v == null ? "none" : fmt(v, key === "danger" ? 1 : 0)}</title></path>`; }).join("");
}
function drawHeatmaps() {
  const ramp = RAMPS[theme];
  miniMap($("#hmStory"), "story_missions", ramp, [0, 10, 20, 30]);
  miniMap($("#hmDanger"), "danger", ramp, breaks(D.counties.map(c => c.danger)));
  const sm = D.counties.filter(c => c.story_missions).sort((a, b) => b.story_missions - a.story_missions), tot = sm.reduce((a, c) => a + c.story_missions, 0);
  $("#hmStoryTxt").textContent = sm.length ? `The story is set in just ${sm.length} of ${D.counties.length} real counties. ${sm[0].name} alone hosts ${sm[0].story_missions} of the ${tot} placed missions.` : "";
  const dz = D.counties.filter(c => c.danger != null).sort((a, b) => b.danger - a.danger).slice(0, 3);
  $("#hmDangerTxt").textContent = `Deadliest: ${dz.map(c => `${c.name} (${fmt(c.danger, 0)} per 100k)`).join(", ")}. ${dz.every(c => !c.story_missions) ? "None of them hosts a story chapter." : ""}`;
  const road = D.counties.reduce((a, c) => a + (c.crash_deaths_per_100k || 0) * c.population / 1e5, 0), hom = D.counties.reduce((a, c) => a + (c.homicide_per_100k || 0) * c.population / 1e5, 0);
  const gd = MS.filter(m => m.theme === "driving").length, gv = MS.filter(m => m.theme === "violence").length, mx = Math.max(road, hom);
  $("#killers").innerHTML = `<h3>The game vs the real killers</h3><div class="funnel">
    <div class="row"><span>🚗 Real road deaths a year</span><div class="bar2" style="width:${road / mx * 100}%"></div><span>${fmt(road, 0)}</span></div>
    <div class="row"><span>🚨 Real homicides a year</span><div class="bar2" style="width:${hom / mx * 100}%"></div><span>${fmt(hom, 0)}</span></div></div>
    <p class="hint">In real Florida, roads kill about <b>${fmt(road / hom, 1)}×</b> as many people as homicide. In the game's story, driving missions (${gd}) and violence missions (${gv}) get about the same airtime.</p>`;
}

// 6. Survive the season: seeded Monte Carlo (stable numbers) + a one-off random roll
function mulberry(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function poisson(l, rnd) { if (l <= 0) return 0; const L = Math.exp(-l); let k = 0, p = 1; do { k++; p *= rnd(); } while (p > L); return k - 1; }
function odds(c) { return {r: c.hurricanes_1950_2025 / YEARS, rm: c.major_hurricanes_1950_2025 / YEARS, rl: (c.landfalls_since_1851 || 0) / 175,
  pr: (c.crash_deaths_per_100k || 0) / 1e5, ph: (c.homicide_per_100k || 0) / 1e5}; }
function simulate(c, n, runs = 10000) {
  const o = odds(c), rnd = mulberry(20261125); let any = 0, s1 = 0, s2 = 0, s3 = 0, s4 = 0;
  for (let i = 0; i < runs; i++) {
    if (poisson(o.r * n, rnd) > 0) any++;
    if (poisson(o.rm * n, rnd) > 0) continue; s1++;
    if (poisson(o.rl * n, rnd) > 0) continue; s2++;
    if (rnd() < 1 - Math.pow(1 - o.pr, n)) continue; s3++;
    if (rnd() < 1 - Math.pow(1 - o.ph, n)) continue; s4++;
  }
  return {runs, any, s1, s2, s3, s4, o};
}
function typicalCounty() { const s = [...D.counties].sort((a, b) => a.hurricanes_1950_2025 - b.hurricanes_1950_2025); return s[Math.floor(s.length / 2)]; }
function surviveMC() {
  const c = byFips[$("#sv").value], n = +$("#yrs").value; $("#yrso").textContent = n + (n === 1 ? " year" : " years");
  const S = simulate(c, n), T = simulate(typicalCounty(), n), pc = x => Math.round(x / S.runs * 100);
  $("#svout").innerHTML = `<div style="color:var(--ink2);font-size:14px">${c.name}, ${n} ${n === 1 ? "year" : "years"}: chance at least one hurricane passes within 60 nm</div>
    <div class="big">${pc(S.any)}%</div>
    <div style="font-size:15px;margin-top:6px">A major (Cat 3+) one: <b>${100 - pc(S.s1)}%</b> · A typical Florida county: <b>${Math.round(T.any / T.runs * 100)}%</b></div>
    <div class="note">${c.name} saw ${c.hurricanes_1950_2025} hurricanes (${c.major_hurricanes_1950_2025} major) pass within 60 nm in ${YEARS} years, about one every ${c.hurricanes_1950_2025 ? fmt(YEARS / c.hurricanes_1950_2025, 1) : "–"} years. Odds come from 10,000 simulated runs.</div>`;
  const rows = [["🎮 Players who start", S.runs], ["🌪️ No major hurricane nearby", S.s1], ["🏝️ …and no landfall in the county", S.s2], ["🚗 …and no fatal road crash", S.s3], ["🚨 …and not a homicide victim", S.s4]];
  $("#funnel").innerHTML = `<div class="funnel">${rows.map(([l, v]) => `<div class="row"><span>${l}</span><div class="bar2" style="width:${v / S.runs * 100}%"></div><span>${v.toLocaleString("en-CA")}</span></div>`).join("")}</div>
    <p class="hint">${(S.s4 / S.runs * 100).toFixed(1)}% get a clean run of ${n} ${n === 1 ? "year" : "years"} in ${c.name}. The biggest drop is the step where most players fall out of the funnel.</p>`;
  const an = k => 1 - Math.exp(-k * n);
  $("#dev6").innerHTML = `<h4>Dev Mode: Monte Carlo + funnel</h4>${sk("Monte Carlo simulation", "Poisson model", "Funnel analysis")}
    <p>Each of 10,000 runs draws hurricanes from a Poisson process with the county's 1950-2025 rate, landfalls from the 1851-2025 rate, and road deaths and homicides as yearly chances. The funnel is the game designer's "how many players clear each stage", applied to real hazards. A fixed random seed keeps the numbers stable between visits.</p>
    <table><tr><th>Event in ${n} yrs</th><th>Formula 1 − e<sup>−λt</sup></th><th>Simulated</th></tr>
    <tr><td>Any hurricane within 60 nm</td><td>${(an(S.o.r) * 100).toFixed(1)}%</td><td>${(S.any / S.runs * 100).toFixed(1)}%</td></tr>
    <tr><td>Major hurricane within 60 nm</td><td>${(an(S.o.rm) * 100).toFixed(1)}%</td><td>${(100 - S.s1 / S.runs * 100).toFixed(1)}%</td></tr></table>
    <p>Assumptions: the past rate holds (no climate trend), events are independent (in reality a landfall usually comes with a nearby major storm), and the person lives in the county the whole time.</p>`;
}
$("#roll").onclick = () => {
  const c = byFips[$("#sv").value], n = +$("#yrs").value, o = odds(c), rnd = Math.random, log = []; let alive = true, ev = 0;
  for (let y = 1; y <= n && alive; y++) {
    for (let i = poisson(o.r, rnd); i > 0; i--) { const maj = rnd() < (o.r ? o.rm / o.r : 0); log.push(["bad", `Year ${y}: ${maj ? "🌪️ a major (Cat 3+) hurricane" : "🌀 a hurricane"} passed within 60 nm`]); ev++; }
    if (poisson(o.rl, rnd) > 0) { log.push(["bad", `Year ${y}: 🏝️ a hurricane made landfall in ${c.name}`]); ev++; }
    if (rnd() < o.pr) { log.push(["bad", `Year ${y}: 🚑 fatal road crash (a ${oneIn(o.pr)} yearly chance). Run over.`]); alive = false; }
    else if (rnd() < o.ph) { log.push(["bad", `Year ${y}: 🚨 homicide (a ${oneIn(o.ph)} yearly chance). Run over.`]); alive = false; }
  }
  if (!ev && alive) log.push(["ok", `${n} quiet ${n === 1 ? "year" : "years"}. Nothing spawned.`]);
  log.push(["ok", alive ? `✅ You made it through ${n} ${n === 1 ? "year" : "years"} in ${c.name}${ev ? ` and ${ev} storm ${ev === 1 ? "event" : "events"}` : ""}.` : "💀 Game over. (Real odds are much kinder than GTA's: try again.)"]);
  $("#rolllog").innerHTML = log.map(([k, t]) => `<li class="${k}">${t}</li>`).join("");
  state.roll = {fips: c.fips, n, alive, ev}; drawResults();
};

// Boss roster: the 17 major landfalls, hit points = wind at landfall
function drawBosses() {
  const list = tracks.map((t, i) => ({...t, i})).sort((a, b) => b.landfall_kt - a.landfall_kt || b.year - a.year);
  $("#bosses").innerHTML = list.length ? list.map(t => `<button type="button" class="boss" data-i="${t.i}"><b>${t.name} ${t.year}</b><div class="hp"><i style="width:${Math.min(100, t.landfall_kt / 160 * 100)}%"></i></div><small>${catName(t.landfall_kt)} · ${t.landfall_kt} kt HP · ${t.counties.join(", ")}</small></button>`).join("") : `<p class="hint">Storm tracks are added when the site is built from NOAA data.</p>`;
}
$("#bosses").addEventListener("click", e => { const b = e.target.closest(".boss"); if (!b) return; $("#trackSel").value = b.dataset.i; stopPlay(); showTracks(b.dataset.i); $("#mapbox").scrollIntoView({behavior: "smooth", block: "center"}); });

// 7. PvP A/B tests: rate ratio with a 95% confidence interval (log method, 0.5 added to zero counts)
function rrCI(a, ea, b, eb) { const x = a || 0.5, y = b || 0.5, rr = (x / ea) / (y / eb), se = Math.sqrt(1 / x + 1 / y); return [rr, rr * Math.exp(-1.96 * se), rr * Math.exp(1.96 * se)]; }
function abTest(k, a, b) {
  const note = t => `<span class="ab">A/B: ${t}</span>`; if (a.fips === b.fips) return "";
  let x;
  if (k === "hurricanes_per_decade") x = rrCI(a.hurricanes_1950_2025, 1, b.hurricanes_1950_2025, 1);
  else if (k === "sinkholes_per_1000km2") { const ar = c => c.area_km2 || (c.sinkholes_per_1000km2 ? c.sinkholes / c.sinkholes_per_1000km2 * 1000 : null);
    if (!ar(a) || !ar(b)) return note("not enough reports to test"); x = rrCI(a.sinkholes, ar(a), b.sinkholes, ar(b)); }
  else if (k === "gators_per_10k_obs") { if (!a.all_obs || !b.all_obs) return note("no sightings data"); x = rrCI(a.alligator_obs, a.all_obs, b.alligator_obs, b.all_obs); }
  else if (k === "homicide_per_100k") { if (a.homicide_n == null || b.homicide_n == null) return note("counts suppressed by the source"); x = rrCI(a.homicide_n, a.population, b.homicide_n, b.population); }
  else if (k === "crash_deaths_per_100k") { if (a.crash_n == null || b.crash_n == null) return note("death counts not in this build"); x = rrCI(a.crash_n, a.population, b.crash_n, b.population); }
  else return note("one value each, nothing to test");
  const [rr, lo, hi] = x, sig = lo > 1 || hi < 1;
  return `<span class="ab">A/B: ${fmt(rr, 2)}× (95% CI ${fmt(lo, 2)}–${fmt(hi, 2)}) · <span class="sig ${sig ? "yes" : "no"}">${sig ? "real difference" : "could be luck"}</span></span>`;
}

// 8. Seasons: hurricanes per decade, per year so the partial 2020s compare fairly
function drawSeasons() {
  const S = D.seasons;
  if (!S) { $("#seasons").innerHTML = `<p class="hint">Season data is added when the site is built from NOAA data.</p>`; return; }
  if (!$("#seaSel").options.length) $("#seaSel").innerHTML = D.regions.map(r => `<option value="r:${r.region}">${r.region} (${r.counties})</option>`).join("") + sorted.map(c => `<option value="c:${c.fips}">${c.name}</option>`).join("");
  const v = $("#seaSel").value, sel = v.startsWith("r:") ? D.regions.find(r => r.region === v.slice(2)).fips.map(f => byFips[f]) : [byFips[v.slice(2)]];
  const loc = S.labels.map((_, i) => sel.reduce((a, c) => a + ((c.dec || [])[i] || 0), 0) / sel.length / S.years[i]);
  const fl = S.fl_pass.map((x, i) => x / S.years[i]), mj = S.fl_major_lf.map((x, i) => x / S.years[i]);
  const Wd = 900, Hd = 240, l = 40, r = 10, t = 16, b = 34, mx = Math.max(...fl, ...loc, 0.1), bw = (Wd - l - r) / S.labels.length;
  const y = q => t + (1 - q / mx) * (Hd - t - b);
  let g = [0.25, 0.5, 0.75, 1].map(f => `<line class="grid" x1="${l}" x2="${Wd - r}" y1="${y(f * mx)}" y2="${y(f * mx)}"></line><text x="${l - 4}" y="${y(f * mx) + 4}" text-anchor="end">${fmt(f * mx, 1)}</text>`).join("");
  S.labels.forEach((lab, i) => { const x0 = l + i * bw + 6, w3 = (bw - 14) / 3;
    [[fl[i], "#2ee6ff", "Florida: hurricanes nearby"], [mj[i], "#ff3ea5", "Florida: major landfalls"], [loc[i], "#ffd23f", "Your pick: hurricanes nearby"]].forEach(([q, col, nm], j) =>
      g += `<rect x="${x0 + j * w3}" y="${y(q)}" width="${w3 - 2}" height="${Hd - b - y(q)}" rx="2" fill="${col}"><title>${lab} · ${nm}: ${fmt(q, 2)} per year</title></rect>`);
    g += `<text x="${l + i * bw + bw / 2}" y="${Hd - 12}" text-anchor="middle">${lab}${S.years[i] < 10 ? "*" : ""}</text>`; });
  $("#seasons").innerHTML = `<svg class="chart" viewBox="0 0 ${Wd} ${Hd}" role="img" aria-label="Hurricanes per year by decade">${g}</svg>
    <div class="legend"><span><i style="background:#2ee6ff;width:10px;height:10px;display:inline-block;border-radius:2px"></i> Hurricanes passing Florida per year</span><span style="margin-left:12px"><i style="background:#ff3ea5;width:10px;height:10px;display:inline-block;border-radius:2px"></i> Major landfalls in Florida per year</span><span style="margin-left:12px"><i style="background:#ffd23f;width:10px;height:10px;display:inline-block;border-radius:2px"></i> Your pick: hurricanes passing within 60 nm per year</span></div>`;
  const hi = fl.indexOf(Math.max(...fl)), lo = fl.indexOf(Math.min(...fl));
  $("#seaTxt").textContent = `Busiest season for Florida: the ${S.labels[hi]} (${fmt(fl[hi], 1)} hurricanes a year passed near the state). Quietest: the ${S.labels[lo]} (${fmt(fl[lo], 1)}). *The 2020s so far cover ${S.years[S.years.length - 1]} years, so every bar is per year.`;
  const xs = fl.map((_, i) => i), mxx = xs.reduce((a, b) => a + b) / xs.length, my = fl.reduce((a, b) => a + b) / fl.length;
  const slope = xs.reduce((a, x, i) => a + (x - mxx) * (fl[i] - my), 0) / xs.reduce((a, x) => a + (x - mxx) ** 2, 0);
  $("#dev8").innerHTML = `<h4>Dev Mode: seasons as cohorts</h4>${sk("Trend analysis", "Cohorts", "Normalisation")}
    <p>Each decade is a cohort, like a game season. Counts are divided by the years in the decade so the 2020s (${S.years[S.years.length - 1]} years so far) compare fairly. Least-squares trend for Florida: <b>${slope >= 0 ? "+" : ""}${fmt(slope, 2)}</b> hurricanes a year per decade. With ${fl.length} points that's a description, not a forecast.</p>`;
}
$("#seaSel").addEventListener("change", drawSeasons);

// 9. Results screen
function drawResults() {
  const f = state.match || selected || "12086", c = byFips[f], p = PERSONAS.find(x => x.id === state.persona);
  const R = state.roll && state.roll.fips === f ? state.roll : null, S = simulate(c, 10);
  $("#resultsbox").innerHTML = `<div><div class="no" style="font-size:11px;font-weight:800;letter-spacing:.14em;color:var(--pink)">YOUR RUN</div>
    <h3 style="margin:2px 0 6px;font-size:24px;font-weight:900;font-style:italic;text-transform:uppercase">${p ? p.ic + " " + p.name + " in " : ""}${c.name} County</h3>
    ${stars(c.chaos_score)} <span class="diff">${diffOf(c.chaos_score)}</span>
    <ul><li>Biome: <b>${bioName(c)}</b>${c.regions.length ? ` · GTA 6: <b>${c.regions.join(" / ")}</b>` : ""}</li>
    <li>${state.match === f ? "Your best match from character select" : "Pick a character in step 1 to get matched"}</li>
    <li>${R ? (R.alive ? `You survived your ${R.n}-year run (${R.ev} storm events)` : `Your ${R.n}-year run ended early`) : `Clean 10-year run in 10,000 simulations: <b>${(S.s4 / S.runs * 100).toFixed(0)}%</b>`}</li></ul>
    <div class="btnrow"><button type="button" class="btn hot" id="rcard">⬇ Download your card</button><a class="btn" href="#s1">↺ New character</a></div></div>
    <div style="font-size:64px;line-height:1">${p ? p.ic : "🎮"}</div>`;
  $("#rcard").onclick = () => idCard(c);
}

// Dev Mode panels for steps 1-5 and 7
function drawDev() {
  $("#dev1").innerHTML = `<h4>Dev Mode: player segmentation + matchmaking</h4>${sk("Segmentation", "Recommendation", "Weighted scoring")}
    <p>Studios split players into segments and match them to content. Here each character is a segment with its own weights on the five hazards and a budget. A county's match = weighted mean of <code>100 − percentile</code> on each hazard (the Chaos seeker flips it to <code>percentile</code>). Counties over budget are left out, and suppressed data counts as a typical county (50), so tiny counties don't win by having no data.</p>
    <table><tr><th>Character</th>${RISKS.map(([, l]) => `<th>${l}</th>`).join("")}<th>Budget</th></tr>${PERSONAS.map(p => `<tr><td>${p.ic} ${p.name}</td>${RISKS.map(([k]) => `<td>${p.w[k]}</td>`).join("")}<td>${p.budget ? money(p.budget) : "any"}</td></tr>`).join("")}</table>`;
  const sil = Object.entries(BIO.silhouette || {});
  const cross = D.regions.map(r => `<tr><td>${r.region}</td><td>${r.fips.map(f => `${byFips[f].name}: ${bioName(byFips[f])}`).join(" · ")}</td></tr>`).join("");
  $("#dev2").innerHTML = `<h4>Dev Mode: clustering the world into biomes</h4>${sk("k-means clustering", "Silhouette score", "Feature scaling")}
    <div class="devgrid"><div><p>Open-world games split the map into biomes. I let the data do it: each county is a point in 5-D (its percentile on hurricanes, sinkholes, gators, homicide, road deaths; missing = 50), then k-means groups similar counties. k = <b>${BIO.k}</b> was picked because it had the best silhouette score (how well each county fits its own zone vs the next one).</p>
    <table><tr><th>k</th><th>Silhouette</th></tr>${sil.map(([k, s]) => `<tr><td>${k}${+k === BIO.k ? " ✓" : ""}</td><td>${s}</td></tr>`).join("")}</table></div>
    <div><table><tr><th>Biome (counties)</th><th>🌀</th><th>🕳️</th><th>🐊</th><th>🚨</th><th>🚗</th></tr>${BIO.clusters.map(b => `<tr><td><i style="background:${BIOCOL[b.id % BIOCOL.length]};width:9px;height:9px;display:inline-block;border-radius:2px"></i> ${b.name} (${b.size})</td>${b.centroid.map(v => `<td style="background:rgba(255,62,165,${(v / 100 * .55).toFixed(2)})">${Math.round(v)}</td>`).join("")}</tr>`).join("")}</table>
    <p>Cells = the zone's average percentile; pinker = more of that hazard. Each zone is named after the hazard it stands out on ("Hardcore Zone" = high on almost everything).</p>
    <p>${(BIO.silhouette || {})[BIO.k] < 0.3 ? `A silhouette of ${(BIO.silhouette || {})[BIO.k]} is moderate: Florida's counties blend into each other, so read the zones as broad tendencies, not hard borders.` : ""}</p></div></div>
    <h4 style="margin-top:10px">Game regions vs data biomes</h4><table>${cross}</table>`;
  $("#dev3").innerHTML = `<h4>Dev Mode: difficulty and spawn rates</h4>${sk("Composite scoring", "Percentiles", "Rate modelling")}
    <p>Each hazard is ranked against all 67 counties (percentile, so different units can be combined), then averaged into a 0-100 difficulty score; ★ = every 20 points. Spawn rates turn raw counts into "how often": 76 years ÷ hurricanes = years between storms; 100,000 ÷ deaths per 100k = "1 in N people a year". The bars on each card (Dev Mode only) are the percentiles behind the stars.</p>
    <table><tr><th>Region</th><th>Hurricanes 1950-2025</th><th>1 every … yrs (95% CI)</th></tr>${D.regions.map(r => { const n = Math.round(regionAgg(r).hur), lo = n ? n * (1 - 1 / (9 * n) - 1.96 / (3 * Math.sqrt(n))) ** 3 : 0, hi = (n + 1) * (1 - 1 / (9 * (n + 1)) + 1.96 / (3 * Math.sqrt(n + 1))) ** 3;
      return `<tr><td>${r.region}</td><td>${n}</td><td>${n ? fmt(YEARS / n, 1) : "–"} (${fmt(YEARS / hi, 1)}–${lo ? fmt(YEARS / lo, 1) : "∞"})</td></tr>`; }).join("")}</table><p>Confidence ranges use Byar's approximation to the Poisson interval: a county with few storms has a wide range.</p>`;
  const sp = state.spike, chAvg = CH.filter(c => c.fips).map(c => { const ms = MS.filter(m => m.ch === c.n && m.d != null); return [c, ms.reduce((a, m) => a + m.d, 0) / ms.length]; });
  $("#dev4").innerHTML = `<h4>Dev Mode: modelling mission difficulty</h4>${sk("Difficulty curve", "Feature engineering", "Game balancing")}
    <p>Designers chart difficulty across a campaign to find spikes. Each mission's real-world difficulty = <code>0.7 × percentile of its hazard</code> (road deaths for driving, homicide for violence, hurricanes for the coast, gators for swamps, home prices for money) <code>+ 0.3 × its county's overall difficulty</code>. Story beats take the county's overall difficulty. A mission's location is its chapter's main region.</p>
    <table><tr><th>Chapter</th><th>Real county</th><th>Average difficulty</th></tr>${chAvg.map(([c, a]) => `<tr><td>${c.n}. ${c.title}</td><td>${byFips[c.fips].name}</td><td>${fmt(a, 0)} ${"★".repeat(nstars(a))}</td></tr>`).join("")}</table>
    ${sp ? `<p>Biggest spike: <b>#${sp.a.i} ${sp.a.name}</b> → <b>#${sp.b.i} ${sp.b.name}</b> (+${fmt(sp.dlt, 0)} points).</p>` : ""}`;
  const dangerMed = [...D.counties].map(c => c.danger).filter(v => v != null).sort((a, b) => a - b), med = dangerMed[Math.floor(dangerMed.length / 2)];
  const inHot = D.counties.filter(c => c.story_missions && c.danger > med).reduce((a, c) => a + c.story_missions, 0), tot = D.counties.reduce((a, c) => a + (c.story_missions || 0), 0);
  $("#dev5").innerHTML = `<h4>Dev Mode: heatmaps done right</h4>${sk("Spatial analysis", "Normalisation", "Choropleths")}
    <p>Two choices make these maps honest. <b>Per-capita rates</b>: raw death counts would just light up big cities, so the danger map uses deaths per 100,000 residents. <b>Quantile colours</b>: 5 groups of about 13 counties each, so colour shows rank and one extreme county can't wash out the rest. The story map is a count of missions per county.</p>
    <p>Overlap: <b>${tot ? Math.round(inHot / tot * 100) : 0}%</b> of placed story missions are set in counties above Florida's median danger (${fmt(med, 1)} deaths per 100k).</p>`;
  $("#dev7").innerHTML = `<h4>Dev Mode: every round is an A/B test</h4>${sk("A/B testing", "Confidence intervals", "Rate ratios")}
    <p>Studios A/B test before saying one version beats another. Each round compares the two counties' rates with a <b>rate ratio</b> and a 95% confidence interval (log method: <code>RR × e<sup>±1.96·√(1/a + 1/b)</sup></code>, using the real counts: storms, sinkhole reports, gator sightings, deaths). If the interval doesn't include 1×, the gap is a <span class="sig yes">real difference</span>; otherwise it <span class="sig no">could be luck</span>. Home prices have one value each, so there's nothing to test.</p>`;
}


// Start
const H = Object.fromEntries(location.hash.slice(1).split("&").filter(Boolean).map(kv => kv.split("=")));
if (H.layer && layerBy[H.layer] && H.layer !== "match") { layer = H.layer; drawControls(); }
setTheme(theme); setMode(mode); drawRegions(); drawPersonas(); table(); rank(false); fight(); survive(); select(byFips[H.county] ? H.county : "12086");
drawCurve(); drawHeatmaps(); drawBosses(); drawSeasons(); drawDev(); drawLoop(); drawResults();
