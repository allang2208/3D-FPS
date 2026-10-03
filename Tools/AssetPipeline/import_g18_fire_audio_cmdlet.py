"""G18 开火声 v2 导入（commandlet 版）：逻辑同 import_g18_fire_audio_20261003.py。"""
import os, unreal
SRC = r"D:\FPS3D\FPSGAME\SourceAssets\G18FireAudio20261003\Masters"
DEST = "/Game/Weapons/G18/Integrated20260929/Audio"
NAMES = ["S_G18_Fire_01", "S_G18_Fire_02", "S_G18_Fire_03", "S_G18_Fire_04"]

tasks = []
for n in NAMES:
    t = unreal.AssetImportTask()
    t.filename = os.path.join(SRC, n + ".wav")
    t.destination_path = DEST
    t.destination_name = n
    t.automated = True
    t.save = True
    t.replace_existing = True
    t.factory = unreal.SoundFactory()
    tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

out = []
for n in NAMES + ["S_G18_Fire"]:
    p = f"{DEST}/{n}.{n}"
    a = unreal.load_asset(p, unreal.SoundWave)
    if a is None:
        out.append(f"{n}: LOAD FAILED")
        continue
    out.append(f"{n}: dur={a.get_editor_property('duration'):.3f} rate={a.get_editor_property('sample_rate')}")
unreal.log_warning(f"[G18FireAudio-cmdlet] {out}")
print("CMDLET_DONE", out)
