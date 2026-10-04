import { useCallback, useEffect, useState } from "react";
import { formatQty, rpc } from "./api";
import { Banner, Camera, Digipad, Qty, ScanField, go, useBusy, useRoute } from "./ui";

const COLORS = ["#875a7b", "#0ea5b7", "#f59e0b", "#198754", "#dc3545", "#3b82f6", "#6f42c1", "#fd7e14"];

export default function App() {
  const route = useRoute();
  const [menu, setMenu] = useState(null);
  const [locate, setLocate] = useState(null);
  const busy = useBusy();

  useEffect(() => {
    if (route.name === "menu") {
      busy.run(() => rpc("/vpk_barcode/menu")).then((data) => {
        if (data) setMenu(data);
      });
    }
  }, [route.name]);

  return (
    <div className={route.name === "menu" ? "app home" : "app"}>
      {route.name === "menu" && (
        <MainMenu menu={menu} locate={locate} setLocate={setLocate} busy={busy} />
      )}
      {route.name === "operations" && <Operations busy={busy} />}
      {route.name === "type" && <PickingList typeId={route.id} busy={busy} />}
      {route.name === "picking" && <PickingScreen pickingId={route.id} busy={busy} />}
      {route.name === "inventory" && <InventoryScreen locationId={route.locationId} busy={busy} />}
    </div>
  );
}

function MainMenu({ menu, locate, setLocate, busy }) {
  const [camera, setCamera] = useState(false);
  const onScan = useCallback(async (barcode) => {
    const result = await busy.run(() => rpc("/vpk_barcode/scan_menu", { barcode }), { sound: true });
    if (!result) return;
    if (result.action === "picking") go("#/picking/" + result.picking_id);
    else if (result.action === "picking_type") go("#/type/" + result.picking_type_id);
    else if (result.action === "inventory") go("#/inventory/" + result.location_id);
    else if (result.action === "product") setLocate(result);
    else setLocate(result);
  }, [busy, setLocate]);

  return (
    <div className="screen-pad">
      <div className="top-row">
        <span className="brand">สแกนบาร์โค้ด</span>
        <span className="user">{menu?.user || ""}</span>
      </div>
      <Banner error={busy.error} message={locate?.warning ? locate.message : ""} warning={locate?.warning} />
      <div className="scan-hero" onClick={() => setCamera((open) => !open)}>
        <div className="bars" aria-hidden="true"><div className="laser" /></div>
        <div className="tap">{camera ? "ปิดกล้อง" : "สแกนหรือแตะ"}</div>
      </div>
      {camera && <Camera onScan={onScan} />}
      <ScanField onSubmit={onScan} />
      <ul className="hints">
        <li>สแกน<b>สินค้า</b> เพื่อดูว่าอยู่ตำแหน่งไหน</li>
        <li>สแกน<b>ล็อต</b> เพื่อเปิดตำแหน่งของล็อตนั้น</li>
        <li>สแกน<b>ใบรับ ใบโอน หรือใบจ่าย</b> เพื่อเปิดใบงาน</li>
        <li>สแกน<b>ตำแหน่ง</b> เพื่อเริ่มนับสต็อก</li>
        <li>สแกน<b>ประเภทการปฏิบัติการ</b> เพื่อเปิดรายการใบงาน</li>
      </ul>
      {locate?.product && (
        <div className="card">
          <div className="code">{locate.product.default_code || locate.product.name}</div>
          <div className="name">{locate.product.name}</div>
          {locate.lot_name && <div className="lot">ล็อต {locate.lot_name}</div>}
          {locate.quants?.length ? locate.quants.map((quant) => (
            <div key={quant.id} className="qty-row" style={{ marginTop: 8 }}>
              <span>{quant.location}{quant.lot ? " · " + quant.lot : ""}</span>
              <strong>{formatQty(quant.qty)} {quant.uom}</strong>
            </div>
          )) : <p className="muted">ไม่มีคงเหลือในคลัง</p>}
        </div>
      )}
      <button className="btn btn-primary" type="button" onClick={() => go("#/operations")}>
        การปฏิบัติการ
      </button>
      <button className="btn btn-info" type="button" onClick={() => go("#/inventory")}>
        นับสต็อก
        {menu?.quant_count ? <span className="badge">{menu.quant_count}</span> : null}
      </button>
    </div>
  );
}

function Operations({ busy }) {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    busy.run(() => rpc("/vpk_barcode/menu")).then((data) => {
      if (data) setRows(data.operations || []);
    });
  }, []);
  return (
    <>
      <Header title="การปฏิบัติการ" back="#/" />
      <Banner error={busy.error} />
      <div className="lines">
        {rows.map((row) => (
          <button key={row.id} className="list-btn" type="button" onClick={() => go("#/type/" + row.id)}>
            <span className="op-card">
              <span>
                <i className="dot" style={{ background: COLORS[row.color % COLORS.length] }} />
                <strong>{row.warehouse ? row.warehouse + ": " : ""}{row.name}</strong>
                <span className="muted">{row.barcode || "ยังไม่มีบาร์โค้ดประเภทงาน"}</span>
              </span>
              {row.count > 0 && <span className="count-pill">{row.count}</span>}
            </span>
          </button>
        ))}
        {!rows.length && !busy.error && <p className="empty">ไม่มีการปฏิบัติการที่เปิดอยู่</p>}
      </div>
    </>
  );
}

function PickingList({ typeId, busy }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    busy.run(() => rpc("/vpk_barcode/pickings", { picking_type_id: typeId })).then((result) => {
      if (result) setData(result);
    });
  }, [typeId]);
  return (
    <>
      <Header title={data?.type?.name || "ใบงาน"} back="#/operations" />
      <Banner error={busy.error} />
      <div className="lines">
        {(data?.pickings || []).map((picking) => (
          <button key={picking.id} className="list-btn" type="button" onClick={() => go("#/picking/" + picking.id)}>
            <strong>{picking.name}</strong>
            <span className="muted">
              {picking.state_label}
              {picking.partner ? " · " + picking.partner : ""}
              {picking.origin ? " · " + picking.origin : ""}
            </span>
          </button>
        ))}
        {data && !data.pickings.length && <p className="empty">ไม่มีใบงานที่ต้องทำ</p>}
      </div>
    </>
  );
}

function PickingScreen({ pickingId, busy }) {
  const [picking, setPicking] = useState(null);
  const [message, setMessage] = useState("สแกนตำแหน่งหรือสินค้า");
  const [warning, setWarning] = useState(false);
  const [ask, setAsk] = useState(false);
  const [camera, setCamera] = useState(false);
  const [locationId, setLocationId] = useState(false);
  const [pendingProduct, setPendingProduct] = useState(false);
  const [selected, setSelected] = useState(false);
  const [editor, setEditor] = useState(null);
  const [backorder, setBackorder] = useState(false);
  const [doneInfo, setDoneInfo] = useState(null);
  const [settings, setSettings] = useState(false);

  const load = useCallback(async () => {
    const result = await busy.run(() => rpc("/vpk_barcode/picking", { picking_id: pickingId }));
    if (result?.picking) setPicking(result.picking);
  }, [pickingId]);

  useEffect(() => { load(); }, [pickingId]);

  const apply = (result) => {
    if (!result) return;
    if (result.picking) setPicking(result.picking);
    if (result.message) setMessage(result.message);
    setWarning(!!result.warning);
    setAsk(result.action === "need_lot");
    if (result.location_id) setLocationId(result.location_id);
    if (result.action === "location") setPendingProduct(false);
    if (result.pending_product_id) setPendingProduct(result.pending_product_id);
    else if (result.action === "product" || result.action === "lot") setPendingProduct(false);
    if (result.selected_line_id) setSelected(result.selected_line_id);
  };

  const onScan = useCallback(async (barcode) => {
    const result = await busy.run(() => rpc("/vpk_barcode/scan", {
      picking_id: pickingId,
      barcode,
      location_id: locationId || false,
      pending_product_id: pendingProduct || false,
    }), { sound: true });
    apply(result);
  }, [pickingId, locationId, pendingProduct, busy]);

  const changeQty = async (line, qty) => {
    const result = await busy.run(() => rpc("/vpk_barcode/set_qty", { line_id: line.id, qty }), { sound: true });
    apply(result);
    setEditor(null);
  };

  const validate = async (choice) => {
    const params = { picking_id: pickingId };
    if (choice !== undefined) params.backorder = choice;
    const result = await busy.run(() => rpc("/vpk_barcode/validate", params), { sound: true });
    if (!result) return;
    if (result.need_backorder) {
      setBackorder(true);
      return;
    }
    setBackorder(false);
    if (result.done || result.blocked) setDoneInfo(result);
  };

  const lines = picking?.lines || [];
  const groups = [];
  for (const line of lines) {
    const last = groups[groups.length - 1];
    if (!last || last.location_id !== line.location_id) {
      groups.push({ location_id: line.location_id, location_name: line.location_name, lines: [line] });
    } else last.lines.push(line);
  }

  return (
    <>
      <Header
        title={picking?.name || "ใบงาน"}
        subtitle={picking?.partner || picking?.origin || ""}
        back="#/operations"
        extra={(
          <button className="icon-btn" type="button" onClick={() => setCamera((open) => !open)} aria-label="กล้อง">▣</button>
        )}
        onSettings={() => setSettings(true)}
      />
      {camera && <Camera onScan={onScan} />}
      <div className={"scan-strip" + (warning ? " warn" : ask ? " ask" : "")}>
        <p>{message}</p>
        <ScanField onSubmit={onScan} autoFocus={!camera && !editor && !backorder} />
      </div>
      <Banner error={busy.error} />
      <div className="lines">
        {groups.map((group) => (
          <div key={group.location_id}>
            <div className={"loc" + (group.location_id === locationId ? " here" : "")}>{group.location_name}</div>
            {group.lines.map((line) => {
              const remain = Math.max(0, Number(line.qty_demand) - Number(line.qty_done));
              const complete = line.picked && Number(line.qty_done) >= Number(line.qty_demand) && Number(line.qty_demand) > 0;
              return (
                <article key={line.id} className={"card" + (selected === line.id ? " selected" : complete ? " done" : "")}>
                  <div className="card-top">
                    <div>
                      <div className="code">{line.default_code || "—"}</div>
                      <div className="name">{line.product_name}</div>
                    </div>
                    <button className="mini" type="button" onClick={() => setEditor(line)} aria-label="แก้จำนวน">✎</button>
                  </div>
                  {line.tracking !== "none" && (
                    <div className="lot">ล็อต {line.lot_name || "ยังไม่ระบุ"}</div>
                  )}
                  <div className="qty-row">
                    <div>
                      <Qty done={line.qty_done} demand={line.qty_demand} />
                      <span className="uom">{line.uom}</span>
                    </div>
                    <div className="actions">
                      {Number(line.qty_done) > 0 && (
                        <button className="mini" type="button" onClick={() => changeQty(line, Number(line.qty_done) - 1)}>-1</button>
                      )}
                      <button className="mini" type="button" onClick={() => changeQty(line, Number(line.qty_done) + 1)}>+1</button>
                      {remain > 1 && (
                        <button className="mini" type="button" onClick={() => changeQty(line, Number(line.qty_demand))}>+{formatQty(remain)}</button>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ))}
        {picking && !lines.length && <p className="empty">ใบนี้ยังไม่มีรายการให้สแกน</p>}
      </div>
      <footer className="footer">
        <button className="btn btn-light" type="button" disabled={busy.busy} onClick={() => busy.run(() => rpc("/vpk_barcode/put_in_pack", { picking_id: pickingId }), { sound: true }).then(apply)}>
          ใส่แพ็ก
        </button>
        <button className="btn btn-primary" type="button" disabled={busy.busy || !picking?.can_validate} onClick={() => validate()}>
          ยืนยัน
        </button>
      </footer>
      {editor && (
        <Digipad
          title={editor.default_code || editor.product_name}
          initial={editor.qty_done || ""}
          uom={editor.uom}
          onClose={() => setEditor(null)}
          onConfirm={(qty) => changeQty(editor, qty)}
        />
      )}
      {backorder && (
        <div className="modal-back">
          <div className="sheet">
            <h2>สร้างใบค้างสำหรับจำนวนที่ยังไม่ครบ?</h2>
            <p className="muted">สินค้าที่สแกนแล้วจะถูกยืนยัน ส่วนที่เหลือเลือกได้ว่าจะเปิดใบใหม่หรือตัดออก</p>
            <button className="btn btn-primary" type="button" onClick={() => validate(true)}>สร้างใบค้าง</button>
            <button className="btn btn-light" type="button" onClick={() => validate(false)}>ไม่สร้าง ตัดจำนวนที่เหลือ</button>
            <button className="btn btn-light" type="button" onClick={() => setBackorder(false)}>กลับไปสแกนต่อ</button>
          </div>
        </div>
      )}
      {doneInfo && (
        <div className="modal-back">
          <div className="sheet">
            <h2>{doneInfo.message || doneInfo.name}</h2>
            {doneInfo.backorders?.length ? <p>ใบค้าง: {doneInfo.backorders.join(", ")}</p> : null}
            <button className="btn btn-primary" type="button" onClick={() => go("#/operations")}>กลับหน้ารายการ</button>
          </div>
        </div>
      )}
      {settings && (
        <div className="modal-back" onClick={() => setSettings(false)}>
          <div className="sheet" onClick={(event) => event.stopPropagation()}>
            <h2>คำสั่ง</h2>
            <p className="muted">{picking?.note || "ไม่มีหมายเหตุ"}</p>
            <button className="btn btn-light" type="button" onClick={() => setSettings(false)}>ปิด</button>
          </div>
        </div>
      )}
    </>
  );
}

function InventoryScreen({ locationId, busy }) {
  const [data, setData] = useState({ location: false, lines: [] });
  const [message, setMessage] = useState(locationId ? "สแกนสินค้า" : "สแกนตำแหน่งจัดเก็บ");
  const [warning, setWarning] = useState(false);
  const [camera, setCamera] = useState(false);
  const [pending, setPending] = useState(false);
  const [selected, setSelected] = useState(false);
  const [editor, setEditor] = useState(null);
  const [reason, setReason] = useState("นับจากแอปสแกน");
  const [doneInfo, setDoneInfo] = useState(null);
  const currentLocation = data.location?.id || locationId || 0;

  useEffect(() => {
    if (!locationId) return;
    busy.run(() => rpc("/vpk_barcode/inventory", { location_id: locationId })).then((result) => {
      if (result) setData(result);
    });
  }, [locationId]);

  const apply = (result) => {
    if (!result) return;
    if (result.location || result.lines) {
      setData({ location: result.location, lines: result.lines || [] });
      if (result.location?.id && result.location.id !== locationId) {
        window.history.replaceState(null, "", "#/inventory/" + result.location.id);
      }
    }
    if (result.message) setMessage(result.message);
    setWarning(!!result.warning);
    if (result.pending_product_id) setPending(result.pending_product_id);
    else if (result.action === "product") setPending(false);
    if (result.selected_quant_id) setSelected(result.selected_quant_id);
    if (result.done) setDoneInfo(result);
  };

  const onScan = useCallback(async (barcode) => {
    const result = await busy.run(() => rpc("/vpk_barcode/inventory_scan", {
      barcode,
      location_id: currentLocation || false,
      pending_product_id: pending || false,
    }), { sound: true });
    apply(result);
  }, [currentLocation, pending, busy]);

  const setQty = async (line, qty) => {
    const result = await busy.run(() => rpc("/vpk_barcode/inventory_set", { quant_id: line.id, qty }), { sound: true });
    apply(result);
    setEditor(null);
  };

  const applyCount = async () => {
    const result = await busy.run(() => rpc("/vpk_barcode/inventory_apply", {
      location_id: currentLocation,
      reason,
    }), { sound: true });
    apply(result);
  };

  const counted = (data.lines || []).filter((line) => line.counted_set).length;

  return (
    <>
      <Header
        title="นับสต็อก"
        subtitle={data.location?.name || "สแกนตำแหน่ง"}
        back="#/"
        extra={<button className="icon-btn" type="button" onClick={() => setCamera((open) => !open)} aria-label="กล้อง">▣</button>}
      />
      {camera && <Camera onScan={onScan} />}
      <div className={"scan-strip" + (warning ? " warn" : "")}>
        <p>{message}</p>
        <ScanField onSubmit={onScan} autoFocus={!camera && !editor} />
      </div>
      <Banner error={busy.error} />
      <div className="lines">
        {(data.lines || []).map((line) => {
          const done = line.counted_set ? Number(line.counted) : 0;
          return (
            <article key={line.id} className={"card" + (selected === line.id ? " selected" : "")}>
              <div className="card-top">
                <div>
                  <div className="code">{line.default_code || "—"}</div>
                  <div className="name">{line.product_name}</div>
                </div>
                <button className="mini" type="button" onClick={() => setEditor(line)}>✎</button>
              </div>
              {line.lot_name && <div className="lot">ล็อต {line.lot_name}</div>}
              <div className="qty-row">
                <div>
                  <Qty done={line.counted_set ? done : 0} demand={line.on_hand} />
                  <span className="uom">{line.uom}</span>
                  <div className="muted">ในระบบ {formatQty(line.on_hand)}</div>
                </div>
                <div className="actions">
                  {line.counted_set && done > 0 && (
                    <button className="mini" type="button" onClick={() => setQty(line, done - 1)}>-1</button>
                  )}
                  <button className="mini" type="button" onClick={() => setQty(line, (line.counted_set ? done : 0) + 1)}>+1</button>
                </div>
              </div>
            </article>
          );
        })}
        {data.location && !data.lines.length && <p className="empty">ตำแหน่งนี้ยังไม่มีสินค้า สแกนสินค้าเพื่อเริ่มนับ</p>}
        {!data.location && <p className="empty">สแกนบาร์โค้ดตำแหน่งจัดเก็บ</p>}
      </div>
      <footer className="footer" style={{ flexDirection: "column" }}>
        <input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="เหตุผลในการปรับยอด" style={{ fontSize: 16, padding: 10 }} />
        <button className="btn btn-primary" type="button" disabled={!counted || busy.busy} onClick={applyCount}>
          ยืนยันการนับ {counted ? "(" + counted + ")" : ""}
        </button>
      </footer>
      {editor && (
        <Digipad
          title={editor.default_code || editor.product_name}
          initial={editor.counted_set ? editor.counted : ""}
          uom={editor.uom}
          onClose={() => setEditor(null)}
          onConfirm={(qty) => setQty(editor, qty)}
        />
      )}
      {doneInfo && (
        <div className="modal-back">
          <div className="sheet">
            <h2>{doneInfo.message}</h2>
            <button className="btn btn-primary" type="button" onClick={() => setDoneInfo(null)}>ปิด</button>
          </div>
        </div>
      )}
    </>
  );
}

function Header({ title, subtitle, back, extra, onSettings }) {
  return (
    <header className="header">
      <button className="icon-btn" type="button" onClick={() => go(back)} aria-label="กลับ">‹</button>
      <h1>
        {title}
        {subtitle ? <span className="sub">{subtitle}</span> : null}
      </h1>
      {extra}
      {onSettings && <button className="icon-btn" type="button" onClick={onSettings} aria-label="คำสั่ง">⚙</button>}
    </header>
  );
}
