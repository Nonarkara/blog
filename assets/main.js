(function () {
  function setLang(l) {
    if (l === "th" || l === "zh") {
      document.documentElement.setAttribute("data-lang", l);
      document.documentElement.lang = l === "zh" ? "zh-Hans" : "th";
    } else {
      document.documentElement.setAttribute("data-lang", "en");
      document.documentElement.lang = "en";
      l = "en";
    }
    try { localStorage.setItem("diary-lang", l); } catch (e) {}
    document.querySelectorAll("[data-set-lang]").forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-set-lang") === l ? "true" : "false");
    });
  }

  var current = document.documentElement.getAttribute("data-lang") || "en";
  setLang(current);

  document.querySelectorAll("[data-set-lang]").forEach(function (b) {
    b.addEventListener("click", function () {
      setLang(b.getAttribute("data-set-lang"));
    });
  });

  document.querySelectorAll("[data-set-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var mode = b.getAttribute("data-set-copy");
      document.body.setAttribute("data-copy", mode);
      document.querySelectorAll("[data-set-copy]").forEach(function (x) {
        x.setAttribute("aria-pressed", x.getAttribute("data-set-copy") === mode ? "true" : "false");
      });
    });
  });

  var q = document.getElementById("q");
  if (q) {
    q.addEventListener("input", function () {
      var n = q.value.trim().toLowerCase();
      document.querySelectorAll(".toc li").forEach(function (li) {
        li.hidden = !!(n && li.textContent.toLowerCase().indexOf(n) === -1);
      });
      document.querySelectorAll(".year").forEach(function (sec) {
        sec.hidden = !sec.querySelector("li:not([hidden])");
      });
    });
  }
})();
