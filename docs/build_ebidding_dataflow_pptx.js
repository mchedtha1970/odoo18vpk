#!/usr/bin/env node
"use strict";

const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(
  "/Users/mchedtha/.claude/skills/synced/d68f830d-3313-4497-b854-cf2eff79e4b6_92a7ad89-b804-4e2c-b4b0-c15499e429d7/pptx/scripts/apply_theme.js"
);

const OUT = path.join(__dirname, "DataFlow-e-Bidding.pptx");

const THEME = {
  name: "Vachira e-Bidding DataFlow",
  headFontFace: "Prompt",
  bodyFontFace: "Prompt",
  colors: {
    dk1: "0F2942",
    lt1: "FFFFFF",
    dk2: "1E293B",
    lt2: "EAF3F1",
    accent1: "0B6848",
    accent2: "0F766E",
    accent3: "C9A227",
    accent4: "B45309",
    accent5: "1D4ED8",
    accent6: "6D28D9",
    hlink: "0B6848",
    folHlink: "0F766E",
  },
};

const ST = {
  done: { label: "พัฒนาแล้ว", fill: "0B6848" },
  design: { label: "ออกแบบ / แนบไฟล์", fill: "C9A227" },
  ext: { label: "นอกระบบ e-GP รัฐ", fill: "1D4ED8" },
};

function shadowCard() {
  return {
    type: "outer",
    color: "0F2942",
    blur: 8,
    offset: 3,
    opacity: 0.1,
    angle: 90,
  };
}

async function applyPromptThemeFonts(deckPath) {
  const JSZip = require(require.resolve("jszip", { paths: [require.resolve("pptxgenjs")] }));
  const zip = await JSZip.loadAsync(fs.readFileSync(deckPath));
  const part = "ppt/theme/theme1.xml";
  let xml = await zip.file(part).async("string");
  xml = xml.replace(/<a:latin typeface="[^"]*"/g, '<a:latin typeface="Prompt"');
  xml = xml.replace(/<a:ea typeface="[^"]*"/g, '<a:ea typeface="Prompt"');
  xml = xml.replace(/<a:cs typeface="[^"]*"/g, '<a:cs typeface="Prompt"');
  xml = xml.replace(/script="Thai" typeface="[^"]*"/g, 'script="Thai" typeface="Prompt"');
  zip.file(part, xml);
  fs.writeFileSync(
    deckPath,
    await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" })
  );
}

function addFnTable(slide, C, rows, y) {
  const header = ["Function", "โมดูล / ปุ่ม", "Data In", "Data Out", "สถานะ"].map((t) => ({
    text: t,
    options: {
      fill: { color: "0F2942" },
      color: "FFFFFF",
      bold: true,
      align: "center",
      valign: "middle",
    },
  }));
  const body = rows.map((r, i) => {
    const bg = i % 2 ? "F8FBFA" : "FFFFFF";
    const st = ST[r.status];
    return [
      { text: r.fn, options: { fill: { color: bg }, valign: "middle" } },
      { text: r.mod, options: { fill: { color: bg }, valign: "middle" } },
      { text: r.din, options: { fill: { color: bg }, valign: "middle" } },
      { text: r.dout, options: { fill: { color: bg }, valign: "middle" } },
      {
        text: st.label,
        options: {
          fill: { color: st.fill },
          color: "FFFFFF",
          bold: true,
          align: "center",
          valign: "middle",
        },
      },
    ];
  });
  slide.addTable([header, ...body], {
    x: 0.5,
    y,
    w: 12.32,
    colW: [2.7, 2.55, 2.55, 2.55, 1.97],
    fontFace: "Prompt",
    fontSize: 11,
    color: "1E293B",
    border: [
      { pt: 0.4, color: "D7E5E1" },
      { pt: 0.4, color: "D7E5E1" },
      { pt: 0.4, color: "D7E5E1" },
      { pt: 0.4, color: "D7E5E1" },
    ],
    valign: "middle",
    align: "left",
  });
}

async function main() {
  const pres = new pptxgen();
  pres.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
  pres.layout = "WIDE";
  pres.title = "Data Flow e-Bidding";
  pres.author = "VPK";
  pres.subject = "Data Flow การจัดซื้อจัดจ้างแบบ e-Bidding สำหรับทบทวน Function";
  pres.company = "Vachira Phuket Hospital";
  pres.theme = { headFontFace: "Prompt", bodyFontFace: "Prompt" };
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "TITLE_DARK",
    background: { color: C.text1 },
    objects: [
      {
        placeholder: {
          options: {
            name: "title",
            type: "title",
            x: 0.7,
            y: 2.05,
            w: 11.9,
            h: 1.25,
            fontSize: 36,
            fontFace: "Prompt",
            bold: true,
            color: C.background1,
            margin: 0,
          },
        },
      },
      {
        placeholder: {
          options: {
            name: "subtitle",
            type: "body",
            x: 0.7,
            y: 3.4,
            w: 11,
            h: 0.7,
            fontSize: 18,
            fontFace: "Prompt",
            color: C.background2,
            margin: 0,
          },
        },
      },
    ],
  });

  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: C.background1 },
    objects: [
      {
        placeholder: {
          options: {
            name: "title",
            type: "title",
            x: 0.5,
            y: 0.26,
            w: 12.3,
            h: 0.5,
            fontSize: 28,
            fontFace: "Prompt",
            bold: true,
            color: C.text1,
            margin: 0,
          },
        },
      },
      {
        text: {
          text: "โรงพยาบาลวชิระภูเก็ต  ·  Data Flow e-Bidding  ·  ทบทวน Function",
          options: {
            x: 0.5,
            y: 7.18,
            w: 10.6,
            h: 0.22,
            fontSize: 11,
            fontFace: "Prompt",
            color: C.text2,
            margin: 0,
          },
        },
      },
    ],
    slideNumber: {
      x: 12.3,
      y: 7.16,
      w: 0.5,
      h: 0.24,
      fontSize: 11,
      fontFace: "Prompt",
      color: C.text2,
    },
  });

  const origAddSlide = pres.addSlide.bind(pres);
  pres.addSlide = (opts) => {
    const slide = origAddSlide(opts);
    const origAddText = slide.addText.bind(slide);
    slide.addText = (text, options) => {
      const next = Object.assign({}, options || {});
      if (!next.placeholder && !next.fontFace) next.fontFace = "Prompt";
      return origAddText(text, next);
    };
    return slide;
  };

  pres.addSection({ title: "ภาพรวม" });
  pres.addSection({ title: "Data Flow รายขั้น" });
  pres.addSection({ title: "ทบทวน Function" });

  // ------------------------------------------------------------------
  // 1 Title
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "ภาพรวม" });
    s.addText("เอกสารทบทวน Function  ·  ออกแบบและที่พัฒนาแล้ว", {
      x: 0.7,
      y: 1.45,
      w: 11,
      h: 0.36,
      fontSize: 14,
      bold: true,
      color: C.accent3,
      margin: 0,
      isTextBox: true,
      objectName: "kicker",
    });
    s.addText("Data Flow การจัดซื้อจัดจ้างแบบ e-Bidding", { placeholder: "title" });
    s.addText("จากแผนงบประมาณถึงส่งของตามสัญญา  ดูข้อมูลที่ไหลและ function ที่รองรับ", {
      placeholder: "subtitle",
    });
    const pills = [
      { t: "พัฒนาแล้ว", f: ST.done.fill },
      { t: "ออกแบบ / แนบไฟล์", f: ST.design.fill },
      { t: "นอกระบบ e-GP รัฐ", f: ST.ext.fill },
    ];
    pills.forEach((p, i) => {
      const x = 0.7 + i * 3.15;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x,
        y: 5.7,
        w: 2.95,
        h: 0.62,
        fill: { color: p.f },
        rectRadius: 0.08,
        objectName: `leg-${i}`,
      });
      s.addText(p.t, {
        x,
        y: 5.7,
        w: 2.95,
        h: 0.62,
        align: "center",
        valign: "middle",
        fontSize: 14,
        bold: true,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `legt-${i}`,
      });
    });
  }

  // ------------------------------------------------------------------
  // 2 End-to-end data flow
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "ภาพรวม" });
    s.addText("ภาพรวม Data Flow ทั้งเส้น e-Bidding", { placeholder: "title" });
    s.addText("กล่องเขียว = ข้อมูลใน ERP   กล่องน้ำเงิน = ระบบ e-GP รัฐ   ลูกศร = เอกสาร/ยอดที่ส่งต่อ", {
      x: 0.5,
      y: 0.82,
      w: 12.3,
      h: 0.28,
      fontSize: 13,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "df-sub",
    });

    const boxes = [
      { t: "1 แผนงบ", d: "ยอดจัดสรร\nหมวดงบ แหล่งเงิน", f: "0B6848" },
      { t: "2 ใบขอซื้อ", d: "PR + Spec\nหนังสืออนุมัติ", f: "0F766E" },
      { t: "3 พัสดุตรวจ", d: "PR ที่ตรวจแล้ว\nงบที่จอง", f: "0B6848" },
      { t: "e-GP รัฐ", d: "แผน ประกวดราคา\nผู้ชนะ ไฟล์ประกาศ", f: "1D4ED8" },
      { t: "3 ERP e-GP", d: "EGP hub\nเอกสารลงนาม", f: "0F766E" },
      { t: "4 สัญญา", d: "CTR ผู้ชนะ\nวงเงินสัญญา", f: "C9A227" },
      { t: "5 ส่งของ", d: "PO ใบรับ\nQC ใบตรวจรับ", f: "B45309" },
    ];
    boxes.forEach((b, i) => {
      const x = 0.42 + i * 1.84;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x,
        y: 1.28,
        w: 1.7,
        h: 2.55,
        fill: { color: b.f },
        shadow: shadowCard(),
        rectRadius: 0.1,
        objectName: `dfb-${i}`,
      });
      s.addText(b.t, {
        x: x + 0.06,
        y: 1.4,
        w: 1.58,
        h: 0.7,
        align: "center",
        valign: "middle",
        fontSize: 13,
        bold: true,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `dft-${i}`,
      });
      s.addText(b.d, {
        x: x + 0.06,
        y: 2.18,
        w: 1.58,
        h: 1.45,
        align: "center",
        fontSize: 12,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `dfd-${i}`,
      });
      if (i < boxes.length - 1) {
        s.addShape(pres.shapes.RIGHT_ARROW, {
          x: x + 1.68,
          y: 2.4,
          w: 0.2,
          h: 0.14,
          fill: { color: C.text1 },
          objectName: `dfa-${i}`,
        });
      }
    });

    const objs = [
      { t: "ข้อมูลหลักที่ไหล", d: "วงเงินงบ  ·  PR  ·  กรรมการ  ·  หนังสือราชการ  ·  แผน e-GP  ·  ผู้ชนะ  ·  สัญญา  ·  PO  ·  Lot/QC  ·  ใบตรวจรับ" },
      { t: "จุดตัดระบบ", d: "ERP ไม่ประกาศขึ้น e-GP รัฐ  ไฟล์จาก e-GP ถูกแนบกลับมาลงนามและบันทึกผลใน ERP" },
    ];
    objs.forEach((o, i) => {
      const y = 4.08 + i * 1.38;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: 0.5,
        y,
        w: 12.32,
        h: 1.24,
        fill: { color: C.background2 },
        rectRadius: 0.1,
        objectName: `dfo-${i}`,
      });
      s.addText(o.t, {
        x: 0.72,
        y: y + 0.12,
        w: 11.9,
        h: 0.34,
        fontSize: 15,
        bold: true,
        color: C.text1,
        margin: 0,
        isTextBox: true,
        objectName: `dfot-${i}`,
      });
      s.addText(o.d, {
        x: 0.72,
        y: y + 0.5,
        w: 11.9,
        h: 0.58,
        fontSize: 14,
        color: C.text2,
        margin: 0,
        isTextBox: true,
        objectName: `dfod-${i}`,
      });
    });
  }

  // ------------------------------------------------------------------
  // 3 Data objects
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "ภาพรวม" });
    s.addText("เอกสารและโมเดลข้อมูลที่ใช้ทบทวน", { placeholder: "title" });
    const items = [
      { k: "คำขอตั้งงบ / แผนงบ", m: "departmental.budget.request\nbudget.budget", s: "พัฒนาแล้ว" },
      { k: "ใบขอซื้อ PR", m: "purchase.request\n+ รายการ + กรรมการ", s: "พัฒนาแล้ว" },
      { k: "หนังสืออนุมัติขอซื้อ", m: "official.document\nกล่องลงนาม PDF", s: "พัฒนาแล้ว" },
      { k: "แผน e-GP ใน ERP", m: "ebidding.plan\nebidding.plan.line", s: "พัฒนาแล้ว" },
      { k: "กระบวนการ e-GP", m: "purchase.requisition\nเอกสาร / ผู้เสนอราคา", s: "พัฒนาแล้ว" },
      { k: "ไฟล์จาก e-GP รัฐ", m: "แนบ PDF ประกาศแผน\nผล ประกาศผู้ชนะ", s: "แนบไฟล์" },
      { k: "ทะเบียนสัญญา", m: "purchase.contract\nงวดงาน หลักประกัน", s: "พัฒนาแล้ว" },
      { k: "PO / รับของ / ตรวจรับ", m: "purchase.order\nstock.picking  QC  WA", s: "พัฒนาแล้ว" },
    ];
    items.forEach((it, i) => {
      const col = i % 4;
      const row = Math.floor(i / 4);
      const x = 0.5 + col * 3.2;
      const y = 1.15 + row * 2.8;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x,
        y,
        w: 3.02,
        h: 2.58,
        fill: { color: C.background2 },
        shadow: shadowCard(),
        rectRadius: 0.1,
        objectName: `obj-${i}`,
      });
      s.addText(it.k, {
        x: x + 0.14,
        y: y + 0.16,
        w: 2.74,
        h: 0.7,
        fontSize: 15,
        bold: true,
        color: C.text1,
        margin: 0,
        isTextBox: true,
        objectName: `objk-${i}`,
      });
      s.addText(it.m, {
        x: x + 0.14,
        y: y + 0.9,
        w: 2.74,
        h: 0.95,
        fontSize: 13,
        color: C.text2,
        margin: 0,
        isTextBox: true,
        objectName: `objm-${i}`,
      });
      s.addText(it.s, {
        x: x + 0.14,
        y: y + 1.95,
        w: 2.74,
        h: 0.4,
        fontSize: 13,
        bold: true,
        color: C.accent1,
        margin: 0,
        isTextBox: true,
        objectName: `objs-${i}`,
      });
    });
  }

  // ------------------------------------------------------------------
  // 4 Step 1
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data Flow รายขั้น" });
    s.addText("ขั้นที่ 1  แผนงบประมาณ  ·  Data / Function", { placeholder: "title" });
    s.addText("Data In: ความต้องการหน่วยงาน    Data Out: วงเงินจัดสรรพร้อมเปิด PR", {
      x: 0.5,
      y: 0.82,
      w: 12.3,
      h: 0.28,
      fontSize: 13,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "s1-sub",
    });
    addFnTable(s, C, [
      {
        fn: "สร้างคำขอตั้งงบวัสดุ/ครุภัณฑ์",
        mod: "คำขอตั้งงบ  ·  สร้าง",
        din: "ปีงบ หน่วยงาน หมวด รายการ",
        dout: "คำขอตั้งงบ ส่งแล้ว",
        status: "done",
      },
      {
        fn: "รวบรวมเข้าแผนงบประมาณ",
        mod: "แผนงบประมาณประจำปี",
        din: "คำขอตั้งงบทุกหน่วยงาน",
        dout: "แผนงบร่าง รวมวงเงิน",
        status: "done",
      },
      {
        fn: "อนุมัติแผนและจัดสรร",
        mod: "อนุมัติแผน / จัดสรรลงหน่วยงาน",
        din: "แผนงบร่าง",
        dout: "ยอดจัดสรร คงเหลือ > 0",
        status: "done",
      },
      {
        fn: "ตรวจงบบนใบขอซื้อ",
        mod: "ตรวจสอบงบประมาณ",
        din: "PR ตามแผน + ยอดจัดสรร",
        dout: "งบเพียงพอ / จองงบ PR",
        status: "done",
      },
    ], 1.22);
  }

  // ------------------------------------------------------------------
  // 5 Step 2
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data Flow รายขั้น" });
    s.addText("ขั้นที่ 2  ขอซื้อ e-Bidding  ·  Data / Function", { placeholder: "title" });
    s.addText("Data In: วงเงินตามแผน    Data Out: PR ส่งพัสดุแล้ว + หนังสืออนุมัติขอซื้อ", {
      x: 0.5,
      y: 0.82,
      w: 12.3,
      h: 0.28,
      fontSize: 13,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "s2-sub",
    });
    addFnTable(s, C, [
      {
        fn: "สร้างใบขอซื้อ วิธี e-Bidding",
        mod: "ใบขอซื้อ  ·  สร้าง",
        din: "แผนงบ รายการ Spec",
        dout: "PR ฉบับร่าง",
        status: "done",
      },
      {
        fn: "บันทึกกรรมการ 3 ชุด",
        mod: "แท็บคณะกรรมการ",
        din: "รายชื่อบุคลากร",
        dout: "กก. ราคากลาง / พิจารณาผล / ตรวจรับ",
        status: "done",
      },
      {
        fn: "ทำหนังสืออนุมัติขอซื้อ",
        mod: "สร้างเอกสารอนุมัติขอซื้อ",
        din: "ข้อมูล PR",
        dout: "หนังสือราชการ PDF",
        status: "done",
      },
      {
        fn: "ส่งลงนามตามสายงาน",
        mod: "กล่องอนุมัติเอกสาร",
        din: "PDF + รายชื่อผู้อนุมัติ",
        dout: "หนังสือลงนามแล้ว",
        status: "done",
      },
      {
        fn: "ส่งให้พัสดุดำเนินการ",
        mod: "ส่งพัสดุ",
        din: "PR งบเพียงพอ เอกสารครบ",
        dout: "สถานะส่งพัสดุแล้ว",
        status: "done",
      },
    ], 1.18);
  }

  // ------------------------------------------------------------------
  // 6 Step 3
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data Flow รายขั้น" });
    s.addText("ขั้นที่ 3  e-GP  ·  Data / Function", { placeholder: "title" });
    s.addText("งานประกาศจริงอยู่ที่ e-GP รัฐ  ERP บันทึกแผน แนบไฟล์ ลงนาม และเก็บผู้ชนะ", {
      x: 0.5,
      y: 0.82,
      w: 12.3,
      h: 0.28,
      fontSize: 13,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "s3-sub",
    });
    addFnTable(s, C, [
      {
        fn: "พัสดุตรวจ PR / ส่งกลับแก้ไข",
        mod: "ยืนยันการตรวจสอบ",
        din: "PR จากหน่วยงาน",
        dout: "PR พร้อมส่ง e-GP",
        status: "done",
      },
      {
        fn: "ส่งเข้าระบบ e-GP ใน ERP",
        mod: "ส่งรายการเข้าระบบ e-GP",
        din: "PR ที่ตรวจแล้ว",
        dout: "เอกสารกระบวนการ e-GP",
        status: "done",
      },
      {
        fn: "สร้าง/ประกาศแผนบน e-GP รัฐ",
        mod: "www.gprocurement.go.th",
        din: "รายการแผน วงเงิน",
        dout: "รหัสแผน + ไฟล์ประกาศ",
        status: "ext",
      },
      {
        fn: "บันทึกแผนที่ประกาศแล้วใน ERP",
        mod: "แผน e-GP  ·  นำเข้า Excel",
        din: "ไฟล์แผนจาก e-GP",
        dout: "ebidding.plan + รายการ",
        status: "done",
      },
      {
        fn: "ขออนุมัติตั้งกรรมการ",
        mod: "เอกสาร e-GP + หนังสือราชการ",
        din: "รายชื่อกรรมการบน PR",
        dout: "คำสั่งแต่งตั้งลงนามแล้ว",
        status: "design",
      },
      {
        fn: "ประกวดราคาจนได้ผู้ชนะ",
        mod: "e-GP รัฐ + แท็บเปรียบเทียบราคา",
        din: "ผู้เสนอราคาจาก e-GP",
        dout: "ผู้ชนะบนเอกสาร e-GP",
        status: "ext",
      },
      {
        fn: "แนบหนังสือขออนุมัติ ส่งลงนาม",
        mod: "เพิ่มเอกสาร  ·  ส่งเข้ากล่อง",
        din: "PDF จาก e-GP",
        dout: "เอกสารลงนามตามขั้นตอน",
        status: "done",
      },
    ], 1.14);
  }

  // ------------------------------------------------------------------
  // 7 Step 4
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data Flow รายขั้น" });
    s.addText("ขั้นที่ 4  ทำสัญญา  ·  Data / Function", { placeholder: "title" });
    s.addText("Data In: ผู้ชนะ + เอกสาร e-GP ที่ลงนามแล้ว    Data Out: สัญญามีผลใช้ + หลักประกัน", {
      x: 0.5,
      y: 0.82,
      w: 12.3,
      h: 0.28,
      fontSize: 13,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "s4-sub",
    });
    addFnTable(s, C, [
      {
        fn: "เปิดทะเบียนสัญญาจาก e-GP",
        mod: "เปิดทะเบียนสัญญา",
        din: "ผู้ชนะ ยอดเสนอราคา เลข e-GP",
        dout: "CTR แบบร่าง",
        status: "done",
      },
      {
        fn: "ระบุประเภท ซื้อ / จ้าง / เช่า",
        mod: "ประเภทสัญญา",
        din: "ลักษณะงานที่ประกวด",
        dout: "สัญญาซื้อ  จ้าง  หรือเช่า",
        status: "done",
      },
      {
        fn: "แบ่งงวดงาน (ถ้ามี)",
        mod: "สร้างรายการงวดงาน",
        din: "มูลค่าสัญญารวม",
        dout: "งวดงานผลรวมเท่าสัญญา",
        status: "done",
      },
      {
        fn: "แนบไฟล์สัญญาที่ลงนามแล้ว",
        mod: "แท็บเอกสารสัญญา",
        din: "PDF สัญญาจาก e-GP / Word",
        dout: "ไฟล์คู่สัญญาใน ERP",
        status: "design",
      },
      {
        fn: "ยืนยันสัญญา",
        mod: "ยืนยันสัญญา",
        din: "ร่างสัญญาครบ",
        dout: "สถานะมีผลบังคับใช้",
        status: "done",
      },
      {
        fn: "รับ / คืนหลักประกันสัญญา",
        mod: "ทะเบียนหลักประกัน",
        din: "หนังสือค้ำประกัน มูลค่า",
        dout: "ถือหลักประกัน / ส่งคืนแล้ว",
        status: "done",
      },
    ], 1.16);
  }

  // ------------------------------------------------------------------
  // 8 Step 5
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data Flow รายขั้น" });
    s.addText("ขั้นที่ 5  ส่งของตามสัญญา  ·  Data / Function", { placeholder: "title" });
    s.addText("Data In: สัญญามีผลใช้    Data Out: ของเข้าคลัง + ใบตรวจรับ", {
      x: 0.5,
      y: 0.82,
      w: 12.3,
      h: 0.28,
      fontSize: 13,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "s5-sub",
    });
    addFnTable(s, C, [
      {
        fn: "สร้างใบสั่งซื้อตามสัญญา",
        mod: "สร้าง PO",
        din: "CTR คงเหลือ + ผู้ชนะ",
        dout: "PO ตัดยอดสัญญา จองเป็นผูกพัน",
        status: "done",
      },
      {
        fn: "ส่งเข้าแอปผู้ขาย",
        mod: "ส่งเข้าแอปผู้ขาย",
        din: "PO ยืนยันแล้ว",
        dout: "คำขอให้ผู้ขายลงนาม",
        status: "done",
      },
      {
        fn: "ผู้ขายยืนยันใบสั่งซื้อ",
        mod: "Vendor Portal",
        din: "PO ในแอปผู้ขาย",
        dout: "PO ผู้ขายยืนยันแล้ว + ใบรับสินค้า",
        status: "done",
      },
      {
        fn: "ตรวจคุณภาพ QC",
        mod: "ตรวจคุณภาพ",
        din: "ใบรับสินค้า WH/IN",
        dout: "QC ผ่าน / ไม่ผ่าน",
        status: "done",
      },
      {
        fn: "รับเข้าคลัง",
        mod: "ตรวจสอบ (Validate)",
        din: "Lot วันหมดอายุ จำนวนจริง",
        dout: "สต็อก On Hand เพิ่มขึ้น",
        status: "done",
      },
      {
        fn: "ตรวจรับพัสดุ WA",
        mod: "สร้างใบตรวจรับ",
        din: "PO + กรรมการตรวจรับ",
        dout: "ใบตรวจรับ WA",
        status: "done",
      },
    ], 1.16);
  }

  // ------------------------------------------------------------------
  // 9 Review summary
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "ทบทวน Function" });
    s.addText("สรุปสถานะ Function ทั้งเส้น", { placeholder: "title" });

    const groups = [
      {
        t: "พัฒนาแล้วใน ERP",
        c: ST.done.fill,
        d: "แผนงบ  ตรวจงบ  สร้าง PR  หนังสืออนุมัติ  ส่งพัสดุ  ตรวจ PR  ส่ง e-GP ใน ERP  บันทึกแผน  เปรียบเทียบราคา  ลงนามเอกสาร  ทะเบียนสัญญา  หลักประกัน  PO  แอปผู้ขาย  QC  รับเข้าคลัง  ใบตรวจรับ",
      },
      {
        t: "ออกแบบ ใช้แนบไฟล์คู่ขนาน",
        c: ST.design.fill,
        d: "คำสั่งตั้งกรรมการ  แบบ บก.06  ร่างประกาศ  TOR  รายงานผล  ประกาศผู้ชนะ  หนังสือเชิญทำสัญญา  ไฟล์สัญญาที่ลงนามแล้ว  — ระบบรองรับการแนบ ส่งกล่องอนุมัติ และลงนามบน PDF",
      },
      {
        t: "นอกระบบ ทำบน e-GP รัฐ",
        c: ST.ext.fill,
        d: "สร้างและประกาศแผนบน gprocurement.go.th  เผยแพร่ร่างประกาศ  รับซองเสนอราคา  พิจารณาผลใน e-GP  ประกาศผู้ชนะบนเว็บ  — ERP ไม่ยิงประกาศขึ้นเว็บเอง",
      },
    ];
    groups.forEach((g, i) => {
      const y = 1.12 + i * 1.82;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: 0.5,
        y,
        w: 12.32,
        h: 1.68,
        fill: { color: C.background2 },
        rectRadius: 0.1,
        objectName: `sum-${i}`,
      });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: 0.7,
        y: y + 0.22,
        w: 3.35,
        h: 1.24,
        fill: { color: g.c },
        rectRadius: 0.08,
        objectName: `sumb-${i}`,
      });
      s.addText(g.t, {
        x: 0.82,
        y: y + 0.22,
        w: 3.1,
        h: 1.24,
        align: "center",
        valign: "middle",
        fontSize: 15,
        bold: true,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `sumt-${i}`,
      });
      s.addText(g.d, {
        x: 4.22,
        y: y + 0.22,
        w: 8.35,
        h: 1.24,
        valign: "middle",
        fontSize: 14,
        color: C.text1,
        margin: 0,
        isTextBox: true,
        objectName: `sumd-${i}`,
      });
    });
  }

  // ------------------------------------------------------------------
  // 10 Review questions
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "ทบทวน Function" });
    s.addText("ประเด็นทบทวน Function", { placeholder: "title" });
    const qs = [
      {
        n: "1",
        t: "ขอบเขต e-GP รัฐ",
        d: "ยืนยันว่า ERP บันทึกแผนและผลเท่านั้น ไม่ประกาศขึ้นเว็บ  ไฟล์จาก e-GP ต้องแนบครบก่อนลงนาม",
      },
      {
        n: "2",
        t: "หนังสือขออนุมัติตามขั้นตอน",
        d: "ชุดเอกสารใดสร้างจากระบบได้  ชุดใดต้องแนบจาก e-GP  ลำดับสายลงนามตรงระเบียบโรงพยาบาลหรือไม่",
      },
      {
        n: "3",
        t: "ประเภทสัญญา",
        d: "ซื้อ จ้าง เช่า  และสัญญาจะซื้อจะขายราคาคงที่ไม่จำกัดปริมาณ  ตัดยอดคงเหลือเมื่อเปิด PO ถูกต้องหรือไม่",
      },
      {
        n: "4",
        t: "จุดตัดคลังและตรวจรับ",
        d: "ผู้ขายยืนยันแล้วสร้างใบรับสินค้าอัตโนมัติ  QC ต้องผ่านก่อนรับเข้าคลัง  แล้วพัสดุจึงสร้างใบตรวจรับ",
      },
    ];
    qs.forEach((q, i) => {
      const y = 1.1 + i * 1.38;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: 0.5,
        y,
        w: 12.32,
        h: 1.24,
        fill: { color: C.background2 },
        rectRadius: 0.1,
        objectName: `q-${i}`,
      });
      s.addShape(pres.shapes.OVAL, {
        x: 0.72,
        y: y + 0.32,
        w: 0.58,
        h: 0.58,
        fill: { color: C.accent1 },
        objectName: `qn-${i}`,
      });
      s.addText(q.n, {
        x: 0.72,
        y: y + 0.32,
        w: 0.58,
        h: 0.58,
        align: "center",
        valign: "middle",
        fontSize: 18,
        bold: true,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `qnt-${i}`,
      });
      s.addText(q.t, {
        x: 1.5,
        y: y + 0.12,
        w: 10.95,
        h: 0.38,
        fontSize: 16,
        bold: true,
        color: C.text1,
        margin: 0,
        isTextBox: true,
        objectName: `qtt-${i}`,
      });
      s.addText(q.d, {
        x: 1.5,
        y: y + 0.54,
        w: 10.95,
        h: 0.56,
        fontSize: 14,
        color: C.text2,
        margin: 0,
        isTextBox: true,
        objectName: `qtd-${i}`,
      });
    });
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  await applyPromptThemeFonts(OUT);
  console.log("Wrote", OUT);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
