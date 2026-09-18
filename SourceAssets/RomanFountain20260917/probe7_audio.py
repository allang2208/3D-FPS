"""Probe 7: registry-based FULL sound listing for /Game (EditorAssetLibrary is unreliable remote)."""

import unreal

reg = unreal.AssetRegistryHelpers.get_asset_registry()
for cls_path, label in (("/Script/Engine", "SoundWave"), ("/Script/Engine", "SoundCue"),
                        ("/Script/Engine", "MetaSoundSource"), ("/Script/AudioModulation", "")):
    if not label:
        continue
    try:
        assets = reg.get_assets_by_class(unreal.TopLevelAssetPath(cls_path, label), True)
        names = [str(a.package_name) for a in assets if str(a.package_name).startswith("/Game/")]
        print("[p7] %s total=%d" % (label, len(names)))
        for n in sorted(names)[:150]:
            print("     ", n)
    except Exception as exc:  # noqa: BLE001
        print("[p7] %s failed: %s" % (label, exc))

# ambient-ish actors already in the level? (for naming conventions / prior art)
try:
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    amb = [a.get_actor_label() for a in actor_sub.get_all_level_actors()
           if "Ambient" in a.get_class().get_name() or "Sound" in a.get_class().get_name()]
    print("[p7] sound actors in level: %s" % amb[:20])
except Exception as exc:  # noqa: BLE001
    print("[p7] actor scan failed: %s" % exc)
print("[p7] DONE")
