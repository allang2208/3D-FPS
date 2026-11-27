"""FPSGAME Local Client for the Colab Ultra Audio Worker.

Supports dual transport:
  1. Direct HTTPS (Cloudflare Quick Tunnel -> FastAPI worker, via local proxy)
  2. Google Drive Queue fallback (via Antigravity `gdrive` CLI)

Automatically discovers the active Colab tunnel URL and Bearer token from
Google Drive (`FPSGAME_AudioBridge/session.json` + `config/token.txt`), storing
credentials ONLY in `%LOCALAPPDATA%/FPSGAME/colab_audio.json` (never inside the repo).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np
import soundfile as sf
from scipy import signal

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NOTEBOOK = Path(__file__).resolve().parent / "colab_audio_worker.ipynb"
DEFAULT_PROXY = "http://127.0.0.1:7897"
DRIVE_ROOT_NAME = "FPSGAME_AudioBridge"


def local_cache_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".config"))
    return base / "FPSGAME" / "colab_audio.json"


def load_local_cache() -> Dict[str, Any]:
    p = local_cache_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_local_cache(data: Dict[str, Any]) -> None:
    p = local_cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_proxy(explicit_proxy: Optional[str]) -> Optional[str]:
    if explicit_proxy is not None:
        return explicit_proxy.strip() or None
    for env_key in ("COLAB_AUDIO_PROXY", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        val = os.environ.get(env_key, "").strip()
        if val:
            return val
    # Auto-probe FPSGAME default local proxy 127.0.0.1:7897
    try:
        with socket.create_connection(("127.0.0.1", 7897), timeout=0.5):
            return DEFAULT_PROXY
    except OSError:
        return None


def make_http_client(proxy: Optional[str], timeout: float = 60.0) -> httpx.Client:
    kwargs: Dict[str, Any] = {"timeout": timeout, "follow_redirects": True}
    if proxy:
        kwargs["proxy"] = proxy
    return httpx.Client(**kwargs)


# ---------------------------------------------------------------------------
# gdrive CLI Bridge Helpers
# ---------------------------------------------------------------------------


def find_gdrive_cmd() -> Optional[str]:
    exe = shutil.which("gdrive")
    if exe:
        return exe
    fallback = Path.home() / ".gemini" / "config" / "plugins" / "gdrive" / "skills" / "gdrive" / "scripts" / "gdrive.cmd"
    if fallback.exists():
        return str(fallback)
    return None


def run_gdrive(args: List[str], check: bool = True, retries: int = 4) -> Tuple[int, str, str]:
    cmd = find_gdrive_cmd()
    if not cmd:
        raise RuntimeError("gdrive CLI not found. Install/enable the Google Drive plugin or pass --url and --token.")
    last_proc = None
    for attempt in range(retries):
        proc = subprocess.run([cmd, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        last_proc = proc
        if proc.returncode == 0:
            return proc.returncode, proc.stdout, proc.stderr
        combined = f"{proc.stderr}\n{proc.stdout}"
        if ("RATE_LIMIT_EXCEEDED" in combined or "rateLimitExceeded" in combined or "429" in combined) and attempt < retries - 1:
            delay = 2.0 * (2**attempt)
            print(f"[gdrive] Rate limited, retrying in {delay:.0f}s ({attempt + 1}/{retries - 1})...", flush=True)
            time.sleep(delay)
            continue
        break
    assert last_proc is not None
    if check and last_proc.returncode != 0:
        raise RuntimeError(
            f"gdrive {' '.join(args)} failed ({last_proc.returncode}): {last_proc.stderr.strip() or last_proc.stdout.strip()}"
        )
    return last_proc.returncode, last_proc.stdout, last_proc.stderr


def gdrive_json(args: List[str]) -> Any:
    _rc, out, _err = run_gdrive(["--json", *args], check=True)
    return json.loads(out) if out.strip() else {}


def gdrive_extract_items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("files", "items", "results", "data"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def gdrive_find_folder(name: str, parent_id: Optional[str] = None, create_if_missing: bool = False) -> Optional[str]:
    if parent_id:
        data = gdrive_json(["readonly", "ls", parent_id, "--max", "200"])
        for item in gdrive_extract_items(data):
            if item.get("name") == name and "folder" in str(item.get("mimeType", "")):
                return item["id"]
    else:
        data = gdrive_json(["readonly", "search", "--name-exact", name, "--type", "folder"])
        items = gdrive_extract_items(data)
        if items:
            return items[0]["id"]
    if create_if_missing:
        cmd = ["mutate", "mkdir", name]
        if parent_id:
            cmd += ["--parent", parent_id]
        _rc, out, _err = run_gdrive(cmd, check=True)
        try:
            created = json.loads(out)
            if isinstance(created, dict) and created.get("id"):
                return created["id"]
        except Exception:
            pass
        # Re-query via readonly JSON command (gdrive --json applies to read commands)
        return gdrive_find_folder(name, parent_id=parent_id, create_if_missing=False)
    return None


def gdrive_find_child(parent_id: str, name: str) -> Optional[Dict[str, Any]]:
    data = gdrive_json(["readonly", "ls", parent_id, "--max", "200"])
    for item in gdrive_extract_items(data):
        if item.get("name") == name:
            return item
    return None


def gdrive_sync_session() -> Dict[str, Any]:
    root_id = gdrive_find_folder(DRIVE_ROOT_NAME, create_if_missing=False)
    if not root_id:
        raise RuntimeError(
            f"Google Drive folder '{DRIVE_ROOT_NAME}' not found. Run colab_audio_worker.ipynb in Colab first."
        )
    cache = load_local_cache()
    cache["drive_root_id"] = root_id

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        sess_item = gdrive_find_child(root_id, "session.json")
        if sess_item:
            sess_path = tmp / "session.json"
            run_gdrive(["readonly", "download", sess_item["id"], "--out", str(sess_path)])
            sess_data = json.loads(sess_path.read_text(encoding="utf-8"))
            cache["session"] = sess_data
            if sess_data.get("tunnel_url"):
                cache["url"] = sess_data["tunnel_url"]

        cfg_id = gdrive_find_folder("config", parent_id=root_id, create_if_missing=False)
        if cfg_id:
            tok_item = gdrive_find_child(cfg_id, "token.txt")
            if tok_item:
                tok_path = tmp / "token.txt"
                run_gdrive(["readonly", "download", tok_item["id"], "--out", str(tok_path)])
                tok = tok_path.read_text(encoding="utf-8").strip()
                if tok:
                    cache["token"] = tok

    cache["synced_at"] = utc_now_iso()
    save_local_cache(cache)
    return cache


def resolve_connection(args: argparse.Namespace, allow_drive_sync: bool = True) -> Tuple[Optional[str], Optional[str]]:
    cache = load_local_cache()
    url = getattr(args, "url", None) or os.environ.get("COLAB_AUDIO_URL") or cache.get("url")
    token = getattr(args, "token", None) or os.environ.get("COLAB_AUDIO_TOKEN") or cache.get("token")
    if (not url or not token) and allow_drive_sync and find_gdrive_cmd():
        try:
            cache = gdrive_sync_session()
            url = url or cache.get("url")
            token = token or cache.get("token")
        except Exception:
            pass
    if url:
        url = url.rstrip("/")
    return url, token


# ---------------------------------------------------------------------------
# Objective Audio Analysis (Pre-Audition Screening, Never Replaces Listening)
# ---------------------------------------------------------------------------


def analyze_wav(path: Path) -> Dict[str, Any]:
    data, sr = sf.read(str(path), always_2d=True)
    mono = data.mean(axis=1).astype(np.float64)
    n = len(mono)
    duration = n / float(sr) if sr > 0 else 0.0
    abs_sig = np.abs(mono)
    peak = float(np.max(abs_sig)) if n else 0.0
    rms = float(np.sqrt(np.mean(mono * mono))) if n else 0.0
    peak_dbfs = round(20.0 * np.log10(max(peak, 1e-9)), 2)
    rms_dbfs = round(20.0 * np.log10(max(rms, 1e-9)), 2)

    # Leading silence before crossing -42 dB relative to peak
    thresh = max(peak * (10.0 ** (-42.0 / 20.0)), 1e-5)
    above = np.flatnonzero(abs_sig >= thresh)
    onset_idx = int(above[0]) if len(above) else 0
    lead_silence_ms = round((onset_idx / float(sr)) * 1000.0, 2) if sr else 0.0

    # Envelope 10% -> 90% attack time around peak after onset
    win = max(1, int(round(sr * 0.002)))
    env = np.sqrt(np.convolve(mono * mono, np.ones(win) / win, mode="same"))
    env_max = float(np.max(env)) if n else 0.0
    if env_max > 1e-7:
        i10 = np.flatnonzero(env >= 0.1 * env_max)
        i90 = np.flatnonzero(env >= 0.9 * env_max)
        if len(i10) and len(i90):
            attack_ms = round(max(0.0, (int(i90[0]) - int(i10[0])) / float(sr) * 1000.0), 2)
        else:
            attack_ms = 0.0
    else:
        attack_ms = 0.0

    # First 30ms energy ratio from onset (tightness metric per weapon-audio.md)
    total_e = float(np.sum(mono * mono)) + 1e-12
    seg_end = min(n, onset_idx + int(round(sr * 0.030)))
    first30_e = float(np.sum(mono[onset_idx:seg_end] ** 2))
    first_30ms_pct = round(100.0 * first30_e / total_e, 1)

    # High-frequency (>1.5kHz) energy ratio
    if n >= 256 and sr > 3200:
        freqs, psd = signal.welch(mono, fs=sr, nperseg=min(2048, n))
        hf_ratio = float(np.sum(psd[freqs >= 1500.0]) / (np.sum(psd) + 1e-12))
        hf_pct = round(100.0 * hf_ratio, 1)
    else:
        hf_pct = 0.0

    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sample_rate": int(sr),
        "channels": int(data.shape[1]),
        "duration_sec": round(duration, 4),
        "peak_dbfs": peak_dbfs,
        "rms_dbfs": rms_dbfs,
        "lead_silence_ms": lead_silence_ms,
        "attack_10_90_ms": attack_ms,
        "first_30ms_energy_pct": first_30ms_pct,
        "hf_above_1500hz_pct": hf_pct,
        "sha256": sha256_file(path),
    }


# ---------------------------------------------------------------------------
# Transports: HTTP & Google Drive Queue
# ---------------------------------------------------------------------------


class ColabJobError(RuntimeError):
    """Raised when Colab received the job and execution itself failed (do not failover transport)."""


def http_check_health(url: str, token: str, proxy: Optional[str]) -> Dict[str, Any]:
    with make_http_client(proxy, timeout=12.0) as client:
        r = client.get(f"{url}/v1/health", headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        return r.json()


def http_run_job(
    url: str,
    token: str,
    proxy: Optional[str],
    payload: Dict[str, Any],
    out_dir: Path,
    ref_video: Optional[Path],
    ref_audio: Optional[Path],
    poll_sec: float,
    timeout_sec: float,
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    with make_http_client(proxy, timeout=120.0) as client:
        if ref_video or ref_audio:
            files_arg: Dict[str, Any] = {}
            opened = []
            try:
                if ref_video:
                    fv = ref_video.open("rb")
                    opened.append(fv)
                    files_arg["ref_video"] = (ref_video.name, fv, "application/octet-stream")
                if ref_audio:
                    fa = ref_audio.open("rb")
                    opened.append(fa)
                    files_arg["ref_audio"] = (ref_audio.name, fa, "application/octet-stream")
                r = client.post(
                    f"{url}/v1/jobs",
                    headers=headers,
                    data={"payload_json": json.dumps(payload, ensure_ascii=False)},
                    files=files_arg,
                )
            finally:
                for f in opened:
                    f.close()
        else:
            r = client.post(f"{url}/v1/jobs", headers=headers, json=payload)
        r.raise_for_status()
        job = r.json()
        jid = job["job_id"]
        print(f"[HTTP] Submitted job {jid} (engine={payload['engine']}, variants={payload['num_variants']})", flush=True)

        deadline = time.time() + timeout_sec
        last_completed = -1
        while time.time() < deadline:
            pr = client.get(f"{url}/v1/jobs/{jid}", headers=headers)
            pr.raise_for_status()
            state = pr.json()
            comp = int(state.get("completed_variants", 0))
            if comp != last_completed:
                print(f"[HTTP] {jid}: status={state['status']} ({comp}/{state['num_variants']})", flush=True)
                last_completed = comp
            if state["status"] == "succeeded":
                cand_dir = out_dir / "Candidates"
                cand_dir.mkdir(parents=True, exist_ok=True)
                for fmeta in state.get("files", []):
                    fname = fmeta["filename"]
                    fr = client.get(f"{url}/v1/jobs/{jid}/files/{fname}", headers=headers, timeout=180.0)
                    fr.raise_for_status()
                    (cand_dir / fname).write_bytes(fr.content)
                return state
            if state["status"] == "failed":
                raise ColabJobError(f"Colab job {jid} failed:\n{state.get('error')}")
            time.sleep(poll_sec)
        raise TimeoutError(f"Colab job {jid} timed out after {timeout_sec}s")


def drive_run_job(
    payload: Dict[str, Any],
    out_dir: Path,
    ref_video: Optional[Path],
    ref_audio: Optional[Path],
    poll_sec: float,
    timeout_sec: float,
) -> Dict[str, Any]:
    root_id = gdrive_find_folder(DRIVE_ROOT_NAME, create_if_missing=False)
    if not root_id:
        raise RuntimeError(f"Drive folder '{DRIVE_ROOT_NAME}' not found. Start Colab notebook first.")
    inbox_id = gdrive_find_folder("inbox", parent_id=root_id, create_if_missing=True)
    outbox_id = gdrive_find_folder("outbox", parent_id=root_id, create_if_missing=True)
    refs_id = gdrive_find_folder("refs", parent_id=root_id, create_if_missing=True)
    assert inbox_id and outbox_id and refs_id

    jid = f"drv_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    job_payload = dict(payload)
    job_payload["job_id"] = jid
    job_payload["mirror_to_drive"] = True

    if ref_video or ref_audio:
        jref_id = gdrive_find_folder(jid, parent_id=refs_id, create_if_missing=True)
        assert jref_id
        if ref_video:
            run_gdrive(["mutate", "upload", str(ref_video), "--parent", jref_id])
            job_payload["ref_video_drive_rel"] = f"refs/{jid}/{ref_video.name}"
        if ref_audio:
            run_gdrive(["mutate", "upload", str(ref_audio), "--parent", jref_id])
            job_payload["ref_audio_drive_rel"] = f"refs/{jid}/{ref_audio.name}"

    with tempfile.TemporaryDirectory() as td:
        req_file = Path(td) / f"{jid}.json"
        req_file.write_text(json.dumps(job_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        run_gdrive(["mutate", "upload", str(req_file), "--parent", inbox_id])
    print(f"[DriveQueue] Uploaded job {jid} to {DRIVE_ROOT_NAME}/inbox/", flush=True)

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        job_out_id = gdrive_find_folder(jid, parent_id=outbox_id, create_if_missing=False)
        if job_out_id:
            res_item = gdrive_find_child(job_out_id, "result.json")
            if res_item:
                with tempfile.TemporaryDirectory() as td:
                    res_local = Path(td) / "result.json"
                    run_gdrive(["readonly", "download", res_item["id"], "--out", str(res_local)])
                    state = json.loads(res_local.read_text(encoding="utf-8"))
                if state["status"] == "failed":
                    raise RuntimeError(f"Drive job {jid} failed: {state.get('error')}")
                if state["status"] == "succeeded":
                    cand_dir = out_dir / "Candidates"
                    cand_dir.mkdir(parents=True, exist_ok=True)
                    listing = gdrive_extract_items(gdrive_json(["readonly", "ls", job_out_id, "--max", "100"]))
                    by_name = {it["name"]: it["id"] for it in listing}
                    for fmeta in state.get("files", []):
                        fname = fmeta["filename"]
                        if fname in by_name:
                            run_gdrive(["readonly", "download", by_name[fname], "--out", str(cand_dir / fname)])
                    return state
        time.sleep(max(3.0, poll_sec))
    raise TimeoutError(f"Drive job {jid} timed out after {timeout_sec}s")


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------


def cmd_sync_session(_args: argparse.Namespace) -> None:
    cache = gdrive_sync_session()
    safe_view = {
        "drive_root_id": cache.get("drive_root_id"),
        "url": cache.get("url"),
        "token_present": bool(cache.get("token")),
        "synced_at": cache.get("synced_at"),
        "session": cache.get("session"),
    }
    print(json.dumps(safe_view, indent=2, ensure_ascii=False))


def cmd_deploy_notebook(args: argparse.Namespace) -> None:
    nb_path = Path(args.notebook).resolve()
    if not nb_path.exists():
        raise SystemExit(f"Notebook not found: {nb_path}")
    mime = "application/vnd.google.colaboratory"
    cache = load_local_cache()
    cached_fid = cache.get("notebook_file_id")
    if cached_fid and not getattr(args, "force_lookup", False):
        rc, _out, _err = run_gdrive(["mutate", "update", cached_fid, str(nb_path), "--mime-type", mime], check=False)
        if rc == 0:
            colab_url = f"https://colab.research.google.com/drive/{cached_fid}"
            print(json.dumps({"action": "updated", "file_id": cached_fid, "drive_folder": DRIVE_ROOT_NAME, "colab_url": colab_url}, indent=2))
            return
    root_id = cache.get("drive_root_id") or gdrive_find_folder(DRIVE_ROOT_NAME, create_if_missing=True)
    assert root_id
    cache["drive_root_id"] = root_id
    existing = gdrive_find_child(root_id, nb_path.name)
    if existing:
        run_gdrive(["mutate", "update", existing["id"], str(nb_path), "--mime-type", mime])
        fid = existing["id"]
        action = "updated"
    else:
        _rc, out, _err = run_gdrive(["mutate", "upload", str(nb_path), "--parent", root_id, "--mime-type", mime])
        fid = ""
        try:
            res = json.loads(out)
            if isinstance(res, dict) and res.get("id"):
                fid = str(res["id"])
        except Exception:
            pass
        if not fid:
            found = gdrive_find_child(root_id, nb_path.name)
            fid = found["id"] if found else ""
        action = "uploaded"
    if fid:
        cache["notebook_file_id"] = fid
        save_local_cache(cache)
    colab_url = f"https://colab.research.google.com/drive/{fid}" if fid else ""
    print(json.dumps({"action": action, "file_id": fid, "drive_folder": DRIVE_ROOT_NAME, "colab_url": colab_url}, indent=2))


def cmd_health(args: argparse.Namespace) -> None:
    proxy = detect_proxy(args.proxy)
    url, token = resolve_connection(args, allow_drive_sync=True)
    if not url or not token:
        raise SystemExit("No Colab URL/token resolved. Start Colab notebook, or pass --url and --token, or run sync-session.")
    try:
        info = http_check_health(url, token, proxy)
        print(json.dumps({"transport": "http", "url": url, "proxy": proxy, "health": info}, indent=2, ensure_ascii=False))
    except Exception as exc:
        # Refresh session from Drive once in case tunnel rotated
        if find_gdrive_cmd():
            try:
                cache = gdrive_sync_session()
                new_url = cache.get("url")
                new_tok = cache.get("token") or token
                if new_url and new_tok and new_url != url:
                    info = http_check_health(new_url, new_tok, proxy)
                    print(json.dumps({"transport": "http", "url": new_url, "proxy": proxy, "health": info}, indent=2, ensure_ascii=False))
                    return
            except Exception:
                pass
        raise SystemExit(f"Health check failed for {url} (proxy={proxy}): {exc}")


def cmd_engines(args: argparse.Namespace) -> None:
    proxy = detect_proxy(args.proxy)
    url, token = resolve_connection(args, allow_drive_sync=True)
    if not url or not token:
        raise SystemExit("No Colab URL/token available.")
    with make_http_client(proxy, timeout=20.0) as client:
        r = client.get(f"{url}/v1/engines", headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))


def cmd_preload(args: argparse.Namespace) -> None:
    proxy = detect_proxy(args.proxy)
    url, token = resolve_connection(args, allow_drive_sync=True)
    if not url or not token:
        raise SystemExit("No Colab URL/token available.")
    with make_http_client(proxy, timeout=600.0) as client:
        if args.engine == "unload":
            r = client.post(f"{url}/v1/engines/unload", headers={"Authorization": f"Bearer {token}"})
        else:
            r = client.post(f"{url}/v1/engines/{args.engine}/load", headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))


def cmd_generate(args: argparse.Namespace) -> None:
    proxy = detect_proxy(args.proxy)
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ref_video = Path(args.ref_video).resolve() if args.ref_video else None
    ref_audio = Path(args.ref_audio).resolve() if args.ref_audio else None
    if ref_video and not ref_video.exists():
        raise SystemExit(f"Reference video not found: {ref_video}")
    if ref_audio and not ref_audio.exists():
        raise SystemExit(f"Reference audio not found: {ref_audio}")

    extra: Dict[str, Any] = {}
    if args.extra_json:
        extra.update(json.loads(args.extra_json))
    if args.voice:
        extra["voice"] = args.voice
    if args.lang_code:
        extra["lang_code"] = args.lang_code
    if args.speed is not None:
        extra["speed"] = args.speed
    if args.lyrics:
        extra["lyrics"] = args.lyrics
    if args.ref_text:
        extra["ref_text"] = args.ref_text

    payload: Dict[str, Any] = {
        "engine": args.engine,
        "prompt": args.prompt,
        "negative_prompt": args.negative_prompt or "",
        "duration": float(args.duration),
        "num_variants": int(args.num_variants),
        "seed": int(args.seed),
        "steps": int(args.steps),
        "guidance_scale": float(args.guidance_scale),
        "prefix": args.prefix,
        "extra": extra,
        "mirror_to_drive": bool(args.mirror_to_drive),
    }

    transport_used = args.transport
    remote_state: Optional[Dict[str, Any]] = None

    if args.transport in ("auto", "http"):
        url, token = resolve_connection(args, allow_drive_sync=True)
        http_err: Optional[Exception] = None
        if url and token:
            try:
                http_check_health(url, token, proxy)
                remote_state = http_run_job(
                    url, token, proxy, payload, out_dir, ref_video, ref_audio, args.poll_sec, args.timeout_sec
                )
                transport_used = "http"
            except ColabJobError as job_err:
                raise SystemExit(str(job_err))
            except Exception as exc:
                http_err = exc
                # Retry once after syncing fresh tunnel URL from Drive
                if find_gdrive_cmd():
                    try:
                        cache = gdrive_sync_session()
                        fresh_url = cache.get("url")
                        fresh_tok = cache.get("token") or token
                        if fresh_url and fresh_tok and fresh_url != url:
                            http_check_health(fresh_url, fresh_tok, proxy)
                            remote_state = http_run_job(
                                fresh_url, fresh_tok, proxy, payload, out_dir, ref_video, ref_audio, args.poll_sec, args.timeout_sec
                            )
                            transport_used = "http"
                            http_err = None
                    except ColabJobError as job_err:
                        raise SystemExit(str(job_err))
                    except Exception as retry_exc:
                        http_err = retry_exc
        else:
            http_err = RuntimeError("No active Colab tunnel URL/token found.")

        if remote_state is None:
            if args.transport == "http":
                raise SystemExit(f"HTTP generation failed: {http_err}")
            print(f"[AutoFailover] HTTP unavailable ({http_err}); switching to Google Drive queue...", flush=True)
            remote_state = drive_run_job(payload, out_dir, ref_video, ref_audio, args.poll_sec, args.timeout_sec)
            transport_used = "drive"
    else:
        remote_state = drive_run_job(payload, out_dir, ref_video, ref_audio, args.poll_sec, args.timeout_sec)
        transport_used = "drive"

    assert remote_state is not None
    cand_dir = out_dir / "Candidates"
    analyzed: List[Dict[str, Any]] = []
    remote_by_name = {f["filename"]: f for f in remote_state.get("files", [])}
    for fmeta in remote_state.get("files", []):
        wav_path = cand_dir / fmeta["filename"]
        if not wav_path.exists():
            continue
        metrics = analyze_wav(wav_path)
        metrics["variant_index"] = fmeta.get("variant_index")
        metrics["seed"] = fmeta.get("seed")
        metrics["elapsed_sec"] = fmeta.get("elapsed_sec")
        metrics["local_path"] = str(wav_path)
        analyzed.append(metrics)

    provenance = {
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "transport": transport_used,
        "job_id": remote_state.get("job_id"),
        "engine": args.engine,
        "model_id": remote_state.get("model_id"),
        "license": remote_state.get("license"),
        "gpu": remote_state.get("gpu"),
        "request": payload,
        "ref_video_local": str(ref_video) if ref_video else None,
        "ref_audio_local": str(ref_audio) if ref_audio else None,
        "candidates": analyzed,
        "user_auditioned": False,
        "gameplay_tested": False,
        "note": "Objective waveform metrics assist screening only; subjective selection requires user audition.",
    }
    prov_path = out_dir / "provenance.json"
    prov_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nSaved {len(analyzed)} candidate(s) -> {cand_dir}")
    print(f"Provenance -> {prov_path}\n")
    print("| # | File | Seed | Dur(s) | SR | Ch | Peak(dBFS) | RMS(dBFS) | LeadSil(ms) | Atk(ms) | 30ms(%) | >1.5k(%) |")
    print("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for c in analyzed:
        print(
            f"| {c.get('variant_index','')} | {c['filename']} | {c.get('seed','')} | {c['duration_sec']:.2f} | "
            f"{c['sample_rate']} | {c['channels']} | {c['peak_dbfs']:.1f} | {c['rms_dbfs']:.1f} | "
            f"{c['lead_silence_ms']:.1f} | {c['attack_10_90_ms']:.1f} | {c['first_30ms_energy_pct']:.1f} | {c['hf_above_1500hz_pct']:.1f} |"
        )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="FPSGAME Colab Audio Pipeline Client")
    p.add_argument("--url", default=None, help="Colab tunnel HTTPS URL (optional if Drive session.json synced)")
    p.add_argument("--token", default=None, help="Worker Bearer token (prefer env COLAB_AUDIO_TOKEN or Drive sync)")
    p.add_argument("--proxy", default=None, help="HTTP proxy URL (default auto-detects 127.0.0.1:7897; pass '' to disable)")

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sync-session", help="Pull active session.json and token from Google Drive into local user cache")

    dp = sub.add_parser("deploy-notebook", help="Upload or update colab_audio_worker.ipynb on Google Drive")
    dp.add_argument("--notebook", default=str(DEFAULT_NOTEBOOK))

    sub.add_parser("health", help="Check Colab worker health, GPU, and loaded engines")
    sub.add_parser("engines", help="List available audio engines and licenses")

    pl = sub.add_parser("preload", help="Preload an engine into Colab GPU VRAM (or pass 'unload' to free VRAM)")
    pl.add_argument("engine")

    gp = sub.add_parser("generate", help="Generate candidate WAVs on Colab and download to SourceAssets")
    gp.add_argument("--engine", default="tangoflux", choices=["tangoflux", "mmaudio", "stable_audio", "audioldm2", "acestep", "musicgen", "kokoro", "f5tts"])
    gp.add_argument("--prompt", required=True, help="English prompt for SFX/BGM, or CN/EN dialogue text for Kokoro/F5-TTS")
    gp.add_argument("--negative-prompt", default="", help="Negative prompt (supported by mmaudio/stable_audio/audioldm2)")
    gp.add_argument("--duration", type=float, default=4.0, help="Duration in seconds")
    gp.add_argument("--num-variants", type=int, default=4, help="Number of candidates (1-8)")
    gp.add_argument("--seed", type=int, default=42, help="Base seed (variants use seed+i)")
    gp.add_argument("--steps", type=int, default=50, help="Inference steps")
    gp.add_argument("--guidance-scale", type=float, default=4.5, help="CFG guidance scale")
    gp.add_argument("--prefix", default="cand", help="Output filename prefix")
    gp.add_argument("--out-dir", required=True, help="Target batch folder (writes Candidates/ and provenance.json)")
    gp.add_argument("--ref-video", default=None, help="Optional reference MP4/GIF for MMAudio video-to-audio sync")
    gp.add_argument("--ref-audio", default=None, help="Optional 3-15s reference WAV for F5-TTS voice cloning")
    gp.add_argument("--ref-text", default="", help="Transcript of --ref-audio for F5-TTS")
    gp.add_argument("--voice", default="", help="Kokoro voice ID (e.g. zf_xiaobei, zm_yunxi, af_heart, am_adam)")
    gp.add_argument("--lang-code", default="", help="Kokoro language code ('z'=Mandarin, 'a'=US EN, 'b'=UK EN)")
    gp.add_argument("--speed", type=float, default=None, help="Speech speed multiplier for Kokoro/F5-TTS")
    gp.add_argument("--lyrics", default="", help="Lyrics for ACE-Step (leave empty for instrumental game BGM)")
    gp.add_argument("--extra-json", default="", help="Additional JSON object merged into request.extra")
    gp.add_argument("--transport", default="auto", choices=["auto", "http", "drive"], help="Transport selection")
    gp.add_argument("--mirror-to-drive", action="store_true", help="Also copy generated outputs to Drive outbox/")
    gp.add_argument("--poll-sec", type=float, default=2.0)
    gp.add_argument("--timeout-sec", type=float, default=600.0)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {
        "sync-session": cmd_sync_session,
        "deploy-notebook": cmd_deploy_notebook,
        "health": cmd_health,
        "engines": cmd_engines,
        "preload": cmd_preload,
        "generate": cmd_generate,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
