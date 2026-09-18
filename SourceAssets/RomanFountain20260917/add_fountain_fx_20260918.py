"""Attach the water-jet FX to the 2x fountain: engine Niagara template FountainLightweight at
the pigna tip, attached to RomanFountain1 so it follows if the fountain is moved.

Sound: the full project sound inventory (192 waves + 29 cues, registry-verified) has NO flowing
water loop - the only water-adjacent waves are one-shot footstep splashes. Nothing is faked
here; see README. Runs via remote exec (editor open) with PIE / already-open-level guards.
"""

import os
import time

import unreal

JET = "/Niagara/DefaultAssets/Templates/Systems/FountainLightweight"
LEVEL = "/Game/GameMaps/DayNight_Lighting"
FOUNTAIN_LOC = unreal.Vector(1350.0, -1150.0, 0.0)
TIP_Z = 720.0            # pigna tip world z at 2x scale
JET_SCALE = 1.2          # eyeball default; the template is a demo-scale fountain jet
STARTED = time.time()
LOG = []


def log(m):
    print("[fx] " + m)


def check(label, ok):
    LOG.append((label, bool(ok)))
    log("%-28s %s" % (label, "OK" if ok else "FAIL"))


jet_sys = unreal.load_asset(JET)
check("jet_system_loadable", jet_sys is not None)

try:
    les = None
    for _ in range(30):
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if les is not None:
            break
        time.sleep(2.0)   # a freshly launched editor registers subsystems late
    check("level_editor_subsystem", les is not None)
    # is_in_play_in_editor() ACCESS-VIOLATES in a headless commandlet (no level editor state)
    # - only query it when running inside the real editor (remote-exec sets nothing).
    headless = os.environ.get("FOUNTAIN_HEADLESS") == "1"
    pie = False
    wpath = ""
    if headless:
        log("headless mode - skipping PIE/world queries")
    else:
        pie = les.is_in_play_in_editor() if les else False
        try:
            sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            wpath = sub.get_editor_world().get_path_name() or "" if sub else ""
        except Exception:
            pass
    log("world=%r PIE=%s headless=%s" % (wpath, pie, headless))
    if pie:
        log("PIE active - FX attach skipped, rerun after PIE stops")
        LOG.append(("fx_skipped_pie", True))
    elif "DayNight_Lighting" in wpath or les.load_level(LEVEL):
        actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        fountains = [a for a in actor_sub.get_all_level_actors()
                     if a.get_actor_label() == "RomanFountain1"]
        check("fountain_actor_found", len(fountains) == 1)
        if len(fountains) == 1 and jet_sys:
            fountain = fountains[0]
            tip = unreal.Vector(FOUNTAIN_LOC.x, FOUNTAIN_LOC.y, TIP_Z)

            existing = [a for a in actor_sub.get_all_level_actors()
                        if a.get_actor_label() == "RomanFountainFX_Jet"]
            if existing:
                jet = existing[0]
                nc = jet.get_component_by_class(unreal.NiagaraComponent)
                nc.set_asset(jet_sys)
                log("existing jet refreshed in place")
            else:
                jet = actor_sub.spawn_actor_from_class(unreal.NiagaraActor, tip, unreal.Rotator(0, 0, 0))
                if not jet:
                    log("spawn FAILED")
                    LOG.append(("jet_spawn", False))
                else:
                    jet.set_actor_label("RomanFountainFX_Jet")
                    nc = jet.get_component_by_class(unreal.NiagaraComponent)
                    nc.set_asset(jet_sys)
                    jet.set_actor_scale3d(unreal.Vector(JET_SCALE, JET_SCALE, JET_SCALE))
                    jet.attach_to_actor(fountain, unreal.Name(""),
                                        unreal.AttachmentRule.KEEP_WORLD,
                                        unreal.AttachmentRule.KEEP_WORLD,
                                        unreal.AttachmentRule.KEEP_WORLD, False)
                    log("jet spawned at (%.0f,%.0f,%.0f) scale %.1f, attached to %s" % (
                        tip.x, tip.y, tip.z, JET_SCALE, fountain.get_actor_label()))
            check("jet_parented", jet.get_attach_parent_actor() is not None and
                  jet.get_attach_parent_actor().get_actor_label() == "RomanFountain1")
            check("jet_asset_set", nc.get_asset() is not None)

            saved = les.save_current_level()
            umap = unreal.Paths.convert_relative_path_to_full(
                unreal.Paths.project_content_dir()) + "GameMaps/DayNight_Lighting.umap"
            st1 = os.stat(umap).st_mtime if os.path.exists(umap) else 0
            check("umap_saved", bool(saved) and st1 >= STARTED - 5.0)
except Exception as exc:  # noqa: BLE001
    log("fx section failed: %s" % exc)
    LOG.append(("fx_section", False))

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
