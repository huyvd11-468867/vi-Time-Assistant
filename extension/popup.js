// Utilities
async function getLocal(keys){ return new Promise(r=>chrome.storage.local.get(keys,r)); }
async function getSync(keys){ return new Promise(r=>chrome.storage.sync.get(keys,r)); }

function fmtMin(seconds){
  const m = Math.max(0, Math.floor(seconds/60));
  if (m >= 60){
    const h = Math.floor(m/60);
    const mm = m % 60;
    return `${h}h ${mm}m`;
  }
  return `${m} phút`;
}
function percent(part, total){
  if (!total) return 0;
  return Math.round((part/total)*100);
}
function faviconURL(domain){
  // Works without extra permissions
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`;
}

// Render KPI + site list + progress bars
async function renderUsage(){
  const { usageMap = {} } = await getLocal(["usageMap"]);
  const entries = Object.entries(usageMap).sort((a,b)=>b[1]-a[1]);
  const totalSec = entries.reduce((acc, [,sec])=>acc+sec, 0);

  // KPI
  document.getElementById("kpiTotal").textContent = fmtMin(totalSec);
  document.getElementById("kpiTop").textContent = entries[0] ? entries[0][0] : "—";

  // Sites list
  const container = document.getElementById("sitesList");
  container.innerHTML = "";
  const top = entries.slice(0, 6);
  for (const [domain, sec] of top){
    const p = percent(sec, totalSec);
    const row = document.createElement("div");
    row.className = "site";
    row.innerHTML = `
      <div class="site__favicon"><img src="${faviconURL(domain)}" alt="" width="24" height="24" /></div>
      <div class="site__name">${domain}</div>
      <div class="site__meta">${fmtMin(sec)} • ${p}%</div>
      <div class="site__bar-wrap">
        <div class="bar"><div class="bar__fill" style="width:${p}%"></div></div>
      </div>
    `;
    container.appendChild(row);
  }

  // Mini chart (top 5 bars)
  drawBarChart("miniChart", top.slice(0,5));
}

// Simple bar chart (canvas)
function drawBarChart(canvasId, items){
  const c = document.getElementById(canvasId);
  const ctx = c.getContext("2d");
  ctx.clearRect(0,0,c.width,c.height);

  const padding = 24;
  const barH = 18;
  const gap = 12;
  const maxW = c.width - padding*2 - 60; // 60 for labels on right
  const maxVal = Math.max(1, ...items.map(([,s])=>s));
  const startY = 18;

  ctx.font = "12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--muted').trim() || "#64748b";
  ctx.fillText("Top 5 hôm nay", padding, 12);

  items.forEach(([domain, sec], i)=>{
    const y = startY + i*(barH+gap);
    const w = Math.max(2, Math.round((sec/maxVal)*maxW));

    // track
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--border').trim() || "#e2e8f0";
    roundRect(ctx, padding, y, maxW, barH, 9);
    ctx.fill();

    // bar
    const grad = ctx.createLinearGradient(padding,0,padding+w,0);
    const p1 = getComputedStyle(document.documentElement).getPropertyValue('--primary').trim() || "#2563eb";
    const p2 = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || "#10b981";
    grad.addColorStop(0, p1); grad.addColorStop(1, p2);
    ctx.fillStyle = grad;
    roundRect(ctx, padding, y, w, barH, 9);
    ctx.fill();

    // labels
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--fg').trim() || "#0f172a";
    ctx.fillText(domain, padding, y-2+barH);
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--muted').trim() || "#64748b";
    ctx.fillText(fmtMin(sec), padding + maxW + 8, y-2+barH);
  });
}
function roundRect(ctx,x,y,w,h,r){
  const rr = Math.min(r, h/2, w/2);
  ctx.beginPath();
  ctx.moveTo(x+rr,y);
  ctx.arcTo(x+w,y, x+w,y+h, rr);
  ctx.arcTo(x+w,y+h, x,y+h, rr);
  ctx.arcTo(x,y+h, x,y, rr);
  ctx.arcTo(x,y, x+w,y, rr);
  ctx.closePath();
}

// Chat
async function sendQuestion(){
  const q = document.getElementById("question").value.trim();
  if (!q) return;
  const { usageMap = {} } = await getLocal(["usageMap"]);
  const { backendUrl, apiKey, userId } = await getSync(["backendUrl", "apiKey", "userId"]);
  const respEl = document.getElementById("response");

  if (!backendUrl || !apiKey || !userId){
    respEl.textContent = "⚠️ Chưa cấu hình backendUrl, apiKey hoặc userId (mở ⚙️ Cấu hình).";
    return;
  }
  respEl.textContent = "Đang phân tích…";

  try{
    const res = await fetch(`${backendUrl.replace(/\/$/, "")}/chat`, {
      method:"POST",
      headers:{
        "Content-Type":"application/json",
        "x-api-key": apiKey
      },
      body: JSON.stringify({ user_id:userId, question:q, usage: usageMap })
    });
    const data = await res.json();
    respEl.textContent = data.answer || data.error || "Lỗi không xác định.";
  }catch(e){
    respEl.textContent = "Lỗi mạng khi gọi backend.";
  }
}

document.getElementById("send").addEventListener("click", sendQuestion);
document.getElementById("question").addEventListener("keydown", (e)=>{ if(e.key==="Enter") sendQuestion(); });
document.getElementById("refresh").addEventListener("click", renderUsage);

// first render
renderUsage();
