export async function rpc(path, params = {}) {
  const response = await fetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "call",
      id: Date.now(),
      params,
    }),
  });
  const data = await response.json();
  if (data.error) {
    if (data.error.code === 100) {
      window.location.href = "/web/login?redirect=" + encodeURIComponent("/vpk/barcode");
    }
    const message = data.error.data?.message || data.error.message || "เกิดข้อผิดพลาด";
    const error = new Error(message);
    error.odoo = data.error;
    throw error;
  }
  return data.result;
}

export function beep(ok = true) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = ok ? 880 : 220;
    osc.type = "sine";
    gain.gain.value = 0.05;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + (ok ? 0.08 : 0.18));
    osc.onended = () => ctx.close();
  } catch {
    /* บางเบราว์เซอร์บล็อกเสียงจนกว่าจะแตะหน้าจอ */
  }
}

export function formatQty(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "0";
  if (Number.isInteger(number)) return String(number);
  return number.toLocaleString("th-TH", { maximumFractionDigits: 2 });
}
