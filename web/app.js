const $ = (id) => document.getElementById(id);

async function request(url, options={}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
  return body;
}

function setMetric(name, value, max=100) {
  $( `${name}-value`).textContent = `${Number(value).toFixed(1)}%`;
  $( `${name}-meter`).style.width = `${Math.max(0, Math.min(100, Number(value)))}%`;
}

function drawHistory(samples) {
  const canvas = $("history-chart");
  const ctx = canvas.getContext("2d");
  const width = canvas.width, height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  const pad = {left: 42, right: 16, top: 15, bottom: 28};
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;
  ctx.font = "12px Segoe UI";
  ctx.fillStyle = "#66778a";
  [0,25,50,75,100].forEach(v => {
    const y = pad.top + chartH - chartH * v / 100;
    ctx.strokeStyle = "#e7edf3"; ctx.beginPath(); ctx.moveTo(pad.left,y); ctx.lineTo(width-pad.right,y); ctx.stroke();
    ctx.fillText(String(v), 8, y+4);
  });
  if (!samples.length) return;
  const maxN = Math.max(samples.length - 1, 1);
  const xAt = i => pad.left + chartW * i / maxN;
  const yAt = v => pad.top + chartH - chartH * Math.max(0,Math.min(100,Number(v)||0)) / 100;
  ctx.strokeStyle = "#2d69aa"; ctx.lineWidth = 2; ctx.beginPath();
  samples.forEach((s,i) => { const x=xAt(i), y=yAt(s.cpu_percent); if(i===0)ctx.moveTo(x,y); else ctx.lineTo(x,y); });
  ctx.stroke();
  samples.forEach((s,i) => {
    ctx.beginPath(); ctx.arc(xAt(i),yAt(s.cpu_percent),4,0,Math.PI*2);
    ctx.fillStyle = s.source === "simulated" ? "#b97724" : "#2d69aa"; ctx.fill();
  });
  const first = samples[0].captured_at?.slice(11,16) || "";
  const last = samples[samples.length-1].captured_at?.slice(11,16) || "";
  ctx.fillStyle="#66778a"; ctx.fillText(first,pad.left,height-6); ctx.fillText(last,width-pad.right-36,height-6);
}

function renderEvents(events) {
  const root = $("events-list");
  root.replaceChildren();
  if (!events.length) { root.textContent = "Todavía no hay eventos registrados."; root.className = "events-list muted"; return; }
  root.className = "events-list";
  events.forEach(event => {
    const row = document.createElement("div"); row.className = "event-row";
    const title = document.createElement("strong"); title.textContent = `${event.event_code} · ${event.title}`;
    const desc = document.createElement("p"); desc.textContent = event.description;
    const evidence = document.createElement("pre"); evidence.className="result-box"; evidence.textContent = JSON.stringify(event.evidence || {}, null, 2);
    const meta = document.createElement("div"); meta.className="event-meta";
    [event.severity, event.source, `Grupo ${event.group_number}`, event.created_at].forEach(value => {
      const tag=document.createElement("span");tag.className="tag";tag.textContent=value;meta.appendChild(tag);
    });
    row.append(title,desc,evidence,meta); root.appendChild(row);
  });
}

async function refresh() {
  try {
    const data = await request("/api/metrics");
    const current=data.current;
    setMetric("cpu",current.cpu_percent);
    setMetric("memory",current.memory_percent);
    setMetric("disk",current.disk_percent);
    $("storage-value").textContent = `${Number(current.storage_used_mb).toFixed(1)} MB`;
    $("storage-meter").style.width = `${Math.min(100,Number(current.storage_used_mb))}%`;
    $("cpu-note").textContent = current.source === "simulated" ? "Último punto mostrado: simulado" : "Uso real del procesador";
    drawHistory(data.history);
    const events = await request("/api/events"); renderEvents(events.events);
  } catch (err) { $("scenario-message").textContent = `No se pudo actualizar: ${err.message}`; }
}

async function activate(id) {
  try {
    const result = await request(`/api/scenarios/${id}/activate`, {method:"POST", body:"{}"});
    $("scenario-message").textContent = result.message;
    await refresh();
  } catch (err) { $("scenario-message").textContent = err.message; }
}
async function reset(id) {
  try {
    const result = await request(`/api/scenarios/${id}/reset`, {method:"POST", body:"{}"});
    $("scenario-message").textContent = result.message;
    await refresh();
  } catch (err) { $("scenario-message").textContent = err.message; }
}

document.querySelectorAll("[data-activate]").forEach(btn => btn.addEventListener("click",()=>activate(btn.dataset.activate)));
document.querySelectorAll("[data-reset]").forEach(btn => btn.addEventListener("click",()=>reset(btn.dataset.reset)));
$("refresh-events").addEventListener("click",refresh);
$("check-contract").addEventListener("click",async()=>{
  try { const x=await request("/api/demo/student"); const shown = x.student_id || "ID no disponible"; $("contract-result").textContent=JSON.stringify(x,null,2)+`\n\nValor mostrado por el componente: ${shown}`; }
  catch(e){$("contract-result").textContent=e.message;}
});
$("check-enrollment").addEventListener("click",async()=>{
  try { const x=await request("/api/demo/enrollment"); $("enrollment-result").textContent=JSON.stringify(x,null,2); }
  catch(e){$("enrollment-result").textContent=e.message;}
});
$("reconcile-enrollment").addEventListener("click",async()=>{
  try { const x=await request("/api/enrollment/reconcile",{method:"POST",body:"{}"}); $("enrollment-result").textContent=x.message; await refresh(); }
  catch(e){$("enrollment-result").textContent=e.message;}
});

refresh();
setInterval(refresh,5000);
