import os, unreal
SRC = r"D:\FPS3D\FPSGAME\SourceAssets\G18FireAudio20261003\Masters\S_G18_Fire_02.wav"
DEST = "/Game/Weapons/G18/Integrated20260929/Audio"
t = unreal.AssetImportTask()
t.filename = SRC
t.destination_path = DEST
t.destination_name = "S_G18_Fire"
t.automated = True
t.save = True
t.replace_existing = True
t.factory = unreal.SoundFactory()
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
a = unreal.load_asset(f"{DEST}/S_G18_Fire.S_G18_Fire", unreal.SoundWave)
print(f"CMDLET_DONE S_G18_Fire dur={a.get_editor_property('duration'):.3f} rate={a.get_editor_property('sample_rate')}")
