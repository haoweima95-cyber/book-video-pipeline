#!/usr/bin/env python3
"""
初始化向导：首次运行检查环境、配置 API、选择生图方案。
"""
import sys, os, subprocess, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PKG = Path(__file__).resolve().parent
CONFIG_PATH = PKG / "config.yaml"
EXAMPLE_PATH = PKG / "config.example.yaml"

# ── 检测函数 ──

def check_python():
    v = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    ok = sys.version_info >= (3, 10)
    return ok, v, "3.10"

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5, check=True,
                       **{"creationflags": 0x08000000} if sys.platform == "win32" else {})
        return True, "已安装"
    except Exception:
        return False, "未找到（下载地址: https://ffmpeg.org/download.html）"

def check_git():
    try:
        subprocess.run(["git", "--version"], capture_output=True, timeout=5, check=True,
                       **{"creationflags": 0x08000000} if sys.platform == "win32" else {})
        return True, "已安装"
    except Exception:
        return False, "未找到"

def check_gpu():
    """检测 GPU 和显存。"""
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            mem = torch.cuda.get_device_properties(0).total_mem // (1024**3)
            return True, f"{name} ({mem}GB VRAM)"
        else:
            return False, f"无 CUDA GPU（CPU 模式，TTS 会慢 3-5 倍，{torch.cuda.is_available()=}）"
    except ImportError:
        return None, "PyTorch 未安装，无法检测"

def check_cosyvoice_model():
    """检查本地 CosyVoice 模型是否已下载。"""
    from config import load
    cfg = load(CONFIG_PATH)
    if not cfg:
        return False, "config.yaml 未生成"
    model_dir = Path(os.path.expanduser(cfg["paths"]["cosyvoice_model"]))
    if model_dir.exists():
        # 粗略检查有模型文件
        files = list(model_dir.rglob("*.safetensors")) + list(model_dir.rglob("*.bin"))
        if files:
            return True, f"已下载 ({model_dir})"
        return False, "模型目录存在但无模型文件"
    return False, f"未下载（模型路径: {model_dir}）"

def check_disk_space():
    """检查工作盘可用空间（至少 10GB）。"""
    try:
        import shutil as sh
        work_dir = os.environ.get("USERPROFILE", "C:\\Users\\default")
        stat = sh.disk_usage(work_dir)
        free_gb = stat.free // (1024**3)
        ok = free_gb >= 10
        return ok, f"{free_gb}GB 可用（需要 ≥10GB）"
    except Exception:
        return None, "无法检测"

# ── 输出美化 ──

def box(title, lines):
    """打印一个框。"""
    width = 66
    print("╔" + "═" * width + "╗")
    print(f"║  {' ' * 2}{title:<{width-4}}║")
    print("╚" + "═" * width + "╝")
    for line in lines:
        print(line)
    print()

def step(label, ok, detail=""):
    mark = "✅" if ok else ("❌" if ok is False else "⚠️ ")
    d = f" — {detail}" if detail else ""
    print(f"  {mark} {label}{d}")

def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

# ── 输入辅助 ──

def ask(prompt, default=None):
    d = f" [默认: {default}]" if default else ""
    val = input(f"  > {prompt}{d}: ").strip()
    return val if val else default

def ask_choice(prompt, choices):
    print(f"  > {prompt}")
    for i, (label, desc) in enumerate(choices, 1):
        print(f"    [{i}] {label} — {desc}")
    while True:
        val = input("  > 请选择: ").strip()
        if val in [str(i) for i in range(1, len(choices)+1)]:
            return int(val) - 1
        print("  无效选择，请重试")

# ── 生成 config.yaml ──

def generate_config(image_cfg, tts_cfg, paths_cfg):
    """从模板生成 config.yaml。"""
    import yaml
    with open(EXAMPLE_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 路径
    if paths_cfg.get("project_root"):
        cfg["paths"]["project_root"] = paths_cfg["project_root"]
        cfg["paths"]["output_dir"] = paths_cfg["project_root"].rstrip("\\/") + "\\视频导出"

    # 生图
    cfg["image"]["provider"] = image_cfg["provider"]
    cfg["image"]["model"] = image_cfg.get("model", "Tongyi-MAI/Z-Image-Turbo")
    cfg["image"]["base_url"] = image_cfg.get("base_url", "https://api.siliconflow.cn/v1")
    cfg["image"]["api_key"] = image_cfg.get("api_key", "${IMAGE_API_KEY}")

    # TTS
    cfg["tts"]["provider"] = tts_cfg["provider"]
    if tts_cfg["provider"] == "cloud":
        cfg["tts"]["cloud"]["api_provider"] = tts_cfg.get("api_provider", "siliconflow")
        cfg["tts"]["cloud"]["base_url"] = tts_cfg.get("base_url", "https://api.siliconflow.cn/v1")
        cfg["tts"]["cloud"]["api_key"] = tts_cfg.get("api_key", "${IMAGE_API_KEY}")
        cfg["tts"]["cloud"]["voice"] = tts_cfg.get("voice", "FunAudioLLM/CosyVoice2-0.5B:alex")
    else:
        cfg["tts"]["local"]["voice"] = tts_cfg.get("voice", "默认音色")

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"\n✅ 配置已写入: {CONFIG_PATH}")

# ── 主流程 ──

def main():
    box("📖 读书视频生成流水线 v1.0", [
        "  从书名到成片，一条龙生成读书口播短视频。",
        "  欢迎！首次使用需要 2 分钟完成配置。",
    ])

    # ── 系统环境检查 ──
    section("1/4 系统环境检查")

    ok, v, req = check_python()
    step(f"Python {v}  (需要 ≥{req})", ok, f"当前 {v}")

    ok_ff, detail_ff = check_ffmpeg()
    step("ffmpeg", ok_ff, detail_ff)

    ok_git, detail_git = check_git()
    step("Git", ok_git, detail_git)

    ok_gpu, detail_gpu = check_gpu()
    step("CUDA GPU", ok_gpu if ok_gpu is not None else None, detail_gpu)

    ok_disk, detail_disk = check_disk_space()
    step("磁盘空间", ok_disk if ok_disk is not None else None, detail_disk)

    if not ok_ff or not ok_git:
        print("\n❌ 缺少必要组件，请先安装后再运行本向导。")
        input("按任意键退出...")
        sys.exit(1)

    # ── API Key ──
    section("2/4 生图 API 配置")

    print("  生图 API 用于将提示词转为图片。默认使用硅基流动，也可以接入其他")
    print("  OpenAI 兼容的 API（如 DeepSeek、OpenRouter）或本地模型。\n")

    choice = ask_choice("选择生图方案：", [
        ("硅基流动 (SiliconFlow)", "注册地址: https://cloud.siliconflow.cn，新用户有免费额度"),
        ("其他 OpenAI 兼容 API", "自填 base_url + model + key"),
        ("本地 Stable Diffusion / ComfyUI", "已有本地运行的生图服务，填 URL 即可"),
    ])

    image_cfg = {}
    api_key = ""

    if choice == 0:
        print("\n  硅基流动 API Key 获取方式：")
        print("    1. 访问 https://cloud.siliconflow.cn")
        print("    2. 注册后在「API 密钥」页面点击「新建 API 密钥」")
        print("    3. 复制密钥到此处\n")
        api_key = ask("请输入 SiliconFlow API Key")
        image_cfg = {
            "provider": "siliconflow",
            "model": "Tongyi-MAI/Z-Image-Turbo",
            "base_url": "https://api.siliconflow.cn/v1",
            "api_key": api_key,
        }
    elif choice == 1:
        print("\n  填写你的 OpenAI 兼容 API 信息：\n")
        api_key = ask("API Key")
        base_url = ask("API Base URL", "https://api.openai.com/v1")
        model = ask("模型名称", "dall-e-3")
        image_cfg = {
            "provider": "openai_compatible",
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
        }
    else:
        print("\n  填写本地生图服务的 URL：\n")
        base_url = ask("本地 API 地址", "http://127.0.0.1:7860")
        model = ask("模型名称", "sd_xl")
        image_cfg = {
            "provider": "local",
            "model": model,
            "base_url": base_url,
            "api_key": api_key or "",
        }

    # ── TTS ──
    section("3/4 配音方案")

    print("  配音支持两种方案：\n")
    print("    ☁️  云端（推荐）— 用刚才的 API key，8种预置音色，无需下载模型")
    print("    💻  本地 CosyVoice — 免费不限量，需下载 5.3GB 模型（约 20-30 分钟）\n")

    tts_choice = ask_choice("选择配音方案：", [
        ("☁️ 云端 API", "使用 SiliconFlow TTS 或其他兼容接口"),
        ("💻 本地 CosyVoice", "免费离线，需 ~5.3GB 模型 + ~5GB VRAM"),
    ])

    tts_cfg = {}
    if tts_choice == 0:
        print("\n  云端配音 API 配置（不填则与生图方案共用）：\n")
        tts_api_key = ask("API Key（回车复用生图 key）", api_key) or api_key
        tts_base = ask("Base URL（回车复用 SiliconFlow）", "https://api.siliconflow.cn/v1")
        print("\n  预置音色：alex(沉稳男)、bella(热情女)、charles(磁性男)、claire(温柔女)等")
        tts_voice = ask("音色名称", "FunAudioLLM/CosyVoice2-0.5B:alex")
        tts_cfg = {
            "provider": "cloud",
            "api_provider": "siliconflow" if "siliconflow" in tts_base else "openai_compatible",
            "base_url": tts_base,
            "api_key": tts_api_key,
            "voice": tts_voice,
        }
    else:
        # 检查本地 CosyVoice 模型
        cosy_ok, cosy_detail = check_cosyvoice_model()
        if not cosy_ok:
            print(f"\n  ⚠️  CosyVoice 模型 {cosy_detail}")
            print("  需要下载吗？（会在下一步 setup 中完成）")
            input("  按回车继续...")
        tts_cfg = {
            "provider": "local",
            "voice": "默认音色",
        }

    # ── 工作目录 ──
    section("4/4 工作目录")
    default_dir = "D:\\自媒体"
    project_root = ask(f"工作目录", default_dir) or default_dir

    # 写入配置
    generate_config(image_cfg, tts_cfg, {"project_root": project_root})

    # 设置环境变量提示
    print(f"\n{'─'*60}")
    print("  📌 建议设置系统环境变量（可选）：")
    print(f"     setx IMAGE_API_KEY \"{api_key}\"")
    print(f"{'─'*60}")

    # 检查是否需要下载 CosyVoice
    if tts_choice == 1 and not cosy_ok:
        section("附加：安装本地 TTS 模型")
        print("  运行 setup.bat 下载 CosyVoice 模型...")
        setup_path = PKG / "setup.bat"
        if setup_path.exists():
            subprocess.call([str(setup_path)], shell=True)

    box("✅ 配置完成！", [
        "  现在可以在 Claude Code 中输入:",
        "",
        "    /book-video-pipeline start <书名>",
        "",
        "  启动你的第一个读书视频制作！",
    ])

    input("按任意键退出...")

if __name__ == "__main__":
    main()
