"""FPSGAME Colab Audio Worker Server.

Runs inside Google Colab (optimized for Colab Ultra A100/H100/L4 GPUs).
Exposes a Bearer-authenticated FastAPI HTTP API (for Cloudflare Tunnel direct
access) AND an integrated Google Drive inbox/outbox queue watcher (fallback
transport + automatic session.json discovery).
"""

from __future__ import annotations

import base64
import gc
import hashlib
import hmac
import importlib.util
import inspect
import json
import os
import queue
import re
import shutil
import threading
import time
import traceback
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf
import torch
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WORK_DIR = Path(os.environ.get("AUDIO_WORK_DIR", "/content/audio_worker_jobs"))
DRIVE_BRIDGE_DIR = Path(os.environ.get("DRIVE_BRIDGE_DIR", "/content/drive/MyDrive/FPSGAME_AudioBridge"))
AUTH_TOKEN = os.environ.get("AUDIO_WORKER_TOKEN", "").strip()
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip() or None
TUNNEL_URL_FILE = Path(os.environ.get("TUNNEL_URL_FILE", "/content/audio_worker_tunnel_url.txt"))

WORK_DIR.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gpu_info() -> Dict[str, Any]:
    if not torch.cuda.is_available():
        return {"available": False, "name": "CPU", "vram_total_gb": 0.0, "vram_used_gb": 0.0, "bf16": False}
    props = torch.cuda.get_device_properties(0)
    total_gb = round(props.total_memory / (1024**3), 2)
    used_gb = round(torch.cuda.memory_allocated(0) / (1024**3), 2)
    bf16 = props.major >= 8
    return {
        "available": True,
        "name": props.name,
        "vram_total_gb": total_gb,
        "vram_used_gb": used_gb,
        "compute_capability": f"{props.major}.{props.minor}",
        "bf16": bf16,
    }


def recommended_max_resident_engines() -> int:
    override = os.environ.get("MAX_RESIDENT_ENGINES")
    if override and override.isdigit():
        return max(1, int(override))
    info = gpu_info()
    vram = info.get("vram_total_gb", 0.0)
    if vram >= 70:
        return 4
    if vram >= 36:
        return 3
    if vram >= 20:
        return 2
    return 1


def has_pkg(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


ENGINE_CATALOG: Dict[str, Dict[str, Any]] = {
    "tangoflux": {
        "category": "sfx",
        "model_id": "declare-lab/TangoFlux",
        "license": "Apache-2.0",
        "sample_rate": 44100,
        "channels": 2,
        "duration_range": [1.0, 30.0],
        "supports_video": False,
        "supports_ref_audio": False,
        "description": "Primary high-fidelity 44.1kHz stereo Text-to-SFX / Foley / Ambience (Flow Matching).",
        "check_pkg": "tangoflux",
    },
    "mmaudio": {
        "category": "sfx_video",
        "model_id": "hkchengrex/MMAudio (large_44k_v2)",
        "license": "MIT",
        "sample_rate": 44100,
        "channels": 1,
        "duration_range": [1.0, 30.0],
        "supports_video": True,
        "supports_ref_audio": False,
        "description": "44.1kHz Video-to-Audio synced Foley & Text-to-SFX (supports negative_prompt and reference MP4/GIF).",
        "check_pkg": "mmaudio",
    },
    "stable_audio": {
        "category": "sfx_ambience",
        "model_id": "stabilityai/stable-audio-open-1.0",
        "license": "Stability AI Community License (requires HF_TOKEN)",
        "sample_rate": 44100,
        "channels": 2,
        "duration_range": [1.0, 47.0],
        "supports_video": False,
        "supports_ref_audio": False,
        "description": "44.1kHz stereo up to 47s ambience/SFX via diffusers (requires gated HF_TOKEN).",
        "check_pkg": "diffusers",
    },
    "audioldm2": {
        "category": "sfx_fallback",
        "model_id": "cvssp/audioldm2-large",
        "license": "Apache-2.0 code / CC-BY-NC-SA-4.0 weights",
        "sample_rate": 16000,
        "channels": 1,
        "duration_range": [1.0, 20.0],
        "supports_video": False,
        "supports_ref_audio": False,
        "description": "Zero-extra-dependency diffusers fallback SFX engine (16kHz).",
        "check_pkg": "diffusers",
    },
    "acestep": {
        "category": "bgm",
        "model_id": "ACE-Step/acestep-v15-xl-turbo-diffusers | ACE-Step/ACE-Step-v1-3.5B",
        "license": "Apache-2.0",
        "sample_rate": 48000,
        "channels": 2,
        "duration_range": [5.0, 240.0],
        "supports_video": False,
        "supports_ref_audio": False,
        "description": "Primary 48kHz stereo game BGM / instrumental soundtrack generator.",
        "check_pkg": "acestep_or_diffusers",
    },
    "musicgen": {
        "category": "bgm_fallback",
        "model_id": "facebook/musicgen-stereo-large",
        "license": "MIT code / CC-BY-NC-4.0 weights",
        "sample_rate": 32000,
        "channels": 2,
        "duration_range": [2.0, 30.0],
        "supports_video": False,
        "supports_ref_audio": False,
        "description": "Zero-extra-dependency transformers stereo BGM fallback (32kHz).",
        "check_pkg": "transformers",
    },
    "kokoro": {
        "category": "voice",
        "model_id": "hexgrad/Kokoro-82M",
        "license": "Apache-2.0",
        "sample_rate": 24000,
        "channels": 1,
        "duration_range": [0.5, 120.0],
        "supports_video": False,
        "supports_ref_audio": False,
        "description": "Primary lightweight Mandarin Chinese (z) & English (a/b) NPC voice synthesis.",
        "check_pkg": "kokoro",
    },
    "f5tts": {
        "category": "voice_clone",
        "model_id": "SWivid/F5-TTS (F5TTS_v1_Base)",
        "license": "MIT (inherits reference audio license)",
        "sample_rate": 24000,
        "channels": 1,
        "duration_range": [0.5, 120.0],
        "supports_video": False,
        "supports_ref_audio": True,
        "description": "Zero-shot CN/EN NPC voice cloning from a 3-15s reference WAV + transcript.",
        "check_pkg": "f5_tts",
    },
}


def is_engine_installed(name: str) -> bool:
    meta = ENGINE_CATALOG.get(name)
    if not meta:
        return False
    check = meta["check_pkg"]
    if check == "acestep_or_diffusers":
        if has_pkg("acestep"):
            return True
        if has_pkg("diffusers"):
            try:
                import diffusers

                return hasattr(diffusers, "AceStepPipeline")
            except Exception:
                return False
        return False
    if name == "stable_audio":
        return has_pkg("diffusers") and bool(HF_TOKEN)
    return has_pkg(check)


# ---------------------------------------------------------------------------
# Audio Helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_waveform_array(wav: np.ndarray) -> np.ndarray:
    """Convert arbitrary tensor/ndarray shape to float32 [samples, channels]."""
    arr = np.asarray(wav, dtype=np.float32)
    arr = np.squeeze(arr)
    if arr.ndim == 1:
        arr = arr[:, None]
    elif arr.ndim == 2:
        # Handle [channels, samples] -> [samples, channels]
        if arr.shape[0] <= 4 and arr.shape[1] > arr.shape[0]:
            arr = arr.T
    elif arr.ndim == 3:
        arr = arr[0]
        if arr.shape[0] <= 4 and arr.shape[1] > arr.shape[0]:
            arr = arr.T
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    peak = float(np.max(np.abs(arr))) if arr.size else 0.0
    if peak > 0.999:
        arr = arr * (0.98 / peak)
    return arr.astype(np.float32, copy=False)


def save_wav_and_metrics(arr: np.ndarray, sr: int, out_path: Path) -> Dict[str, Any]:
    audio = normalize_waveform_array(arr)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), audio, int(sr), subtype="PCM_24")
    mono = audio.mean(axis=1) if audio.shape[1] > 1 else audio[:, 0]
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(mono * mono))) if mono.size else 0.0
    peak_dbfs = round(20.0 * np.log10(max(peak, 1e-9)), 2)
    rms_dbfs = round(20.0 * np.log10(max(rms, 1e-9)), 2)
    duration_sec = round(float(audio.shape[0]) / float(sr), 4)
    return {
        "filename": out_path.name,
        "bytes": out_path.stat().st_size,
        "sample_rate": int(sr),
        "channels": int(audio.shape[1]),
        "duration_sec": duration_sec,
        "peak_dbfs": peak_dbfs,
        "rms_dbfs": rms_dbfs,
        "sha256": sha256_file(out_path),
    }


def detect_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def seed_everything(seed: int) -> None:
    np.random.seed(seed % (2**32 - 1))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
# Engine Implementations (Lazy Loaded + LRU VRAM Management)
# ---------------------------------------------------------------------------


class EngineManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded: "OrderedDict[str, Any]" = OrderedDict()
        self.max_resident = recommended_max_resident_engines()
        if torch.cuda.is_available():
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

    def loaded_names(self) -> List[str]:
        with self._lock:
            return list(self._loaded.keys())

    def unload_all(self) -> List[str]:
        with self._lock:
            evicted = list(self._loaded.keys())
            self._loaded.clear()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return evicted

    def _evict_if_needed(self, incoming: str) -> None:
        while len(self._loaded) >= self.max_resident and incoming not in self._loaded:
            old_name, _ = self._loaded.popitem(last=False)
            print(f"[EngineManager] Evicting {old_name} to keep VRAM clean", flush=True)
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def get(self, name: str) -> Any:
        with self._lock:
            if name in self._loaded:
                self._loaded.move_to_end(name)
                return self._loaded[name]
            self._evict_if_needed(name)
            engine = self._load_engine(name)
            self._loaded[name] = engine
            return engine

    def _device_dtype(self) -> Tuple[str, torch.dtype]:
        if torch.cuda.is_available():
            bf16 = torch.cuda.get_device_properties(0).major >= 8
            return "cuda", (torch.bfloat16 if bf16 else torch.float16)
        return "cpu", torch.float32

    def _load_engine(self, name: str) -> Any:
        device, dtype = self._device_dtype()
        print(f"[EngineManager] Loading engine={name} on {device} ({dtype})...", flush=True)

        if name == "tangoflux":
            from tangoflux import TangoFluxInference

            sig = inspect.signature(TangoFluxInference.__init__)
            if "device" in sig.parameters:
                return TangoFluxInference(name="declare-lab/TangoFlux", device=device)
            return TangoFluxInference(name="declare-lab/TangoFlux")

        if name == "mmaudio":
            from mmaudio.eval_utils import all_model_cfg
            from mmaudio.model.networks import get_my_mmaudio
            from mmaudio.model.utils.features_utils import FeaturesUtils

            variant = os.environ.get("MMAUDIO_VARIANT", "large_44k_v2")
            model_cfg = all_model_cfg[variant]
            model_cfg.download_if_needed()
            # Use bf16 on Ampere/Hopper (A100/H100/L4), fp32 on T4 to prevent fp16 NaNs
            mm_dtype = torch.bfloat16 if (device == "cuda" and dtype == torch.bfloat16) else torch.float32
            net = get_my_mmaudio(model_cfg.model_name).to(device, mm_dtype).eval()
            net.load_weights(torch.load(model_cfg.model_path, map_location=device, weights_only=True))
            feature_utils = FeaturesUtils(
                tod_vae_ckpt=model_cfg.vae_path,
                synchformer_ckpt=model_cfg.synchformer_ckpt,
                enable_conditions=True,
                mode=model_cfg.mode,
                bigvgan_vocoder_ckpt=model_cfg.bigvgan_16k_path,
                need_vae_encoder=False,
            ).to(device, mm_dtype).eval()
            return {"cfg": model_cfg, "net": net, "feature_utils": feature_utils, "device": device, "dtype": mm_dtype}

        if name == "stable_audio":
            if not HF_TOKEN:
                raise RuntimeError("stable_audio requires HF_TOKEN in Colab Secrets (gated model).")
            from diffusers import StableAudioPipeline

            pipe = StableAudioPipeline.from_pretrained(
                "stabilityai/stable-audio-open-1.0",
                torch_dtype=dtype,
                token=HF_TOKEN,
            ).to(device)
            return pipe

        if name == "audioldm2":
            from diffusers import AudioLDM2Pipeline, AudioLDMPipeline

            pipe_dtype = torch.float16 if device == "cuda" else torch.float32
            try:
                pipe = AudioLDM2Pipeline.from_pretrained(
                    "cvssp/audioldm2-large",
                    torch_dtype=pipe_dtype,
                ).to(device)
                # Guard against transformers 5.x removing GPT2Model._update_model_kwargs_for_generation
                if not hasattr(pipe.language_model, "_update_model_kwargs_for_generation"):
                    raise RuntimeError("transformers 5.x incompatible with AudioLDM2Pipeline; switching to AudioLDM")
                return {"pipe": pipe, "model_id": "cvssp/audioldm2-large"}
            except Exception as exc:
                print(f"[EngineManager] AudioLDM2 unavailable ({exc}), falling back to cvssp/audioldm-l-full", flush=True)
                pipe = AudioLDMPipeline.from_pretrained(
                    "cvssp/audioldm-l-full",
                    torch_dtype=pipe_dtype,
                ).to(device)
                return {"pipe": pipe, "model_id": "cvssp/audioldm-l-full"}

        if name == "acestep":
            # Prefer native diffusers AceStepPipeline (v1.5 turbo) if installed, else official acestep package
            try:
                from diffusers import AceStepPipeline

                ckpt = os.environ.get("ACESTEP_DIFFUSERS_REPO", "ACE-Step/acestep-v15-xl-turbo-diffusers")
                pipe = AceStepPipeline.from_pretrained(ckpt, torch_dtype=dtype).to(device)
                return {"backend": "diffusers", "pipe": pipe, "model_id": ckpt}
            except Exception as diffusers_err:
                if not has_pkg("acestep"):
                    raise RuntimeError(
                        f"Neither diffusers.AceStepPipeline ({diffusers_err}) nor acestep package is available."
                    )
                from acestep.pipeline_ace_step import ACEStepPipeline

                ckpt_dir = os.environ.get("ACESTEP_CKPT_DIR", "/content/.cache/ace-step/checkpoints")
                dtype_str = "bfloat16" if dtype == torch.bfloat16 else "float16"
                pipe = ACEStepPipeline(checkpoint_dir=ckpt_dir, dtype=dtype_str, torch_compile=False)
                if hasattr(pipe, "load_checkpoint"):
                    pipe.load_checkpoint(ckpt_dir)
                return {"backend": "native", "pipe": pipe, "model_id": "ACE-Step/ACE-Step-v1-3.5B"}

        if name == "musicgen":
            from transformers import AutoProcessor, MusicgenForConditionalGeneration

            repo = os.environ.get("MUSICGEN_REPO", "facebook/musicgen-stereo-large")
            processor = AutoProcessor.from_pretrained(repo)
            model = MusicgenForConditionalGeneration.from_pretrained(
                repo,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            ).to(device)
            return {"processor": processor, "model": model, "device": device, "model_id": repo}

        if name == "kokoro":
            from kokoro import KPipeline

            return {"pipelines": {}, "cls": KPipeline}

        if name == "f5tts":
            from f5_tts.api import F5TTS

            return F5TTS(model="F5TTS_v1_Base", device=device)

        raise ValueError(f"Unsupported engine: {name}")

    def generate_variant(
        self,
        engine_name: str,
        params: Dict[str, Any],
        seed: int,
        ref_video_path: Optional[Path] = None,
        ref_audio_path: Optional[Path] = None,
        tmp_out_path: Optional[Path] = None,
    ) -> Tuple[np.ndarray, int, str]:
        """Returns (waveform_array, sample_rate, resolved_model_id)."""
        seed_everything(seed)
        eng = self.get(engine_name)
        prompt = str(params.get("prompt", "")).strip()
        negative_prompt = str(params.get("negative_prompt", "")).strip()
        duration = float(params.get("duration", 5.0))
        steps = int(params.get("steps", 50))
        guidance_scale = float(params.get("guidance_scale", 4.5))
        extra = params.get("extra") or {}

        if engine_name == "tangoflux":
            duration = float(np.clip(duration, 1.0, 30.0))
            sig = inspect.signature(eng.generate)
            kwargs: Dict[str, Any] = {"steps": steps, "duration": duration}
            if "guidance_scale" in sig.parameters:
                kwargs["guidance_scale"] = guidance_scale
            with torch.inference_mode():
                audio = eng.generate(prompt, **kwargs)
            arr = audio.detach().float().cpu().numpy() if torch.is_tensor(audio) else np.asarray(audio, dtype=np.float32)
            return arr, 44100, "declare-lab/TangoFlux"

        if engine_name == "mmaudio":
            from mmaudio.eval_utils import generate as mmaudio_generate, load_video
            from mmaudio.model.flow_matching import FlowMatching

            duration = float(np.clip(duration, 1.0, 30.0))
            model_cfg = eng["cfg"]
            net = eng["net"]
            feature_utils = eng["feature_utils"]
            device = eng["device"]
            seq_cfg = model_cfg.seq_cfg

            clip_frames = None
            sync_frames = None
            if ref_video_path and ref_video_path.exists():
                video_info = load_video(ref_video_path, duration)
                clip_frames = video_info.clip_frames.unsqueeze(0)
                sync_frames = video_info.sync_frames.unsqueeze(0)
                duration = float(video_info.duration_sec)

            seq_cfg.duration = duration
            net.update_seq_lengths(seq_cfg.latent_seq_len, seq_cfg.clip_seq_len, seq_cfg.sync_seq_len)
            fm = FlowMatching(min_sigma=0, inference_mode="euler", num_steps=max(10, min(steps, 100)))
            rng = torch.Generator(device=device).manual_seed(seed)
            with torch.inference_mode():
                audios = mmaudio_generate(
                    clip_frames,
                    sync_frames,
                    [prompt],
                    negative_text=[negative_prompt] if negative_prompt else None,
                    feature_utils=feature_utils,
                    net=net,
                    fm=fm,
                    rng=rng,
                    cfg_strength=guidance_scale,
                )
            arr = audios.float().cpu()[0].numpy()
            return arr, int(seq_cfg.sampling_rate), f"hkchengrex/MMAudio:{model_cfg.model_name}"

        if engine_name == "stable_audio":
            duration = float(np.clip(duration, 1.0, 47.0))
            device = "cuda" if torch.cuda.is_available() else "cpu"
            gen = torch.Generator(device=device).manual_seed(seed)
            with torch.inference_mode():
                out = eng(
                    prompt,
                    negative_prompt=negative_prompt or "low quality, distortion, clipping, speech",
                    num_inference_steps=max(20, min(steps, 150)),
                    audio_end_in_s=duration,
                    num_waveforms_per_prompt=1,
                    generator=gen,
                )
            audio = out.audios[0].T.float().cpu().numpy()
            sr = int(getattr(eng.vae, "sampling_rate", 44100))
            return audio, sr, "stabilityai/stable-audio-open-1.0"

        if engine_name == "audioldm2":
            duration = float(np.clip(duration, 1.0, 20.0))
            device = "cuda" if torch.cuda.is_available() else "cpu"
            gen = torch.Generator(device=device).manual_seed(seed)
            pipe = eng["pipe"] if isinstance(eng, dict) else eng
            mid = eng["model_id"] if isinstance(eng, dict) else "cvssp/audioldm2-large"
            with torch.inference_mode():
                out = pipe(
                    prompt,
                    negative_prompt=negative_prompt or "low quality, noise, distortion",
                    num_inference_steps=max(20, min(steps, 150)),
                    audio_length_in_s=duration,
                    guidance_scale=guidance_scale,
                    generator=gen,
                )
            audio = np.asarray(out.audios[0], dtype=np.float32)
            return audio, 16000, mid

        if engine_name == "acestep":
            duration = float(np.clip(duration, 5.0, 240.0))
            lyrics = str(extra.get("lyrics", "")).strip()
            pipe = eng["pipe"]
            if eng["backend"] == "diffusers":
                device = "cuda" if torch.cuda.is_available() else "cpu"
                gen = torch.Generator(device=device).manual_seed(seed)
                sig = inspect.signature(pipe.__call__)
                kwargs = {"prompt": prompt, "lyrics": lyrics or "[instrumental]"}
                if "audio_duration" in sig.parameters:
                    kwargs["audio_duration"] = duration
                if "infer_step" in sig.parameters:
                    kwargs["infer_step"] = int(extra.get("infer_step", min(steps, 32)))
                elif "num_inference_steps" in sig.parameters:
                    kwargs["num_inference_steps"] = int(extra.get("infer_step", min(steps, 32)))
                if "guidance_scale" in sig.parameters:
                    kwargs["guidance_scale"] = guidance_scale
                if "generator" in sig.parameters:
                    kwargs["generator"] = gen
                with torch.inference_mode():
                    res = pipe(**kwargs)
                audio = res.audios[0] if hasattr(res, "audios") else res
                arr = audio.detach().float().cpu().numpy() if torch.is_tensor(audio) else np.asarray(audio, dtype=np.float32)
                return arr, 48000, eng["model_id"]
            else:
                out_dir = tmp_out_path.parent if tmp_out_path else WORK_DIR / "_acestep_tmp"
                out_dir.mkdir(parents=True, exist_ok=True)
                target_wav = out_dir / f"acestep_{seed}.wav"
                res = pipe(
                    audio_duration=duration,
                    prompt=prompt,
                    lyrics=lyrics,
                    infer_step=int(extra.get("infer_step", max(27, min(steps, 60)))),
                    guidance_scale=float(extra.get("guidance_scale", 15.0)),
                    scheduler_type=str(extra.get("scheduler_type", "euler")),
                    cfg_type=str(extra.get("cfg_type", "apg")),
                    manual_seeds=[seed],
                    save_path=str(target_wav),
                )
                saved_path = target_wav
                if isinstance(res, (list, tuple)) and res and isinstance(res[0], str) and Path(res[0]).exists():
                    saved_path = Path(res[0])
                data, sr = sf.read(str(saved_path), always_2d=True)
                if saved_path.exists():
                    saved_path.unlink(missing_ok=True)
                return data.astype(np.float32), int(sr), eng["model_id"]

        if engine_name == "musicgen":
            duration = float(np.clip(duration, 2.0, 30.0))
            processor = eng["processor"]
            model = eng["model"]
            device = eng["device"]
            inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(device)
            # MusicGen generates ~50 tokens per second
            max_new_tokens = max(64, min(int(round(duration * 50.0)), 1503))
            with torch.inference_mode():
                audio_values = model.generate(
                    **inputs,
                    do_sample=True,
                    guidance_scale=float(extra.get("guidance_scale", 3.0)),
                    max_new_tokens=max_new_tokens,
                )
            sr = int(model.config.audio_encoder.sampling_rate)
            arr = audio_values[0].detach().float().cpu().numpy()
            return arr, sr, eng["model_id"]

        if engine_name == "kokoro":
            lang_code = str(extra.get("lang_code") or ("z" if detect_cjk(prompt) else "a"))
            default_voice = "zf_xiaobei" if lang_code == "z" else "af_heart"
            voice = str(extra.get("voice") or default_voice)
            speed = float(extra.get("speed", 1.0))
            pipelines = eng["pipelines"]
            if lang_code not in pipelines:
                pipelines[lang_code] = eng["cls"](lang_code=lang_code)
            pipe = pipelines[lang_code]
            chunks: List[np.ndarray] = []
            for _gs, _ps, chunk in pipe(prompt, voice=voice, speed=speed):
                c = chunk.detach().float().cpu().numpy() if torch.is_tensor(chunk) else np.asarray(chunk, dtype=np.float32)
                chunks.append(c.reshape(-1))
            if not chunks:
                raise RuntimeError("Kokoro produced empty audio.")
            return np.concatenate(chunks, axis=0), 24000, f"hexgrad/Kokoro-82M:{lang_code}:{voice}"

        if engine_name == "f5tts":
            if not ref_audio_path or not ref_audio_path.exists():
                raise RuntimeError("f5tts requires ref_audio (3-15s clean reference WAV).")
            ref_text = str(extra.get("ref_text", "")).strip()
            out_wav = (tmp_out_path.parent if tmp_out_path else WORK_DIR) / f"f5_{seed}.wav"
            wav, sr, _spec = eng.infer(
                ref_file=str(ref_audio_path),
                ref_text=ref_text,
                gen_text=prompt,
                file_wave=str(out_wav),
                seed=seed,
                speed=float(extra.get("speed", 1.0)),
            )
            if out_wav.exists():
                data, file_sr = sf.read(str(out_wav), always_2d=True)
                out_wav.unlink(missing_ok=True)
                return data.astype(np.float32), int(file_sr), "SWivid/F5-TTS:F5TTS_v1_Base"
            return np.asarray(wav, dtype=np.float32), int(sr), "SWivid/F5-TTS:F5TTS_v1_Base"

        raise ValueError(f"Unsupported engine: {engine_name}")


# ---------------------------------------------------------------------------
# Job Queue & Drive Bridge
# ---------------------------------------------------------------------------


class JobRequest(BaseModel):
    engine: str = Field(default="tangoflux")
    prompt: str = Field(..., min_length=1)
    negative_prompt: str = Field(default="")
    duration: float = Field(default=5.0, ge=0.5, le=240.0)
    num_variants: int = Field(default=4, ge=1, le=8)
    seed: int = Field(default=42)
    steps: int = Field(default=50, ge=4, le=150)
    guidance_scale: float = Field(default=4.5, ge=0.0, le=30.0)
    prefix: str = Field(default="cand")
    extra: Dict[str, Any] = Field(default_factory=dict)
    mirror_to_drive: bool = Field(default=False)


class JobRunner:
    def __init__(self, engines: EngineManager) -> None:
        self.engines = engines
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._jobs_lock = threading.Lock()
        self._q: "queue.Queue[str]" = queue.Queue()
        self._worker = threading.Thread(target=self._run_loop, name="audio-gpu-worker", daemon=True)
        self._worker.start()

    def submit(
        self,
        req: Dict[str, Any],
        job_id: Optional[str] = None,
        ref_video_path: Optional[Path] = None,
        ref_audio_path: Optional[Path] = None,
        source: str = "http",
    ) -> Dict[str, Any]:
        jid = job_id or f"job_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        job_dir = WORK_DIR / jid
        job_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "job_id": jid,
            "source": source,
            "status": "queued",
            "created_at": utc_now_iso(),
            "started_at": None,
            "finished_at": None,
            "engine": req.get("engine", "tangoflux"),
            "request": req,
            "ref_video": str(ref_video_path) if ref_video_path else None,
            "ref_audio": str(ref_audio_path) if ref_audio_path else None,
            "completed_variants": 0,
            "num_variants": int(req.get("num_variants", 4)),
            "files": [],
            "model_id": None,
            "gpu": gpu_info().get("name", "unknown"),
            "license": ENGINE_CATALOG.get(req.get("engine", "tangoflux"), {}).get("license", "unknown"),
            "error": None,
        }
        with self._jobs_lock:
            self._jobs[jid] = record
        self._save_job_json(jid)
        self._q.put(jid)
        return dict(record)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._jobs_lock:
            rec = self._jobs.get(job_id)
            return dict(rec) if rec else None

    def queue_size(self) -> int:
        return self._q.qsize()

    def _save_job_json(self, job_id: str) -> None:
        rec = self.get_job(job_id)
        if not rec:
            return
        job_dir = WORK_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "result.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")

    def _mirror_job_to_drive(self, job_id: str) -> None:
        if not DRIVE_BRIDGE_DIR.exists():
            return
        rec = self.get_job(job_id)
        if not rec:
            return
        out_dir = DRIVE_BRIDGE_DIR / "outbox" / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        job_dir = WORK_DIR / job_id
        for fmeta in rec.get("files", []):
            src = job_dir / fmeta["filename"]
            if src.exists():
                shutil.copy2(src, out_dir / src.name)
        tmp_json = out_dir / "result.json.tmp"
        final_json = out_dir / "result.json"
        tmp_json.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_json.replace(final_json)

    def _run_loop(self) -> None:
        while True:
            jid = self._q.get()
            try:
                self._execute_job(jid)
            except Exception as exc:
                tb = traceback.format_exc()
                print(f"[JobRunner] Fatal error on {jid}: {exc}\n{tb}", flush=True)
                with self._jobs_lock:
                    if jid in self._jobs:
                        self._jobs[jid]["status"] = "failed"
                        self._jobs[jid]["finished_at"] = utc_now_iso()
                        self._jobs[jid]["error"] = f"{exc}\n{tb[-1200:]}"
                self._save_job_json(jid)
                rec = self.get_job(jid)
                if rec and (rec.get("source") == "drive" or rec.get("request", {}).get("mirror_to_drive")):
                    self._mirror_job_to_drive(jid)
            finally:
                self._q.task_done()

    def _execute_job(self, jid: str) -> None:
        with self._jobs_lock:
            rec = self._jobs[jid]
            rec["status"] = "running"
            rec["started_at"] = utc_now_iso()
            req = dict(rec["request"])
            ref_video = Path(rec["ref_video"]) if rec.get("ref_video") else None
            ref_audio = Path(rec["ref_audio"]) if rec.get("ref_audio") else None
        self._save_job_json(jid)

        engine_name = str(req.get("engine", "tangoflux"))
        num_variants = max(1, min(int(req.get("num_variants", 4)), 8))
        base_seed = int(req.get("seed", 42))
        safe_prefix = re.sub(r"[^A-Za-z0-9_-]+", "_", str(req.get("prefix", "cand"))).strip("_") or "cand"
        job_dir = WORK_DIR / jid
        files_meta: List[Dict[str, Any]] = []
        resolved_model_id = ENGINE_CATALOG.get(engine_name, {}).get("model_id", engine_name)

        for idx in range(num_variants):
            cur_seed = base_seed + idx
            out_wav = job_dir / f"{safe_prefix}_{idx + 1:02d}_s{cur_seed}.wav"
            t0 = time.time()
            arr, sr, model_id = self.engines.generate_variant(
                engine_name=engine_name,
                params=req,
                seed=cur_seed,
                ref_video_path=ref_video,
                ref_audio_path=ref_audio,
                tmp_out_path=out_wav,
            )
            resolved_model_id = model_id
            meta = save_wav_and_metrics(arr, sr, out_wav)
            meta["variant_index"] = idx + 1
            meta["seed"] = cur_seed
            meta["elapsed_sec"] = round(time.time() - t0, 2)
            files_meta.append(meta)
            with self._jobs_lock:
                self._jobs[jid]["completed_variants"] = idx + 1
                self._jobs[jid]["files"] = list(files_meta)
                self._jobs[jid]["model_id"] = resolved_model_id
            self._save_job_json(jid)

        with self._jobs_lock:
            self._jobs[jid]["status"] = "succeeded"
            self._jobs[jid]["finished_at"] = utc_now_iso()
            self._jobs[jid]["gpu"] = gpu_info().get("name", "unknown")
        self._save_job_json(jid)

        rec = self.get_job(jid)
        if rec and (rec.get("source") == "drive" or req.get("mirror_to_drive")):
            self._mirror_job_to_drive(jid)


# ---------------------------------------------------------------------------
# Drive Session Heartbeat & Inbox Watcher
# ---------------------------------------------------------------------------


def read_current_tunnel_url() -> Optional[str]:
    if TUNNEL_URL_FILE.exists():
        text = TUNNEL_URL_FILE.read_text(encoding="utf-8").strip()
        if text.startswith("https://"):
            return text
    return None


_SESSION_WRITE_LOCK = threading.Lock()


def write_drive_session_heartbeat(engines: EngineManager, runner: JobRunner) -> None:
    if not DRIVE_BRIDGE_DIR.exists():
        return
    DRIVE_BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "online",
        "updated_at": utc_now_iso(),
        "tunnel_url": read_current_tunnel_url(),
        "gpu": gpu_info(),
        "max_resident_engines": engines.max_resident,
        "engines_installed": [k for k in ENGINE_CATALOG if is_engine_installed(k)],
        "engines_loaded": engines.loaded_names(),
        "queue_size": runner.queue_size(),
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    with _SESSION_WRITE_LOCK:
        tmp = DRIVE_BRIDGE_DIR / f"session.{uuid.uuid4().hex[:8]}.tmp"
        dst = DRIVE_BRIDGE_DIR / "session.json"
        tmp.write_text(text, encoding="utf-8")
        try:
            tmp.replace(dst)
        except OSError:
            dst.write_text(text, encoding="utf-8")
            tmp.unlink(missing_ok=True)


def start_drive_watcher(engines: EngineManager, runner: JobRunner) -> None:
    def _loop() -> None:
        last_hb = 0.0
        while True:
            try:
                now = time.time()
                if DRIVE_BRIDGE_DIR.exists():
                    for sub in ("inbox", "outbox", "processed", "failed", "refs"):
                        (DRIVE_BRIDGE_DIR / sub).mkdir(parents=True, exist_ok=True)
                    if now - last_hb >= 20.0:
                        write_drive_session_heartbeat(engines, runner)
                        last_hb = now
                    inbox = DRIVE_BRIDGE_DIR / "inbox"
                    for item in sorted(inbox.glob("*.json")):
                        try:
                            raw = json.loads(item.read_text(encoding="utf-8"))
                            jid = str(raw.get("job_id") or item.stem)
                            job_dir = WORK_DIR / jid
                            job_dir.mkdir(parents=True, exist_ok=True)

                            ref_video: Optional[Path] = None
                            ref_audio: Optional[Path] = None
                            if raw.get("ref_video_drive_rel"):
                                cand = DRIVE_BRIDGE_DIR / str(raw["ref_video_drive_rel"])
                                if cand.exists():
                                    ref_video = job_dir / f"ref_video{cand.suffix}"
                                    shutil.copy2(cand, ref_video)
                            if raw.get("ref_audio_drive_rel"):
                                cand = DRIVE_BRIDGE_DIR / str(raw["ref_audio_drive_rel"])
                                if cand.exists():
                                    ref_audio = job_dir / f"ref_audio{cand.suffix}"
                                    shutil.copy2(cand, ref_audio)
                            if raw.get("ref_audio_b64") and not ref_audio:
                                ref_audio = job_dir / "ref_audio.wav"
                                ref_audio.write_bytes(base64.b64decode(raw["ref_audio_b64"]))

                            req = JobRequest(
                                engine=raw.get("engine", "tangoflux"),
                                prompt=raw["prompt"],
                                negative_prompt=raw.get("negative_prompt", ""),
                                duration=float(raw.get("duration", 5.0)),
                                num_variants=int(raw.get("num_variants", 4)),
                                seed=int(raw.get("seed", 42)),
                                steps=int(raw.get("steps", 50)),
                                guidance_scale=float(raw.get("guidance_scale", 4.5)),
                                prefix=raw.get("prefix", "cand"),
                                extra=raw.get("extra") or {},
                                mirror_to_drive=True,
                            ).model_dump()
                            runner.submit(req, job_id=jid, ref_video_path=ref_video, ref_audio_path=ref_audio, source="drive")
                            shutil.move(str(item), str(DRIVE_BRIDGE_DIR / "processed" / item.name))
                            print(f"[DriveWatcher] Picked up Drive job {jid}", flush=True)
                        except Exception as item_err:
                            print(f"[DriveWatcher] Failed parsing {item.name}: {item_err}", flush=True)
                            try:
                                shutil.move(str(item), str(DRIVE_BRIDGE_DIR / "failed" / item.name))
                            except Exception:
                                pass
            except Exception as err:
                print(f"[DriveWatcher] Loop warning: {err}", flush=True)
            time.sleep(2.5)

    threading.Thread(target=_loop, name="drive-bridge-watcher", daemon=True).start()


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

engines_mgr = EngineManager()
job_runner = JobRunner(engines_mgr)
start_drive_watcher(engines_mgr, job_runner)

app = FastAPI(title="FPSGAME Colab Audio Worker", version="1.0.0")


def require_auth(authorization: Optional[str] = Header(default=None)) -> None:
    if not AUTH_TOKEN:
        raise HTTPException(status_code=503, detail="Worker token not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    provided = authorization.split(" ", 1)[1].strip()
    if not hmac.compare_digest(provided, AUTH_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid token")


@app.get("/v1/ping")
def ping() -> Dict[str, Any]:
    return {"ok": True, "ts": utc_now_iso()}


@app.get("/v1/health", dependencies=[Depends(require_auth)])
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "ts": utc_now_iso(),
        "gpu": gpu_info(),
        "tunnel_url": read_current_tunnel_url(),
        "drive_mounted": DRIVE_BRIDGE_DIR.exists(),
        "max_resident_engines": engines_mgr.max_resident,
        "engines_installed": [k for k in ENGINE_CATALOG if is_engine_installed(k)],
        "engines_loaded": engines_mgr.loaded_names(),
        "queue_size": job_runner.queue_size(),
    }


@app.get("/v1/engines", dependencies=[Depends(require_auth)])
def list_engines() -> Dict[str, Any]:
    loaded = set(engines_mgr.loaded_names())
    out = {}
    for name, meta in ENGINE_CATALOG.items():
        out[name] = {
            **{k: v for k, v in meta.items() if k != "check_pkg"},
            "installed": is_engine_installed(name),
            "loaded": name in loaded,
        }
    return {"engines": out}


@app.post("/v1/engines/{engine_name}/load", dependencies=[Depends(require_auth)])
def load_engine(engine_name: str) -> Dict[str, Any]:
    if engine_name not in ENGINE_CATALOG:
        raise HTTPException(status_code=404, detail=f"Unknown engine: {engine_name}")
    try:
        engines_mgr.get(engine_name)
    except Exception as exc:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"{exc}\n{tb[-1200:]}")
    write_drive_session_heartbeat(engines_mgr, job_runner)
    return {"loaded": engines_mgr.loaded_names(), "gpu": gpu_info()}


@app.get("/v1/logs", dependencies=[Depends(require_auth)])
def get_logs(lines: int = 80) -> Dict[str, Any]:
    log_path = Path("/content/audio_worker_server.log")
    if not log_path.exists():
        return {"lines": []}
    content = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return {"lines": content[-max(1, min(lines, 400)):]}


@app.post("/v1/engines/unload", dependencies=[Depends(require_auth)])
def unload_engines() -> Dict[str, Any]:
    evicted = engines_mgr.unload_all()
    write_drive_session_heartbeat(engines_mgr, job_runner)
    return {"evicted": evicted, "gpu": gpu_info()}


@app.post("/v1/jobs", dependencies=[Depends(require_auth)])
async def create_job(
    request: Request,
    payload_json: Optional[str] = Form(default=None),
    ref_video: Optional[UploadFile] = File(default=None),
    ref_audio: Optional[UploadFile] = File(default=None),
) -> JSONResponse:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        parsed = JobRequest(**body)
    elif payload_json:
        parsed = JobRequest(**json.loads(payload_json))
    else:
        raise HTTPException(status_code=400, detail="Send application/json body or multipart field payload_json")

    if parsed.engine not in ENGINE_CATALOG:
        raise HTTPException(status_code=400, detail=f"Unknown engine: {parsed.engine}")

    jid = f"job_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    job_dir = WORK_DIR / jid
    job_dir.mkdir(parents=True, exist_ok=True)

    saved_video: Optional[Path] = None
    saved_audio: Optional[Path] = None
    if ref_video is not None:
        ext = Path(ref_video.filename or "ref.mp4").suffix or ".mp4"
        saved_video = job_dir / f"ref_video{ext}"
        saved_video.write_bytes(await ref_video.read())
    if ref_audio is not None:
        ext = Path(ref_audio.filename or "ref.wav").suffix or ".wav"
        saved_audio = job_dir / f"ref_audio{ext}"
        saved_audio.write_bytes(await ref_audio.read())

    rec = job_runner.submit(
        parsed.model_dump(),
        job_id=jid,
        ref_video_path=saved_video,
        ref_audio_path=saved_audio,
        source="http",
    )
    return JSONResponse(status_code=202, content=rec)


@app.get("/v1/jobs/{job_id}", dependencies=[Depends(require_auth)])
def get_job(job_id: str) -> Dict[str, Any]:
    rec = job_runner.get_job(job_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Job not found")
    return rec


@app.get("/v1/jobs/{job_id}/files/{filename}", dependencies=[Depends(require_auth)])
def download_file(job_id: str, filename: str) -> FileResponse:
    if Path(job_id).name != job_id or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid path")
    target = (WORK_DIR / job_id / filename).resolve()
    base = (WORK_DIR / job_id).resolve()
    if not str(target).startswith(str(base)) or not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(target), media_type="audio/wav", filename=filename)


@app.delete("/v1/jobs/{job_id}", dependencies=[Depends(require_auth)])
def delete_job(job_id: str) -> Dict[str, Any]:
    if Path(job_id).name != job_id:
        raise HTTPException(status_code=400, detail="Invalid job_id")
    job_dir = WORK_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
    return {"deleted": job_id}
