/* /collection showcase. Reads nft/metadata.json, shows ONE form at a time.
   Reroll draws a random form from the active palette; Prev/Next step through
   the filtered list; the view toggle flips bust <-> animated full body. */
(async function () {
  const stage = document.getElementById("stage");
  const toggle = document.getElementById("viewtoggle");
  const title = document.getElementById("title");
  const paletteTag = document.getElementById("palette-tag");
  const traits = document.getElementById("traits");
  const countEl = document.getElementById("count");
  const prevBtn = document.getElementById("prev");
  const nextBtn = document.getElementById("next");
  const rerollBtn = document.getElementById("reroll");
  const chips = [...document.querySelectorAll(".chip[data-palette]")];

  const pad = n => String(n).padStart(4, "0");

  let all = [], view = [], idx = 0, palette = "all", expanded = false;

  const PALETTE_COLORS = { ink: "#111", warm: "#c2410c", cold: "#2563eb", green: "#15803d", violet: "#7c3aed" };

  function cleanValue(a) {
    // "Body color (olive)" -> "olive"; everything else reads fine as-is
    if (a.trait_type === "Body") return a.value.replace(/^Body color\s*/i, "");
    return a.value;
  }

  function render() {
    const t = view[idx];
    if (!t) return;
    const pal = (t.attributes.find(a => a.trait_type === "Palette") || {}).value || "ink";
    stage.closest(".show").classList.toggle("is-expanded", expanded);
    if (expanded) {
      stage.src = `/nft/gif/${pad(t.id)}.gif`;
      stage.alt = `Polaris Form #${t.id} full body`;
      toggle.textContent = "Bust";
      toggle.setAttribute("aria-pressed", "true");
    } else {
      stage.src = `/nft/bust/${pad(t.id)}.png`;
      stage.alt = `Polaris Form #${t.id} bust`;
      toggle.textContent = "Full view";
      toggle.setAttribute("aria-pressed", "false");
    }
    title.textContent = `#${t.id}`;
    paletteTag.textContent = pal;
    paletteTag.style.setProperty("--pal", PALETTE_COLORS[pal] || "#111");
    traits.innerHTML = t.attributes
      .filter(a => a.trait_type !== "Palette")
      .map(a => `<div><dt>${a.trait_type}</dt><dd>${cleanValue(a)}</dd></div>`).join("");
    prevBtn.disabled = idx <= 0;
    nextBtn.disabled = idx >= view.length - 1;
    history.replaceState(null, "", `/collection?id=${t.id}`);
  }

  function buildView() {
    view = palette === "all"
      ? all
      : all.filter(t => t.attributes.some(a => a.trait_type === "Palette" && a.value === palette));
  }

  function setPalette(p) {
    palette = p;
    chips.forEach(c => c.setAttribute("aria-pressed", String(c.dataset.palette === p)));
    buildView();
    idx = Math.floor(Math.random() * view.length);
    render();
  }

  try {
    all = await (await fetch("/nft/metadata.json", { cache: "force-cache" })).json();
  } catch (e) {
    traits.innerHTML = '<p class="lede">Metadata failed to load.</p>';
    return;
  }
  countEl.textContent = `${all.length.toLocaleString()} forms`;
  buildView();

  const deep = new URLSearchParams(location.search).get("id");
  if (deep) {
    const i = view.findIndex(t => t.id === Number(deep));
    idx = i >= 0 ? i : Math.floor(Math.random() * view.length);
  } else {
    idx = Math.floor(Math.random() * view.length);
  }
  render();

  toggle.addEventListener("click", () => { expanded = !expanded; render(); });
  rerollBtn.addEventListener("click", () => {
    idx = Math.floor(Math.random() * view.length);
    render();
    stage.parentElement.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  prevBtn.addEventListener("click", () => { if (idx > 0) { idx--; render(); } });
  nextBtn.addEventListener("click", () => { if (idx < view.length - 1) { idx++; render(); } });
  chips.forEach(c => c.addEventListener("click", () => setPalette(c.dataset.palette)));

  document.addEventListener("keydown", e => {
    if (e.key === "ArrowLeft" && !prevBtn.disabled) { idx--; render(); }
    if (e.key === "ArrowRight" && !nextBtn.disabled) { idx++; render(); }
    if (e.key.toLowerCase() === "r") { idx = Math.floor(Math.random() * view.length); render(); }
  });
})();
