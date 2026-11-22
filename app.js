const { title: _clientTitle = "Review", tokenVar, csvPath } = window.__MD_CFG__ || {};
const OWNER  = "jayreck996";
const REPO   = "XLS";
const TOKEN  = window[tokenVar] || "";
const CSV_PATH = csvPath || "";
const CSV_URL  = `https://raw.githubusercontent.com/${OWNER}/${REPO}/main/${CSV_PATH}`;

// RFC 4180 compliant CSV parser — handles quoted fields with embedded
// newlines, commas, and escaped double-quotes (""). Replaces the old
// line-split parser that broke when description fields contained \n.
function _csvReadField(text, i) {
  const len = text.length;
  if (text[i] === '"') {
    i++;
    let s = "";
    while (i < len) {
      if (text[i] === '"') {
        i++;
        if (i < len && text[i] === '"') { s += '"'; i++; }
        else break;
      } else {
        s += text[i++];
      }
    }
    return [s, i];
  }
  let s = "";
  while (i < len && text[i] !== ',' && text[i] !== '\r' && text[i] !== '\n') s += text[i++];
  return [s, i];
}

function _csvReadRow(text, i) {
  const len = text.length;
  const fields = [];
  while (i < len && text[i] !== '\r' && text[i] !== '\n') {
    const [val, ni] = _csvReadField(text, i);
    fields.push(val);
    i = ni;
    if (i < len && text[i] === ',') i++;
    else break;
  }
  if (i < len && text[i] === '\r') i++;
  if (i < len && text[i] === '\n') i++;
  return [fields, i];
}

function parseHeaders(text) {
  const [fields] = _csvReadRow(text.trimStart(), 0);
  return fields;
}

function parseCSV(text) {
  const len = text.trimStart().length;
  const src = text.trimStart();
  let i = 0;
  const [headers, afterHeader] = _csvReadRow(src, i);
  i = afterHeader;
  const rows = [];
  while (i < len) {
    if (src[i] === '\r') { i++; continue; }
    if (src[i] === '\n') { i++; continue; }
    const [fields, ni] = _csvReadRow(src, i);
    i = ni;
    if (fields.some(f => f !== "")) {
      rows.push(Object.fromEntries(headers.map((h, j) => [h, (fields[j] || "").trim()])));
    }
  }
  return rows;
}

function mediaLink(row) {
  const url = (row["media URL"] || "").trim();
  const type = (row["media-type"] || "").toUpperCase();
  const label = row["media"] || "View media";
  const pendingHtml = `<div class="media-box"><div class="media-pending"><svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M1.75 2.5a.25.25 0 0 0-.25.25v10.5c0 .138.112.25.25.25h12.5a.25.25 0 0 0 .25-.25V2.75a.25.25 0 0 0-.25-.25ZM0 2.75C0 1.784.784 1 1.75 1h12.5c.966 0 1.75.784 1.75 1.75v10.5A1.75 1.75 0 0 1 14.25 15H1.75A1.75 1.75 0 0 1 0 13.25ZM8 5.5a.75.75 1 1 1 0 1.5.75.75 0 0 1 0-1.5Zm-2 3.5 1.5 1.5 2-2 2.5 2.5H4Z"/></svg>Media pending${type ? " · " + type : ""}</div></div>`;
  if (!url) return pendingHtml;
  if (/\.(png|jpe?g|gif|webp|svg)$/i.test(url)) {
    const ext = url.match(/\.(\w+)$/i)[1].toUpperCase();
    return `<div class="media-box"><a href="${url}" target="_blank"><img class="media-preview" src="${url}" alt="${label}" loading="lazy"></a><span class="media-type-badge">${ext}</span></div>
            <div class="post-media"><a href="${url}" target="_blank">${label}</a></div>`;
  }
  if (/\.pdf$/i.test(url)) {
    return `<div class="media-box"><a class="pdf-preview-card" href="${url}" target="_blank" rel="noopener"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#636e7b" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg><span class="pdf-card-label">${label}</span><span class="pdf-card-cta">Open PDF ↗</span></a><span class="media-type-badge">PDF</span></div>
            <div class="post-media"><a href="${url}" target="_blank">${label}</a></div>`;
  }
  if (/\.mp4$/i.test(url)) {
    return `<div class="media-box"><video class="media-preview" controls preload="metadata" src="${url}"></video><span class="media-type-badge">MP4</span></div>
            <div class="post-media"><a href="${url}" target="_blank">${label}</a></div>`;
  }
  return `<div class="post-media"><a href="${url}" target="_blank">${label}</a></div>`;
}

function serializeCSV(rows, headers) {
  const q = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  return [headers.map(q).join(","), ...rows.map(r => headers.map(h => q(r[h] ?? "")).join(","))].join("\n") + "\n";
}

function toBase64(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = "";
  bytes.forEach(b => { bin += String.fromCharCode(b); });
  return btoa(bin);
}

async function submitFeedback(postId, result, comment, btn, statusEl, allBtns, commentOnly = false) {
  if (!TOKEN || !csvSha) { statusEl.textContent = "Error: not ready"; statusEl.className = "status err"; return false; }
  allBtns.forEach(b => b.disabled = true);
  statusEl.textContent = "Saving…";
  statusEl.className = "status";
  try {
    const applyChange = () => {
      const row = csvRows.find(r => r.item === postId);
      if (row) { row.feedback = result; row["feedback-comment"] = comment; }
      return !!row;
    };
    let res;
    for (let attempt = 0; attempt < 3; attempt++) {
      // Always start from the latest CSV on main (this also refreshes csvSha) and
      // reapply only this one change to it. The rows loaded with the page may be
      // stale (a bot or another person committed since), and writing them back
      // would overwrite those edits.
      const fresh = await fetchCSV();
      csvHeaders = parseHeaders(fresh);
      csvRows    = parseCSV(fresh);
      if (!applyChange()) throw new Error(`${postId} is no longer in the CSV`);
      res = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/contents/${CSV_PATH}`, {
        method: "PUT",
        headers: { "Authorization": `Bearer ${TOKEN}`, "Accept": "application/vnd.github+json", "Content-Type": "application/json" },
        body: JSON.stringify({ message: `feedback: ${postId} -> ${result || "cleared"}`, content: toBase64(serializeCSV(csvRows, csvHeaders)), sha: csvSha })
      });
      // 409: someone committed between our fetch and our update; go round again.
      if (res.status !== 409) break;
    }
    if (res.status === 200 || res.status === 201) {
      const json = await res.json();
      csvSha = json.content.sha;
      if (commentOnly) {
        const activeResult = allBtns.find(b => b.classList.contains("active"))?.dataset.result;
        allBtns.forEach(b => { b.style.opacity = activeResult && b.dataset.result !== activeResult ? "0.35" : ""; });
        statusEl.textContent = comment ? "Comment saved" : "Comment cleared";
        statusEl.className = "status ok";
      } else if (result === "") {
        allBtns.forEach(b => { b.classList.remove("active"); b.style.opacity = ""; });
        statusEl.textContent = "Cleared";
        statusEl.className = "status";
      } else {
        allBtns.forEach(b => { b.classList.remove("active"); b.style.opacity = b.dataset.result !== result ? "0.35" : ""; });
        btn.classList.add("active");
        statusEl.textContent = `Saved: ${result}`;
        statusEl.className = "status ok";
      }
      allBtns.forEach(b => b.disabled = false);
      return true;
    } else {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch (e) {
    statusEl.textContent = `Error: ${e.message}`;
    statusEl.className = "status err";
    allBtns.forEach(b => b.disabled = false);
    return false;
  }
}

async function fetchCSV() {
  if (TOKEN) {
    const res = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/contents/${CSV_PATH}`, {
      headers: { "Authorization": `Bearer ${TOKEN}`, "Accept": "application/vnd.github+json" },
      cache: "no-store"
    });
    const json = await res.json();
    csvSha = json.sha;
    const bytes = Uint8Array.from(atob(json.content.replace(/\n/g, "")), c => c.charCodeAt(0));
    return new TextDecoder("utf-8").decode(bytes);
  }
  const res = await fetch(CSV_URL + "?t=" + Date.now());
  return res.text();
}

async function load() {
  const text = await fetchCSV();
  csvHeaders = parseHeaders(text);
  csvRows    = parseCSV(text);
  const rows = csvRows;

  const qMatch = CSV_URL.match(/XLS-(\d{4})(Q\d)\.xls/i);
  const qLabel = qMatch ? `${qMatch[2]} ${qMatch[1]}` : "";
  function syncWeekLabel() {
    const w = document.querySelector("#f-week select")?.value || String(latestWeek);
    document.getElementById("week-label").textContent = w ? `${qLabel} · Week ${w}` : qLabel;
  }
  document.getElementById("week-label").textContent = qLabel;

  const container = document.getElementById("posts");
  container.innerHTML = "";

  rows.forEach(row => {
    const feedback = row["feedback"] || "";
    const div = document.createElement("div");
    div.className = "post";
    div.dataset.week     = row.week     || "";
    div.dataset.topic    = row.topic    || "";
    div.dataset.type     = row.type     || "";
    div.dataset.feedback = feedback     || "unreviewed";
    div.dataset.score    = parseFloat(row.score) || 0;
    div.dataset.search   = [row.title, row.description, row.topic, row.type, row.hashtag, row["linkedin account tag"]].filter(Boolean).join(" ").toLowerCase();
    div.innerHTML = `
      <div class="post-header">
        <span class="badge">${row.topic}</span>
        <span class="badge">${row.type}</span>
        <span class="post-id">${row.item}</span>
        <span class="score">Score: ${row.score}</span>
      </div>
      <div class="post-body">
        <div class="post-title">${row.title}</div>
        <div class="post-desc">${row.description}</div>
        ${row["linkedin account tag"] ? `<div class="mentions"><span class="mentions-label">Tag:</span>${row["linkedin account tag"]}</div>` : ""}
        <div class="hashtags">${row.hashtag}</div>
        ${mediaLink(row)}
      </div>
      <div class="feedback">
        <div class="feedback-buttons">
          <span>Feedback:</span>
          <button class="btn btn-win ${feedback==='win'?'active':''}"  data-result="win">Win</button>
          <button class="btn btn-tie ${feedback==='tie'?'active':''}"  data-result="tie">Tie</button>
          <button class="btn btn-lost ${feedback==='lost'?'active':''}" data-result="lost">Lost</button>
          <span class="status">${feedback ? 'Saved: '+feedback : ''}</span>
          <button class="btn-copy" title="Copy post content">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"/><path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"/></svg>
          </button>
        </div>
        <div class="feedback-comment-row">
          <input type="text" class="feedback-comment" placeholder="Add a comment (optional)…" value="${(row['feedback-comment']||'').replace(/"/g,'&quot;')}">
          <button class="btn-comment-post">Post</button>
          <button class="btn-comment-delete">Delete</button>
        </div>
        <div class="saved-comment ${row['feedback-comment'] ? 'visible' : ''}"><span class="saved-comment-label">Saved:</span>${(row['feedback-comment']||'').replace(/</g,'&lt;')}</div>
      </div>`;

    const btns = [...div.querySelectorAll(".btn")];
    const statusEl  = div.querySelector(".status");
    const commentEl = div.querySelector(".feedback-comment");
    const postCommentBtn   = div.querySelector(".btn-comment-post");
    const deleteCommentBtn = div.querySelector(".btn-comment-delete");

    btns.forEach(btn => {
      btn.addEventListener("click", () => {
        const result  = btn.classList.contains("active") ? "" : btn.dataset.result;
        const comment = result === "" ? "" : (commentEl?.value || "").trim();
        submitFeedback(row.item, result, comment, btn, statusEl, btns);
      });
    });

    let savedComment = row["feedback-comment"] || "";
    const savedCommentEl = div.querySelector(".saved-comment");
    function syncCommentButtons() {
      const hasText = commentEl.value.trim().length > 0;
      postCommentBtn.style.display   = hasText ? "" : "none";
      deleteCommentBtn.style.display = !hasText && savedComment ? "" : "none";
    }
    function updateSavedComment(text) {
      savedComment = text;
      savedCommentEl.innerHTML = text ? `<span class="saved-comment-label">Saved:</span>${text.replace(/</g,'&lt;')}` : "";
      savedCommentEl.classList.toggle("visible", !!text);
      syncCommentButtons();
    }
    commentEl.addEventListener("input", syncCommentButtons);
    syncCommentButtons();

    postCommentBtn.addEventListener("click", () => {
      const activeBtn = btns.find(b => b.classList.contains("active"));
      const result  = activeBtn?.dataset.result || feedback || "";
      const comment = commentEl.value.trim();
      submitFeedback(row.item, result, comment, null, statusEl, btns, true)
        .then(ok => { if (ok) updateSavedComment(comment); });
    });

    deleteCommentBtn.addEventListener("click", () => {
      const activeBtn = btns.find(b => b.classList.contains("active"));
      const result = activeBtn?.dataset.result || feedback || "";
      commentEl.value = "";
      submitFeedback(row.item, result, "", null, statusEl, btns, true)
        .then(ok => { if (ok) updateSavedComment(""); });
    });
    if (feedback) {
      btns.forEach(b => {
        if (b.dataset.result !== feedback) b.style.opacity = "0.35";
      });
    }

    const copyBtn = div.querySelector(".btn-copy");
    copyBtn.addEventListener("click", () => {
      const text = [row.title, "", row.description, "", row["linkedin account tag"], row.hashtag].filter(Boolean).join("\n");
      navigator.clipboard.writeText(text).then(() => {
        const orig = copyBtn.innerHTML;
        copyBtn.classList.add("copied");
        copyBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 0 1 1.06-1.06L6 11.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"/></svg>`;
        setTimeout(() => { copyBtn.innerHTML = orig; copyBtn.classList.remove("copied"); }, 2000);
      });
    });

    container.appendChild(div);
  });

  // Populate dynamic filter dropdowns
  function makeSelect(containerId, filterKey, label, values) {
    const el = document.getElementById(containerId);
    const sel = document.createElement("select");
    sel.className = "filter-select";
    sel.dataset.filter = filterKey;
    const all = document.createElement("option");
    all.value = "";
    all.textContent = `All ${label}`;
    sel.appendChild(all);
    values.forEach(v => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", applyFilters);
    el.appendChild(sel);
  }
  makeSelect("f-week",  "week",  "weeks",  [...new Set(rows.map(r => r.week).filter(Boolean))]);
  makeSelect("f-topic", "topic", "topics", [...new Set(rows.map(r => r.topic).filter(Boolean))]);
  makeSelect("f-type",  "type",  "types",  [...new Set(rows.map(r => r.type).filter(Boolean))]);

  const weekSel = document.querySelector("#f-week select");
  function currentISOWeek() {
    const now = new Date();
    const jan4 = new Date(now.getFullYear(), 0, 4);
    const startOfWeek1 = new Date(jan4);
    startOfWeek1.setDate(jan4.getDate() - ((jan4.getDay() + 6) % 7));
    return 1 + Math.floor((now - startOfWeek1) / (7 * 24 * 60 * 60 * 1000));
  }
  const weekOptions = [...weekSel.options].filter(o => o.value).map(o => Number(o.value));
  const isoWeek = currentISOWeek();
  const latestWeek = weekOptions.includes(isoWeek)
    ? isoWeek
    : Math.max(...weekOptions);
  if (latestWeek) weekSel.value = String(latestWeek);
  weekSel.addEventListener("change", syncWeekLabel);
  syncWeekLabel();
  function syncFeedbackReset() {
    const chips = document.querySelectorAll("#f-feedback .chip");
    const allActive = [...chips].every(c => c.classList.contains("active"));
    document.getElementById("feedback-reset").style.display = allActive ? "none" : "";
  }
  document.querySelectorAll("#f-feedback .chip").forEach(chip =>
    chip.addEventListener("click", () => { chip.classList.toggle("active"); syncFeedbackReset(); applyFilters(); })
  );
  document.getElementById("feedback-reset").addEventListener("click", () => {
    document.querySelectorAll("#f-feedback .chip").forEach(c => c.classList.add("active"));
    syncFeedbackReset();
    applyFilters();
  });
  document.getElementById("keyword-search").addEventListener("input", applyFilters);
  document.getElementById("filter-clear").addEventListener("click", () => {
    document.getElementById("keyword-search").value = "";
    document.querySelectorAll(".filter-select").forEach(s => {
      if (s.dataset.filter) s.value = s.dataset.filter === "week" ? String(latestWeek) : "";
    });
    document.querySelectorAll(".chip").forEach(c => c.classList.add("active"));
    syncFeedbackReset();
    syncWeekLabel();
    applyFilters();
  });
  document.getElementById("filter-search").addEventListener("click", applyFilters);
  document.getElementById("sort-toggle").addEventListener("click", () => {
    const btn = document.getElementById("sort-toggle");
    const next = btn.dataset.sort === "score-desc" ? "score-asc" : "score-desc";
    btn.dataset.sort = next;
    btn.querySelector(".sort-pill-label").textContent = next === "score-desc" ? "High score" : "Low score";
    btn.classList.toggle("active", next !== "score-desc");
    sortPosts();
  });
  sortPosts();
  applyFilters();
  document.getElementById("filter-toggle-bar").style.display = "";
  document.getElementById("filter-toggle").addEventListener("click", () => {
    document.getElementById("filter-bar").classList.toggle("open");
    document.getElementById("filter-toggle").classList.toggle("active");
  });
}

function sortPosts() {
  const val = document.getElementById("sort-toggle")?.dataset.sort || "score-desc";
  const container = document.getElementById("posts");
  [...container.querySelectorAll(".post")]
    .sort((a, b) => {
      const sa = parseFloat(a.dataset.score) || 0;
      const sb = parseFloat(b.dataset.score) || 0;
      return val === "score-asc" ? sa - sb : sb - sa;
    })
    .forEach(p => container.appendChild(p));
}

function updateFilterCount() {
  const keyword = (document.getElementById("keyword-search")?.value || "").trim();
  let count = keyword ? 1 : 0;
  document.querySelectorAll(".filter-select").forEach(s => { if (s.dataset.filter && s.value) count++; });
  const chipTotals = {};
  document.querySelectorAll(".chip").forEach(c => {
    const key = c.dataset.filter;
    if (!chipTotals[key]) chipTotals[key] = { active: 0, total: 0 };
    chipTotals[key].total++;
    if (c.classList.contains("active")) chipTotals[key].active++;
  });
  Object.values(chipTotals).forEach(({ active, total }) => { if (active < total) count++; });
  const badge = document.getElementById("filter-count");
  if (badge) { badge.textContent = count; badge.classList.toggle("visible", count > 0); }
}

function applyFilters() {
  const keyword = (document.getElementById("keyword-search")?.value || "").toLowerCase().trim();
  const selVals = {};
  document.querySelectorAll(".filter-select").forEach(s => { if (s.dataset.filter) selVals[s.dataset.filter] = s.value; });
  const chipGroups = {};
  document.querySelectorAll(".chip").forEach(c => {
    const key = c.dataset.filter;
    if (!chipGroups[key]) chipGroups[key] = { active: [], total: 0 };
    chipGroups[key].total++;
    if (c.classList.contains("active")) chipGroups[key].active.push(c.dataset.value);
  });
  document.querySelectorAll(".post").forEach(post => {
    const selPass  = Object.entries(selVals).every(([k, v]) => !v || post.dataset[k] === v);
    const chipPass = Object.entries(chipGroups).every(([k, { active, total }]) =>
      active.length === 0 || active.length === total || active.includes(post.dataset[k])
    );
    const kwPass   = !keyword || post.dataset.search.includes(keyword);
    post.classList.toggle("hidden", !(selPass && chipPass && kwPass));
  });
  updateFilterCount();
}

if (window.__MD_CFG__) {
  load().catch(e => {
    document.getElementById("posts").innerHTML = `<p class="loading" style="color:#f85149">Failed to load: ${e.message}</p>`;
  });
}
