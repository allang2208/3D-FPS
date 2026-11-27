"""Build the self-contained Google Colab notebook `colab_audio_worker.ipynb`
from `colab_audio_server.py` so the server source stays single-sourced in Git.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER_PY = HERE / "colab_audio_server.py"
NOTEBOOK_OUT = HERE / "colab_audio_worker.ipynb"


def md_cell(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in text.rstrip("\n").splitlines()],
    }


def code_cell(code: str, form_view: bool = False) -> dict:
    meta = {"cellView": "form"} if form_view else {}
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": meta,
        "outputs": [],
        "source": [line + "\n" for line in code.rstrip("\n").splitlines()],
    }


def build() -> None:
    server_src = SERVER_PY.read_text(encoding="utf-8")

    cells = [
        md_cell(
            """# FPSGAME Colab Ultra Audio Studio (自动音频工作流服务端)

适用于 **Google Colab Ultra / Pro+ (推荐 A100 / H100 / L4)**。

### 使用方式（一键启动）
1. 菜单栏选择 **代码执行程序 (Runtime) -> 更改运行时类型 -> GPU (A100 / H100 / L4)**（Ultra 会员可同时开启「后台执行」）。
2. 点击 **全部运行 (Run all)**。
3. 首次运行挂载 Google Drive 后，会自动在 `MyDrive/FPSGAME_AudioBridge/` 生成鉴权 Token 与实时隧道地址 `session.json`。
4. 本地 Agent 会自动通过 Google Drive 读取最新隧道地址并直连；若隧道偶发波动，自动回退到 Drive 队列，**无需手动复制 URL**。

### 内置引擎一览
- **SFX / 环境音**：`tangoflux`（默认，44.1kHz 立体声 Apache-2.0）、`mmaudio`（支持动画 MP4/GIF 同步 Foley，MIT）、`stable_audio`（可选，需在 Colab 左侧钥匙图标 Secrets 配置 `HF_TOKEN`）、`audioldm2`（零依赖兜底）
- **BGM 配乐**：`acestep`（默认，48kHz 立体声 Apache-2.0）、`musicgen`（立体声兜底）
- **NPC 语音**：`kokoro`（默认，中/英文 24kHz Apache-2.0）、`f5tts`（可选，中/英文零样本音色克隆 MIT）
"""
        ),
        code_cell(
            """#@title 1. 检查 GPU、挂载 Google Drive 并初始化持久化 Token
import os, secrets, subprocess, torch
from pathlib import Path
from google.colab import drive

drive.mount('/content/drive', force_remount=False)

BRIDGE_DIR = Path('/content/drive/MyDrive/FPSGAME_AudioBridge')
for sub in ('config', 'inbox', 'outbox', 'processed', 'failed', 'refs'):
    (BRIDGE_DIR / sub).mkdir(parents=True, exist_ok=True)

TOKEN_FILE = BRIDGE_DIR / 'config' / 'token.txt'
if TOKEN_FILE.exists() and TOKEN_FILE.read_text(encoding='utf-8').strip():
    WORKER_TOKEN = TOKEN_FILE.read_text(encoding='utf-8').strip()
else:
    WORKER_TOKEN = secrets.token_urlsafe(32)
    TOKEN_FILE.write_text(WORKER_TOKEN, encoding='utf-8')

os.environ['AUDIO_WORKER_TOKEN'] = WORKER_TOKEN
os.environ['DRIVE_BRIDGE_DIR'] = str(BRIDGE_DIR)
os.environ['AUDIO_WORK_DIR'] = '/content/audio_worker_jobs'

# Optional: pull HF_TOKEN from Colab Secrets (only needed for gated Stable Audio Open 1.0)
try:
    from google.colab import userdata
    hf_tok = userdata.get('HF_TOKEN')
    if hf_tok:
        os.environ['HF_TOKEN'] = hf_tok.strip()
        print('HF_TOKEN loaded from Colab Secrets (Stable Audio Open enabled).')
except Exception:
    pass

CACHE_MODELS_ON_DRIVE = False #@param {type:"boolean"}
if CACHE_MODELS_ON_DRIVE:
    hf_cache = BRIDGE_DIR / 'hf_cache'
    hf_cache.mkdir(parents=True, exist_ok=True)
    os.environ['HF_HOME'] = str(hf_cache)
    print(f'HF_HOME -> {hf_cache}')

if torch.cuda.is_available():
    p = torch.cuda.get_device_properties(0)
    print(f'GPU Ready: {p.name} | VRAM: {p.total_memory / (1024**3):.1f} GB | BF16: {p.major >= 8}')
    if 'T4' in p.name:
        print('TIP (Ultra): 当前为默认 T4，建议在菜单「代码执行程序 -> 更改运行时类型」切到 A100 / L4 以获得 3-5x 速度与多模型常驻显存。')
else:
    print('WARNING: No GPU detected! Switch Runtime -> Change runtime type -> A100 / L4 GPU.')

print(f'Drive Bridge Ready: {BRIDGE_DIR}')
print(f'Token stored securely in: {TOKEN_FILE} (prefix: {WORKER_TOKEN[:6]}...)')
""",
            form_view=True,
        ),
        code_cell(
            r"""#@title 2. 按需安装音频引擎与 Cloudflare Tunnel（保留 Colab 原生 CUDA PyTorch）
import subprocess, sys, urllib.request, os, stat

INSTALL_TANGOFLUX = True #@param {type:"boolean"}
INSTALL_MMAUDIO = True #@param {type:"boolean"}
INSTALL_ACESTEP = True #@param {type:"boolean"}
INSTALL_KOKORO = True #@param {type:"boolean"}
INSTALL_F5TTS = False #@param {type:"boolean"}

def run_cmd(cmd, check=True):
    print('>>', cmd, flush=True)
    res = subprocess.run(cmd, shell=True)
    if check and res.returncode != 0:
        raise RuntimeError(f'Command failed ({res.returncode}): {cmd}')
    return res.returncode

# Core server dependencies (pin transformers<5.0 so AudioLDM2/TangoFlux/MusicGen stay 100% compatible on Colab Python 3.13)
run_cmd('pip install -q fastapi "uvicorn[standard]" python-multipart soundfile scipy numpy httpx accelerate diffusers "transformers>=4.46,<5.0" datasets pyyaml einops safetensors sentencepiece protobuf')

if INSTALL_TANGOFLUX:
    # Clone + --no-deps editable install avoids TangoFlux's outdated pinned torch/diffusers constraints on Colab Python 3.12/3.13
    run_cmd('pip install -q torchlibrosa librosa', check=False)
    if not os.path.exists('/content/TangoFlux'):
        run_cmd('git clone -q https://github.com/declare-lab/TangoFlux.git /content/TangoFlux', check=False)
    run_cmd('pip install -q --no-deps -e /content/TangoFlux', check=False)

if INSTALL_MMAUDIO:
    run_cmd('pip install -q open_clip_torch av librosa timm colorlog hydra-core hydra_colorlog torchdiffeq tensordict nitrous-ema python-dotenv', check=False)
    if not os.path.exists('/content/MMAudio'):
        run_cmd('git clone -q https://github.com/hkchengrex/MMAudio.git /content/MMAudio', check=False)
    run_cmd('pip install -q --no-deps -e /content/MMAudio', check=False)

if INSTALL_ACESTEP:
    run_cmd('pip install -q loguru pypinyin hangul-romanize num2words', check=False)
    run_cmd('pip install -q --no-deps git+https://github.com/ace-step/ACE-Step.git', check=False)

if INSTALL_KOKORO:
    run_cmd('apt-get -qq -y install espeak-ng > /dev/null 2>&1', check=False)
    # Install kokoro and misaki[zh] in separate steps to avoid pip resolver conflicts
    run_cmd('pip install -q "kokoro>=0.9.4" soundfile loguru', check=False)
    if run_cmd('pip install -q "misaki[zh]"', check=False) != 0:
        run_cmd('pip install -q --no-deps kokoro misaki && pip install -q pypinyin jieba cn2an ordered-set', check=False)

if INSTALL_F5TTS:
    run_cmd('pip install -q f5-tts', check=False)

# Install cloudflared static binary (no account required for quick tunnels)
cf_bin = '/usr/local/bin/cloudflared'
if not os.path.exists(cf_bin):
    print('Downloading cloudflared...', flush=True)
    urllib.request.urlretrieve(
        'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64',
        cf_bin,
    )
    os.chmod(cf_bin, os.stat(cf_bin).st_mode | stat.S_IEXEC)

print('\n=== Engine Import Verification (Real Imports) ===')
checks = [
    ('tangoflux (SFX)', 'from tangoflux import TangoFluxInference'),
    ('mmaudio (Video/SFX)', 'from mmaudio.eval_utils import all_model_cfg'),
    ('acestep (BGM)', 'import acestep'),
    ('kokoro (CN/EN Voice)', 'from kokoro import KPipeline'),
    ('f5tts (Voice Clone)', 'from f5_tts.api import F5TTS'),
    ('diffusers (audioldm2/stable_audio)', 'from diffusers import AudioLDM2Pipeline'),
    ('transformers (musicgen)', 'from transformers import MusicgenForConditionalGeneration'),
]
for label, stmt in checks:
    try:
        exec(stmt, {})
        print(f'  [OK]   {label}')
    except Exception as exc:
        print(f'  [MISS] {label} -> {type(exc).__name__}: {exc}')
print('Dependencies & cloudflared ready.')
""",
            form_view=True,
        ),
        code_cell(
            "%%writefile /content/colab_audio_server.py\n" + server_src,
            form_view=False,
        ),
        code_cell(
            r"""#@title 3. 启动音频 Worker 服务 + 自动重连 HTTPS 隧道 + Drive 队列守护
import os, re, shutil, subprocess, sys, threading, time, urllib.request
from pathlib import Path

PORT = 8765 #@param {type:"integer"}
PRELOAD_ENGINES = "mmaudio" #@param {type:"string"}
ENABLE_CLOUDFLARE_TUNNEL = True #@param {type:"boolean"}

if 'AUDIO_WORKER_TOKEN' not in os.environ:
    raise RuntimeError('AUDIO_WORKER_TOKEN missing — please run Cell 1 (Mount Drive & Token) first!')

TUNNEL_FILE = Path('/content/audio_worker_tunnel_url.txt')
LOG_FILE = Path('/content/audio_worker_server.log')
BRIDGE_DIR = Path(os.environ.get('DRIVE_BRIDGE_DIR', '/content/drive/MyDrive/FPSGAME_AudioBridge'))
os.environ['TUNNEL_URL_FILE'] = str(TUNNEL_FILE)
TUNNEL_FILE.unlink(missing_ok=True)

# Clean up any prior uvicorn/cloudflared from an earlier cell run
subprocess.run('pkill -f "colab_audio_server:app" || true', shell=True)
subprocess.run('pkill -f "cloudflared tunnel" || true', shell=True)
time.sleep(1.0)

# Launch FastAPI worker via current Python interpreter
server_log = open(LOG_FILE, 'w', encoding='utf-8')
server_proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'colab_audio_server:app', '--host', '127.0.0.1', '--port', str(PORT), '--log-level', 'info'],
    cwd='/content',
    stdout=server_log,
    stderr=subprocess.STDOUT,
    env=os.environ.copy(),
)

# Wait up to 60s for local FastAPI health, aborting early with full log if uvicorn exits
for _ in range(120):
    if server_proc.poll() is not None:
        server_log.flush()
        err_text = LOG_FILE.read_text(encoding='utf-8', errors='replace') if LOG_FILE.exists() else '(no log)'
        if BRIDGE_DIR.exists():
            (BRIDGE_DIR / 'last_error.log').write_text(err_text, encoding='utf-8')
        print('=== FastAPI startup log ===\n' + err_text[-3000:], flush=True)
        raise RuntimeError(f'FastAPI worker exited with code {server_proc.returncode}')
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/v1/ping', timeout=2) as r:
            if r.status == 200:
                break
    except Exception:
        time.sleep(0.5)
else:
    server_log.flush()
    err_text = LOG_FILE.read_text(encoding='utf-8', errors='replace') if LOG_FILE.exists() else '(no log)'
    if BRIDGE_DIR.exists():
        (BRIDGE_DIR / 'last_error.log').write_text(err_text, encoding='utf-8')
    print('=== FastAPI startup log ===\n' + err_text[-3000:], flush=True)
    raise RuntimeError('FastAPI worker timed out starting (>60s).')

print(f'Local FastAPI worker online at http://127.0.0.1:{PORT}', flush=True)

# Start Cloudflare Quick Tunnel BEFORE model preload so URL is immediately live & synced
stop_flag = False
url_re = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')

def run_tunnel_forever():
    while not stop_flag:
        proc = subprocess.Popen(
            ['/usr/local/bin/cloudflared', 'tunnel', '--url', f'http://127.0.0.1:{PORT}', '--no-autoupdate'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        announced = False
        for line in proc.stdout:
            m = url_re.search(line)
            if m and not announced:
                url = m.group(0)
                TUNNEL_FILE.write_text(url, encoding='utf-8')
                announced = True
                print('=' * 72, flush=True)
                print(f'COLAB AUDIO TUNNEL READY: {url}', flush=True)
                print('Drive session.json will sync this URL automatically within 20s.', flush=True)
                print('=' * 72, flush=True)
        proc.wait()
        if not stop_flag:
            print('[Tunnel] cloudflared exited, reconnecting in 5s...', flush=True)
            time.sleep(5)

if ENABLE_CLOUDFLARE_TUNNEL:
    threading.Thread(target=run_tunnel_forever, daemon=True).start()

# Optional background pre-warm so tunnel prints immediately without blocking
def preload_worker():
    token = os.environ['AUDIO_WORKER_TOKEN']
    for eng in [e.strip() for e in PRELOAD_ENGINES.split(',') if e.strip()]:
        try:
            print(f'Preloading engine in background: {eng}...', flush=True)
            req = urllib.request.Request(
                f'http://127.0.0.1:{PORT}/v1/engines/{eng}/load',
                method='POST',
                headers={'Authorization': f'Bearer {token}'},
            )
            with urllib.request.urlopen(req, timeout=600) as r:
                print(f'Preloaded {eng} OK:', r.read().decode('utf-8'), flush=True)
        except Exception as exc:
            print(f'Preload {eng} skipped/warn: {exc}', flush=True)

if PRELOAD_ENGINES.strip():
    threading.Thread(target=preload_worker, daemon=True).start()

print('Worker is running (HTTP Tunnel + Google Drive Queue). Keep this cell running.', flush=True)
try:
    while server_proc.poll() is None:
        time.sleep(10)
except KeyboardInterrupt:
    stop_flag = True
    server_proc.terminate()
    print('Worker stopped.')
""",
            form_view=True,
        ),
    ]

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "colab": {
                "provenance": [],
                "gpuType": "A100",
                "machine_shape": "hm",
            },
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3",
            },
            "language_info": {
                "name": "python",
            },
            "accelerator": "GPU",
        },
        "cells": cells,
    }

    # Verify every generated Python code cell parses cleanly before writing
    for idx, cell in enumerate(cells):
        if cell["cell_type"] != "code":
            continue
        code_src = "".join(cell["source"])
        if code_src.startswith("%%writefile"):
            code_src = "\n".join(code_src.splitlines()[1:])
        ast.parse(code_src, filename=f"colab_audio_worker.ipynb:cell_{idx}")

    NOTEBOOK_OUT.write_text(json.dumps(nb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated {NOTEBOOK_OUT} ({NOTEBOOK_OUT.stat().st_size} bytes, all code cells AST-verified)")


if __name__ == "__main__":
    build()
