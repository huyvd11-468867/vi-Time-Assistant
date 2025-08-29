async function getSync(keys) {
  return new Promise((resolve) => chrome.storage.sync.get(keys, resolve));
}
async function setSync(obj) {
  return new Promise((resolve) => chrome.storage.sync.set(obj, resolve));
}

async function load() {
  const { backendUrl, apiKey, userId } = await getSync(["backendUrl", "apiKey", "userId"]);
  document.getElementById("backendUrl").value = backendUrl || "http://127.0.0.1:8000";
  document.getElementById("apiKey").value = apiKey || "";
  document.getElementById("userId").value = userId || "u1";
}

async function save() {
  const backendUrl = document.getElementById("backendUrl").value.trim();
  const apiKey = document.getElementById("apiKey").value.trim();
  const userId = document.getElementById("userId").value.trim();
  await setSync({ backendUrl, apiKey, userId });
  document.getElementById("status").textContent = "Đã lưu ✔️";
  setTimeout(() => (document.getElementById("status").textContent = ""), 1500);
}

document.getElementById("save").addEventListener("click", save);
load();
