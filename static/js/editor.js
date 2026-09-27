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

  // ---- Icon picker (cards / portfolio section) -------------------------------
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

  // ---- Popover helpers --------------------------------------------------------
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

  // ---- Consolidated "⚙ Settings" popover --------------------------------------
  // One button per box/section instead of separate Style / Hide / Delete / Change-image
  // buttons. Size, image (upload/link/remove), overlay, text style, visibility and
  // delete all live in this single popover.
  document.querySelectorAll(".ed-toolbar--sec, .ed-toolbar--box").forEach(function (toolbar) {
    var visBtn = toolbar.querySelector(".ed-vis");
    var delBtn = toolbar.querySelector(".ed-del");
    var styleBtn = toolbar.querySelector(".ed-style-btn");
    if (!visBtn || !delBtn) return;

    var kind = visBtn.getAttribute("data-vis-kind");
    var id = visBtn.getAttribute("data-vis-id");
    var styleTarget = document.querySelector('[data-style-for="' + kind + '-' + id + '"]');
    var imgBtn = document.querySelector('.ed-img-btn[data-img-kind="' + kind + '"][data-img-id="' + id + '"]');
    var boxEl = kind === "box" ? document.querySelector('[data-box-id="' + id + '"]') : null;
    var hasImage = !!imgBtn;
    var hasSize = kind === "box" || hasImage; // a section only gets a size control when it actually shows an image

    // Old scattered buttons are gone; the image button is hidden (its job moves into
    // this popover) but stays in the DOM so we can still read its current image from it.
    if (styleBtn) styleBtn.remove();
    visBtn.remove();
    delBtn.remove();
    if (imgBtn) imgBtn.style.display = "none";

    var gearBtn = document.createElement("button");
    gearBtn.type = "button";
    gearBtn.title = "Settings";
    gearBtn.textContent = "\u2699";
    toolbar.appendChild(gearBtn);

    gearBtn.addEventListener("click", function () {
      closePopovers();
      var dimsEl = kind === "box" ? boxEl : (imgBtn ? imgBtn.parentElement.querySelector("img") : null);
      var curW = dimsEl ? (parseInt(dimsEl.style.width, 10) || "") : "";
      var curH = dimsEl ? (parseInt(dimsEl.style.height, 10) || "") : "";
      var curOverlay = boxEl ? !boxEl.classList.contains("card--photo-plain") : false;
      var curImg = imgBtn ? imgBtn.parentElement.querySelector("img") : null;
      var curImgUrl = curImg ? curImg.getAttribute("src") : "";
      var visOn = visBtn.getAttribute("data-vis") === "on";

      var html = "<button class='close' type='button'>&times;</button><h4>Settings</h4>";

      if (hasSize) {
        html += "<label>Width (px)<input type='number' min='20' max='2000' placeholder='auto' class='ed-w' value='" + curW + "'></label>" +
          "<label>Height (px)<input type='number' min='20' max='2000' placeholder='auto' class='ed-h' value='" + curH + "'></label>";
      }
      if (hasImage) {
        html += "<label>Upload from device<input type='file' accept='.jpg,.jpeg,.png,.webp,.gif,image/jpeg,image/png,image/webp,image/gif'></label>" +
          "<p class='ed-upload-msg' style='display:none;font-size:.8rem'></p>" +
          "<label>Or paste an image link<input type='url' value='" + curImgUrl + "' placeholder='https://...'></label>" +
          (kind === "box" ? "<label class='ed-check'><input type='checkbox' class='ed-overlay'" + (curOverlay ? " checked" : "") + "> Show text as a caption over the image</label>" : "") +
          "<button type='button' class='ed-img-remove' style='width:100%;margin:.2rem 0 .8rem;padding:.4rem;border:1px solid #eecaca;color:#a11a1a;border-radius:6px;background:#fff;cursor:pointer'>Remove image</button>";
      }
      html += "<h4 style='margin-top:.9rem'>Text style</h4>" +
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
        "<button type='button' class='ed-style-reset' style='width:100%;margin-bottom:.7rem;padding:.4rem;border:1px solid #eecaca;color:#a11a1a;border-radius:6px;background:#fff;cursor:pointer'>Reset text style</button>" +
        "<div class='row'>" +
        "<button type='button' class='ed-vis2'>" + (visOn ? "Hide" : "Show") + "</button>" +
        "<button type='button' class='ed-del2' style='color:#a11a1a'>Delete</button>" +
        "</div>";

      var pop = document.createElement("div");
      pop.className = "ed-pop";
      pop.style.minWidth = "270px";
      pop.innerHTML = html;
      positionPopover(pop, gearBtn);

      // --- size ---
      if (hasSize) {
        var saveSize = function () {
          post("/admin/api/size", { kind: kind, id: +id, width: pop.querySelector(".ed-w").value, height: pop.querySelector(".ed-h").value })
            .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not save size.", false); });
        };
        pop.querySelector(".ed-w").addEventListener("change", saveSize);
        pop.querySelector(".ed-h").addEventListener("change", saveSize);
      }

      // --- image: upload / link / overlay / remove ---
      if (hasImage) {
        var msg = pop.querySelector(".ed-upload-msg");
        pop.querySelector("input[type=file]").addEventListener("change", function (e) {
          var file = e.target.files[0];
          if (!file) return;
          msg.style.display = "block"; msg.style.color = "#171540"; msg.textContent = "Uploading...";
          var fd = new FormData();
          fd.append("kind", kind); fd.append("id", id); fd.append("file", file); fd.append("csrf_token", CSRF);
          fetch("/admin/api/image/upload", { method: "POST", body: fd })
            .then(function (r) { return r.json().catch(function () { return { ok: false }; }); })
            .then(function (r) {
              if (r.ok) location.reload();
              else { msg.style.color = "#a11a1a"; msg.textContent = r.error || "Upload failed."; }
            });
        });
        pop.querySelector("input[type=url]").addEventListener("change", function (e) {
          post("/admin/api/image", { kind: kind, id: id, url: e.target.value.trim(), width: "100" })
            .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not save.", false); });
        });
        var overlayBox = pop.querySelector(".ed-overlay");
        if (overlayBox) overlayBox.addEventListener("change", function () {
          post("/admin/api/overlay", { kind: kind, id: id, overlay: overlayBox.checked })
            .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not save.", false); });
        });
        pop.querySelector(".ed-img-remove").addEventListener("click", function () {
          post("/admin/api/image/delete", { kind: kind, id: id })
            .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not remove.", false); });
        });
      }

      // --- text style ---
      var align = "";
      pop.querySelectorAll(".row button[data-a]").forEach(function (b) {
        b.addEventListener("click", function () {
          pop.querySelectorAll(".row button[data-a]").forEach(function (x) { x.classList.remove("on"); });
          b.classList.add("on"); align = b.getAttribute("data-a"); saveStyle();
        });
      });
      pop.querySelector("[name=font_size]").addEventListener("change", saveStyle);
      pop.querySelector("[name=font_family]").addEventListener("change", saveStyle);
      pop.querySelector("[name=font_color]").addEventListener("change", saveStyle);
      pop.querySelector(".ed-style-reset").addEventListener("click", function () {
        pop.querySelector("[name=font_size]").value = "";
        pop.querySelector("[name=font_family]").value = "";
        pop.querySelector("[name=font_color]").value = "#171540";
        align = ""; pop.querySelectorAll(".row button[data-a]").forEach(function (x) { x.classList.remove("on"); });
        saveStyle(true);
      });
      function saveStyle(resetColor) {
        post("/admin/api/style", {
          kind: kind, id: +id,
          font_size: pop.querySelector("[name=font_size]").value,
          font_family: pop.querySelector("[name=font_family]").value,
          font_color: resetColor ? "" : pop.querySelector("[name=font_color]").value,
          text_align: align,
        }).then(function (r) {
          if (r.ok && styleTarget) styleTarget.setAttribute("style", r.style || "");
          else if (!r.ok) toast(r.error || "Could not save.", false);
        });
      }

      // --- visibility / delete ---
      pop.querySelector(".ed-vis2").addEventListener("click", function () {
        post("/admin/api/visibility", { kind: kind, id: +id, visible: !visOn })
          .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not save.", false); });
      });
      pop.querySelector(".ed-del2").addEventListener("click", function () {
        if (!confirm("Delete this " + kind + "? This can't be undone.")) return;
        post("/admin/api/" + kind + "/" + id + "/delete", {})
          .then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not delete.", false); });
      });

      pop.querySelector(".close").addEventListener("click", closePopovers);
    });
  });

  // ---- Add box / add section (asks for a size first) ---------------------------
  function sizeFields() {
    return "<label>Width (px)<input type='number' min='20' max='2000' placeholder='auto' class='ed-w'></label>" +
      "<label>Height (px)<input type='number' min='20' max='2000' placeholder='auto' class='ed-h'></label>";
  }
  document.querySelectorAll(".ed-add-box").forEach(function (btn) {
    btn.addEventListener("click", function () {
      closePopovers();
      var pop = document.createElement("div");
      pop.className = "ed-pop";
      pop.style.minWidth = "240px";
      pop.innerHTML = "<button class='close' type='button'>&times;</button><h4>Box size</h4>" +
        sizeFields() +
        "<button type='button' class='ed-reset' style='width:100%;margin-top:.7rem;padding:.5rem;border:none;border-radius:6px;background:#3b2fd6;color:#fff;cursor:pointer'>Add</button>";
      positionPopover(pop, btn);
      pop.querySelector(".ed-reset").addEventListener("click", function () {
        post("/admin/api/box/add", {
          section_id: +btn.getAttribute("data-add-section"),
          width: pop.querySelector(".ed-w").value, height: pop.querySelector(".ed-h").value,
        }).then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not add.", false); });
      });
      pop.querySelector(".close").addEventListener("click", closePopovers);
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
        sizeFields() +
        "<button type='button' class='ed-reset' style='width:100%;margin-top:.7rem;padding:.5rem;border:none;border-radius:6px;background:#3b2fd6;color:#fff;cursor:pointer'>Add section</button>";
      positionPopover(pop, addSecBtn);
      pop.querySelector(".ed-reset").addEventListener("click", function () {
        post("/admin/api/section/add", {
          page_id: window.EDITOR_PAGE_ID, type: pop.querySelector("select").value,
          width: pop.querySelector(".ed-w").value, height: pop.querySelector(".ed-h").value,
        }).then(function (r) { if (r.ok) location.reload(); else toast(r.error || "Could not add.", false); });
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
