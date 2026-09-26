/* On-page editor for admins. Loaded only when logged in as admin. */
(function () {
  "use strict";
  var CSRF = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
  var LONG_FIELDS = ["body", "text"];

  function post(url, data) {
    data = data || {};
    data.csrf_token = CSRF;
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then(function (r) { return r.json().catch(function () { return { ok: r.ok }; }); });
  }

  function toast(msg, ok) {
    var t = document.createElement("div");
    t.textContent = msg;
    t.style.cssText = "position:fixed;bottom:18px;left:50%;transform:translateX(-50%);z-index:10002;" +
      "background:" + (ok === false ? "#a11a1a" : "#171540") + ";color:#fff;padding:.6rem 1.1rem;border-radius:999px;" +
      "font:600 .85rem system-ui;box-shadow:0 6px 20px rgba(0,0,0,.25)";
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 1800);
  }

  if (!document.body.classList.contains("edit-mode")) {
    // Not in edit mode: only the admin bar's New page / Settings buttons are active.
    wireModals();
    return;
  }

  // ---- Inline text editing -------------------------------------------------
  document.querySelectorAll("[data-editable]").forEach(function (el) {
    el.setAttribute("contenteditable", "true");
    el.setAttribute("spellcheck", "false");
    var isLong = LONG_FIELDS.indexOf(el.getAttribute("data-field")) !== -1;
    var original = el.textContent;

    if (el.tagName === "A" && el.hasAttribute("data-link-field")) {
      el.addEventListener("click", function (e) {
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          editLink(el);
        } else if (document.activeElement !== el) {
          e.preventDefault();
          el.focus();
        }
      });
      el.title = "Click to edit text. Ctrl+click to edit the link.";
    }

    el.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !isLong) { e.preventDefault(); el.blur(); }
    });
    el.addEventListener("blur", function () {
      var val = el.textContent.trim();
      if (val === original) return;
      original = val;
      post("/admin/api/text", {
        kind: el.getAttribute("data-kind"), id: +el.getAttribute("data-id"),
        field: el.getAttribute("data-field"), value: val,
      }).then(function (r) { if (!r.ok) toast(r.error || "Could not save.", false); });
    });
  });

  function editLink(el) {
    var current = el.getAttribute("href") || "";
    var url = prompt("Link address (e.g. /contact or https://example.com):", current === "#" ? "" : current);
    if (url === null) return;
    el.setAttribute("href", url);
    post("/admin/api/text", {
      kind: el.getAttribute("data-kind"), id: +el.getAttribute("data-id"),
      field: el.getAttribute("data-link-field"), value: url,
    }).then(function (r) { if (!r.ok) toast(r.error || "Could not save.", false); });
  }

  // ---- Icon picker (cards section) -----------------------------------------
  var ICONS = ["code", "design", "database", "speed", "shield", "chart", "mobile", "search", "cart", "mail", "globe"];
  document.querySelectorAll(".ed-icon-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      closePopovers();
      var pop = document.createElement("div");
      pop.className = "ed-pop";
      pop.innerHTML = "<button class='close' type='button'>&times;</button><h4>Choose an icon</h4>" +
        "<select>" + ICONS.map(function (n) {
          return "<option value='" + n + "'" + (n === btn.getAttribute("data-icon") ? " selected" : "") + ">" + n + "</option>";
        }).join("") + "</select>";
      positionPopover(pop, btn);
      var sel = pop.querySelector("select");
      sel.addEventListener("change", function () {
        post("/admin/api/text", { kind: "box", id: +btn.getAttribute("data-icon-id"), field: "icon", value: sel.value })
          .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not save.", false); });
      });
      pop.querySelector(".close").addEventListener("click", closePopovers);
    });
  });

  // ---- Image change / resize ------------------------------------------------
  document.querySelectorAll(".ed-img-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      closePopovers();
      var kind = btn.getAttribute("data-img-kind"), id = +btn.getAttribute("data-img-id");
      var width = btn.getAttribute("data-img-width") || "100";
      var img = btn.parentElement.querySelector("img");
      var pop = document.createElement("div");
      pop.className = "ed-pop";
      pop.innerHTML = "<button class='close' type='button'>&times;</button><h4>Image</h4>" +
        "<label>Image link (URL)<input type='url' value='" + (img ? img.getAttribute("src") : "") + "' placeholder='https://...'></label>" +
        "<label>Width<div class='row'>" +
        ["25", "50", "75", "100"].map(function (w) { return "<button type='button' data-w='" + w + "' class='" + (w === width ? "on" : "") + "'>" + w + "%</button>"; }).join("") +
        "</div></label>";
      positionPopover(pop, btn);
      var urlInput = pop.querySelector("input");
      var chosenWidth = width;
      pop.querySelectorAll(".row button").forEach(function (b) {
        b.addEventListener("click", function () {
          pop.querySelectorAll(".row button").forEach(function (x) { x.classList.remove("on"); });
          b.classList.add("on"); chosenWidth = b.getAttribute("data-w");
          save();
        });
      });
      urlInput.addEventListener("change", save);
      function save() {
        post("/admin/api/image", { kind: kind, id: id, url: urlInput.value.trim(), width: chosenWidth })
          .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not save.", false); });
      }
      pop.querySelector(".close").addEventListener("click", closePopovers);
    });
  });

  // ---- Text style popover ---------------------------------------------------
  document.querySelectorAll(".ed-style-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      closePopovers();
      var kind = btn.getAttribute("data-style-kind"), id = btn.getAttribute("data-style-id");
      var target = document.querySelector('[data-style-for="' + kind + '-' + id + '"]');
      var pop = document.createElement("div");
      pop.className = "ed-pop";
      pop.innerHTML =
        "<button class='close' type='button'>&times;</button><h4>Text style</h4>" +
        "<label>Size<select name='font_size'>" +
        "<option value=''>Normal</option><option value='sm'>Small</option><option value='lg'>Large</option><option value='xl'>Extra large</option>" +
        "</select></label>" +
        "<label>Font<select name='font_family'>" +
        "<option value=''>Default</option><option value='display'>Heading style</option><option value='body'>Body style</option>" +
        "<option value='serif'>Serif</option><option value='mono'>Monospace</option></select></label>" +
        "<label>Color<input type='color' name='font_color' value='#171540'></label>" +
        "<label>Align<div class='row'>" +
        "<button type='button' data-a='left'>Left</button><button type='button' data-a='center'>Center</button><button type='button' data-a='right'>Right</button>" +
        "</div></label>" +
        "<label><button type='button' class='ed-reset' style='width:100%;padding:.4rem;border:1px solid #eecaca;color:#a11a1a;border-radius:6px;background:#fff;cursor:pointer'>Reset to default</button></label>";
      positionPopover(pop, btn);
      var align = "";
      pop.querySelectorAll(".row button[data-a]").forEach(function (b) {
        b.addEventListener("click", function () {
          pop.querySelectorAll(".row button[data-a]").forEach(function (x) { x.classList.remove("on"); });
          b.classList.add("on"); align = b.getAttribute("data-a"); save();
        });
      });
      pop.querySelector("[name=font_size]").addEventListener("change", save);
      pop.querySelector("[name=font_family]").addEventListener("change", save);
      pop.querySelector("[name=font_color]").addEventListener("change", save);
      pop.querySelector(".ed-reset").addEventListener("click", function () {
        pop.querySelector("[name=font_size]").value = "";
        pop.querySelector("[name=font_family]").value = "";
        pop.querySelector("[name=font_color]").value = "#171540";
        align = ""; pop.querySelectorAll(".row button[data-a]").forEach(function (x) { x.classList.remove("on"); });
        save(true);
      });
      function save(resetColor) {
        post("/admin/api/style", {
          kind: kind, id: +id,
          font_size: pop.querySelector("[name=font_size]").value,
          font_family: pop.querySelector("[name=font_family]").value,
          font_color: resetColor ? "" : pop.querySelector("[name=font_color]").value,
          text_align: align,
        }).then(function (r) {
          if (r.ok && target) target.setAttribute("style", r.style || "");
          else if (!r.ok) toast(r.error || "Could not save.", false);
        });
      }
      pop.querySelector(".close").addEventListener("click", closePopovers);
    });
  });

  function positionPopover(pop, anchor) {
    document.body.appendChild(pop);
    var r = anchor.getBoundingClientRect();
    var top = Math.min(r.bottom + 6, window.innerHeight - pop.offsetHeight - 10);
    var left = Math.min(r.left, window.innerWidth - 250);
    pop.style.top = Math.max(10, top) + "px";
    pop.style.left = Math.max(10, left) + "px";
    setTimeout(function () { document.addEventListener("click", outsideClose); }, 0);
  }
  function outsideClose(e) {
    document.querySelectorAll(".ed-pop").forEach(function (p) {
      if (!p.contains(e.target)) p.remove();
    });
    document.removeEventListener("click", outsideClose);
  }
  function closePopovers() { document.querySelectorAll(".ed-pop").forEach(function (p) { p.remove(); }); }

  // ---- Visibility + delete ----------------------------------------------------
  document.querySelectorAll(".ed-vis").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var on = btn.getAttribute("data-vis") !== "on";
      post("/admin/api/visibility", { kind: btn.getAttribute("data-vis-kind"), id: +btn.getAttribute("data-vis-id"), visible: on })
        .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not save.", false); });
    });
  });
  document.querySelectorAll(".ed-del").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var kind = btn.getAttribute("data-del-kind");
      if (!confirm("Delete this " + kind + "? This can't be undone.")) return;
      post("/admin/api/" + kind + "/" + btn.getAttribute("data-del-id") + "/delete", {})
        .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not delete.", false); });
    });
  });

  // ---- Add box / add section ---------------------------------------------------
  document.querySelectorAll(".ed-add-box").forEach(function (btn) {
    btn.addEventListener("click", function () {
      post("/admin/api/box/add", { section_id: +btn.getAttribute("data-add-section") })
        .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not add.", false); });
    });
  });
  var addSecBtn = document.getElementById("ed-add-section-btn");
  if (addSecBtn) {
    addSecBtn.addEventListener("click", function () {
      closePopovers();
      var types = window.EDITOR_SECTION_TYPES || [];
      var pop = document.createElement("div");
      pop.className = "ed-pop";
      pop.style.minWidth = "260px";
      pop.innerHTML = "<button class='close' type='button'>&times;</button><h4>Add a section</h4>" +
        "<select>" + types.map(function (t) { return "<option value='" + t[0] + "'>" + t[1] + "</option>"; }).join("") + "</select>" +
        "<button type='button' class='ed-reset' style='width:100%;margin-top:.7rem;padding:.5rem;border:none;border-radius:6px;background:#3b2fd6;color:#fff;cursor:pointer'>Add section</button>";
      positionPopover(pop, addSecBtn);
      pop.querySelector(".ed-reset").addEventListener("click", function () {
        post("/admin/api/section/add", { page_id: window.EDITOR_PAGE_ID, type: pop.querySelector("select").value })
          .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not add.", false); });
      });
      pop.querySelector(".close").addEventListener("click", closePopovers);
    });
  }

  // ---- Drag reorder (boxes within a section, sections within a page) ----------
  function makeSortable(container, itemSelector, kind) {
    var dragEl = null;
    container.querySelectorAll(itemSelector + " .ed-drag").forEach(function (handle) {
      var item = handle.closest(itemSelector);
      handle.addEventListener("dragstart", function (e) {
        dragEl = item; item.classList.add("ed-dragging");
        e.dataTransfer.effectAllowed = "move";
      });
      handle.addEventListener("dragend", function () {
        item.classList.remove("ed-dragging");
        var items = Array.prototype.slice.call(container.querySelectorAll(itemSelector));
        var ids = items.map(function (el) { return +el.getAttribute(kind === "section" ? "data-section-id" : "data-box-id"); });
        post("/admin/api/reorder", { kind: kind, ids: ids }).then(function (r) { if (!r.ok) toast(r.error || "Could not reorder.", false); });
      });
    });
    container.addEventListener("dragover", function (e) {
      e.preventDefault();
      var after = getDragAfter(container, itemSelector, e.clientY);
      if (!dragEl) return;
      if (after == null) container.appendChild(dragEl); else container.insertBefore(dragEl, after);
    });
  }
  function getDragAfter(container, sel, y) {
    var items = Array.prototype.slice.call(container.querySelectorAll(sel + ":not(.ed-dragging)"));
    var closest = null, closestOffset = -Infinity;
    items.forEach(function (child) {
      var box = child.getBoundingClientRect();
      var offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closestOffset) { closestOffset = offset; closest = child; }
    });
    return closest;
  }
  var secList = document.getElementById("ed-sections");
  if (secList) makeSortable(secList, ".ed-section", "section");
  document.querySelectorAll(".ed-boxlist").forEach(function (grid) {
    if (grid.querySelector("[data-box-id] .ed-drag")) makeSortable(grid, "[data-box-id]", "box");
  });

  wireModals();

  // ---- Modals: New page / Site settings ---------------------------------------
  function modal(title, bodyHtml, onMount) {
    var overlay = document.createElement("div");
    overlay.className = "ed-modal-overlay";
    overlay.innerHTML = "<div class='ed-modal'><button class='close' type='button'>&times;</button><h3>" + title + "</h3><div class='body'>" + bodyHtml + "</div></div>";
    document.body.appendChild(overlay);
    overlay.addEventListener("click", function (e) { if (e.target === overlay) overlay.remove(); });
    overlay.querySelector(".close").addEventListener("click", function () { overlay.remove(); });
    if (onMount) onMount(overlay.querySelector(".body"), overlay);
    return overlay;
  }

  function wireModals() {
    var newPageBtn = document.getElementById("ab-new-page");
    if (newPageBtn) newPageBtn.addEventListener("click", function () {
      modal("Add a new page", "<div class='err' style='display:none'></div>" +
        "<label class='f'><span>Page title</span><input type='text' id='np-title' placeholder='e.g. Careers'></label>" +
        "<button type='button' class='btn-p' id='np-save'>Create page</button>", function (body) {
        body.querySelector("#np-save").addEventListener("click", function () {
          post("/admin/api/page/add", { title: body.querySelector("#np-title").value })
            .then(function (r) {
              if (r.ok) location.href = r.url;
              else { var e = body.querySelector(".err"); e.textContent = r.error || "Could not create page."; e.style.display = "block"; }
            });
        });
      });
    });

    var settingsBtn = document.getElementById("ab-settings");
    if (settingsBtn) settingsBtn.addEventListener("click", function () {
      fetch("/admin/settings", { headers: { "X-Requested-With": "fetch" } }).then(function (r) { return r.text(); }).then(function (html) {
        modal("Site settings", "<div class='err' style='display:none'></div>" + html +
          "<button type='button' class='btn-p' id='set-save'>Save settings</button>", function (body) {
          body.querySelector("#set-save").addEventListener("click", function () {
            var data = {};
            body.querySelectorAll("input, select, textarea").forEach(function (el) { if (el.name) data[el.name] = el.value; });
            fetch("/admin/settings", {
              method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "fetch" },
              body: new URLSearchParams(Object.assign({ csrf_token: CSRF }, data)).toString(),
            }).then(function (r) { return r.json(); }).then(function (r) {
              if (r.ok) location.reload();
              else { var e = body.querySelector(".err"); e.textContent = "Could not save settings."; e.style.display = "block"; }
            });
          });
        });
      });
    });
  }
})();
