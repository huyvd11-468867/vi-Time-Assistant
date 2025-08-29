// Tracks per-domain usage and flushes deltas to backend.
// Uses chrome.storage.local for { usageMap, lastSentMap, lastActive }.
// Uses chrome.storage.sync for config { backendUrl, apiKey, userId }.

const TICK_SECONDS = 15;         // add time every 15s
const FLUSH_PERIOD_MIN = 1;      // send deltas every 1 min

let activeTabId = null;
let activeDomain = null;
let lastTick = Date.now();
let isIdle = false;

// Initialize alarms
chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create("tick", { periodInMinutes: TICK_SECONDS / 60 });
  chrome.alarms.create("flush", { periodInMinutes: FLUSH_PERIOD_MIN });
});

// Helper: parse domain
function getDomain(url) {
  try {
    const u = new URL(url);
    if (u.protocol !== "http:" && u.protocol !== "https:") return null;
    return u.hostname.replace(/^www\./, "");
  } catch (e) {
    return null;
  }
}

async function getLocal(keys) {
  return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
}
async function setLocal(obj) {
  return new Promise((resolve) => chrome.storage.local.set(obj, resolve));
}
async function getSync(keys) {
  return new Promise((resolve) => chrome.storage.sync.get(keys, resolve));
}

// Update active tab/domain
async function updateActive(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    const domain = getDomain(tab.url);
    activeTabId = tabId;
    activeDomain = domain;
    lastTick = Date.now();
  } catch (e) {
    // Tab might not exist yet
  }
}

// Ticking logic: add seconds to current domain
async function onTick() {
  if (isIdle || !activeDomain) return;
  const now = Date.now();
  const elapsed = Math.floor((now - lastTick) / 1000);
  if (elapsed <= 0) {
    lastTick = now;
    return;
  }

  const { usageMap = {} } = await getLocal(["usageMap"]);
  usageMap[activeDomain] = (usageMap[activeDomain] || 0) + elapsed;
  await setLocal({ usageMap });
  lastTick = now;
}

// Flush logic: send delta = usageMap - lastSentMap
async function onFlush() {
  const { usageMap = {}, lastSentMap = {} } = await getLocal(["usageMap", "lastSentMap"]);
  const { backendUrl, apiKey, userId } = await getSync(["backendUrl", "apiKey", "userId"]);

  if (!backendUrl || !apiKey || !userId) {
    // Not configured yet; skip.
    return;
  }

  const entries = [];
  for (const [site, total] of Object.entries(usageMap)) {
    const sent = lastSentMap[site] || 0;
    const delta = total - sent;
    if (delta > 0) {
      entries.push({ site, duration: delta }); // let backend set log_date= today
    }
  }

  if (entries.length === 0) return;

  try {
    await fetch(`${backendUrl.replace(/\/$/, "")}/log_usage_bulk`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ user_id: userId, entries })
    });

    // On success, update lastSentMap
    for (const e of entries) {
      lastSentMap[e.site] = (lastSentMap[e.site] || 0) + e.duration;
    }
    await setLocal({ lastSentMap });
  } catch (e) {
    // network error; keep deltas for next try
  }
}

// Events
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "tick") onTick();
  if (alarm.name === "flush") onFlush();
});

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  await onTick(); // finalize previous domain time up to switch
  await updateActive(activeInfo.tabId);
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (tab.active && changeInfo.url) {
    await onTick();
    await updateActive(tabId);
  }
});

// Idle handling
chrome.idle.setDetectionInterval(60); // 60s idle threshold
chrome.idle.onStateChanged.addListener((state) => {
  isIdle = state !== "active";
  lastTick = Date.now();
});
