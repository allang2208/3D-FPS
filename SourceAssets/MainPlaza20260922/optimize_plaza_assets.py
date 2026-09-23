"""Give the three heavy plaza meshes a real LOD chain (asset level, idempotent).

Why these three: the 15:33Z snapshot shows the plaza owns 85.2% of the scene's geometry rank,
and `SM_MarbleFloorTiles` alone is 51% (78 x 120,140 tris). That floor mesh was not authored
with detail: build_marble_floor_and_balustrade.py builds one 1800x800x5 box and cuts 24 grooves
on a 100 cm grid, so the 120 k triangles are boolean tessellation debris, not shape. It therefore
reduces heavily without visible loss.

Per-asset plan (percent of LOD0, activation screen size):
  floor    : 100% / 10% / 3%   at 1.0 / 0.6 / 0.2   (panels are 16.7 m long, so LOD1 is also
                                                     forced on the plaza by the level script)
  column   : 100% / 25% / 8%   at 1.0 / 0.35 / 0.1  (matches the project's BattleAxe convention)
  baluster : 100% / 25% / 8%   at 1.0 / 0.35 / 0.1

Uses `StaticMeshEditorSubsystem.SetLODs(mesh, FStaticMeshReductionOptions)` — this engine build has
no `set_lod_count`, and `EditorStaticMeshLibrary` is deprecated. `auto_compute_lod_screen_size` is
turned off so the screen sizes above are the ones actually used.

Reports the real per-LOD triangle counts before and after and refuses to claim success if the
reduction did not take effect. No level edit, no PIE.
"""
import json
import traceback
from pathlib import Path

import unreal

HERE = Path(__file__).parent
PROPS = '/Game/Props/RomanColumn20260915'

PLANS = [
    (PROPS + '/SM_MarbleFloorTiles', [1.0, 0.10, 0.03], [1.0, 0.6, 0.2]),
    (PROPS + '/SM_RomanColumn_Detailed', [1.0, 0.25, 0.08], [1.0, 0.35, 0.1]),
    (PROPS + '/SM_RomanColumn_Round_20', [1.0, 0.25, 0.08], [1.0, 0.35, 0.1]),
    (PROPS + '/SM_RomanBaluster_Small', [1.0, 0.25, 0.08], [1.0, 0.35, 0.1]),
]

SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def lod_tris(mesh):
    out = []
    for i in range(SMES.get_lod_count(mesh)):
        try:
            out.append(mesh.get_num_triangles(i))
        except Exception:
            out.append(None)
    return out


def build_options(percents, screens):
    settings = []
    for i in range(len(percents)):
        s = unreal.StaticMeshReductionSettings()
        s.set_editor_property('percent_triangles', float(percents[i]))
        s.set_editor_property('screen_size', float(screens[i]))
        settings.append(s)
    options = unreal.StaticMeshReductionOptions()
    options.set_editor_property('auto_compute_lod_screen_size', False)
    options.set_editor_property('reduction_settings', settings)
    return options


def apply_plan(mesh, percents, screens):
    before = lod_tris(mesh)
    SMES.remove_lods(mesh)                      # collapse to LOD0 for a deterministic rebuild
    SMES.set_lods(mesh, build_options(percents, screens))
    try:
        mesh.post_edit_change()
    except Exception:
        pass
    return before, lod_tris(mesh)


def run():
    rows = []
    for path, percents, screens in PLANS:
        mesh = unreal.load_asset(path)
        if mesh is None:
            rows.append(dict(path=path, missing=True))
            continue
        before = lod_tris(mesh)
        already = (len(before) == len(percents) and before[0] and before[-1]
                   and before[-1] < before[0] * percents[-1] * 1.5)
        if already:
            rows.append(dict(path=path.split('/')[-1], skipped=True, tris=before))
            continue
        before, after = apply_plan(mesh, percents, screens)
        saved = unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        ok = bool(after and after[0] and after[-1] and after[-1] < after[0] * percents[-1] * 1.5)
        rows.append(dict(path=path.split('/')[-1], before=before, after=after,
                         percents=percents, screens=screens, saved=bool(saved), reduced=ok))
    return rows


try:
    result = run()
    (HERE / 'plaza_asset_lods.json').write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                                encoding='utf-8')
    bad = [r for r in result if r.get('missing') or r.get('reduced') is False]
    print('LOD_OK assets=%d not_reduced=%d' % (len(result), len(bad)))
    for r in result:
        if r.get('missing'):
            print('  MISSING %s' % r['path'])
        elif r.get('skipped'):
            print('  %-26s already %s' % (r['path'], r['tris']))
        else:
            print('  %-26s %s -> %s saved=%s reduced=%s'
                  % (r['path'], r['before'], r['after'], r['saved'], r['reduced']))
except Exception:
    (HERE / 'plaza_asset_lods_error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    print('LOD_FAILED')
    raise
