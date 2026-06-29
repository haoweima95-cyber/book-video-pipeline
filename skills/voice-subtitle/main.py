#!/usr/bin/env python3
"""
voice-subtitle: 配音 + 字幕生成
为逐行 txt 文件生成配音 WAV 和分段 ASS 字幕。
"""

import sys, os, re, json, subprocess, shutil
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ── 统一 config 导入 ──
_PIPELINE_SRC = Path.home() / ".claude" / "skills" / "book-video-pipeline" / "src"
if str(_PIPELINE_SRC) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_SRC))


def _load_cfg():
    try:
        from config import load as load_config
        return load_config()
    except Exception:
        return None


_cfg = _load_cfg()


def _get_path(key, default):
    if _cfg and _cfg.get("paths", {}).get(key):
        return os.path.expanduser(_cfg["paths"][key])
    return os.path.expanduser(default)


_COSYVOICE_REPO = _get_path("cosyvoice_repo",
    os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "CosyVoice"))
_MATCHA_REPO = _get_path("matcha_tts_repo",
    os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Matcha-TTS"))

if _COSYVOICE_REPO not in sys.path and os.path.exists(_COSYVOICE_REPO):
    sys.path.insert(0, _COSYVOICE_REPO)
if _MATCHA_REPO not in sys.path and os.path.exists(_MATCHA_REPO):
    sys.path.insert(0, _MATCHA_REPO)

import torch
import torchaudio

MODEL_DIR = _get_path("cosyvoice_model", r"~\.cache\modelscope\iic\CosyVoice2-0___5B")
VOICE_DIR = _get_path("voice_storage", r"~\.cosyvoice\voices")
os.makedirs(VOICE_DIR, exist_ok=True)

DEFAULTS = {
    "voice": _cfg["tts"]["local_voice"] if _cfg and _cfg.get("tts", {}).get("local_voice") else "默认音色",
    "speed": _cfg["tts"]["speed"] if _cfg and _cfg.get("tts", {}).get("speed") else 1.1,
    "font_name": _cfg["subtitle"]["font_name"] if _cfg and _cfg.get("subtitle", {}).get("font_name") else "SimHei",
    "font_size": _cfg["subtitle"]["font_size"] if _cfg and _cfg.get("subtitle", {}).get("font_size") else 50,
    "font_bold": _cfg["subtitle"]["font_bold"] if _cfg and _cfg.get("subtitle", {}).get("font_bold") else True,
    "outline": _cfg["subtitle"]["outline_width"] if _cfg and _cfg.get("subtitle", {}).get("outline_width") else 3,
    "outline_color": _cfg["subtitle"]["outline_color"] if _cfg and _cfg.get("subtitle", {}).get("outline_color") else "&H00000000",
    "shadow": _cfg["subtitle"]["shadow"] if _cfg and _cfg.get("subtitle", {}).get("shadow") else 0,
    "alignment": _cfg["subtitle"]["alignment"] if _cfg and _cfg.get("subtitle", {}).get("alignment") else 2,
    "margin_v": _cfg["subtitle"]["margin_v"] if _cfg and _cfg.get("subtitle", {}).get("margin_v") else 80,
    "chars_per_line": _cfg["subtitle"]["chars_per_line"] if _cfg and _cfg.get("subtitle", {}).get("chars_per_line") else 25,
    "segment_by_punct": True,
    "clean_end_punct": True,
    "keep_end_chars": "？\"\"''》」』",
    "strip_end_chars": "。，！；、：…—",
}


class TTS:
    def __init__(self):
        self._model = None
        self._sample_rate = None

    @property
    def model(self):
        if self._model is None:
            from cosyvoice.cli.cosyvoice import CosyVoice2
            self._model = CosyVoice2(MODEL_DIR, fp16=False)
            self._sample_rate = self._model.sample_rate
        return self._model

    @property
    def sample_rate(self):
        if self._model is None:
            _ = self.model
        return self._sample_rate

    def synthesize(self, text, ref_wav, prompt_text, speed=1.0):
        chunks = _split_text(text, max_chars=180)
        speeches = []
        for chunk in chunks:
            gen = self.model.inference_zero_shot(
                chunk, prompt_text, ref_wav,
                zero_shot_spk_id='', stream=False, speed=speed
            )
            for result in gen:
                speeches.append(result["tts_speech"])
        if not speeches:
            raise RuntimeError(f"合成失败: {text[:30]}...")
        merged = torch.cat(speeches, dim=-1)
        dur = merged.shape[-1] / self.sample_rate
        return merged, dur


def list_voices():
    voices = []
    if not os.path.exists(VOICE_DIR):
        return voices
    for name in os.listdir(VOICE_DIR):
        info_file = os.path.join(VOICE_DIR, name, "info.json")
        if os.path.exists(info_file):
            with open(info_file, "r", encoding="utf-8") as f:
                voices.append(json.load(f))
    return voices


def clone_voice(name, reference_audio, reference_text,
                instruct_text="用自然的方式说话。"):
    vdir = os.path.join(VOICE_DIR, name)
    os.makedirs(vdir, exist_ok=True)
    ref_wav = os.path.join(vdir, "reference.wav")
    _to_wav(reference_audio, ref_wav)
    info = {
        "id": name, "name": name,
        "reference_text": reference_text,
        "instruct_text": instruct_text,
        "created_at": datetime.now().isoformat(),
        "type": "cloned",
    }
    with open(os.path.join(vdir, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    with open(os.path.join(vdir, "reference.txt"), "w", encoding="utf-8") as f:
        f.write(reference_text)
    return name


def delete_voice(voice_id):
    vdir = os.path.join(VOICE_DIR, voice_id)
    if os.path.exists(vdir):
        shutil.rmtree(vdir)


def _split_by_punct(text):
    parts = re.split(r"(?<=[。！？；\n])", text)
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        sub_parts = re.split(r"(?<=[，])", part)
        sub_parts = [s.strip() for s in sub_parts if s.strip()]
        if len(sub_parts) <= 1:
            result.append(part)
        else:
            merged, buf = [], ""
            for sp in sub_parts:
                if buf and len(buf) + len(sp) < 12:
                    buf += sp
                elif buf:
                    merged.append(buf)
                    buf = sp
                else:
                    buf = sp
            if buf:
                merged.append(buf)
            result.extend(merged)
    return [r for r in result if r]


def _clean_sub(text, cfg):
    keep, strip = cfg["keep_end_chars"], cfg["strip_end_chars"]
    while text and text[-1] in strip and text[-1] not in keep:
        text = text[:-1]
    return text


def _split_text(text, max_chars=180):
    text = text.replace("\n\n", "\n　\n")
    sentences = [s for s in re.split(r"(?<=[。！？\n])", text) if s.strip()]
    chunks, buf = [], ""
    for s in sentences:
        s = s.strip().replace("　", "")
        if not s:
            continue
        if len(s) > max_chars:
            if buf:
                chunks.append(buf)
                buf = ""
            while len(s) > max_chars:
                cut = max_chars
                for sep in ["，", "；", "、", "："]:
                    pos = s.rfind(sep, 0, max_chars)
                    if pos > max_chars // 2:
                        cut = pos + 1
                        break
                chunks.append(s[:cut])
                s = s[cut:].strip()
            if s:
                buf = s
            continue
        if len(buf) + len(s) <= max_chars:
            buf += s
        else:
            chunks.append(buf)
            buf = s
    if buf:
        chunks.append(buf)
    return chunks


def _trim_trailing_silence(speech, sample_rate, threshold_db=-30, keep_tail=0.1):
    peak = speech.abs().max()
    if peak == 0:
        return speech, speech.shape[-1] / sample_rate
    threshold = peak * (10 ** (threshold_db / 20))
    samples = speech.abs().squeeze()
    if samples.dim() == 0:
        return speech, speech.shape[-1] / sample_rate
    nonzero = (samples > threshold).nonzero(as_tuple=True)[0]
    if len(nonzero) == 0:
        return speech, speech.shape[-1] / sample_rate
    last_idx = nonzero[-1].item()
    keep_samples = min(last_idx + int(keep_tail * sample_rate), samples.shape[0])
    trimmed = speech[..., :keep_samples]
    return trimmed, keep_samples / sample_rate


def generate_ass(text, duration, output_path, cfg=None):
    if cfg is None:
        cfg = DEFAULTS
    segments = _split_by_punct(text) if cfg["segment_by_punct"] else [text]
    total_chars = sum(len(s) for s in segments) or 1
    dialogue_lines = []
    cursor = 0.0
    for seg in segments:
        seg_dur = (len(seg) / total_chars) * duration
        start_sec, end_sec = cursor, cursor + seg_dur
        cursor += seg_dur
        if cfg["clean_end_punct"]:
            seg = _clean_sub(seg, cfg)
        cpl = cfg["chars_per_line"]
        seg_lines = [seg[i:i + cpl] for i in range(0, len(seg), cpl)]
        seg_wrapped = "\\N".join(seg_lines)
        sh, sm = int(start_sec // 3600), int((start_sec % 3600) // 60)
        ss = start_sec % 60
        eh, em = int(end_sec // 3600), int((end_sec % 3600) // 60)
        es = end_sec % 60
        dialogue_lines.append(
            f"Dialogue: 0,{sh:02d}:{sm:02d}:{ss:05.2f},{eh:02d}:{em:02d}:{es:05.2f},"
            f"Default,,0,0,0,,{seg_wrapped}"
        )
    bold_val = -1 if cfg["font_bold"] else 0
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{cfg['font_name']},{cfg['font_size']},&H00FFFFFF,{cfg['outline_color']},&H00000000,{bold_val},0,0,0,100,100,0,0,1,{cfg['outline']},{cfg['shadow']},{cfg['alignment']},20,20,{cfg['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(dialogue_lines) + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass)


def generate(txt_path, voice_id=None, speed=None, cfg=None):
    if cfg is None:
        cfg = DEFAULTS
    if speed is None:
        speed = cfg["speed"]
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    voices = list_voices()
    if not voices:
        raise ValueError("没有可用的音色")
    voice_info = None
    if voice_id or cfg["voice"]:
        vid = voice_id or cfg["voice"]
        for v in voices:
            if v["id"] == vid:
                voice_info = v
                break
        if voice_info is None:
            raise ValueError(f"未找到音色: {vid}")
    else:
        voice_info = voices[0]
    vdir = os.path.join(VOICE_DIR, voice_info["id"])
    ref_wav = os.path.join(vdir, "reference.wav")
    prompt_text = voice_info.get("reference_text", "")
    out_dir = os.path.join(os.path.dirname(txt_path), "voice_output")
    os.makedirs(out_dir, exist_ok=True)
    basename = os.path.splitext(os.path.basename(txt_path))[0]
    safe = text[:20].replace("/", "").replace("\\", "").replace(":", "：") \
        .replace('"', "").replace("?", "").replace("*", "") \
        .replace("<", "").replace(">", "").replace("|", "")
    wav_path = os.path.join(out_dir, f"{int(basename):d}. {safe}.wav")
    ass_path = os.path.join(out_dir, f"{int(basename):d}. {safe}.ass")
    tts = TTS()
    speech, duration = tts.synthesize(text, ref_wav, prompt_text, speed)
    peak = speech.abs().max()
    if peak > 0:
        speech = speech * (0.7 / peak)
    speech, duration = _trim_trailing_silence(speech, tts.sample_rate)
    torchaudio.save(wav_path, speech, tts.sample_rate)
    generate_ass(text, duration, ass_path, cfg)
    print(f"  [{basename}] {safe}... → WAV {duration:.1f}s + ASS")
    return {"wav": wav_path, "ass": ass_path, "duration": duration, "text": text}


def generate_batch(txt_dir, voice_id=None, speed=None, cfg=None, files=None):
    all_files = sorted(
        [f for f in os.listdir(txt_dir) if f.endswith(".txt") and f.split(".")[0].isdigit()],
        key=lambda x: int(x.rsplit(".", 1)[0])
    )
    if files:
        # --files "1,3,5-8" → 只处理指定编号
        wanted = set()
        for part in files.split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = part.split("-", 1)
                wanted.update(range(int(lo), int(hi) + 1))
            else:
                wanted.add(int(part))
        txt_files = [f for f in all_files if int(f.rsplit(".", 1)[0]) in wanted]
    else:
        txt_files = all_files
    if not txt_files:
        print("未找到匹配的编号 txt 文件（如 1.txt, 2.txt ...）")
        return []
    print(f"处理 {len(txt_files)} 个 txt 文件...\n")
    results = []
    for tf in txt_files:
        txt_path = os.path.join(txt_dir, tf)
        try:
            r = generate(txt_path, voice_id=voice_id, speed=speed, cfg=cfg)
            results.append(r)
        except Exception as e:
            print(f"  失败 {tf}: {e}")
    print(f"\n完成: {len(results)}/{len(txt_files)}")
    return results


def _to_wav(src, dst, sample_rate=16000):
    if not os.path.exists(src):
        raise FileNotFoundError(f"音频文件不存在: {src}")
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-ac", "1", "-ar", str(sample_rate),
         "-sample_fmt", "s16", dst],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        creationflags=creationflags)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="配音+字幕生成工具")
    sub = parser.add_subparsers(dest="cmd")
    p_gen = sub.add_parser("gen")
    p_gen.add_argument("txt")
    p_gen.add_argument("--voice", "-v", default=None)
    p_batch = sub.add_parser("gen-batch")
    p_batch.add_argument("txt_dir")
    p_batch.add_argument("--voice", "-v", default=None)
    p_batch.add_argument("--files", default=None,
                         help="只处理指定编号，如 '1,3,5-8'")
    p_clone = sub.add_parser("clone")
    p_clone.add_argument("name")
    p_clone.add_argument("audio")
    p_clone.add_argument("text")
    sub.add_parser("list")
    p_del = sub.add_parser("delete")
    p_del.add_argument("voice_id")
    sub.add_parser("defaults")
    args = parser.parse_args()
    if args.cmd == "gen":
        generate(args.txt, voice_id=args.voice)
    elif args.cmd == "gen-batch":
        generate_batch(args.txt_dir, voice_id=args.voice, files=args.files)
    elif args.cmd == "clone":
        print(f"[OK] 音色已保存: {clone_voice(args.name, args.audio, args.text)}")
    elif args.cmd == "list":
        voices = list_voices()
        if voices:
            for v in voices:
                print(f"  {v['id']} | {v.get('reference_text', '')[:40]}")
        else:
            print("  (无已保存音色)")
    elif args.cmd == "delete":
        delete_voice(args.voice_id)
        print(f"[OK] 已删除: {args.voice_id}")
    elif args.cmd == "defaults":
        for k, v in DEFAULTS.items():
            print(f"  {k}: {v}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
