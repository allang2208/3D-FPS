import unreal


DESTINATION = "/Game/Weather/Audio"
SOURCES = {
    "S_Rain_Light_Loop": r"E:\3d\3-dfps\assets\sfx\weather\rain_leaves_ground_ccby_v4.wav",
    "S_Rain_Soft_Loop": r"E:\3d\3-dfps\assets\sfx\weather\rain_soft_v2.wav",
    "S_Rain_Patter_Loop": r"E:\3d\3-dfps\assets\sfx\weather\rain_patter_v2.wav",
}


asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
asset_subsystem.make_directory(DESTINATION)
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

for asset_name, source_file in SOURCES.items():
    package_path = f"{DESTINATION}/{asset_name}"
    sound_wave = unreal.load_asset(package_path)
    if sound_wave is None:
        task = unreal.AssetImportTask()
        task.filename = source_file
        task.destination_path = DESTINATION
        task.destination_name = asset_name
        task.automated = True
        task.replace_existing = False
        task.save = False
        asset_tools.import_asset_tasks([task])
        sound_wave = unreal.load_asset(package_path)

    if sound_wave is None:
        raise RuntimeError(f"WEATHER_AUDIO_IMPORT_FAILED {asset_name} from {source_file}")

    sound_wave.set_editor_property("looping", True)
    if not asset_subsystem.save_loaded_asset(sound_wave, False):
        raise RuntimeError(f"WEATHER_AUDIO_SAVE_FAILED {package_path}")
    unreal.log(f"WEATHER_AUDIO_READY {package_path} looping={sound_wave.get_editor_property('looping')}")

unreal.log(f"WEATHER_AUDIO_IMPORT_COMPLETE count={len(SOURCES)}")
