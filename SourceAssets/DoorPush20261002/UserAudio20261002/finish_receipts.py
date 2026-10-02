"""Record the completed replacement, preserving previous door/audio history."""
from pathlib import Path
import json
import shutil

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
import_receipt = json.loads((HERE / "import-receipt.json").read_text(encoding="utf-8"))
if import_receipt["status"] != "imported_and_saved":
    raise RuntimeError("Audio asset has not been saved; keep the integration record unchanged")

production_path = HERE / "production-receipt.json"
production = json.loads(production_path.read_text(encoding="utf-8-sig"))
production.update(status="wav_authored_unreal_asset_imported_and_saved",
                  output_duration_seconds=import_receipt["duration_seconds"],
                  output_channels=import_receipt["channels"],
                  unreal_import_receipt="import-receipt.json")

integration_path = HERE.parent / "integration-completion.json"
history = HERE / "BeforeRecords"
history.mkdir(exist_ok=True)
if not (history / integration_path.name).exists():
    shutil.copy2(integration_path, history / integration_path.name)
integration = json.loads(integration_path.read_text(encoding="utf-8-sig"))
old_audio = integration["audio_integration"]
integration["previous_web_candidate_audio_integration"] = old_audio.copy()
prefix = "SourceAssets/DoorPush20261002/UserAudio20261002/"
new_audio = old_audio.copy()
for key in ("source_page", "source_format", "license"):
    new_audio.pop(key, None)
new_audio.update(
    status="user_provided_soundwave_replaced_and_saved",
    source_audio=prefix + "S_DoorPushImpact.wav",
    source_mp3="D:/FPS3D/资产/音效/撞门.mp3",
    source_origin="User-provided local MP3",
    source_format="Complete MP3 decoded to 48 kHz 16-bit PCM WAV; original channels retained",
    license="User-provided; no third-party license claim assigned",
    duration_seconds=import_receipt["duration_seconds"],
    channels=import_receipt["channels"],
    production_receipt=prefix + "production-receipt.json",
    import_receipt=prefix + "import-receipt.json",
    audio_asset_backup=prefix + "BeforeAsset",
    import_attempt="Existing-editor Python import completed and SoundWave saved",
    import_log="Saved/DoorPushUserAudio20261002/import-live-editor-02.txt",
    background_import_commandlet_run=False,
    imported=True, asset_saved=True, auditioned=False, runtime_tested=False,
)
integration["audio_integration"] = new_audio
integration["audio_search"]["status"] = "historical_search_candidate_superseded_by_user_audio"
integration["user_audio_replacement"] = {
    "date": "2026-10-02", "imported_and_saved": True,
    "native_code_changed": False, "native_build_required": False,
    "interactive_editor_started_by_this_replacement": False,
    "game_tested": False, "audio_auditioned": False,
}
for path, data in ((production_path, production), (integration_path, integration)):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
doc_paths = (PROJECT / "Docs/Gameplay/door-push-audio-candidates-20261002.md",
             PROJECT / "Docs/Gameplay/sprint-door-push-20261002.md")
for path in doc_paths:
    saved = history / path.name
    if not saved.exists():
        shutil.copy2(path, saved)
duration = import_receipt["duration_seconds"]
channels = import_receipt["channels"]
current = (
    "## 用户指定音效替换（当前，2026-10-02）\n\n"
    "撞门声音已替换为用户提供的 `D:/FPS3D/资产/音效/撞门.mp3`。"
    f"完整转换为 {duration:.6f} s、48 kHz、16-bit PCM、{channels} 声道 WAV，"
    "保留录音长度和原声道，不裁剪、不归一化。来源按用户提供记录，不继承旧候选的 CC0 声明。\n\n"
    "同一个 SoundWave `/Game/Audio/Interactions/DoorPush20261002/S_DoorPushImpact` "
    "已通过现有编辑器 Python 连接导入并保存；保留原音量、音高、加载方式及音频分类。"
    "运行逻辑仍为成功开门后的 0.36 s 事件播放一次，音量倍率 0.85，独立于镜头抖动设置。"
    "制作源、旧资产备份和本次回执位于 `SourceAssets/DoorPush20261002/UserAudio20261002/`；"
    "导入输出为 `Saved/DoorPushUserAudio20261002/import-live-editor-02.txt`。"
    "本次只替换资产，不需要原生编译；未试听、未运行游戏测试。\n\n"
)
path = doc_paths[0]
text = path.read_text(encoding="utf-8-sig")
text = text.replace("## 本轮实际采用", current + "## 已替换的旧音效来源", 1)
text = text.replace("本轮采用原作者公开预览中的单次撞击，", "旧版采用原作者公开预览中的单次撞击，", 1)
path.write_text(text, encoding="utf-8")
path = doc_paths[1]
text = path.read_text(encoding="utf-8-sig")
text = text.replace("采用 Kodack", "旧版采用 Kodack", 1)
text = text.rstrip() + "\n\n" + current
path.write_text(text, encoding="utf-8")
print("User audio replacement records saved.")
