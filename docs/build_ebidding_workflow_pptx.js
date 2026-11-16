#!/usr/bin/env node
"use strict";

const path = require("path");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(
  "/Users/mchedtha/.claude/skills/synced/d68f830d-3313-4497-b854-cf2eff79e4b6_92a7ad89-b804-4e2c-b4b0-c15499e429d7/pptx/scripts/apply_theme.js"
);
const {
  MdAccountBalance,
  MdAssignment,
  MdGavel,
  MdHandshake,
  MdLocalShipping,
  MdFactCheck,
  MdGroups,
  MdCampaign,
  MdHowToVote,
  MdInventory2,
  MdStorefront,
  MdVerified,
  MdDescription,
  MdRequestQuote,
  MdApartment,
  MdBadge,
} = require("react-icons/md");

const OUT = path.join(__dirname, "Workflow-e-Bidding.pptx");

const THEME = {
  name: "Vachira e-Bidding",
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

async function iconData(Icon, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Icon, { color: `#${color}`, size })
  );
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

function shadowSoft() {
  return {
    type: "outer",
    color: "0F2942",
    blur: 10,
    offset: 4,
    opacity: 0.12,
    angle: 90,
  };
}

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

async function main() {
  const I = {
    budget: await iconData(MdAccountBalance, THEME.colors.accent1),
    budgetW: await iconData(MdAccountBalance, "FFFFFF"),
    pr: await iconData(MdAssignment, THEME.colors.accent2),
    prW: await iconData(MdAssignment, "FFFFFF"),
    gavel: await iconData(MdGavel, THEME.colors.accent5),
    gavelW: await iconData(MdGavel, "FFFFFF"),
    contract: await iconData(MdHandshake, THEME.colors.accent3),
    contractW: await iconData(MdHandshake, "FFFFFF"),
    ship: await iconData(MdLocalShipping, THEME.colors.accent4),
    shipW: await iconData(MdLocalShipping, "FFFFFF"),
    check: await iconData(MdFactCheck, THEME.colors.accent1),
    groups: await iconData(MdGroups, THEME.colors.accent2),
    campaign: await iconData(MdCampaign, THEME.colors.accent5),
    vote: await iconData(MdHowToVote, THEME.colors.accent6),
    inventory: await iconData(MdInventory2, THEME.colors.accent4),
    inventoryW: await iconData(MdInventory2, "FFFFFF"),
    store: await iconData(MdStorefront, THEME.colors.accent1),
    storeW: await iconData(MdStorefront, "FFFFFF"),
    groupsW: await iconData(MdGroups, "FFFFFF"),
    verified: await iconData(MdVerified, THEME.colors.accent1),
    doc: await iconData(MdDescription, THEME.colors.accent2),
    quote: await iconData(MdRequestQuote, THEME.colors.accent3),
    dept: await iconData(MdApartment, THEME.colors.accent2),
    badge: await iconData(MdBadge, THEME.colors.accent1),
  };

  const pres = new pptxgen();
  pres.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
  pres.layout = "WIDE";
  pres.title = "Workflow e-Bidding";
  pres.author = "VPK";
  pres.subject = "Workflow การจัดซื้อจัดจ้างแบบ e-Bidding";
  pres.company = "Vachira Phuket Hospital";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
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
            y: 1.85,
            w: 11.9,
            h: 1.35,
            fontSize: 36,
            fontFace: "Prompt",
            bold: true,
            color: C.background1,
            align: "left",
            valign: "middle",
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
            y: 3.28,
            w: 10.5,
            h: 0.7,
            fontSize: 18,
            fontFace: "Prompt",
            color: C.background2,
            align: "left",
            valign: "top",
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
            y: 0.28,
            w: 12.3,
            h: 0.52,
            fontSize: 30,
            fontFace: "Prompt",
            bold: true,
            color: C.text1,
            align: "left",
            valign: "middle",
            margin: 0,
          },
        },
      },
      {
        text: {
          text: "โรงพยาบาลวชิระภูเก็ต  ·  Workflow e-Bidding",
          options: {
            x: 0.5,
            y: 7.18,
            w: 10.4,
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
      x: 12.35,
      y: 7.16,
      w: 0.45,
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
  pres.addSection({ title: "รายละเอียดขั้นตอน" });
  pres.addSection({ title: "สรุป" });

  // ------------------------------------------------------------------
  // Slide 1 — Title
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "ภาพรวม" });
    s.addShape(pres.shapes.OVAL, {
      x: 11.55,
      y: -0.85,
      w: 3.2,
      h: 3.2,
      fill: { color: C.accent1, transparency: 78 },
      objectName: "orb-tr",
    });
    s.addShape(pres.shapes.OVAL, {
      x: -1.1,
      y: 5.4,
      w: 3.6,
      h: 3.6,
      fill: { color: C.accent2, transparency: 82 },
      objectName: "orb-bl",
    });
    s.addText("ระบบ ERP  ·  โรงพยาบาลวชิระภูเก็ต", {
      x: 0.7,
      y: 1.28,
      w: 10,
      h: 0.36,
      fontSize: 14,
      color: C.accent3,
      bold: true,
      margin: 0,
      isTextBox: true,
      objectName: "kicker",
    });
    s.addText("Workflow การจัดซื้อจัดจ้างแบบ e-Bidding", { placeholder: "title" });
    s.addText("จากแผนงบประมาณ ถึงการส่งมอบตามสัญญา", { placeholder: "subtitle" });

    const pills = [
      { n: "1", t: "แผนงบประมาณ" },
      { n: "2", t: "ขอซื้อ e-Bidding" },
      { n: "3", t: "กระบวนการ e-GP" },
      { n: "4", t: "ทำสัญญา" },
      { n: "5", t: "ส่งของตามสัญญา" },
    ];
    pills.forEach((p, i) => {
      const x = 0.7 + i * 2.42;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x,
        y: 5.55,
        w: 2.22,
        h: 0.78,
        fill: { color: C.background1, transparency: 88 },
        rectRadius: 0.1,
        objectName: `pill-${i}`,
      });
      s.addText(p.n, {
        x,
        y: 5.55,
        w: 0.42,
        h: 0.78,
        align: "center",
        valign: "middle",
        fontSize: 18,
        bold: true,
        color: C.accent3,
        margin: 0,
        isTextBox: true,
        objectName: `pill-n-${i}`,
      });
      s.addText(p.t, {
        x: x + 0.4,
        y: 5.55,
        w: 1.76,
        h: 0.78,
        valign: "middle",
        fontSize: 12,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `pill-t-${i}`,
      });
    });
    s.addNotes("สไลด์เปิด: ภาพรวม 5 ขั้นตอนหลักของการจัดซื้อจัดจ้างแบบ e-Bidding");
  }

  // ------------------------------------------------------------------
  // Slide 2 — Overview 5 steps
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "ภาพรวม" });
    s.addText("ภาพรวม 5 ขั้นตอนหลัก", { placeholder: "title" });
    s.addText("เส้นทางเดียวกันทั้งงานซื้อ งานจ้าง และงานเช่า ที่ใช้วิธีประกวดราคาอิเล็กทรอนิกส์", {
      x: 0.5,
      y: 0.82,
      w: 12.3,
      h: 0.32,
      fontSize: 14,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "overview-sub",
    });

    const steps = [
      {
        n: "1",
        icon: I.budget,
        fill: C.accent1,
        title: "แผนงบประมาณ",
        who: "หน่วยงาน + งบประมาณ",
        lines: "ตั้งงบประจำปี\nรวบรวมเป็นแผน\nอนุมัติและจัดสรร",
        out: "วงเงินพร้อมใช้",
      },
      {
        n: "2",
        icon: I.pr,
        fill: C.accent2,
        title: "ขอซื้อ e-Bidding",
        who: "หน่วยงานผู้ขอซื้อ",
        lines: "สร้างใบขอซื้อ\nทำหนังสืออนุมัติขอซื้อ\nส่งให้พัสดุดำเนินการ",
        out: "PR ส่งพัสดุแล้ว",
      },
      {
        n: "3",
        icon: I.gavel,
        fill: C.accent5,
        title: "กระบวนการ e-GP",
        who: "พัสดุ บน e-GP รัฐ",
        lines: "ดำเนินการในระบบ e-GP รัฐ\nสร้าง/ประกาศแผน\nขออนุมัติตั้งกรรมการ\nประกวดราคาจนได้ผู้ชนะ\nแนบหนังสือขออนุมัติต่างๆ\nส่งขออนุมัติตามขั้นตอน",
        out: "ประกาศผู้ชนะ",
      },
      {
        n: "4",
        icon: I.contract,
        fill: C.accent3,
        title: "ทำสัญญา",
        who: "พัสดุ + ผู้ชนะ",
        lines: "เลือกประเภทสัญญา\nลงนามทะเบียนสัญญา\nหลักประกันสัญญา",
        out: "สัญญามีผลใช้",
      },
      {
        n: "5",
        icon: I.ship,
        fill: C.accent4,
        title: "ส่งของตามสัญญา",
        who: "ผู้ขาย + คลัง + ตรวจรับ",
        lines: "ออกใบสั่งซื้อ PO\nส่งของและตรวจ QC\nรับเข้าคลัง ตรวจรับ",
        out: "ของเข้าคลังแล้ว",
      },
    ];

    steps.forEach((st, i) => {
      const x = 0.5 + i * 2.56;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x,
        y: 1.28,
        w: 2.36,
        h: 5.52,
        fill: { color: C.background2 },
        shadow: shadowCard(),
        rectRadius: 0.12,
        objectName: `ov-card-${i}`,
      });
      s.addShape(pres.shapes.OVAL, {
        x: x + 0.92,
        y: 1.42,
        w: 0.52,
        h: 0.52,
        fill: { color: st.fill },
        objectName: `ov-num-bg-${i}`,
      });
      s.addText(st.n, {
        x: x + 0.92,
        y: 1.42,
        w: 0.52,
        h: 0.52,
        align: "center",
        valign: "middle",
        fontSize: 20,
        bold: true,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `ov-num-${i}`,
      });
      s.addImage({
        data: st.icon,
        x: x + 0.94,
        y: 2.02,
        w: 0.48,
        h: 0.48,
        objectName: `ov-icon-${i}`,
      });
      s.addText(st.title, {
        x: x + 0.12,
        y: 2.52,
        w: 2.12,
        h: 0.52,
        align: "center",
        valign: "middle",
        fontSize: 15,
        bold: true,
        color: C.text1,
        margin: 0,
        isTextBox: true,
        objectName: `ov-title-${i}`,
      });
      s.addText(st.who, {
        x: x + 0.12,
        y: 3.04,
        w: 2.12,
        h: 0.32,
        align: "center",
        fontSize: 12,
        color: st.fill,
        bold: true,
        margin: 0,
        isTextBox: true,
        objectName: `ov-who-${i}`,
      });
      s.addText(st.lines, {
        x: x + 0.12,
        y: 3.38,
        w: 2.12,
        h: 2.22,
        align: "center",
        valign: "middle",
        fontSize: 12,
        color: C.text2,
        margin: 0,
        isTextBox: true,
        objectName: `ov-lines-${i}`,
      });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: x + 0.16,
        y: 5.72,
        w: 2.04,
        h: 0.82,
        fill: { color: C.background1 },
        rectRadius: 0.08,
        objectName: `ov-out-bg-${i}`,
      });
      s.addText("ผลลัพธ์", {
        x: x + 0.16,
        y: 5.76,
        w: 2.04,
        h: 0.28,
        align: "center",
        fontSize: 10,
        color: C.text2,
        margin: 0,
        isTextBox: true,
        objectName: `ov-out-l-${i}`,
      });
      s.addText(st.out, {
        x: x + 0.16,
        y: 6.02,
        w: 2.04,
        h: 0.42,
        align: "center",
        valign: "middle",
        fontSize: 13,
        bold: true,
        color: C.text1,
        margin: 0,
        isTextBox: true,
        objectName: `ov-out-${i}`,
      });
      if (i < steps.length - 1) {
        s.addShape(pres.shapes.RIGHT_ARROW, {
          x: x + 2.3,
          y: 3.08,
          w: 0.32,
          h: 0.18,
          fill: { color: C.accent1 },
          objectName: `ov-arr-${i}`,
        });
      }
    });
  }

  // ------------------------------------------------------------------
  // Slide 3 — Step 1 Budget
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "รายละเอียดขั้นตอน" });
    s.addText("ขั้นที่ 1  แผนงบประมาณ", { placeholder: "title" });
    s.addText("ต้องมีวงเงินในแผนประจำปีก่อน จึงจะเปิดใบขอซื้อวิธี e-Bidding ได้", {
      x: 0.5,
      y: 0.84,
      w: 12.3,
      h: 0.3,
      fontSize: 14,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "s1-sub",
    });

    const items = [
      {
        n: "1",
        t: "หน่วยงานตั้งงบ",
        d: "จัดทำคำขอตั้งงบวัสดุ ครุภัณฑ์ หรือโครงการ ตามความต้องการประจำปี",
      },
      {
        n: "2",
        t: "งบประมาณรวบรวมแผน",
        d: "ดึงคำขอตั้งงบทุกหน่วยงานเข้าแผนงบประมาณประจำปี ตรวจวงเงินและหมวดงบ",
      },
      {
        n: "3",
        t: "อนุมัติแผนประจำปี",
        d: "ผู้อำนวยการอนุมัติแผน ระบบจัดสรรวงเงินลงหน่วยงาน แหล่งเงิน และหมวดงบ",
      },
      {
        n: "4",
        t: "วงเงินพร้อมใช้",
        d: "หน่วยงานเห็นยอดจัดสรร คงเหลือ และสามารถเปิดใบขอซื้อตามแผนได้",
      },
    ];
    items.forEach((it, i) => {
      const y = 1.32 + i * 1.28;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: 0.5,
        y,
        w: 8.35,
        h: 1.14,
        fill: { color: C.background2 },
        rectRadius: 0.1,
        objectName: `s1-row-${i}`,
      });
      s.addShape(pres.shapes.OVAL, {
        x: 0.72,
        y: y + 0.28,
        w: 0.58,
        h: 0.58,
        fill: { color: C.accent1 },
        objectName: `s1-num-bg-${i}`,
      });
      s.addText(it.n, {
        x: 0.72,
        y: y + 0.28,
        w: 0.58,
        h: 0.58,
        align: "center",
        valign: "middle",
        fontSize: 18,
        bold: true,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `s1-num-${i}`,
      });
      s.addText(it.t, {
        x: 1.5,
        y: y + 0.14,
        w: 7.1,
        h: 0.38,
        fontSize: 16,
        bold: true,
        color: C.text1,
        margin: 0,
        isTextBox: true,
        objectName: `s1-t-${i}`,
      });
      s.addText(it.d, {
        x: 1.5,
        y: y + 0.52,
        w: 7.1,
        h: 0.48,
        fontSize: 14,
        color: C.text2,
        margin: 0,
        isTextBox: true,
        objectName: `s1-d-${i}`,
      });
    });

    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 9.1,
      y: 1.32,
      w: 3.72,
      h: 5.26,
      fill: { color: C.text1 },
      rectRadius: 0.12,
      objectName: "s1-side",
    });
    s.addImage({
      data: I.budgetW,
      x: 10.48,
      y: 1.62,
      w: 0.95,
      h: 0.95,
      objectName: "s1-side-icon",
    });
    s.addText("ผู้เกี่ยวข้อง", {
      x: 9.32,
      y: 2.72,
      w: 3.28,
      h: 0.36,
      align: "center",
      fontSize: 14,
      color: C.accent3,
      bold: true,
      margin: 0,
      isTextBox: true,
      objectName: "s1-side-h",
    });
    s.addText(
      "หน่วยงานผู้ขอซื้อ\nจัดทำคำขอตั้งงบ\n\nกลุ่มงานงบประมาณ\nรวบรวมและจัดสรร\n\nผู้อำนวยการ\nอนุมัติแผนประจำปี",
      {
        x: 9.32,
        y: 3.16,
        w: 3.28,
        h: 3.1,
        align: "center",
        fontSize: 14,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: "s1-side-b",
      }
    );
  }

  // ------------------------------------------------------------------
  // Slide 4 — Step 2 Department PR
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "รายละเอียดขั้นตอน" });
    s.addText("ขั้นที่ 2  หน่วยงานขอซื้อแบบ e-Bidding", { placeholder: "title" });
    s.addText("หน่วยงานสร้างใบขอซื้อ ทำหนังสืออนุมัติขอซื้อ แล้วส่งให้พัสดุดำเนินการ ไม่ประกาศใน e-GP เอง", {
      x: 0.5,
      y: 0.84,
      w: 12.3,
      h: 0.3,
      fontSize: 14,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "s2-sub",
    });

    const cards = [
      {
        n: "1",
        t: "สร้างใบขอซื้อ",
        d: "วิธีจัดซื้อ = e-Bidding\nเชื่อมโยงตามแผนงบ\nระบุรายการและวงเงิน",
      },
      {
        n: "2",
        t: "Spec และกรรมการ",
        d: "คุณลักษณะเฉพาะ\nกก. ราคากลาง\nกก. พิจารณาผล และตรวจรับ",
      },
      {
        n: "3",
        t: "ตรวจงบประมาณ",
        d: "กดตรวจสอบงบ\nต้องขึ้นงบเพียงพอ\nจึงส่งต่อได้",
      },
      {
        n: "4",
        t: "ทำหนังสืออนุมัติขอซื้อ",
        d: "จัดทำหนังสืออนุมัติขอซื้อ\nแบบ e-Bidding\nลงนามตามสายงาน",
      },
      {
        n: "5",
        t: "ส่งให้พัสดุดำเนินการ",
        d: "ส่งใบขอซื้อให้พัสดุ\nสถานะส่งพัสดุแล้ว\nพัสดุรับไปทำ e-GP",
      },
    ];
    cards.forEach((c, i) => {
      const x = 0.5 + i * 2.56;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x,
        y: 1.32,
        w: 2.4,
        h: 4.05,
        fill: { color: C.background2 },
        shadow: shadowCard(),
        rectRadius: 0.1,
        objectName: `s2-card-${i}`,
      });
      s.addShape(pres.shapes.OVAL, {
        x: x + 0.9,
        y: 1.52,
        w: 0.58,
        h: 0.58,
        fill: { color: C.accent2 },
        objectName: `s2-num-bg-${i}`,
      });
      s.addText(c.n, {
        x: x + 0.9,
        y: 1.52,
        w: 0.58,
        h: 0.58,
        align: "center",
        valign: "middle",
        fontSize: 18,
        bold: true,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `s2-num-${i}`,
      });
      s.addText(c.t, {
        x: x + 0.12,
        y: 2.22,
        w: 2.16,
        h: 0.72,
        align: "center",
        valign: "middle",
        fontSize: 15,
        bold: true,
        color: C.text1,
        margin: 0,
        isTextBox: true,
        objectName: `s2-t-${i}`,
      });
      s.addText(c.d, {
        x: x + 0.14,
        y: 2.98,
        w: 2.12,
        h: 2.1,
        align: "center",
        fontSize: 13,
        color: C.text2,
        margin: 0,
        isTextBox: true,
        objectName: `s2-d-${i}`,
      });
      if (i < cards.length - 1) {
        s.addShape(pres.shapes.RIGHT_ARROW, {
          x: x + 2.34,
          y: 3.15,
          w: 0.28,
          h: 0.16,
          fill: { color: C.accent2 },
          objectName: `s2-arr-${i}`,
        });
      }
    });

    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.5,
      y: 5.55,
      w: 12.32,
      h: 1.42,
      fill: { color: C.text1 },
      rectRadius: 0.1,
      objectName: "s2-note",
    });
    s.addText("สิ่งที่ต้องครบก่อนส่งพัสดุ", {
      x: 0.74,
      y: 5.68,
      w: 11.85,
      h: 0.32,
      fontSize: 14,
      bold: true,
      color: C.accent3,
      margin: 0,
      isTextBox: true,
      objectName: "s2-note-h",
    });
    s.addText(
      "รายการสินค้าและชื่อสำหรับซื้อใน e-GP  ·  คุณลักษณะเฉพาะ  ·  คณะกรรมการครบชุด  ·  งบเพียงพอ  ·  หนังสืออนุมัติขอซื้อ",
      {
        x: 0.74,
        y: 6.05,
        w: 11.85,
        h: 0.7,
        fontSize: 14,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: "s2-note-b",
      }
    );
  }

  // ------------------------------------------------------------------
  // Slide 5 — Step 3 e-GP process
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "รายละเอียดขั้นตอน" });
    s.addText("ขั้นที่ 3  ดำเนินการในระบบ e-GP รัฐ", { placeholder: "title" });
    s.addText("พัสดุทำงานบนระบบ e-GP ของกรมบัญชีกลาง และแนบหนังสือขออนุมัติใน ERP เพื่อส่งอนุมัติตามขั้นตอน", {
      x: 0.5,
      y: 0.82,
      w: 12.3,
      h: 0.32,
      fontSize: 14,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "s3-sub",
    });

    const row1 = [
      {
        n: "3.1",
        t: "ทำในระบบ e-GP รัฐ",
        d: "งานประกาศและประกวดราคาทำบนระบบ e-GP ของกรมบัญชีกลาง ไม่ประกาศจาก ERP โดยตรง",
      },
      {
        n: "3.2",
        t: "สร้าง / ประกาศแผน",
        d: "พัสดุจัดทำแผนจัดซื้อจัดจ้างใน e-GP แล้วประกาศเผยแพร่ตามระเบียบ",
      },
      {
        n: "3.3",
        t: "ขออนุมัติตั้งกรรมการ",
        d: "ขออนุมัติตั้งกรรมการกำหนดคุณลักษณะ ราคากลาง พิจารณาผล และตรวจรับ",
      },
    ];
    const row2 = [
      {
        n: "3.4",
        t: "ประกวดราคาจนได้ผู้ชนะ",
        d: "ร่างประกาศ รับฟังความเห็น เสนอราคา พิจารณาผล จนประกาศผู้ชนะ",
      },
      {
        n: "3.5",
        t: "แนบหนังสือขออนุมัติ",
        d: "หนังสือขออนุมัติต่างๆ แนบในระบบ เพื่อส่งขออนุมัติตามขั้นตอน",
      },
      {
        n: "3.6",
        t: "ได้ผู้ชนะ พร้อมทำสัญญา",
        d: "พ้นระยะอุทธรณ์แล้ว มีเอกสารอนุมัติครบ จึงเชิญผู้ชนะมาทำสัญญา",
      },
    ];

    const drawEgRow = (items, y0) => {
      items.forEach((it, i) => {
        const x = 0.5 + i * 4.22;
        s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
          x,
          y: y0,
          w: 3.95,
          h: 2.28,
          fill: { color: C.background2 },
          shadow: shadowCard(),
          rectRadius: 0.1,
          objectName: `s3-${y0}-${i}`,
        });
        s.addShape(pres.shapes.OVAL, {
          x: x + 0.18,
          y: y0 + 0.22,
          w: 0.5,
          h: 0.5,
          fill: { color: C.accent5 },
          objectName: `s3nbg-${y0}-${i}`,
        });
        s.addText(it.n.replace("3.", ""), {
          x: x + 0.18,
          y: y0 + 0.22,
          w: 0.5,
          h: 0.5,
          align: "center",
          valign: "middle",
          fontSize: 14,
          bold: true,
          color: C.background1,
          margin: 0,
          isTextBox: true,
          objectName: `s3n-${y0}-${i}`,
        });
        s.addText(it.t, {
          x: x + 0.78,
          y: y0 + 0.22,
          w: 2.98,
          h: 0.5,
          valign: "middle",
          fontSize: 15,
          bold: true,
          color: C.text1,
          margin: 0,
          isTextBox: true,
          objectName: `s3t-${y0}-${i}`,
        });
        s.addText(it.d, {
          x: x + 0.2,
          y: y0 + 0.86,
          w: 3.55,
          h: 1.2,
          fontSize: 14,
          color: C.text2,
          margin: 0,
          isTextBox: true,
          objectName: `s3d-${y0}-${i}`,
        });
        if (i < items.length - 1) {
          s.addShape(pres.shapes.RIGHT_ARROW, {
            x: x + 3.96,
            y: y0 + 1.05,
            w: 0.26,
            h: 0.16,
            fill: { color: C.accent5 },
            objectName: `s3a-${y0}-${i}`,
          });
        }
      });
    };

    drawEgRow(row1, 1.26);
    s.addText("ต่อไป  ประกวดราคา แนบหนังสือขออนุมัติ จนได้ผู้ชนะ", {
      x: 0.5,
      y: 3.56,
      w: 12.3,
      h: 0.38,
      align: "center",
      valign: "middle",
      fontSize: 13,
      bold: true,
      color: C.accent5,
      margin: 0,
      isTextBox: true,
      objectName: "s3-next",
    });
    drawEgRow(row2, 3.98);

    s.addText("ผลลัพธ์ของขั้นนี้: มีผู้ชนะการเสนอราคา ผ่านระยะอุทธรณ์ พร้อมเข้าทำสัญญา", {
      x: 0.5,
      y: 6.42,
      w: 12.3,
      h: 0.42,
      fontSize: 15,
      bold: true,
      color: C.accent1,
      margin: 0,
      isTextBox: true,
      objectName: "s3-out",
    });
  }

  // ------------------------------------------------------------------
  // Slide 6 — Step 4 Contract types
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "รายละเอียดขั้นตอน" });
    s.addText("ขั้นที่ 4  ทำสัญญา ตามประเภทสัญญา", { placeholder: "title" });
    s.addText("เลือกประเภทตามลักษณะงานที่ประกวดราคา แล้วเปิดทะเบียนสัญญาใน ERP จากเอกสาร e-GP", {
      x: 0.5,
      y: 0.82,
      w: 12.3,
      h: 0.32,
      fontSize: 14,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "s4-sub",
    });

    const kinds = [
      { t: "ซื้อ", d: "พัสดุ ยา วัสดุ ครุภัณฑ์", icon: I.inventoryW },
      { t: "จ้าง", d: "จ้างทำของ จ้างบริการ ก่อสร้าง", icon: I.groupsW },
      { t: "เช่า", d: "เช่าทรัพย์สินหรือบริการต่อเนื่อง", icon: I.storeW },
    ];
    kinds.forEach((k, i) => {
      const x = 0.5 + i * 4.22;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x,
        y: 1.24,
        w: 4.02,
        h: 1.42,
        fill: { color: C.text1 },
        rectRadius: 0.1,
        objectName: `s4-kind-${i}`,
      });
      s.addImage({
        data: k.icon,
        x: x + 0.22,
        y: 1.52,
        w: 0.7,
        h: 0.7,
        objectName: `s4-kicon-${i}`,
      });
      s.addText(k.t, {
        x: x + 1.08,
        y: 1.42,
        w: 2.7,
        h: 0.52,
        valign: "middle",
        fontSize: 22,
        bold: true,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `s4-kt-${i}`,
      });
      s.addText(k.d, {
        x: x + 1.08,
        y: 1.94,
        w: 2.7,
        h: 0.48,
        fontSize: 13,
        color: C.background2,
        margin: 0,
        isTextBox: true,
        objectName: `s4-kd-${i}`,
      });
    });

    const forms = [
      {
        t: "สัญญาซื้อขาย",
        d: "ปริมาณกำหนด ส่งมอบครั้งเดียวหรือเป็นงวด ตามรายการที่ประกวดราคา",
      },
      {
        t: "สัญญาจะซื้อจะขาย",
        d: "ราคาคงที่ ไม่จำกัดปริมาณ ใช้กับยาและวัสดุที่สั่งตามความต้องการจริง",
      },
      {
        t: "สัญญาจ้างทำของ / จ้างบริการ",
        d: "งานจ้างตาม TOR มีงวดงาน ตรวจรับตามผลงาน ไม่ใช่การรับสินค้าเข้าคลัง",
      },
      {
        t: "สัญญาเช่า",
        d: "เช่าทรัพย์สินหรือบริการต่อเนื่อง มีวันเริ่ม-สิ้นสุด และต่ออายุเมื่อใกล้หมดสัญญา",
      },
    ];
    forms.forEach((f, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = 0.5 + col * 6.4;
      const y = 2.86 + row * 1.72;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x,
        y,
        w: 6.2,
        h: 1.56,
        fill: { color: C.background2 },
        rectRadius: 0.1,
        objectName: `s4-form-${i}`,
      });
      s.addShape(pres.shapes.OVAL, {
        x: x + 0.18,
        y: y + 0.48,
        w: 0.58,
        h: 0.58,
        fill: { color: C.accent3 },
        objectName: `s4-fn-${i}-bg`,
      });
      s.addText(String(i + 1), {
        x: x + 0.18,
        y: y + 0.48,
        w: 0.58,
        h: 0.58,
        align: "center",
        valign: "middle",
        fontSize: 18,
        bold: true,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `s4-fn-${i}`,
      });
      s.addText(f.t, {
        x: x + 0.92,
        y: y + 0.18,
        w: 5.05,
        h: 0.42,
        fontSize: 16,
        bold: true,
        color: C.text1,
        margin: 0,
        isTextBox: true,
        objectName: `s4-ft-${i}`,
      });
      s.addText(f.d, {
        x: x + 0.92,
        y: y + 0.64,
        w: 5.05,
        h: 0.72,
        fontSize: 14,
        color: C.text2,
        margin: 0,
        isTextBox: true,
        objectName: `s4-fd-${i}`,
      });
    });
  }

  // ------------------------------------------------------------------
  // Slide 7 — Step 5 Delivery
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "รายละเอียดขั้นตอน" });
    s.addText("ขั้นที่ 5  เริ่มต้นส่งของตามสัญญา", { placeholder: "title" });
    s.addText("เมื่อสัญญามีผลบังคับใช้แล้ว จึงสร้างใบสั่งซื้อและรับมอบตามเงื่อนไขสัญญา", {
      x: 0.5,
      y: 0.84,
      w: 12.3,
      h: 0.3,
      fontSize: 14,
      color: C.text2,
      margin: 0,
      isTextBox: true,
      objectName: "s5-sub",
    });

    const flow = [
      { n: "1", t: "สร้างใบสั่งซื้อ", d: "ออก PO ตามสัญญา ไม่เกินวงเงินคงเหลือ" },
      { n: "2", t: "ผู้ขายยืนยัน", d: "ส่งเข้าแอปผู้ขาย ลงนามรับทราบคำสั่งซื้อ" },
      { n: "3", t: "ส่งของตามสัญญา", d: "ผู้ขายส่งมอบตามกำหนด งวด หรือความต้องการ" },
      { n: "4", t: "ตรวจคุณภาพ QC", d: "คลังตรวจสภาพ ฉลาก Lot วันหมดอายุ" },
      { n: "5", t: "รับเข้าคลัง", d: "บันทึก Lot จำนวนจริง ยอดคงเหลือเพิ่มขึ้น" },
      { n: "6", t: "ตรวจรับพัสดุ", d: "กรรมการตรวจรับ ออกใบตรวจรับ WA" },
    ];
    flow.forEach((f, i) => {
      const col = i % 3;
      const row = Math.floor(i / 3);
      const x = 0.5 + col * 4.22;
      const y = 1.26 + row * 2.72;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x,
        y,
        w: 4.02,
        h: 2.18,
        fill: { color: C.background2 },
        shadow: shadowCard(),
        rectRadius: 0.1,
        objectName: `s5-c-${i}`,
      });
      s.addShape(pres.shapes.OVAL, {
        x: x + 0.22,
        y: y + 0.28,
        w: 0.58,
        h: 0.58,
        fill: { color: C.accent4 },
        objectName: `s5-nbg-${i}`,
      });
      s.addText(f.n, {
        x: x + 0.22,
        y: y + 0.28,
        w: 0.58,
        h: 0.58,
        align: "center",
        valign: "middle",
        fontSize: 18,
        bold: true,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `s5-n-${i}`,
      });
      s.addText(f.t, {
        x: x + 0.96,
        y: y + 0.28,
        w: 2.82,
        h: 0.58,
        valign: "middle",
        fontSize: 16,
        bold: true,
        color: C.text1,
        margin: 0,
        isTextBox: true,
        objectName: `s5-t-${i}`,
      });
      s.addText(f.d, {
        x: x + 0.22,
        y: y + 1.05,
        w: 3.58,
        h: 0.95,
        fontSize: 14,
        color: C.text2,
        margin: 0,
        isTextBox: true,
        objectName: `s5-d-${i}`,
      });
      if (col < 2) {
        s.addShape(pres.shapes.RIGHT_ARROW, {
          x: x + 4.02,
          y: y + 1.08,
          w: 0.22,
          h: 0.16,
          fill: { color: C.accent4 },
          objectName: `s5-arr-${i}`,
        });
      }
    });
    s.addText("ต่อไป  ตรวจรับเข้าคลังและออกใบตรวจรับ", {
      x: 0.5,
      y: 3.48,
      w: 12.3,
      h: 0.42,
      align: "center",
      valign: "middle",
      fontSize: 13,
      bold: true,
      color: C.accent4,
      margin: 0,
      isTextBox: true,
      objectName: "s5-next",
    });
  }

  // ------------------------------------------------------------------
  // Slide 8 — Who does what / closing map
  // ------------------------------------------------------------------
  {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "สรุป" });
    s.addText("ใครทำอะไร ในแต่ละขั้น", { placeholder: "title" });

    const headerY = 1.05;
    const cols = [
      { t: "ขั้นที่ 1\nแผนงบ", x: 3.55 },
      { t: "ขั้นที่ 2\nขอซื้อ", x: 5.45 },
      { t: "ขั้นที่ 3\ne-GP", x: 7.35 },
      { t: "ขั้นที่ 4\nสัญญา", x: 9.25 },
      { t: "ขั้นที่ 5\nส่งของ", x: 11.15 },
    ];
    cols.forEach((c, i) => {
      s.addText(c.t, {
        x: c.x,
        y: headerY,
        w: 1.78,
        h: 0.7,
        align: "center",
        fontSize: 12,
        bold: true,
        color: C.text1,
        margin: 0,
        isTextBox: true,
        objectName: `map-h-${i}`,
      });
    });

    const rows = [
      { role: "งบประมาณ", cells: ["รวบรวม\nอนุมัติแผน", "", "", "", ""] },
      { role: "หน่วยงาน", cells: ["ตั้งงบประจำปี", "ขอซื้อ + หนังสือ\nส่งพัสดุ", "ร่วมกรรมการ", "", "ร่วมตรวจรับ"] },
      { role: "พัสดุ", cells: ["", "ตรวจ PR", "แผน กรรมการ\nแนบหนังสือ", "ทำสัญญา\nออก PO", "สร้างใบตรวจรับ"] },
      { role: "e-GP", cells: ["", "", "ประกวดราคา\nได้ผู้ชนะ", "แบบสัญญา\n(ถ้าใช้)", ""] },
      { role: "ผู้ขาย / คลัง", cells: ["", "", "เสนอราคา", "ลงนามสัญญา", "ส่งของ QC\nรับเข้าคลัง"] },
    ];
    const fills = [C.accent1, C.accent2, C.accent5, C.accent3, C.accent4];
    rows.forEach((r, ri) => {
      const y = 1.82 + ri * 0.98;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: 0.5,
        y,
        w: 2.9,
        h: 0.86,
        fill: { color: fills[ri] },
        rectRadius: 0.08,
        objectName: `map-role-${ri}`,
      });
      s.addText(r.role, {
        x: 0.5,
        y,
        w: 2.9,
        h: 0.86,
        align: "center",
        valign: "middle",
        fontSize: 14,
        bold: true,
        color: C.background1,
        margin: 0,
        isTextBox: true,
        objectName: `map-role-t-${ri}`,
      });
      r.cells.forEach((cell, ci) => {
        const x = 3.55 + ci * 1.9;
        s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
          x,
          y,
          w: 1.78,
          h: 0.86,
          fill: { color: cell ? C.background2 : C.background1 },
          rectRadius: 0.08,
          objectName: `map-c-${ri}-${ci}`,
        });
        if (cell) {
          s.addText(cell, {
            x,
            y,
            w: 1.78,
            h: 0.86,
            align: "center",
            valign: "middle",
            fontSize: 11,
            color: C.text1,
            margin: 0,
            isTextBox: true,
            objectName: `map-ct-${ri}-${ci}`,
          });
        }
      });
    });
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  await applyPromptThemeFonts(OUT);
  console.log("Wrote", OUT);
}

async function applyPromptThemeFonts(deckPath) {
  const fs = require("fs");
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

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
