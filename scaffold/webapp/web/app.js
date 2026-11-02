/* 범용 프런트: 로그인 → 운영자(데이터셋/실행/결과/내보내기) · 사용자(내 결과). 서버의 뷰 스펙을 그대로 그린다 (engine.py 참고). */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const COLORS = ["#0f62fe", "#da1e28", "#198038", "#8a3ffc", "#ff832b", "#007d79", "#d12771", "#6f6f6f", "#a56eff", "#b28600", "#009d9a", "#ee5396"];

  async function api(path, opt = {}) {
    const r = await fetch(path, { headers: { "Content-Type": "application/json" }, credentials: "same-origin", ...opt, body: opt.body ? JSON.stringify(opt.body) : undefined });
    let data; try { data = await r.json(); } catch { data = { error: "응답 해석 실패 (" + r.status + ")" }; }
    if (!r.ok) { const e = new Error(data.error || ("HTTP " + r.status)); e.data = data; e.status = r.status; throw e; }
    return data;
  }
  const mount = (id) => { const v = $("#view"); v.innerHTML = ""; v.appendChild($("#" + id).content.cloneNode(true)); };
  const state = { user: null };

  function setBadge(st) {
    const b = $("#dsbadge");
    if (!st) { b.textContent = ""; return; }
    b.textContent = "데이터셋: " + (st.active_dataset || "없음") + (st.result ? ` · 결과 #${st.result.id}` : " · 결과 없음") + (st.stale ? " · 재생성 필요" : "");
    b.classList.toggle("stale", !!st.stale);
  }

  // ------------------------------------------------------------ 뷰 스펙 렌더러
  function renderView(el, v, onFilter) {
    let h = "";
    if (v.title) h += `<h2>${esc(v.title)} ${v.stale ? '<span class="pill warn">이전 데이터 기준 — 재생성 필요</span>' : ""}</h2>`;
    if (v.notice) h += `<div class="notice">${esc(v.notice)}</div>`;
    if (v.metrics && v.metrics.length) h += `<div>${v.metrics.map((m) => `<div class="metric"><div class="v">${esc(m.v)}</div><div class="k">${esc(m.k)}${m.sub ? " · " + esc(m.sub) : ""}</div></div>`).join("")}</div>`;
    if (v.text) h += `<p class="muted">${esc(v.text).replace(/\n/g, "<br>")}</p>`;
    if (v.graph) h += `<div class="graph-wrap"><svg class="mini" viewBox="0 0 1000 700" preserveAspectRatio="xMidYMid meet"></svg><div class="legend"><span>■ 거점 · ○ 지점 · ▲ 표식</span></div></div>`;
    if (v.timeline && v.timeline.length) h += `<ol class="timeline">${v.timeline.map((t) => `<li class="${t.me ? "me" : ""} ${t.kind === "site" ? "site" : ""}"><span>${esc(t.time)}</span><span>${esc(t.label)}${t.me ? " ← 나" : ""}</span><span class="muted small">${esc(t.note || "")}</span></li>`).join("")}</ol>`;
    (v.tables || []).forEach((t) => {
      h += `<h3>${esc(t.title || "")}</h3><div class="routes-list"><table class="tbl small"><thead><tr>${t.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${t.rows.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    });
    el.innerHTML = h;
    if (v.graph) drawGraph($("svg.mini", el), v.graph);
    if (v.filters && onFilter) renderFilters(v.filters, onFilter);
  }

  function renderFilters(filters, onFilter) {
    const box = $("#res-filters") || $("#u-filters"); if (!box) return;
    box.innerHTML = filters.map((f) => `<label>${esc(f.label)} ${f.options ? `<select name="${esc(f.name)}">${f.options.map((o) => `<option value="${esc(o)}"${String(o) === String(f.value) ? " selected" : ""}>${esc(o)}</option>`).join("")}</select>` : `<input name="${esc(f.name)}" value="${esc(f.value ?? "")}" type="${f.type || "text"}">`}</label>`).join("") + ` <button class="btn" id="btn-filter">조회</button>`;
    $("#btn-filter").onclick = () => { const q = {}; $$("select,input", box).forEach((i) => { if (i.value !== "") q[i.name] = i.value; }); onFilter(q); };
  }

  function drawGraph(svg, g) {
    const byId = Object.fromEntries(g.nodes.map((n) => [n.id, n])); let out = "";
    (g.edges || []).forEach((e, i) => {
      const pts = e.path.filter((id) => byId[id]).map((id) => `${byId[id].x},${byId[id].y}`).join(" ");
      out += `<polyline class="edge" points="${pts}" stroke="${COLORS[(e.color ?? i) % 12]}"><title>${esc(e.label || e.id || "")}</title></polyline>`;
    });
    g.nodes.forEach((n) => {
      if (n.kind === "site") out += `<rect class="node site" x="${n.x - 7}" y="${n.y - 7}" width="14" height="14" rx="2"><title>${esc(n.name)}</title></rect>`;
      else out += `<circle class="node${n.me ? " me" : ""}" cx="${n.x}" cy="${n.y}" r="${n.me ? 6 : 4}"><title>${esc(n.name)} (${esc(n.id)})</title></circle>`;
      if (n.kind === "site" || n.me || g.nodes.length <= 40) out += `<text class="lbl" x="${n.x + 8}" y="${n.y + 3}">${esc(String(n.name).slice(0, 14))}</text>`;
    });
    (g.marks || []).forEach((m) => { out += `<g transform="translate(${m.x},${m.y})"><polygon class="bus" points="-9,6 9,6 6,-6 -6,-6"/><text class="lbl" x="11" y="4">${esc(m.label || "")}</text></g>`; });
    svg.innerHTML = out;
  }

  // ------------------------------------------------------------ 로그인
  function showLogin() {
    mount("t-login"); $("#logout").classList.add("hidden"); $("#who").textContent = "";
    $("#f-login").onsubmit = async (e) => {
      e.preventDefault(); const f = new FormData(e.target);
      try { await api("/api/login", { method: "POST", body: { username: f.get("username"), password: f.get("password") } }); boot(); }
      catch (err) { $("#login-err").textContent = err.message; }
    };
  }
  async function boot() {
    const me = await api("/api/me"); state.user = me.user; setBadge(me.state);
    if (!me.user) return showLogin();
    $("#logout").classList.remove("hidden");
    $("#who").textContent = (me.user.role === "operator" ? "운영자 " : "사용자 ") + me.user.username;
    if (me.user.role === "operator") showOperator(); else showUser();
  }
  $("#logout").onclick = async () => { await api("/api/logout", { method: "POST" }); setBadge(null); showLogin(); };

  // ------------------------------------------------------------ 운영자
  async function showOperator() {
    mount("t-operator");
    $$(".tabs button").forEach((b) => (b.onclick = () => {
      $$(".tabs button").forEach((x) => x.classList.toggle("active", x === b));
      $$(".pane").forEach((p) => p.classList.toggle("hidden", p.dataset.pane !== b.dataset.tab));
      if (b.dataset.tab === "result") loadResult({});
    }));
    await refreshState(); await loadDatasets(); await loadRunForm();
    $("#btn-run").onclick = runNow;
    $("#btn-export").onclick = doExport;
    $("#btn-copy").onclick = () => { $("#exp-json").select(); document.execCommand("copy"); $("#exp-status").textContent = "복사됨"; };
    $("#btn-verify").onclick = doVerify;
  }
  async function refreshState() {
    const me = await api("/api/me"); setBadge(me.state);
    const n = $("#stale"); if (!n) return;
    if (me.state.stale) { n.classList.remove("hidden"); n.innerHTML = `현재 결과 #${me.state.result.id}은(는) <b>${esc(me.state.result.dataset)}</b> 데이터 기준입니다. 적용 데이터셋이 <b>${esc(me.state.active_dataset)}</b>(으)로 바뀌었으므로 <b>생성</b>을 다시 실행하기 전까지 결과를 새 데이터의 결과로 보여주지 않습니다.`; }
    else n.classList.add("hidden");
  }
  async function loadDatasets() {
    const d = await api("/api/datasets"); const tb = $("#ds-table tbody"); tb.innerHTML = "";
    d.datasets.forEach((ds) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td><b>${esc(ds.name)}</b></td><td><code>${esc(ds.path)}</code></td><td>${ds.files_present}/${ds.files_total}${ds.files_missing.length ? ` <span class="bad">누락: ${esc(ds.files_missing.join(", "))}</span>` : ""}</td><td class="muted small">${esc(ds.note)}</td><td>${ds.active ? `<span class="pill ok">적용 중 (${esc((d.applied_at || "").replace("T", " "))})</span>` : ""}</td><td><button class="btn sm" data-act="validate">검증</button> <button class="btn sm primary" data-act="apply">적용</button></td>`;
      $$("button", tr).forEach((b) => (b.onclick = () => dsAction(b.dataset.act, ds.name)));
      tb.appendChild(tr);
    });
  }
  function renderValidation(res, title) {
    const w = (res.warnings || []).length;
    let h = `<h3>${esc(title)} — ${res.ok ? '<span class="ok">검증 통과</span>' : `<span class="bad">검증 실패 (오류 ${(res.errors || []).length}건)</span>`}${w ? ` <span class="warn">경고 ${w}건</span>` : ""}</h3>`;
    if (res.message) h += `<p>${esc(res.message)}</p>`;
    if (res.counts && Object.keys(res.counts).length) h += `<p class="muted small">행 수: ${Object.entries(res.counts).map(([k, v]) => `${esc(k)} ${v}`).join(" · ")}</p>`;
    const rows = [...(res.errors || []).map((e) => ({ ...e, lv: "오류" })), ...(res.warnings || []).map((e) => ({ ...e, lv: "경고" }))];
    if (rows.length) h += `<table class="tbl small"><thead><tr><th>구분</th><th>파일</th><th>행</th><th>열</th><th>코드</th><th>내용</th></tr></thead><tbody>${rows.slice(0, 200).map((e) => `<tr><td class="${e.lv === "오류" ? "bad" : "warn"}">${e.lv}</td><td>${esc(e.file || "")}</td><td>${e.row ?? ""}</td><td>${esc(e.column || "")}</td><td><code>${esc(e.code)}</code></td><td>${esc(e.message)}</td></tr>`).join("")}</tbody></table>`;
    return h;
  }
  async function dsAction(act, name) {
    const box = $("#ds-result"); box.innerHTML = `<p class="muted">${act === "apply" ? "검증 후 적용" : "검증"} 중… (${esc(name)})</p>`;
    try {
      const res = await api(`/api/datasets/${act}`, { method: "POST", body: { name } });
      box.innerHTML = renderValidation(res, (act === "apply" ? "적용: " : "검증: ") + name);
      if (act === "apply") { await loadDatasets(); await refreshState(); }
    } catch (err) { box.innerHTML = err.data && err.data.errors ? renderValidation(err.data, "적용 거부: " + name) : `<p class="bad">${esc(err.message)}</p>`; }
  }
  async function loadRunForm() {
    const d = await api("/api/run/defaults"); const f = $("#f-run");
    f.innerHTML = `<fieldset><legend>조건</legend>${d.fields.map((p) => `<label>${esc(p.label)} ${p.type === "select" ? `<select name="${esc(p.name)}">${(p.options || []).map((o) => `<option${String(o) === String(p.value) ? " selected" : ""}>${esc(o)}</option>`).join("")}</select>` : `<input name="${esc(p.name)}" type="${p.type === "number" ? "number" : p.type === "date" ? "date" : "text"}" value="${esc(p.value ?? "")}" ${p.min != null ? `min="${p.min}"` : ""} ${p.step != null ? `step="${p.step}"` : ""}>`}</label>`).join("")}</fieldset>`;
  }
  async function runNow() {
    const body = Object.fromEntries(new FormData($("#f-run")).entries());
    $("#btn-run").disabled = true; $("#run-status").textContent = "생성 중…";
    try {
      const d = await api("/api/run", { method: "POST", body });
      $("#run-status").innerHTML = `완료 — 결과 #${d.result_id} ${d.verify.ok ? '<span class="pill ok">규칙 검증 통과</span>' : `<span class="pill bad">규칙 위반 ${Object.values(d.verify.counts).reduce((a, b) => a + b, 0)}건</span>`}`;
      renderView($("#run-view"), d.view); await refreshState();
    } catch (err) { $("#run-status").innerHTML = `<span class="bad">${esc(err.message)}</span>`; }
    $("#btn-run").disabled = false;
  }
  async function loadResult(q) {
    const el = $("#res-view");
    try { const v = await api("/api/result?" + new URLSearchParams(q)); renderView(el, v, loadResult); }
    catch (err) { el.innerHTML = `<p class="${err.status === 404 ? "muted" : "bad"}">${esc(err.message)}</p>`; }
  }
  async function doExport() {
    $("#exp-status").textContent = "내보내는 중…";
    try { const d = await api("/api/result/export"); $("#exp-json").value = d.json; $("#exp-status").innerHTML = `저장: <code>${esc(d.saved_to)}</code> (${(d.bytes / 1024).toFixed(0)} KB)${d.stale ? ' · <span class="warn">이전 데이터 기준</span>' : ""}`; }
    catch (err) { $("#exp-status").innerHTML = `<span class="bad">${esc(err.message)}</span>`; }
  }
  async function doVerify() {
    const el = $("#verify-result"); el.innerHTML = `<p class="muted">검증 중…</p>`;
    try {
      const d = await api("/api/result/verify");
      let h = `<h3>${d.ok ? '<span class="ok">규칙 검증 통과</span>' : '<span class="bad">규칙 위반</span>'} <span class="muted small">${Object.entries(d.checked || {}).map(([k, v]) => `${esc(k)} ${v}`).join(" · ")}</span></h3>`;
      if (!d.ok) h += `<table class="tbl small"><thead><tr><th>코드</th><th>내용</th><th>위치</th></tr></thead><tbody>${d.violations.map((v) => `<tr><td><code>${esc(v.code)}</code></td><td>${esc(v.message)}</td><td>${esc(Object.entries(v).filter(([k]) => !["code", "message"].includes(k)).map(([k, x]) => `${k}=${x}`).join(", "))}</td></tr>`).join("")}</tbody></table>`;
      el.innerHTML = h;
    } catch (err) { el.innerHTML = `<p class="bad">${esc(err.message)}</p>`; }
  }

  // ------------------------------------------------------------ 사용자
  async function showUser() { mount("t-user"); loadUser({}); }
  async function loadUser(q) {
    const el = $("#u-view");
    try { const v = await api("/api/me/result?" + new URLSearchParams(q)); renderView(el, v, loadUser); }
    catch (err) { el.innerHTML = `<p class="${err.status === 409 || err.status === 404 ? "warn" : "bad"}">${esc(err.message)}</p>`; }
  }

  boot().catch((e) => { $("#view").innerHTML = `<p class="bad">${esc(e.message)}</p>`; });
})();
