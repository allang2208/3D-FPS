"""Headless UE 5.8 Python SoundWave batch importer for FPSGAME AudioPipeline.

Invoked via Tools/AudioPipeline/run_ue_import.ps1 (UnrealEditor-Cmd.exe -nullrhi).
Reads JSON spec from environment variable FPSGAME_AUDIO_IMPORT_SPEC and writes
a receipt to FPSGAME_AUDIO_IMPORT_RECEIPT.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import unreal as ue

LIB = ue.EditorAssetLibrary
TOOLS = ue.AssetToolsHelpers.get_asset_tools()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require_asset(package_dir: str, name: str, cls: Any, factory: Any) -> Any:
    asset_path = f"{package_dir.rstrip('/')}/{name}"
    asset = ue.load_asset(asset_path) if LIB.does_asset_exist(asset_path) else TOOLS.create_asset(name, package_dir, cls, factory)
    if not isinstance(asset, cls):
        raise RuntimeError(f"Failed to create or load {cls.__name__} at {asset_path}")
    return asset


def save_asset(asset: Any) -> None:
    if not LIB.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"Failed to save asset: {asset.get_path_name()}")


def wave_duration(wave: Any) -> float:
    try:
        return float(wave.get_editor_property("duration"))
    except Exception:
        return float(getattr(wave, "duration", 0.0))


def resolve_loading_behavior(name: str) -> Any:
    mapping = {
        "FORCE_INLINE": ue.SoundWaveLoadingBehavior.FORCE_INLINE,
        "RETAIN_ON_LOAD": ue.SoundWaveLoadingBehavior.RETAIN_ON_LOAD,
        "PRIME_ON_LOAD": ue.SoundWaveLoadingBehavior.PRIME_ON_LOAD,
        "LOAD_ON_DEMAND": ue.SoundWaveLoadingBehavior.LOAD_ON_DEMAND,
        "INHERITED": ue.SoundWaveLoadingBehavior.INHERITED,
    }
    return mapping.get(name.upper(), ue.SoundWaveLoadingBehavior.RETAIN_ON_LOAD)


def build_attenuation(cfg: Dict[str, Any]) -> Any:
    dest_dir = str(cfg["destination_path"]).rstrip("/")
    name = str(cfg["name"])
    LIB.make_directory(dest_dir)
    att = require_asset(dest_dir, name, ue.SoundAttenuation, ue.SoundAttenuationFactory())
    settings = att.get_editor_property("attenuation")
    settings.set_editor_property("attenuate", bool(cfg.get("attenuate", True)))
    settings.set_editor_property("spatialize", bool(cfg.get("spatialize", True)))
    inner = float(cfg.get("inner_radius", 150.0))
    falloff = float(cfg.get("falloff_distance", 2400.0))
    settings.set_editor_property("attenuation_shape_extents", ue.Vector(inner, 0.0, 0.0))
    settings.set_editor_property("falloff_distance", falloff)
    att.set_editor_property("attenuation", settings)
    save_asset(att)
    return att


def build_concurrency(cfg: Dict[str, Any]) -> Any:
    dest_dir = str(cfg["destination_path"]).rstrip("/")
    name = str(cfg["name"])
    LIB.make_directory(dest_dir)
    con = require_asset(dest_dir, name, ue.SoundConcurrency, ue.SoundConcurrencyFactory())
    settings = con.get_editor_property("concurrency")
    settings.set_editor_property("max_count", int(cfg.get("max_count", 6)))
    settings.set_editor_property("limit_to_owner", bool(cfg.get("limit_to_owner", False)))
    rule_name = str(cfg.get("resolution_rule", "STOP_OLDEST")).upper()
    rule = getattr(ue.MaxConcurrentResolutionRule, rule_name, ue.MaxConcurrentResolutionRule.STOP_OLDEST)
    settings.set_editor_property("resolution_rule", rule)
    con.set_editor_property("concurrency", settings)
    save_asset(con)
    return con


def run_import() -> None:
    spec_env = os.environ.get("FPSGAME_AUDIO_IMPORT_SPEC")
    if not spec_env:
        raise RuntimeError("FPSGAME_AUDIO_IMPORT_SPEC environment variable is required")
    spec_path = Path(spec_env).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    project_root = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve()

    dirty = {p.get_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()}

    attenuation_cache: Dict[str, Any] = {}
    for key, acfg in (spec.get("attenuations") or {}).items():
        attenuation_cache[key] = build_attenuation(acfg)

    concurrency_cache: Dict[str, Any] = {}
    for key, ccfg in (spec.get("concurrencies") or {}).items():
        concurrency_cache[key] = build_concurrency(ccfg)

    imported_records: List[Dict[str, Any]] = []
    for item in spec.get("sounds", []):
        wav_path = Path(item["wav_path"])
        if not wav_path.is_absolute():
            wav_path = (project_root / wav_path).resolve()
        if not wav_path.exists():
            raise RuntimeError(f"Master WAV missing: {wav_path}")

        dest_path = str(item["destination_path"]).rstrip("/")
        asset_name = str(item["asset_name"])
        full_pkg = f"{dest_path}/{asset_name}"
        if full_pkg in dirty:
            raise RuntimeError(f"Refusing to overwrite dirty package: {full_pkg}")

        LIB.make_directory(dest_path)

        # Avoid silent skip when replacing owned assets (monster-audio.md reimport lesson)
        if bool(item.get("force_reimport", False)) and LIB.does_asset_exist(full_pkg):
            LIB.delete_asset(full_pkg)

        task = ue.AssetImportTask()
        task.filename = str(wav_path)
        task.destination_path = dest_path
        task.destination_name = asset_name
        task.automated = True
        task.replace_existing = True
        task.save = False
        TOOLS.import_asset_tasks([task])

        if not task.imported_object_paths:
            raise RuntimeError(f"UE SoundWave import failed for {wav_path} -> {full_pkg}")

        wave = ue.load_asset(task.imported_object_paths[0])
        if not isinstance(wave, ue.SoundWave):
            raise RuntimeError(f"Imported object is not USoundWave: {task.imported_object_paths[0]}")

        wave.set_editor_property("looping", bool(item.get("looping", False)))
        wave.set_editor_property("volume", float(item.get("volume", 1.0)))
        if "pitch" in item:
            wave.set_editor_property("pitch", float(item["pitch"]))
        wave.set_editor_property("compression_quality", int(item.get("compression_quality", 85)))
        if item.get("compression_type"):
            ctype = getattr(ue.SoundAssetCompressionType, str(item["compression_type"]).upper(), None)
            if ctype is not None:
                wave.set_sound_asset_compression_type(ctype)
        if item.get("sound_class_from"):
            baseline = ue.load_asset(str(item["sound_class_from"]))
            if baseline:
                wave.set_editor_property("sound_class_object", baseline.get_editor_property("sound_class_object"))

        behavior = str(item.get("loading_behavior", "")).strip()
        if not behavior:
            dur = wave_duration(wave)
            if dur <= 3.0 and not bool(item.get("looping", False)):
                behavior = "FORCE_INLINE"
            elif dur <= 20.0:
                behavior = "RETAIN_ON_LOAD"
            else:
                behavior = "LOAD_ON_DEMAND"
        wave.set_editor_property("loading_behavior", resolve_loading_behavior(behavior))

        att_ref = item.get("attenuation")
        if att_ref:
            att_obj = attenuation_cache.get(att_ref) if att_ref in attenuation_cache else ue.load_asset(att_ref)
            if att_obj:
                wave.set_editor_property("attenuation_settings", att_obj)

        con_ref = item.get("concurrency")
        if con_ref:
            con_obj = concurrency_cache.get(con_ref) if con_ref in concurrency_cache else ue.load_asset(con_ref)
            if con_obj:
                wave.set_editor_property("override_concurrency", False)
                wave.set_editor_property("concurrency_set", {con_obj})

        wav_sha = sha256_file(wav_path)
        LIB.set_metadata_tag(wave, "FPSGAME_AudioPipeline", "ColabAudioWorkflow")
        LIB.set_metadata_tag(wave, "FPSGAME_MasterSha256", wav_sha)
        if item.get("source_provenance"):
            LIB.set_metadata_tag(wave, "FPSGAME_AudioProvenance", str(item["source_provenance"]))

        save_asset(wave)
        imported_records.append(
            {
                "asset_path": wave.get_path_name(),
                "package_path": full_pkg,
                "wav_path": str(wav_path),
                "wav_sha256": wav_sha,
                "duration_sec": round(wave_duration(wave), 4),
                "looping": bool(item.get("looping", False)),
                "loading_behavior": behavior,
                "attenuation": att_ref,
                "concurrency": con_ref,
            }
        )

    receipt = {
        "schema_version": 1,
        "imported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "spec_path": str(spec_path),
        "attenuations": {k: v.get_path_name() for k, v in attenuation_cache.items()},
        "concurrencies": {k: v.get_path_name() for k, v in concurrency_cache.items()},
        "sounds": imported_records,
        "user_auditioned": False,
        "gameplay_tested": False,
    }
    receipt_env = os.environ.get("FPSGAME_AUDIO_IMPORT_RECEIPT")
    if receipt_env:
        rpath = Path(receipt_env).resolve()
        rpath.parent.mkdir(parents=True, exist_ok=True)
        rpath.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    ue.log(f"FPSGAME_AUDIO_IMPORTED count={len(imported_records)}")


if __name__ == "__main__":
    run_import()
