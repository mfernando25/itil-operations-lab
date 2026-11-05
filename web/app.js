const $ = id => document.getElementById(id);
async function request(url) { const r = await fetch(url, {cache:"no-store"}); const data = await r.json(); if(!r.ok) throw new Error(data.error || `HTTP ${r.status}`); return data; }
function metric(name,value){const v=Number(value??0);$(name+"-value").textContent=v.toFixed(1)+"%";$(name+"-meter").style.width=Math.max(0,Math.min(100,v))+"%";}
function drawChart(canvasId, rows, key, maxValue, suffix="") {
  const canvas=$(canvasId), ctx=canvas.getContext("2d"), w=canvas.width,h=canvas.height,p={l:45,r:18,t:16,b:30};
  ctx.clearRect(0,0,w,h); const cw=w-p.l-p.r,ch=h-p.t-p.b;
  ctx.font="12px Segoe UI";ctx.fillStyle="#66778a";
  for(let i=0;i<=4;i++){const v=maxValue*i/4,y=p.t+ch-ch*i/4;ctx.strokeStyle="#e5ebf2";ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(w-p.r,y);ctx.stroke();ctx.fillText(v.toFixed(0)+suffix,6,y+4);}
  if(!rows?.length){ctx.fillText("Sin historial disponible para este indicador.",p.l+8,p.t+24);return;}
  const vals=rows.map(r=>Number(r[key]??0)), maxN=Math.max(1,rows.length-1);
  const x=i=>p.l+cw*i/maxN, y=v=>p.t+ch-ch*Math.max(0,Math.min(maxValue,v))/maxValue;
  ctx.strokeStyle="#2d69aa";ctx.lineWidth=2.5;ctx.beginPath();vals.forEach((v,i)=>i?ctx.lineTo(x(i),y(v)):ctx.moveTo(x(i),y(v)));ctx.stroke();
  vals.forEach((v,i)=>{ctx.beginPath();ctx.arc(x(i),y(v),4,0,Math.PI*2);ctx.fillStyle="#2d69aa";ctx.fill();});
  ctx.fillStyle="#66778a";ctx.fillText((rows[0].captured_at||"").slice(0,16).replace("T"," "),p.l,h-7);const last=(rows.at(-1).captured_at||"").slice(0,16).replace("T"," ");ctx.fillText(last,w-p.r-130,h-7);
}
function renderEvents(events){const root=$("events-list");root.replaceChildren();if(!events.length){root.innerHTML='<p class="muted">No se han registrado eventos nuevos.</p>';return;}events.forEach(ev=>{const item=document.createElement("article");item.className="event-row";const title=document.createElement("strong");title.textContent=ev.title;const desc=document.createElement("p");desc.textContent=ev.description;const meta=document.createElement("div");meta.className="event-meta";[ev.severity,`Grupo ${ev.group_number||"Operaciones"}`,ev.status,ev.created_at].forEach(v=>{const s=document.createElement("span");s.className="tag";s.textContent=v;meta.appendChild(s);});item.append(title,desc,meta);root.appendChild(item);});}
async function refresh(){try{const data=await request("/api/metrics"),c=data.current||{},s=data.storage_current||{};metric("cpu",c.cpu_percent);metric("memory",c.memory_percent);metric("disk",c.disk_percent);
  const used=Number(s.storage_capacity_gb!=null?Number(s.storage_capacity_gb)-Number(s.storage_available_gb):Number(s.storage_used_mb||0)/1024);const capacity=Number(s.storage_capacity_gb||0);
  $("storage-value").textContent=capacity?`${used.toFixed(1)} GB`:`${(Number(s.storage_used_mb||0)/1024).toFixed(2)} GB`;
  $("storage-caption").textContent=capacity?`${Number(s.storage_available_gb).toFixed(1)} GB disponibles de ${capacity.toFixed(1)} GB`:"Uso de archivos locales del laboratorio";
  $("storage-meter").style.width=(capacity?Math.min(100,used/capacity*100):Math.min(100,Number(s.storage_used_mb||0)/1024*10))+"%";
  drawChart("cpu-chart",data.history,"cpu_percent",100,"%");
  if(data.history?.length){const last=data.history.at(-1);$("requests-stat").textContent=last.requests_per_minute!=null?`Solicitudes por minuto: ${Number(last.requests_per_minute).toLocaleString("es-PE")}`:"Solicitudes por minuto: sin dato";$("latency-stat").textContent=last.avg_response_ms!=null?`Tiempo medio de respuesta: ${Number(last.avg_response_ms).toLocaleString("es-PE")} ms`:"Tiempo medio de respuesta: sin dato";}
  drawChart("storage-chart",data.storage_history||[],"storage_used_mb",10240," MB");
  const ev=await request("/api/events");renderEvents(ev.events);
 }catch(e){console.error(e);}}
$("refresh-events").addEventListener("click",refresh);
$("check-profile").addEventListener("click",async()=>{try{const x=await request("/api/portal/student-profile");$("profile-result").textContent=x.status==="ok"?`Perfil consultado correctamente.\nCódigo: ${x.student_id}\nCurso: ${x.course_id}`:x.message;}catch(e){$("profile-result").textContent="No fue posible completar la consulta del perfil.";}});
$("check-enrollment").addEventListener("click",async()=>{try{const x=await request("/api/demo/enrollment");$("enrollment-result").textContent=`Estado disponible: ${x.consultation.status}\nÚltima consulta: ${x.consultation.cached_at}`;}catch(e){$("enrollment-result").textContent=e.message;}});
refresh();setInterval(refresh,5000);
