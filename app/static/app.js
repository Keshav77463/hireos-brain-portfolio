"use strict";
const $ = id => document.getElementById(id);
let token = sessionStorage.getItem("hireos-token") || "";
let identity = null;
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function notice(text, error = false) {
  $("notice").textContent = text;
  $("notice").className = error ? "error" : "success";
}
async function api(path, options = {}) {
  if (!token) throw new Error("Connect a demo token first.");
  const response = await fetch(path, {...options, headers: {
    ...options.headers, Authorization: "Bearer " + token,
  }});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) disconnect();
    const detail = typeof data.detail === "string" ? data.detail : "Check the request fields.";
    throw new Error(response.status + " · " + detail);
  }
  return data;
}
function clearAnswer() {
  $("answer-content").hidden = true;
  $("answer-empty").hidden = false;
  ["metric-cards", "claims", "evidence", "limitations", "sources", "audit"].forEach(id => $(id).replaceChildren());
  $("source-count").textContent = "0";
}
function disconnect() {
  token = ""; identity = null;
  sessionStorage.removeItem("hireos-token");
  $("token").value = "";
  $("identity").textContent = "Disconnected";
  clearAnswer();
}
async function refresh() {
  const [sources, logs] = await Promise.all([api("/api/sources"), api("/api/retrieval-logs")]);
  $("sources").replaceChildren(...sources.map(s => {
    const row = node("div", undefined, "source-row");
    row.append(node("strong", s.source_id), node("div", s.filename + " · " + s.min_role));
    return row;
  }));
  $("source-count").textContent = sources.length;
  $("audit").replaceChildren(...logs.map(log => {
    const row = node("div", undefined, "audit-row");
    row.append(node("span", log.status, "tag"), node("span", log.question),
      node("div", new Date(log.created_at).toLocaleString() + " · " + log.role + " · " + log.evidence_ids.length + " references", "muted"));
    const details = node("details"); details.append(node("summary", "Inspect retrieval log"),
      node("pre", JSON.stringify(log, null, 2))); row.append(details);
    return row;
  }));
}
async function connect() {
  clearAnswer();
  identity = await api("/api/me");
  sessionStorage.setItem("hireos-token", token);
  $("identity").textContent = "Connected · tenant " + identity.tenant_id + " · " + identity.role;
  await refresh();
  notice("Identity verified. Your evidence scope is set.");
}
$("connect-form").addEventListener("submit", async event => {
  event.preventDefault();
  token = $("token").value.trim();
  try { await connect(); } catch (error) { disconnect(); notice(error.message, true); }
});
$("disconnect").addEventListener("click", () => { disconnect(); notice("Disconnected."); });
$("file").addEventListener("change", () => {
  if ($("file").files[0]) $("source").value = $("file").files[0].name.replace(/\.[^.]+$/, "");
});
async function runForm(form, action) {
  const button = form.querySelector("button");
  button.disabled = true;
  try { await action(); } catch (error) { notice(error.message, true); }
  finally { button.disabled = false; }
}
$("upload-form").addEventListener("submit", event => {
  event.preventDefault();
  runForm(event.target, async () => {
    const kind = $("kind").value;
    const body = new FormData();
    body.append("source_id", $("source").value);
    body.append("min_role", $("access").value);
    body.append("file", $("file").files[0]);
    if (kind !== "policy") body.append("kind", kind);
    const result = await api("/api/ingest/" + (kind === "policy" ? "policy" : "csv"), {method: "POST", body});
    notice("Upload complete · " + JSON.stringify(result));
    await refresh();
  });
});
function request() {
  const data = {question: $("question").value, job_title: $("job-title").value};
  ["baseline_start", "baseline_end", "current_start", "current_end", "as_of"].forEach(id => {
    if ($(id).value) data[id] = $(id).value;
  });
  return data;
}
function renderAnswer(result) {
  ["claims", "evidence", "metric-cards", "limitations"].forEach(id => $(id).replaceChildren());
  if (result.status !== "answered") {
    $("answer-empty").hidden = false; $("answer-content").hidden = true;
    notice(result.message || "No authorized evidence found.");
    return;
  }
  $("answer-empty").hidden = true; $("answer-content").hidden = false;
  const metrics = result.metrics;
  $("scope-note").textContent = metrics.job_title + " · current tenant and role only · outcomes through " + metrics.as_of;
  ["baseline", "current"].forEach(key => {
    const p = metrics[key];
    const card = node("div", undefined, "metric " + key);
    card.append(node("p", (key === "baseline" ? "BASELINE" : "CURRENT") + " · " + p.start + " → " + p.end),
      node("div", p.conversion_percent === null ? "Undefined" : p.conversion_percent + "%", "rate"));
    const counts = node("div", undefined, "counts");
    ["submissions", "interviews", "starts"].forEach(name => {
      const item = node("div"); item.append(node("strong", p[name]), node("span", name));
      counts.append(item);
    });
    card.append(counts); $("metric-cards").append(card);
  });
  $("delta").textContent = "Submissions: " + metrics.submission_change + " · Interviewed submissions: " +
    metrics.interview_change + " · Conversion: " + (metrics.conversion_change_pp === null ? "undefined" : metrics.conversion_change_pp + " percentage points");
  result.interpretation.forEach(claim => {
    const div = node("div", undefined, "claim");
    div.append(node("p", claim.text));
    const citations = node("div", undefined, "citations");
    claim.citations.forEach(id => {
      const button = node("button", id, "citation"); button.type = "button";
      button.addEventListener("click", () => {
        const entry = document.getElementById("e-" + id);
        if (entry) { entry.open = true; entry.scrollIntoView({behavior: "smooth", block: "center"}); entry.focus(); }
      });
      citations.append(button);
    });
    div.append(citations); $("claims").append(div);
  });
  $("evidence-count").textContent = result.evidence.length + " references";
  result.evidence.forEach(record => {
    const details = node("details", undefined, "record");
    details.id = "e-" + record.id; details.tabIndex = -1;
    details.append(node("summary", record.id), node("pre", JSON.stringify(record, null, 2)));
    $("evidence").append(details);
  });
  $("limitations").append(...result.limitations.map(text => node("li", text)));
  notice("Answer grounded in " + result.evidence.length + " references · retrieval " + result.log_id);
}
$("ask-form").addEventListener("submit", event => {
  event.preventDefault();
  runForm(event.target, async () => {
    $("answer-content").hidden = true; $("answer-empty").hidden = false;
    const result = await api("/api/ask", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(request())});
    renderAnswer(result); await refresh();
  });
});
$("outcome-form").addEventListener("submit", event => {
  event.preventDefault();
  runForm(event.target, async () => {
    if (!identity) throw new Error("Connect a demo token first.");
    const occurred = new Date($("outcome-time").value + ":00Z").toISOString();
    const body = {tenant_id: identity.tenant_id, source_id: "manual-outcomes",
      record_id: $("outcome-id").value, submission_id: $("outcome-sub").value,
      kind: $("outcome-kind").value, occurred_at: occurred, updated_at: occurred, min_role: "viewer"};
    const result = await api("/api/outcomes", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    notice("Outcome " + result.status + ". Ask again to see the updated calculation.");
    await refresh();
  });
});
$("probe").addEventListener("click", async () => {
  if (!identity) return notice("Connect a demo token first.", true);
  const other = identity.tenant_id === "22222222-2222-4222-8222-222222222222" ?
    "11111111-1111-4111-8111-111111111111" : "22222222-2222-4222-8222-222222222222";
  try {
    await api("/api/ask", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({...request(), target_tenant_id: other})});
    notice("Unexpected response: cross-tenant request should be denied.", true);
  } catch (error) { notice(error.message); }
  await refresh();
});
if (token) { $("token").value = token; connect().catch(error => { disconnect(); notice(error.message, true); }); }
