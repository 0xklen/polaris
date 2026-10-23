/* Polaris - small, dependency-free behaviours.
   No scroll listeners: nav state and reveals use IntersectionObserver. */

(function () {
  "use strict";

  /* --- mark wall (decorative) --- */
  var wall = document.getElementById("wall");
  if (wall) {
    var fill = function () {
      var cols = Math.max(3, Math.floor(wall.clientWidth / 104));
      var count = cols * (window.innerWidth < 720 ? 3 : 4);
      if (wall.children.length === count) return;
      wall.textContent = "";
      var frag = document.createDocumentFragment();
      for (var i = 0; i < count; i++) frag.appendChild(document.createElement("i"));
      wall.appendChild(frag);
    };
    fill();
    var t;
    window.addEventListener("resize", function () {
      clearTimeout(t);
      t = setTimeout(fill, 180);
    }, { passive: true });
  }

  /* --- nav hairline once the page has scrolled past the hero top --- */
  var nav = document.getElementById("nav");
  var sentinel = document.querySelector(".hero");
  if (nav && sentinel && "IntersectionObserver" in window) {
    new IntersectionObserver(function (entries) {
      nav.classList.toggle("is-stuck", !entries[0].isIntersecting);
    }, { rootMargin: "-70px 0px 0px 0px" }).observe(sentinel);
  }

  /* --- reveal on first view --- */
  var targets = document.querySelectorAll(".split, .steps, .faq, .wall-copy");
  if (targets.length && "IntersectionObserver" in window &&
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("is-in");
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
    targets.forEach(function (t) {
      t.classList.add("reveal");
      io.observe(t);
    });
  }

  /* --- cookie notice: one local key, no trackers --- */
  var KEY = "polaris.cookie-notice.v1";
  var box = document.getElementById("cookies");
  var accept = document.getElementById("cookie-accept");
  var settings = document.getElementById("cookie-settings");

  function stored() {
    try { return localStorage.getItem(KEY); } catch (err) { return "blocked"; }
  }
  function store() {
    try { localStorage.setItem(KEY, new Date().toISOString()); } catch (err) {}
  }
  function open() {
    if (!box) return;
    box.classList.add("is-open");
  }
  function close() {
    if (!box) return;
    box.classList.remove("is-open");
  }

  if (box && accept && !stored()) {
    window.setTimeout(open, 900);
    accept.addEventListener("click", function () {
      store();
      close();
    });
  }

  if (settings) {
    settings.addEventListener("click", function (e) {
      e.preventDefault();
      open();
    });
  }

  /* --- year in footer stays honest --- */
  var yearNode = document.querySelector(".foot-bottom span");
  if (yearNode) yearNode.innerHTML = "\u00a9 " + new Date().getFullYear() + " Polaris. All rights reserved.";
})();
