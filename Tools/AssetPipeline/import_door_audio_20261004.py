"""门族开/关/铁/锁晃/解锁五条音效导入（commandlet）。"""
import os, unreal
SRC = r"D:\FPS3D\FPSGAME\SourceAssets\DoorAudio20261003\Masters"
DEST = "/Game/Audio/Interactions/DoorAudio20261004"
NAMES = ["S_Door_Open", "S_Door_Close", "S_Door_Iron", "S_Door_LockedJiggle", "S_Door_Unlock"]
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
for n in NAMES:
    a = unreal.load_asset(f"{DEST}/{n}.{n}", unreal.SoundWave)
    out.append(f"{n}: dur={a.get_editor_property('duration'):.2f} rate={a.get_editor_property('sample_rate')}" if a else f"{n}: LOAD FAILED")
unreal.log_warning(f"[DoorAudio] {out}")
print("CMDLET_DONE", out)
