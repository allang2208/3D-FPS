"""G18 开火声替换导入（2026-10-03）。

来源：Wikimedia Commons「Glock 18 - Full Auto」（CC BY 3.0，作者 Manobras de Diversão），
从连发录音中截取 4 发孤立单发（34.20s / 36.46s / 58.65s / 76.51s），
48kHz 单声道 PCM16，峰值归一 0.800 对齐现有变体口径。

同名替换 /Game/Weapons/G18/Integrated20260929/Audio/S_G18_Fire_01..04，
路径合同不变（G18WeaponAssets::SoundPath("Fire_%02d")），C++ 零改动。
回退：旧母版保留在 SourceAssets/G18Integration20260929/Audio/，从那里重导即可还原。
"""

import os
import unreal

SRC_DIR = r"D:\FPS3D\FPSGAME\SourceAssets\G18FireAudio20261003\Masters"
DEST = "/Game/Weapons/G18/Integrated20260929/Audio"
NAMES = ["S_G18_Fire_01", "S_G18_Fire_02", "S_G18_Fire_03", "S_G18_Fire_04"]

files = [os.path.join(SRC_DIR, n + ".wav") for n in NAMES]
missing = [f for f in files if not os.path.isfile(f)]
if missing:
    raise RuntimeError(f"missing sources: {missing}")

at = unreal.AssetToolsHelpers.get_asset_tools()
tasks = []
for src, name in zip(files, NAMES):
    t = unreal.AssetImportTask()
    t.filename = src
    t.destination_path = DEST
    t.destination_name = name
    t.automated = True
    t.save = False
    t.replace_existing = True
    t.factory = unreal.SoundFactory()
    tasks.append(t)
at.import_asset_tasks(tasks)
imported = [f"{DEST}/{n}.{n}" for n in NAMES]
unreal.log_warning(f"[G18FireAudio] import tasks done: {len(tasks)}")

# 干净回读终验：导入后重新加载这四个资产，核对时长与采样率。
results = []
for name in NAMES:
    path = f"{DEST}/{name}.{name}"
    asset = unreal.load_asset(path)
    if not asset:
        results.append(f"{name}: LOAD FAILED")
        continue
    dur = asset.get_editor_property("duration")
    rate = asset.get_editor_property("sample_rate")
    results.append(f"{name}: dur={float(dur):.3f}s rate={int(rate)}Hz")
unreal.log_warning(f"[G18FireAudio] verify: {results}")

# 只保存这四个音频资产，不扫全量。
at2 = unreal.AssetToolsHelpers.get_asset_tools()
saved = 0
for name in NAMES:
    path = f"{DEST}/{name}.{name}"
    asset = unreal.load_asset(path, unreal.SoundWave)
    if asset:
        saved += unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=True)
unreal.log_warning(f"[G18FireAudio] saved {saved}/{len(NAMES)}")

print("RESULT", results, "saved", saved)
