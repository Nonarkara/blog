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

  function setCopy(mode) {
    if (mode === "original") document.documentElement.setAttribute("data-copy", "original");
    else {
      document.documentElement.removeAttribute("data-copy");
      mode = "reading";
    }
    try { localStorage.setItem("diary-copy", mode); } catch (e) {}
    document.querySelectorAll("[data-set-copy]").forEach(function (x) {
      x.setAttribute("aria-pressed", x.getAttribute("data-set-copy") === mode ? "true" : "false");
    });
  }

  if (document.documentElement.getAttribute("data-copy") === "original") setCopy("original");

  document.querySelectorAll("[data-set-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      setCopy(b.getAttribute("data-set-copy"));
    });
  });

  var q = document.getElementById("q");
  if (q) {
    var status = document.getElementById("find-status");
    q.addEventListener("input", function () {
      var n = q.value.trim().toLowerCase();
      var shown = 0;
      document.querySelectorAll(".toc li").forEach(function (li) {
        var hide = !!(n && li.textContent.toLowerCase().indexOf(n) === -1);
        li.hidden = hide;
        if (!hide) shown++;
      });
      document.querySelectorAll(".year, .pages-block").forEach(function (sec) {
        if (!sec.querySelector(".toc li")) return;
        sec.hidden = !sec.querySelector("li:not([hidden])");
      });
      if (!status) return;
      if (!n) {
        status.hidden = true;
        return;
      }
      status.hidden = false;
      var en = status.querySelector(".en");
      var th = status.querySelector(".th");
      var zh = status.querySelector(".zh");
      if (!shown) {
        if (en) en.textContent = "No entry matches.";
        if (th) th.textContent = "ไม่พบบันทึกที่ตรงกัน";
        if (zh) zh.textContent = "没有相符的篇目。";
      } else if (shown === 1) {
        if (en) en.textContent = "1 match";
        if (th) th.textContent = "1 ชิ้น";
        if (zh) zh.textContent = "1 篇";
      } else {
        if (en) en.textContent = shown + " matches";
        if (th) th.textContent = shown + " ชิ้น";
        if (zh) zh.textContent = shown + " 篇";
      }
    });
  }
})();
