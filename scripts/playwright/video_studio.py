#!/usr/bin/env python3
"""
ชุดเครื่องมือบันทึกหน้าจอสด (Live Screen Recording) + เคอร์เซอร์จำลอง + กรอบไฮไลต์
+ แผ่นป้ายชื่อบท + ซับไตเติลภาษาไทย + เสียงพากย์ภาษาไทย (macOS 'Kanya')
สำหรับผลิตวิดีโอคู่มือการใช้งานระบบ VPK Odoo 18 แบบ Full HD (1920x1080)
"""

from __future__ import annotations

import asyncio
import math
import os
import shutil
import subprocess
import tempfile
import textwrap
import wave
from pathlib import Path
from typing import List, Optional, Tuple

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
VIDEO_W = 1920
VIDEO_H = 1080
FPS = 12  # 12 fps ลื่นไหลสำหรับ UI screencast และเรนเดอร์เร็ว

# ฟอนต์ภาษาไทยสำหรับ Title Card และ Subtitle Bar
SUKHUMVIT_PATH = "/System/Library/Fonts/Supplemental/SukhumvitSet.ttc"
THONBURI_PATH = "/System/Library/Fonts/Supplemental/Thonburi.ttc"
SARABUN_BOLD = "/Users/mchedtha/odoo18vpk/odoo18-custom-addons/l10n-thailand-18.0/l10n_th_base_utils/static/fonts/thai/THSarabunNew/THSarabunNew-Bold.ttf"
SARABUN_REG = "/Users/mchedtha/odoo18vpk/odoo18-custom-addons/l10n-thailand-18.0/l10n_th_base_utils/static/fonts/thai/THSarabunNew/THSarabunNew-Regular.ttf"


def load_thai_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if os.path.exists(SUKHUMVIT_PATH):
        # SukhumvitSet.ttc index 5/4 bold, 0/2 regular
        candidates.append((SUKHUMVIT_PATH, 4 if bold else 2, size))
        candidates.append((SUKHUMVIT_PATH, 0, size))
    if os.path.exists(THONBURI_PATH):
        candidates.append((THONBURI_PATH, 1 if bold else 0, size))
    if bold and os.path.exists(SARABUN_BOLD):
        candidates.append((SARABUN_BOLD, 0, int(size * 1.35)))
    if os.path.exists(SARABUN_REG):
        candidates.append((SARABUN_REG, 0, int(size * 1.35)))

    for path, idx, sz in candidates:
        try:
            return ImageFont.truetype(path, sz, index=idx)
        except Exception:
            continue
    return ImageFont.load_default()


# CSS + DOM Overlay สำหรับเคอร์เซอร์จำลองและกรอบไฮไลต์บนหน้าเบราว์เซอร์จริง
INJECT_OVERLAY_JS = """
() => {
    if (document.getElementById('vpk-demo-overlay-root')) return;
    const style = document.createElement('style');
    style.id = 'vpk-demo-overlay-style';
    style.textContent = `
        #vpk-demo-overlay-root {
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 2147483640;
            overflow: hidden;
        }
        #vpk-demo-highlight {
            position: fixed;
            border: 3.5px solid #ef4444;
            border-radius: 10px;
            box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.25), 0 8px 24px rgba(239, 68, 68, 0.35);
            transition: all 0.22s cubic-bezier(0.22, 1, 0.36, 1);
            opacity: 0;
            pointer-events: none;
        }
        #vpk-demo-highlight-label {
            position: absolute;
            top: -34px;
            left: -3px;
            background: #dc2626;
            color: #ffffff;
            font-family: 'Prompt', 'Sukhumvit Set', sans-serif;
            font-size: 14px;
            font-weight: 600;
            padding: 3px 11px;
            border-radius: 6px;
            white-space: nowrap;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.22);
        }
        #vpk-demo-cursor {
            position: fixed;
            left: 960px;
            top: 540px;
            width: 34px;
            height: 34px;
            transform: translate(-4px, -3px);
            transition: left 0.38s cubic-bezier(0.22, 1, 0.36, 1), top 0.38s cubic-bezier(0.22, 1, 0.36, 1), transform 0.12s ease;
            pointer-events: none;
            filter: drop-shadow(0 4px 8px rgba(0,0,0,0.38));
            z-index: 2147483646;
        }
        #vpk-demo-ripple {
            position: fixed;
            width: 48px;
            height: 48px;
            margin-left: -24px;
            margin-top: -24px;
            border-radius: 50%;
            border: 3px solid #f59e0b;
            background: rgba(245, 158, 11, 0.28);
            transform: scale(0.2);
            opacity: 0;
            pointer-events: none;
            z-index: 2147483645;
        }
        #vpk-demo-ripple.is-active {
            transition: transform 0.38s ease-out, opacity 0.38s ease-out;
            transform: scale(1.45);
            opacity: 0;
        }
        #vpk-demo-subtitle {
            position: fixed;
            left: 50%;
            bottom: 24px;
            transform: translateX(-50%);
            max-width: 1520px;
            width: max-content;
            background: rgba(15, 23, 42, 0.90);
            border: 1.5px solid rgba(56, 189, 248, 0.45);
            border-left: 6px solid #10b981;
            color: #f8fafc;
            font-family: 'Prompt', 'Sukhumvit Set', 'Thonburi', sans-serif;
            padding: 13px 26px;
            border-radius: 14px;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.42);
            display: flex;
            align-items: center;
            gap: 14px;
            z-index: 2147483647;
            opacity: 0;
            transition: opacity 0.2s ease;
        }
        #vpk-demo-step-badge {
            background: #10b981;
            color: #052e16;
            font-weight: 700;
            font-size: 15px;
            padding: 4px 12px;
            border-radius: 8px;
            white-space: nowrap;
            flex-shrink: 0;
        }
        #vpk-demo-subtitle-text {
            font-size: 20px;
            font-weight: 500;
            line-height: 1.42;
            max-width: 1300px;
        }
    `;
    document.head.appendChild(style);

    const root = document.createElement('div');
    root.id = 'vpk-demo-overlay-root';
    root.innerHTML = `
        <div id="vpk-demo-highlight"><span id="vpk-demo-highlight-label"></span></div>
        <div id="vpk-demo-ripple"></div>
        <div id="vpk-demo-cursor">
            <svg viewBox="0 0 32 32" width="34" height="34">
                <path d="M5 3 L5 26 L11.5 20 L16.2 29 L20 27.2 L15.3 18.2 L24 18.2 Z"
                      fill="#ffffff" stroke="#0f172a" stroke-width="2.2" stroke-linejoin="round"/>
            </svg>
        </div>
        <div id="vpk-demo-subtitle">
            <span id="vpk-demo-step-badge"></span>
            <span id="vpk-demo-subtitle-text"></span>
        </div>
    `;
    document.body.appendChild(root);
}
"""


def synthesize_thai_tts(text: str, out_wav: Path, rate: int = 185) -> float:
    """สร้างไฟล์เสียงพากย์ภาษาไทยด้วยเสียง Kanya บน macOS และคืนความยาวเป็นวินาที"""
    clean_text = (
        text.replace("ERP", "อีอาร์พี")
        .replace("PR", "พีอาร์")
        .replace("PO", "พีโอ")
        .replace("Dashboard", "แดชบอร์ด")
        .replace("Excel", "เอ็กเซล")
        .replace("(New)", "")
        .replace("→", " ไปที่ ")
        .replace("/", " หรือ ")
    )
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        aiff_path = tmp.name
    try:
        subprocess.run(
            ["say", "-v", "Kanya", "-r", str(rate), "-o", aiff_path, clean_text],
            check=True,
        )
        subprocess.run(
            [
                FFMPEG_EXE,
                "-y",
                "-i",
                aiff_path,
                "-ar",
                "44100",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(out_wav),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        if os.path.exists(aiff_path):
            os.remove(aiff_path)

    with wave.open(str(out_wav), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def create_silent_wav(out_wav: Path, duration_sec: float) -> None:
    sample_rate = 44100
    n_frames = max(1, int(sample_rate * duration_sec))
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n_frames)


def pad_wav_to_duration(wav_path: Path, target_duration: float) -> None:
    """เติมความเงียบท้ายไฟล์เสียงให้ยาวตรงกับความยาววิดีโอของ segment นั้นพอดี"""
    with wave.open(str(wav_path), "rb") as r:
        params = r.getparams()
        frames = r.readframes(r.getnframes())
        current_dur = r.getnframes() / float(r.getframerate())

    if target_duration <= current_dur:
        return

    extra_frames = int((target_duration - current_dur) * params.framerate)
    with wave.open(str(wav_path), "wb") as w:
        w.setparams(params)
        w.writeframes(frames + (b"\x00\x00" * extra_frames * params.nchannels))


def render_title_card_png(
    out_png: Path,
    kicker: str,
    title: str,
    subtitle: str,
    role_badge: str = "",
) -> None:
    """วาดแผ่นป้ายเปิดบท (Title Card) ความละเอียด 1920x1080 สไตล์โรงพยาบาลวชิระภูเก็ต"""
    img = Image.new("RGB", (VIDEO_W, VIDEO_H), (11, 46, 40))
    draw = ImageDraw.Draw(img)

    # พื้นหลังไล่เฉดสีเขียวเข้ม-น้ำเงินเข้ม
    for y in range(VIDEO_H):
        t = y / float(VIDEO_H)
        r = int(10 * (1 - t) + 15 * t)
        g = int(58 * (1 - t) + 28 * t)
        b = int(48 * (1 - t) + 46 * t)
        draw.line([(0, y), (VIDEO_W, y)], fill=(r, g, b))

    # แถบตกแต่งด้านซ้ายและกรอบการ์ดกลาง
    draw.rounded_rectangle(
        [(130, 150), (1790, 930)],
        radius=28,
        fill=(17, 36, 48),
        outline=(45, 212, 191),
        width=3,
    )
    draw.rounded_rectangle([(130, 150), (152, 930)], radius=10, fill=(16, 185, 129))

    f_kicker = load_thai_font(30, bold=True)
    f_title = load_thai_font(54, bold=True)
    f_sub = load_thai_font(30, bold=False)
    f_badge = load_thai_font(26, bold=True)
    f_footer = load_thai_font(24, bold=False)

    draw.text((210, 225), kicker, font=f_kicker, fill=(52, 211, 153))

    # ตัดบรรทัดชื่อบทอัตโนมัติ
    y_cursor = 305
    for line in textwrap.wrap(title, width=42):
        draw.text((210, y_cursor), line, font=f_title, fill=(248, 250, 252))
        y_cursor += 74

    y_cursor += 20
    for line in textwrap.wrap(subtitle, width=62):
        draw.text((210, y_cursor), line, font=f_sub, fill=(203, 213, 225))
        y_cursor += 48

    if role_badge:
        badge_w = max(360, len(role_badge) * 18 + 60)
        draw.rounded_rectangle(
            [(210, 745), (210 + badge_w, 810)],
            radius=14,
            fill=(16, 185, 129),
        )
        draw.text((238, 758), role_badge, font=f_badge, fill=(6, 44, 30))

    draw.text(
        (210, 852),
        "โรงพยาบาลวชิระภูเก็ต · ระบบบริหารทรัพยากรองค์กร (VPK Odoo 18 ERP) · คู่มือกลุ่มงานงบประมาณ ver.1",
        font=f_footer,
        fill=(148, 163, 184),
    )

    img.save(out_png, format="PNG")


def render_info_diagram_png(
    out_png: Path,
    header_title: str,
    boxes: List[Tuple[str, str, Tuple[int, int, int]]],
    footer_note: str,
) -> None:
    """วาดแผ่นผังสรุป (เช่น สรุป 4 แบบฟอร์ม หรือ สูตรคำนวณงบคงเหลือ / 4 มิติ PR)"""
    img = Image.new("RGB", (VIDEO_W, VIDEO_H), (15, 23, 42))
    draw = ImageDraw.Draw(img)

    f_head = load_thai_font(44, bold=True)
    f_box_t = load_thai_font(30, bold=True)
    f_box_b = load_thai_font(25, bold=False)
    f_foot = load_thai_font(26, bold=True)

    draw.text((120, 80), header_title, font=f_head, fill=(52, 211, 153))

    n = len(boxes)
    cols = 2 if n == 4 else n
    rows = math.ceil(n / cols)
    margin_x = 120
    gap_x = 40
    gap_y = 36
    avail_w = VIDEO_W - 2 * margin_x - (cols - 1) * gap_x
    box_w = avail_w // cols
    box_h = 280 if rows == 2 else 460
    start_y = 185

    for idx, (b_title, b_desc, color) in enumerate(boxes):
        r = idx // cols
        c = idx % cols
        x0 = margin_x + c * (box_w + gap_x)
        y0 = start_y + r * (box_h + gap_y)
        x1 = x0 + box_w
        y1 = y0 + box_h

        draw.rounded_rectangle(
            [(x0, y0), (x1, y1)],
            radius=20,
            fill=(30, 41, 59),
            outline=color,
            width=3,
        )
        draw.rounded_rectangle([(x0, y0), (x1, y0 + 12)], radius=6, fill=color)
        draw.text((x0 + 28, y0 + 32), b_title, font=f_box_t, fill=(248, 250, 252))

        yy = y0 + 88
        for ln in textwrap.wrap(b_desc, width=44 if cols == 2 else 28):
            draw.text((x0 + 28, yy), ln, font=f_box_b, fill=(203, 213, 225))
            yy += 38

    draw.rounded_rectangle(
        [(120, 845), (1800, 945)],
        radius=16,
        fill=(6, 78, 59),
        outline=(16, 185, 129),
        width=2,
    )
    draw.text((155, 875), footer_note, font=f_foot, fill=(236, 253, 245))
    img.save(out_png, format="PNG")


class ChapterVideoRecorder:
    """ตัวจัดการบันทึกเฟรมหน้าจอสด + เสียงพากย์ไทยของแต่ละบท แล้วรวมเป็นไฟล์ MP4"""

    def __init__(self, page, work_dir: Path, chapter_slug: str):
        self.page = page
        self.work_dir = work_dir / chapter_slug
        self.frames_dir = self.work_dir / "frames"
        self.audio_dir = self.work_dir / "audio"
        self.segments: List[Tuple[int, int, Path]] = []  # (start_frame, end_frame, wav_path)
        self.frame_idx = 0
        self._capture_task: Optional[asyncio.Task] = None
        self._capturing = False

        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def _next_frame_path(self) -> Path:
        p = self.frames_dir / f"frame_{self.frame_idx:06d}.jpg"
        self.frame_idx += 1
        return p

    def add_static_card_segment(self, png_path: Path, narration: str, min_sec: float = 4.0) -> None:
        """เพิ่มช่วงแผ่นป้ายชื่อบทหรือผังสรุป พร้อมเสียงพากย์ไทย"""
        seg_id = len(self.segments)
        wav_path = self.audio_dir / f"seg_{seg_id:03d}.wav"
        tts_dur = synthesize_thai_tts(narration, wav_path)
        total_dur = max(min_sec, tts_dur + 0.6)
        pad_wav_to_duration(wav_path, total_dur)

        n_frames = max(1, round(total_dur * FPS))
        start_f = self.frame_idx
        img = Image.open(png_path).convert("RGB")
        first_jpg = self._next_frame_path()
        img.save(first_jpg, format="JPEG", quality=92)
        for _ in range(n_frames - 1):
            os.link(first_jpg, self._next_frame_path())
        end_f = self.frame_idx
        self.segments.append((start_f, end_f, wav_path))

    async def ensure_overlay(self) -> None:
        try:
            await self.page.evaluate(INJECT_OVERLAY_JS)
        except Exception:
            pass

    async def set_subtitle(self, badge: str, text: str) -> None:
        await self.ensure_overlay()
        await self.page.evaluate(
            """([b, t]) => {
                const box = document.getElementById('vpk-demo-subtitle');
                const bEl = document.getElementById('vpk-demo-step-badge');
                const tEl = document.getElementById('vpk-demo-subtitle-text');
                if (!box) return;
                if (!t) { box.style.opacity = '0'; return; }
                bEl.textContent = b || 'ขั้นตอน';
                tEl.textContent = t;
                box.style.opacity = '1';
            }""",
            [badge, text],
        )

    async def clear_highlight(self) -> None:
        try:
            await self.page.evaluate(
                """() => {
                    const hl = document.getElementById('vpk-demo-highlight');
                    if (hl) hl.style.opacity = '0';
                }"""
            )
        except Exception:
            pass

    async def point_and_highlight(self, locator, label: str = "", pause: float = 0.65) -> Optional[dict]:
        """เลื่อนเคอร์เซอร์จำลองไปยังปุ่ม/ช่องข้อมูลและวาดกรอบสีแดงล้อมรอบก่อนคลิก"""
        await self.ensure_overlay()
        try:
            target = locator.first
            await target.wait_for(state="visible", timeout=15000)
            await target.scroll_into_view_if_needed(timeout=5000)
            box = await target.bounding_box()
            if not box:
                return None
            cx = box["x"] + min(box["width"] * 0.5, 90)
            cy = box["y"] + box["height"] * 0.5
            pad = 6
            await self.page.evaluate(
                """([bx, by, bw, bh, cx, cy, lbl]) => {
                    const hl = document.getElementById('vpk-demo-highlight');
                    const hlLbl = document.getElementById('vpk-demo-highlight-label');
                    const cur = document.getElementById('vpk-demo-cursor');
                    if (hl) {
                        hl.style.left = (bx - 6) + 'px';
                        hl.style.top = (by - 6) + 'px';
                        hl.style.width = (bw + 12) + 'px';
                        hl.style.height = (bh + 12) + 'px';
                        hl.style.opacity = '1';
                        if (hlLbl) {
                            hlLbl.textContent = lbl || '';
                            hlLbl.style.display = lbl ? 'block' : 'none';
                            hlLbl.style.top = (by < 44 ? (bh + 14) : -34) + 'px';
                        }
                    }
                    if (cur) {
                        cur.style.left = cx + 'px';
                        cur.style.top = cy + 'px';
                    }
                }""",
                [box["x"], box["y"], box["width"], box["height"], cx, cy, label],
            )
            await asyncio.sleep(pause)
            return {"x": cx, "y": cy, "box": box}
        except Exception as exc:
            print(f"  [warn] point_and_highlight skipped ({label}): {exc}")
            return None

    async def demo_click(self, locator, label: str = "", pause_before: float = 0.65, pause_after: float = 0.8) -> None:
        info = await self.point_and_highlight(locator, label=label, pause=pause_before)
        if info:
            await self.page.evaluate(
                """([cx, cy]) => {
                    const rp = document.getElementById('vpk-demo-ripple');
                    const cur = document.getElementById('vpk-demo-cursor');
                    if (cur) cur.style.transform = 'translate(-4px, -3px) scale(0.86)';
                    if (rp) {
                        rp.classList.remove('is-active');
                        rp.style.left = cx + 'px';
                        rp.style.top = cy + 'px';
                        rp.style.opacity = '1';
                        void rp.offsetWidth;
                        rp.classList.add('is-active');
                    }
                    setTimeout(() => {
                        if (cur) cur.style.transform = 'translate(-4px, -3px) scale(1)';
                    }, 150);
                }""",
                [info["x"], info["y"]],
            )
        await locator.first.click()
        await asyncio.sleep(pause_after)
        await self.clear_highlight()

    async def _capture_loop(self) -> None:
        interval = 1.0 / FPS
        while self._capturing:
            t0 = asyncio.get_event_loop().time()
            try:
                jpg_bytes = await self.page.screenshot(type="jpeg", quality=86)
                out_p = self._next_frame_path()
                out_p.write_bytes(jpg_bytes)
            except Exception:
                # หากหน้ากำลังโหลดเปลี่ยน URL ให้ซ้ำเฟรมก่อนหน้าไม่ให้สะดุด
                if self.frame_idx > 0:
                    prev = self.frames_dir / f"frame_{self.frame_idx - 1:06d}.jpg"
                    if prev.exists():
                        os.link(prev, self._next_frame_path())
            elapsed = asyncio.get_event_loop().time() - t0
            await asyncio.sleep(max(0.005, interval - elapsed))

    async def run_step(self, badge: str, subtitle: str, narration: str, action_coro, hold_after: float = 0.8) -> None:
        """
        รัน 1 ขั้นตอน:
        1) สร้างเสียงพากย์ภาษาไทยล่วงหน้าเพื่อวัดความยาวเสียง
        2) แสดงแถบซับไตเติลบนหน้าเว็บจริง
        3) เริ่มอัดเฟรมหน้าจอสดขณะรัน action_coro()
        4) ค้างหน้าจอจนเสียงพูดจบครบถ้วนเพื่อให้ภาพและเสียงตรงกัน 100%
        """
        seg_id = len(self.segments)
        wav_path = self.audio_dir / f"seg_{seg_id:03d}.wav"
        tts_dur = synthesize_thai_tts(narration, wav_path)

        await self.set_subtitle(badge, subtitle)
        start_f = self.frame_idx

        self._capturing = True
        self._capture_task = asyncio.create_task(self._capture_loop())
        t_start = asyncio.get_event_loop().time()
        try:
            if action_coro is not None:
                # รองรับทั้ง callable (async def) และ coroutine ที่สร้างไว้แล้ว
                result = action_coro() if callable(action_coro) else action_coro
                if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                    await result
            await asyncio.sleep(hold_after)
            # รอให้ครบความยาวเสียงพากย์ + จังหวะพักสั้นๆ
            elapsed = asyncio.get_event_loop().time() - t_start
            target_sec = tts_dur + 0.55
            if elapsed < target_sec:
                await asyncio.sleep(target_sec - elapsed)
        finally:
            self._capturing = False
            if self._capture_task:
                await self._capture_task

        end_f = self.frame_idx
        actual_video_dur = max(0.2, (end_f - start_f) / float(FPS))
        if actual_video_dur > tts_dur:
            pad_wav_to_duration(wav_path, actual_video_dur)
        else:
            # กรณีเฟรมได้น้อยกว่าความยาวเสียงเล็กน้อย ให้ซ้ำเฟรมสุดท้ายให้เท่าความยาวเสียงพอดี
            needed_frames = max(0, round(tts_dur * FPS) - (end_f - start_f))
            last_frame = self.frames_dir / f"frame_{self.frame_idx - 1:06d}.jpg"
            for _ in range(needed_frames):
                os.link(last_frame, self._next_frame_path())
            end_f = self.frame_idx
            pad_wav_to_duration(wav_path, (end_f - start_f) / float(FPS))

        self.segments.append((start_f, end_f, wav_path))

    def build_mp4(self, out_mp4: Path) -> Path:
        """รวมเฟรมภาพทั้งหมดและรวมไฟล์เสียงทุกช่วงเป็นไฟล์วิดีโอ H.264 + AAC (.mp4)"""
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        merged_wav = self.work_dir / "merged_audio.wav"

        with wave.open(str(merged_wav), "wb") as out_w:
            out_w.setnchannels(1)
            out_w.setsampwidth(2)
            out_w.setframerate(44100)
            for _s, _e, wav_p in self.segments:
                with wave.open(str(wav_p), "rb") as in_w:
                    out_w.writeframes(in_w.readframes(in_w.getnframes()))

        cmd = [
            FFMPEG_EXE,
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(self.frames_dir / "frame_%06d.jpg"),
            "-i",
            str(merged_wav),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(out_mp4),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(self.work_dir, ignore_errors=True)
        return out_mp4


def concat_mp4_files(mp4_files: List[Path], out_mp4: Path) -> Path:
    """รวมไฟล์ MP4 ของทุกบทเข้าเป็นวิดีโอฉบับเต็ม 1 ไฟล์"""
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        list_file = f.name
        for mp4 in mp4_files:
            f.write(f"file '{mp4.resolve()}'\n")
    try:
        subprocess.run(
            [
                FFMPEG_EXE,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_file,
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(out_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)
    return out_mp4
