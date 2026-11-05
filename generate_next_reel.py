#!/usr/bin/env python3
"""One-command TYB Reel generator: question -> AI script -> validation -> render."""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, urllib.request, urllib.error
from pathlib import Path
from openpyxl import load_workbook
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "output"
STATE_DIR = ROOT / "state"
STATE_FILE = STATE_DIR / "state.json"
BANK = ROOT / "TYB_Question_Bank_v2.xlsx"
W, H, FPS = 1080, 1920, 10
FONT_PATH = os.environ.get("TYB_FONT_PATH", "/usr/share/fonts/opentype/lobster/lobster.otf")
TEXT_COLOR = (24, 143, 122)
HOOK_ZONE = (203, 259, 745, 309)
CTA_ZONE = (156, 250, 765, 328)
CTA_TEXTS = [
    "Follow for more thoughtful conversations about food.",
    "Know someone who would find this useful? Share this with them.",
    "Have you ever wondered about this? Share your experience below.",
    "Follow us for more food myths explained simply.",
    "Share this with someone who enjoys understanding food better.",
    "Curious about food? You're in the right place. Follow for more!",
    "What food-related question should we discuss next? Tell us in the comments.",
    "Share this with a health phile you know.",
]
TEMPLATE_PAIRS = [
    ("Template 1.1.png", "Template 1.2.png"),
    ("Template 2.1.png", "Template 2.2.png"),
    ("Template 3.1.png", "Template 3.2.png"),
    ("Template 4.1.png", "Template 4.2.png"),
]
BGM_FILES = [f"BGM{i}.mp3" for i in range(1, 6)]

BRAND_RULES = """
You are writing a text-only Instagram Reel for The Yogic Belief, a thoughtful, wholesome vegetarian food brand.
VOICE: friendly expert + fair myth-buster + lightly witty chef. Sound like a real customer and chef, not a lecture or advertisement.
PURPOSE: teach something useful about food, eating habits, food quality, vegetarian nutrition, mindful eating, or Ayurveda-inspired food philosophy.
FORMAT: 5–8 short on-screen dialogue scenes, normally 45–80 seconds total. Open with the exact approved question as a compelling customer hook. Use roles only 'customer' or 'chef'. Give the chef a clear answer, practical explanation, optional customer follow-up, and a natural concluding takeaway.
CRITICAL MENU RULE: never mention any specific menu-item name, branded dish name, or specific item offered by the restaurant anywhere. General food categories and ingredient names may be used educationally. Do not promote products.
CLAIMS: Use general knowledge for straightforward, non-high-stakes food education. Do not invent studies, statistics, citations, medical claims, or certainty. Do not claim food cures/treats disease, guarantees weight loss, detoxifies the body, balances hormones, or clinically boosts immunity. Don't say a vegetarian label alone guarantees nutritional adequacy. Distinguish traditional/Ayurvedic perspectives from established scientific evidence. Don't imply natural always means safe/healthier, no refined sugar means sugar-free/low-calorie, or no maida means low-carb. Do not invent TYB operational claims.
STYLE: simple natural English; specific, memorable, useful; avoid generic filler and repeated points. Keep each scene short enough to read comfortably on a phone (ideally 5–20 words; max 26 words). No voice-over directions, emojis, markdown, stage directions, or sound effects.
OUTPUT: return valid JSON only in this exact shape:
{"hook":"...","scenes":[{"role":"customer","text":"..."},{"role":"chef","text":"..."},...]}
The first scene must be role customer and text must exactly equal the approved question. The last scene must be role chef and conclude the idea. Include 5–8 scenes total including the hook. Do not include CTA; the renderer adds it.
"""

def load_state():
    STATE_DIR.mkdir(exist_ok=True)
    if not STATE_FILE.exists():
        return {"question_cursor": 0, "pair_cursor": 0, "music_cursor": 0, "cta_cursor": 0, "used_question_ids": [], "completed_reels": []}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        defaults = {"question_cursor": 0, "pair_cursor": 0, "music_cursor": 0, "cta_cursor": 0, "used_question_ids": [], "completed_reels": []}
        defaults.update(data)
        return defaults
    except Exception:
        raise RuntimeError(f"State file is unreadable: {STATE_FILE}. Back it up and repair it rather than silently resetting sequence counters.")

def save_state(state):
    STATE_DIR.mkdir(exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_FILE)

def load_questions():
    wb = load_workbook(BANK, read_only=True, data_only=True)
    ws = wb["Approved Questions"]
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(x).strip() if x is not None else "" for x in rows[0]]
    q_idx = headers.index("Question ID")
    text_idx = headers.index("Approved Question")
    status_idx = headers.index("Selection Status")
    questions = []
    for row in rows[1:]:
        if not row or not row[q_idx] or not row[text_idx]:
            continue
        status = str(row[status_idx] or "").strip().lower()
        if status.startswith("selected"):
            questions.append({"id": str(row[q_idx]).strip(), "question": str(row[text_idx]).strip()})
    wb.close()
    if not questions:
        raise RuntimeError("No approved questions found in the Question Bank.")
    return questions

def select_question(state, explicit_id=None, allow_repeat=False):
    questions = load_questions()
    used = set(state.get("used_question_ids", []))
    if explicit_id:
        found = next((q for q in questions if q["id"].upper() == explicit_id.upper()), None)
        if not found:
            raise ValueError(f"{explicit_id} is not an approved Question Bank ID.")
        if found["id"] in used and not allow_repeat:
            raise ValueError(f"{explicit_id} has already been rendered successfully. Use --repeat to override only if intended.")
        return found, questions.index(found)
    available = [q for q in questions if q["id"] not in used]
    if not available:
        # Begin a new cycle only after every approved question has been used.
        state["used_question_ids"] = []
        available = questions
    cursor = int(state.get("question_cursor", 0)) % len(questions)
    for offset in range(len(questions)):
        i = (cursor + offset) % len(questions)
        if questions[i]["id"] not in set(state.get("used_question_ids", [])):
            return questions[i], i
    return available[0], questions.index(available[0])

def call_ai(question):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. See README.md. Use --demo to test rendering without an API key.")
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    payload = {
        "model": model,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": BRAND_RULES},
            {"role": "user", "content": f"Create the Reel script for this approved question.\nQuestion ID: {question['id']}\nApproved question (must be the exact first scene): {question['question']}"}
        ]
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:1500]
        raise RuntimeError(f"AI API request failed (HTTP {e.code}): {detail}") from e
    except Exception as e:
        raise RuntimeError(f"AI request failed: {e}") from e
    try:
        content = data["choices"][0]["message"]["content"]
        script = json.loads(content)
    except Exception as e:
        raise RuntimeError(f"AI response was not valid JSON: {e}") from e
    return script, model

def repair_ai_script(question, previous_script, error_message):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    payload = {
        "model": model,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": BRAND_RULES},
            {"role": "user", "content": (
                f"Repair this script so it passes the validation error below. Keep the approved question exact. "
                f"Return JSON only in the required shape.\nValidation error: {error_message}\n"
                f"Question ID: {question['id']}\nApproved question: {question['question']}\n"
                f"Previous JSON: {json.dumps(previous_script, ensure_ascii=False)}"
            )}
        ]
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        raise RuntimeError(f"One automatic script-repair attempt failed: {e}") from e

def demo_script(question):
    return {
        "hook": question["question"],
        "scenes": [
            {"role": "customer", "text": question["question"]},
            {"role": "chef", "text": "Not necessarily. Food choices make more sense when we look at the overall pattern, not one label alone."},
            {"role": "customer", "text": "So I should look beyond a single number or claim?"},
            {"role": "chef", "text": "Exactly. Consider variety, portions, preparation, and what works for your needs."},
            {"role": "chef", "text": "A thoughtful food choice is rarely about one magic rule. Context matters."}
        ]
    }

def validate_script(script, question):
    if not isinstance(script, dict):
        raise ValueError("Script must be a JSON object.")
    hook = str(script.get("hook", "")).strip()
    scenes = script.get("scenes")
    if hook != question["question"]:
        raise ValueError("Hook must exactly match the approved Question Bank question.")
    if not isinstance(scenes, list) or not 5 <= len(scenes) <= 8:
        raise ValueError("Script must contain 5–8 scenes.")
    if any(not isinstance(scene, dict) for scene in scenes):
        raise ValueError("Every scene must be a JSON object with role and text.")
    if str(scenes[0].get("role", "")).lower().strip() != "customer":
        raise ValueError("First scene must be spoken by the customer.")
    # The approved hook is already validated above. Preserve the model's dialogue,
    # but canonicalize the opening scene to the exact approved question so minor
    # punctuation/wording drift cannot trigger an unnecessary AI repair.
    scenes[0]["text"] = question["question"]
    if str(scenes[-1].get("role", "")).lower() != "chef":
        raise ValueError("Final dialogue scene must be the chef's conclusion.")
    for i, scene in enumerate(scenes):
        role = str(scene.get("role", "")).lower().strip()
        text = str(scene.get("text", "")).strip()
        if role not in ("customer", "chef") or not text:
            raise ValueError(f"Scene {i+1} needs role customer/chef and non-empty text.")
        if len(text.split()) > 28:
            raise ValueError(f"Scene {i+1} is too long ({len(text.split())} words). Keep scenes to 28 words or fewer.")
        if re.search(r"\b(study found|research proves|scientists proved|clinically proven)\b", text, re.I):
            raise ValueError(f"Scene {i+1} contains a research/clinical claim that should not be asserted without a source.")
        if re.search(r"\b(cures?|treats?|detoxifies|guarantees weight loss|balances hormones|boosts immunity)\b", text, re.I):
            raise ValueError(f"Scene {i+1} contains a prohibited health claim.")
    return {"hook": hook, "scenes": [{"role": str(s["role"]).lower().strip(), "text": str(s["text"]).strip()} for s in scenes]}

def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = word if not line else line + " " + word
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def draw_centered_text(img, text, zone, font_size=58):
    x, y, w, h = zone
    draw = ImageDraw.Draw(img)
    chosen, lines = None, None
    for size in range(font_size, 27, -1):
        font = ImageFont.truetype(FONT_PATH, size)
        ls = wrap_text(text, font, w, draw)
        heights = [draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in ls]
        total = sum(heights) + max(0, len(ls)-1) * 12
        if total <= h:
            chosen, lines = font, ls
            break
    if chosen is None:
        chosen = ImageFont.truetype(FONT_PATH, 28)
        lines = wrap_text(text, chosen, w, draw)
    heights = []
    for line in lines:
        box = draw.textbbox((0, 0), line, font=chosen)
        heights.append(box[3] - box[1])
    gap = 10
    total = sum(heights) + max(0, len(lines)-1) * gap
    yy = y + (h-total)//2
    for line, lh in zip(lines, heights):
        box = draw.textbbox((0, 0), line, font=chosen)
        xx = x + (w - (box[2]-box[0]))//2
        draw.text((xx, yy), line, font=chosen, fill=TEXT_COLOR)
        yy += lh + gap
    return img

def duration_for(text, is_hook=False):
    # Comfortable reading speed for text-only Reels, with modest pauses.
    words = len(text.split())
    return max(3.0 if is_hook else 3.2, min(7.0, words / 2.3 + 1.6))

def make_scene(template, text, duration, start_frame, frames_dir, zone=HOOK_ZONE):
    total_frames = max(1, round(duration * FPS))
    reveal_seconds = min(max(len(text) * 0.045, 0.8), duration * 0.70)
    reveal_frames = max(1, round(reveal_seconds * FPS))
    for j in range(total_frames):
        img = template.copy()
        chars = min(len(text), round(len(text) * j / max(1, reveal_frames-1))) if j < reveal_frames else len(text)
        draw_centered_text(img, text[:chars], zone, font_size=62)
        img.save(frames_dir / f"{start_frame+j:05d}.jpg", quality=90, optimize=True)
    return start_frame + total_frames

def render(script, question, state):
    if not Path(FONT_PATH).exists():
        raise RuntimeError(f"Lobster font not found at {FONT_PATH}. Set TYB_FONT_PATH to the font file path.")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg not found. Install FFmpeg and ensure it is on PATH.")
    pair_i = int(state.get("pair_cursor", 0)) % len(TEMPLATE_PAIRS)
    music_i = int(state.get("music_cursor", 0)) % len(BGM_FILES)
    cta_i = int(state.get("cta_cursor", 0)) % len(CTA_TEXTS)
    customer_path, chef_path = [ASSETS / name for name in TEMPLATE_PAIRS[pair_i]]
    music_path = ASSETS / BGM_FILES[music_i]
    cta_path = ASSETS / "CTA.png"
    for p in (customer_path, chef_path, music_path, cta_path):
        if not p.exists():
            raise RuntimeError(f"Required asset is missing: {p.name}")
    customer_template = Image.open(customer_path).convert("RGB")
    chef_template = Image.open(chef_path).convert("RGB")
    cta_template = Image.open(cta_path).convert("RGB")
    reel_slug = f"TYB_{question['id']}_{question['question'][:38]}"
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", reel_slug).strip("_")
    temp_root = OUTPUT / "_render_temp"
    if temp_root.exists():
        shutil.rmtree(temp_root)
    frames_dir = temp_root / "frames"
    frames_dir.mkdir(parents=True)
    frame_index = 0
    for i, scene in enumerate(script["scenes"]):
        role = scene["role"]
        text = scene["text"]
        template = customer_template if role == "customer" else chef_template
        frame_index = make_scene(template, text, duration_for(text, i == 0), frame_index, frames_dir)
    cta_text = CTA_TEXTS[cta_i]
    frame_index = make_scene(cta_template, cta_text, 4.0, frame_index, frames_dir, CTA_ZONE)
    duration = frame_index / FPS
    output_path = OUTPUT / f"{slug}.mp4"
    cover_path = OUTPUT / f"{slug}_cover.jpg"
    # Static cover always uses Template 1.1, independent of the rotating scene pair.
    cover_template = customer_template.copy()  # Keep the cover aligned with the selected rotating template pair.
    draw_centered_text(cover_template, script["hook"], HOOK_ZONE, font_size=62)
    cover_template.save(cover_path, quality=95, optimize=True)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", str(FPS), "-i", str(frames_dir / "%05d.jpg"),
        "-i", str(music_path), "-t", f"{duration:.2f}",
        "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "21", "-c:a", "aac", "-b:a", "128k",
        "-af", f"volume=0.16,afade=t=in:st=0:d=0.7,afade=t=out:st={max(0,duration-0.9):.2f}:d=0.8",
        "-shortest", str(output_path)
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)
        ], check=True, capture_output=True, text=True)
        actual_duration = float(probe.stdout.strip())
        if actual_duration < 5 or output_path.stat().st_size < 100_000:
            raise RuntimeError("Rendered video failed basic duration/file-size checks.")
    except Exception:
        if output_path.exists():
            output_path.unlink()
        if cover_path.exists():
            cover_path.unlink()
        raise
    finally:
        if temp_root.exists():
            shutil.rmtree(temp_root)
    return output_path, cover_path, actual_duration, pair_i, music_i, cta_i

def main():
    parser = argparse.ArgumentParser(description="Generate the next The Yogic Belief text-only Reel.")
    parser.add_argument("--question-id", help="Optional approved question ID, e.g. Q001")
    parser.add_argument("--demo", action="store_true", help="Test rendering with demonstration dialogue; no API key required.")
    parser.add_argument("--repeat", action="store_true", help="Allow an already-used question ID (does not change normal sequence).")
    args = parser.parse_args()
    state = load_state()
    question, question_index = select_question(state, args.question_id, allow_repeat=args.repeat)
    print(f"Question: {question['id']} — {question['question']}", flush=True)
    if args.demo:
        raw_script, model = demo_script(question), "demo"
    else:
        raw_script, model = call_ai(question)
    try:
        script = validate_script(raw_script, question)
    except ValueError as first_error:
        if args.demo:
            raise
        print(f"Script validation failed; attempting one automatic repair: {first_error}", flush=True)
        repaired = repair_ai_script(question, raw_script, str(first_error))
        script = validate_script(repaired, question)
    # Save generated script before rendering for easy troubleshooting/reuse.
    pair_preview = int(state.get("pair_cursor", 0)) % len(TEMPLATE_PAIRS)
    music_preview = int(state.get("music_cursor", 0)) % len(BGM_FILES)
    cta_preview = int(state.get("cta_cursor", 0)) % len(CTA_TEXTS)
    script_record = {
        "question_id": question["id"], "question": question["question"],
        "model": model, "hook": script["hook"], "scenes": script["scenes"],
        "cta": CTA_TEXTS[cta_preview], "template_pair": pair_preview+1,
        "music": BGM_FILES[music_preview], "status": "script_validated"
    }
    script_path = OUTPUT / f"{question['id']}_script.json"
    script_path.write_text(json.dumps(script_record, indent=2, ensure_ascii=False), encoding="utf-8")
    output_path, cover_path, duration, pair_i, music_i, cta_i = render(script, question, state)
    script_record.update({
        "status": "rendered", "video": output_path.name, "cover": cover_path.name,
        "duration_seconds": round(duration, 2)
    })
    script_path.write_text(json.dumps(script_record, indent=2, ensure_ascii=False), encoding="utf-8")
    # Advance all independent sequences only after successful render.
    used = list(state.get("used_question_ids", []))
    if question["id"] not in used:
        used.append(question["id"])
    questions = load_questions()
    state["used_question_ids"] = used
    state["question_cursor"] = (question_index + 1) % len(questions)
    state["pair_cursor"] = (pair_i + 1) % len(TEMPLATE_PAIRS)
    state["music_cursor"] = (music_i + 1) % len(BGM_FILES)
    state["cta_cursor"] = (cta_i + 1) % len(CTA_TEXTS)
    state.setdefault("completed_reels", []).append({
        "question_id": question["id"], "video": output_path.name,
        "cover": cover_path.name, "duration_seconds": round(duration, 2)
    })
    save_state(state)
    print("\nSUCCESS")
    print(f"VIDEO: {output_path}")
    print(f"COVER: {cover_path}")
    print(f"SCRIPT: {script_path}")
    print(f"DURATION: {duration:.1f}s")
    print(f"ASSETS: Pair {pair_i+1}, {BGM_FILES[music_i]}, CTA {cta_i+1}")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
