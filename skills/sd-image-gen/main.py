#!/usr/bin/env python3
"""
Image Generation — 支持多种生图后端。
========================================
从 book-video-pipeline/config.yaml 读取 image 配置，支持：
  - siliconflow (SiliconFlow API)
  - openai_compatible (任何 OpenAI 兼容 API)
  - local (本地 Stable Diffusion / ComfyUI)

用法:
  python main.py "一只猫在晒太阳"                    # 单张生成
  python main.py "一只猫" -n 4 -s 1024x1024          # 4张
  python main.py -f prompts.txt -o ./output/          # 批量生成
"""

import sys, os, json, argparse, base64, time, urllib.request
from pathlib import Path
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── 统一 config 导入 ──
_PIPELINE_SRC = Path.home() / ".claude" / "skills" / "book-video-pipeline" / "src"
if str(_PIPELINE_SRC) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_SRC))
_PIPELINE_ROOT = Path.home() / ".claude" / "skills" / "book-video-pipeline"


def _load_image_cfg():
    try:
        from config import load as load_config
        cfg = load_config()
        if cfg and "image" in cfg:
            return cfg["image"]
    except Exception:
        pass
    return {}

_img_cfg = _load_image_cfg()

DEFAULT_PROVIDER = _img_cfg.get("provider", "siliconflow")
DEFAULT_MODEL = _img_cfg.get("model", "Tongyi-MAI/Z-Image-Turbo")
DEFAULT_SIZE = _img_cfg.get("default_size", "1024x1024")
API_BASE = _img_cfg.get("base_url", "https://api.siliconflow.com/v1")

API_KEY = os.environ.get("SILICONFLOW_API_KEY", "").strip()
if not API_KEY:
    API_KEY = os.environ.get("IMAGE_API_KEY", "").strip()
if not API_KEY:
    # 回退到 Claude settings 配置（读 local 优先，避免被代理覆盖）
    for _cfg_name in ["settings.local.json", "settings.json"]:
        try:
            with open(Path.home() / ".claude" / _cfg_name, encoding="utf-8") as _f:
                _env = json.load(_f).get("env", {})
                if "IMAGE_API_KEY" in _env:
                    API_KEY = _env["IMAGE_API_KEY"].strip()
                    break
        except Exception:
            pass
if not API_KEY:
    raw = _img_cfg.get("api_key", "")
    if raw and not raw.startswith("${") and not raw.startswith('"${'):
        API_KEY = raw.strip()
if not API_KEY:
    raw = _img_cfg.get("api_key", "")
    if raw:
        import re as _re
        m = _re.match(r'"?\$\{(\w+)\}"?', raw)
        if m:
            API_KEY = os.environ.get(m.group(1), "").strip()
if not API_KEY:
    try:
        with open(_PIPELINE_ROOT / "config.yaml", encoding="utf-8") as _f:
            for _line in _f:
                if "siliconflow_key:" in _line:
                    API_KEY = _line.split(":", 1)[1].strip().strip('"').strip("'")
                    break
    except Exception:
        pass


def _parse_ar(prompt, size):
    import re
    m = re.search(r'--ar\s+(\d+):(\d+)', prompt)
    if not m:
        return size
    w, h = int(m.group(1)), int(m.group(2))
    ar_map = {
        (16, 9): "1920x1080", (9, 16): "1080x1920",
        (1, 1): "1024x1024", (4, 3): "1440x1080", (3, 4): "1080x1440",
        (3, 2): "1440x960", (2, 3): "960x1440",
    }
    return ar_map.get((w, h), size)


def generate_image(prompt, model=DEFAULT_MODEL, size=DEFAULT_SIZE, num_images=1):
    size = _parse_ar(prompt, size)
    url = f"{API_BASE}/images/generations"
    payload = {"model": model, "prompt": prompt, "num_images": num_images, "size": size}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"API 错误 ({e.code}): {body[:500]}")
    except Exception as e:
        raise RuntimeError(f"请求失败: {e}")
    if "images" not in data:
        raise RuntimeError(f"API 返回异常: {json.dumps(data, ensure_ascii=False)[:300]}")
    urls = [img["url"] for img in data["images"] if "url" in img]
    if not urls:
        urls = [img.get("b64_json", img.get("url", "")) for img in data["images"]]
    timing = data.get("timings", {})
    if timing:
        print(f"   ⚡ 推理耗时: {timing.get('inference', '?')}s")
    return urls


def download_image(url, output_path):
    if url.startswith("data:"):
        header, b64 = url.split(",", 1)
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(b64))
    else:
        urllib.request.urlretrieve(url, output_path)
    return output_path


def generate_one(prompt, output=None, size=DEFAULT_SIZE, model=DEFAULT_MODEL):
    print(f'🎨 生成: "{prompt}"')
    urls = generate_image(prompt, model=model, size=size, num_images=1)
    img_url = urls[0]
    if output is None:
        safe = "".join(c for c in prompt[:20] if c.isalnum() or c in " _-").strip()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"{ts}_{safe}.png" if safe else f"{ts}.png"
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    download_image(img_url, str(output))
    size_kb = output.stat().st_size / 1024
    print(f"✅ 已保存: {output} ({size_kb:.0f} KB)")
    return str(output)


def generate_batch(prompts_file, output_dir, size=DEFAULT_SIZE, model=DEFAULT_MODEL):
    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    print(f"📋 共 {len(prompts)} 条提示词\n")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"[{i}/{len(prompts)}] ", end="")
        safe = "".join(c for c in prompt[:20] if c.isalnum() or c in " _-").strip()
        out = output_dir / f"{i:03d}_{safe}.png"
        try:
            generate_one(prompt, output=str(out), size=size, model=model)
            results.append({"prompt": prompt, "output": str(out), "status": "ok"})
        except Exception as e:
            print(f"❌ 失败: {e}")
            results.append({"prompt": prompt, "output": None, "status": str(e)})
        if i < len(prompts):
            time.sleep(0.5)
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\n✨ 完成: {ok}/{len(results)} 张")
    return results


def generate_multi(prompt, num, output_dir=".", size=DEFAULT_SIZE, model=DEFAULT_MODEL):
    print(f'🎨 生成 {num} 张: "{prompt}"')
    urls = generate_image(prompt, model=model, size=size, num_images=num)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in prompt[:20] if c.isalnum() or c in " _-").strip()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for i, url in enumerate(urls, 1):
        out = output_dir / f"{ts}_{safe}_{i:02d}.png"
        download_image(url, str(out))
        print(f"   [{i}/{len(urls)}] {out}")
    return [str(output_dir / f"{ts}_{safe}_{i:02d}.png") for i in range(1, len(urls) + 1)]


def list_models():
    url = f"{API_BASE}/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    for m in data.get("data", []):
        print(f"  {m['id']}")


def main():
    parser = argparse.ArgumentParser(description="SiliconFlow 图片生成")
    parser.add_argument("prompt", nargs="?", help="提示词")
    parser.add_argument("-n", "--num", type=int, default=1)
    parser.add_argument("-s", "--size", default=DEFAULT_SIZE)
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL)
    parser.add_argument("-f", "--file", default=None, help="批量模式")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--key", default=None)
    args = parser.parse_args()

    global API_KEY
    if args.key:
        API_KEY = args.key
    if args.list_models:
        list_models()
        return
    if args.file:
        generate_batch(args.file, args.output or "./output", size=args.size, model=args.model)
    elif args.prompt:
        if args.num > 1:
            generate_multi(args.prompt, args.num, args.output or ".", size=args.size, model=args.model)
        else:
            generate_one(args.prompt, args.output, size=args.size, model=args.model)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
