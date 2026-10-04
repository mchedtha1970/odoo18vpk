import { useCallback, useEffect, useRef, useState } from "react";
import { beep, formatQty, rpc } from "./api";

export function go(hash) {
  window.location.hash = hash;
}

export function useRoute() {
  const read = () => {
    const parts = (window.location.hash || "#/").replace(/^#\/?/, "").split("/").filter(Boolean);
    if (parts[0] === "operations") return { name: "operations" };
    if (parts[0] === "type" && parts[1]) return { name: "type", id: Number(parts[1]) };
    if (parts[0] === "picking" && parts[1]) return { name: "picking", id: Number(parts[1]) };
    if (parts[0] === "inventory") return { name: "inventory", locationId: parts[1] ? Number(parts[1]) : 0 };
    return { name: "menu" };
  };
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onHash = () => setRoute(read());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return route;
}

export function ScanField({ onSubmit, placeholder, autoFocus = true }) {
  const [value, setValue] = useState("");
  const ref = useRef(null);
  useEffect(() => {
    if (autoFocus) ref.current?.focus();
  }, [autoFocus]);
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        const barcode = value.trim();
        if (!barcode) return;
        setValue("");
        onSubmit(barcode);
        ref.current?.focus();
      }}
    >
      <input
        ref={ref}
        value={value}
        placeholder={placeholder || "สแกนหรือพิมพ์บาร์โค้ด"}
        onChange={(event) => setValue(event.target.value)}
        autoCapitalize="off"
        autoCorrect="off"
        enterKeyHint="done"
      />
    </form>
  );
}

export function Camera({ onScan }) {
  const videoRef = useRef(null);
  const last = useRef("");
  useEffect(() => {
    let stop = false;
    let stream;
    const Detector = window.BarcodeDetector;
    if (!Detector || !navigator.mediaDevices) return undefined;
    let detector;
    try {
      detector = new Detector({
        formats: ["code_128", "ean_13", "ean_8", "code_39", "qr_code", "upc_a", "upc_e", "itf", "codabar"],
      });
    } catch {
      return undefined;
    }
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        if (!videoRef.current) return;
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        const tick = async () => {
          if (stop || !videoRef.current) return;
          try {
            const codes = await detector.detect(videoRef.current);
            const raw = codes[0]?.rawValue;
            if (raw && raw !== last.current) {
              last.current = raw;
              onScan(raw);
              setTimeout(() => {
                if (last.current === raw) last.current = "";
              }, 1200);
            }
          } catch {
            /* เฟรมที่ยังไม่พร้อม */
          }
          if (!stop) requestAnimationFrame(tick);
        };
        tick();
      } catch {
        /* ผู้ใช้ไม่ให้สิทธิ์กล้อง */
      }
    })();
    return () => {
      stop = true;
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [onScan]);
  if (!window.BarcodeDetector) {
    return <p className="empty">เบราว์เซอร์นี้ใช้ช่องพิมพ์บาร์โค้ด หรือเครื่องสแกนต่อพ่วง</p>;
  }
  return (
    <div className="camera">
      <video ref={videoRef} muted playsInline />
    </div>
  );
}

export function Digipad({ title, initial, uom, onClose, onConfirm }) {
  const [text, setText] = useState(initial ? String(initial) : "");
  const push = (key) => {
    setText((prev) => {
      if (key === "⌫") return prev.slice(0, -1);
      if (key === "." && prev.includes(".")) return prev;
      if (prev.length > 8) return prev;
      return prev + key;
    });
  };
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="sheet" onClick={(event) => event.stopPropagation()}>
        <h2>{title}</h2>
        <div className="display">{text || "0"} <span className="uom">{uom}</span></div>
        <div className="pad">
          {["1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "0", "⌫"].map((key) => (
            <button key={key} type="button" onClick={() => push(key)}>{key}</button>
          ))}
        </div>
        <button
          className="btn btn-primary"
          style={{ marginTop: 12 }}
          type="button"
          onClick={() => onConfirm(Number(text || "0"))}
        >
          ยืนยันจำนวน
        </button>
      </div>
    </div>
  );
}

export function useBusy() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const run = useCallback(async (job, { sound = false } = {}) => {
    setBusy(true);
    setError("");
    try {
      const result = await job();
      if (sound) beep(!result?.warning && !result?.blocked);
      return result;
    } catch (err) {
      setError(err.message || "เกิดข้อผิดพลาด");
      beep(false);
      return null;
    } finally {
      setBusy(false);
    }
  }, []);
  return { error, setError, busy, run };
}

export function Banner({ error, message, warning }) {
  if (error) return <p className="toast error">{error}</p>;
  if (message && warning) return <p className="toast error">{message}</p>;
  return null;
}

export function Qty({ done, demand }) {
  const full = demand > 0 && done >= demand;
  const cls = done === 0 ? "zero" : full ? "full" : "";
  return (
    <span className="qty">
      <span className={cls}>{formatQty(done)}</span>
      {demand > 0 ? <span>/{formatQty(demand)}</span> : null}
    </span>
  );
}

export async function loadMenu() {
  return rpc("/vpk_barcode/menu");
}
