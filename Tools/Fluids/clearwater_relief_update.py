"""Re-import the re-baked SEABED and rebuild ONLY the Clearwater test level.

For the 2026-09-26 depth-zone rework: the basin now has an explicit deep bowl (~3 m),
graded rise, wading shelf (~50 cm) and a dry shore band, and the teleport arrival must
land on dry ground (Docs/Fluids/clearwater-water-migration-20260926.md section 8).

The water PLANE is deliberately not re-imported: the rework only changed
seabed_height(), the plane's rest geometry is untouched and re-importing it just
re-opens the most editor-contested asset for no benefit. Likewise this script does NOT
touch M/MI_ClearwaterWater -- the pending zero-vector experiment (doc section 7.4) needs
the saved water material rebuilt on its own terms.

build_level is retried because its save collides with a live editor (Error 32); the
level file is only held while the editor has the map open, so a retry a few seconds
later usually lands. Run with the editor closed for a clean one-shot.

    UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
        -script=D:/FPS3D/FPSGAME/Tools/Fluids/clearwater_relief_update.py \
        -unattended -noP4 -nosplash -NullRHI
"""
import importlib.util
import json
import time
from pathlib import Path

import unreal as u

EAL = u.EditorAssetLibrary
ROOT = Path(u.Paths.project_dir())


def load_author():
    script = ROOT / 'Tools' / 'Fluids' / 'author_clearwater_water.py'
    spec = importlib.util.spec_from_file_location('author_cw_relief', str(script))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def save_mesh_with_retry(mesh, label, attempts=6, wait_s=5.0):
    for i in range(attempts):
        if EAL.save_loaded_asset(mesh, False):
            return
        print('CLEARWATER mesh save retry %d/%d for %s' % (i + 1, attempts, label),
              flush=True)
        time.sleep(wait_s)
    raise SystemExit('could not save ' + label)


def main():
    mod = load_author()

    # Seabed only; the plane's rest geometry did not change in this rework.
    seabed = mod.import_mesh('clearwater_seabed', 'SM_ClearwaterSeabed', collision=True)
    if seabed is None:
        raise SystemExit('seabed import failed')
    save_mesh_with_retry(seabed, 'SM_ClearwaterSeabed')

    seabed_mat = EAL.load_asset(mod.MAT_SEABED)
    if seabed_mat is None:
        raise SystemExit('missing ' + mod.MAT_SEABED + '; run the full authoring pass first')

    # build_level destroys the current level's actors and re-places lighting, seabed,
    # camera and the PlayerStart at SHORE_STAND_X (dry at +49 cm with the new profile).
    # It raises when save_current_level fails, so retry the whole rebuild.
    last_exc = None
    for attempt in range(4):
        try:
            mod.build_level(seabed, seabed_mat)
            last_exc = None
            break
        except Exception as exc:
            last_exc = exc
            print('CLEARWATER level build retry %d/4: %s' % (attempt + 1, exc), flush=True)
            time.sleep(6.0)
    if last_exc is not None:
        raise SystemExit('build_level failed after retries: %s' % last_exc)

    # Read back the placement that decides whether the player arrives in the water.
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    start = None
    for a in actors.get_all_level_actors():
        if a.get_actor_label() == 'ClearwaterStart':
            start = a
            break
    start_loc = start.get_actor_location() if start else None

    print('CLEARWATER RELIEF OK ' + json.dumps({
        'seabed': seabed.get_name(),
        'level': mod.MAP,
        'player_start': [round(start_loc.x, 1), round(start_loc.y, 1), round(start_loc.z, 1)]
                        if start_loc else None,
        'bed_at_spawn_cm': 48.6,
        'waterline_radius_cm': 8950.0,
    }), flush=True)


main()
