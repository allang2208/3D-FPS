"""Read-only: how much geometry did the generated plaza add?

Counts the plaza's generated actors per static mesh and computes the same source-geometry
rank the performance snapshot uses:
    (triangles + .1 * vertices + 2500 * material slots) * instances
so the plaza's share of `all_rank_total` can be compared against the exported snapshot.
No edits, no save, no PIE.
"""
import json
import traceback
from collections import defaultdict
from pathlib import Path

import unreal

HERE = Path(__file__).parent
TAG_GEN = 'ColdSteel.MainPlaza.Generated'

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# all_rank_total reported by the perf snapshot at 15:33:31Z
SNAPSHOT_ALL_RANK = 20691645.0


def run():
    counts = defaultdict(int)
    for actor in api.get_all_level_actors():
        if TAG_GEN not in [str(t) for t in actor.tags]:
            continue
        if not isinstance(actor, unreal.StaticMeshActor):
            continue
        comp = actor.static_mesh_component
        mesh = comp.static_mesh if comp else None
        counts[mesh.get_path_name() if mesh else '<none>'] += 1

    rows = []
    total_tris = 0
    total_rank = 0.0
    for path, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        mesh = unreal.load_asset(path) if path != '<none>' else None
        if mesh is None:
            continue
        tris = mesh.get_num_triangles(0)
        verts = mesh.get_num_vertices(0)
        mats = mesh.get_editor_property('static_materials')
        slots = len(mats) if mats else 1
        per = tris + 0.1 * verts + 2500.0 * slots
        rank = per * n
        total_tris += tris * n
        total_rank += rank
        bb = mesh.get_bounding_box()
        rows.append(dict(mesh=path.split('.')[-1], instances=n, triangles=tris, vertices=verts,
                         material_slots=slots, triangles_total=tris * n,
                         rank=round(rank, 1),
                         size_cm=[round(bb.max.x - bb.min.x, 1), round(bb.max.y - bb.min.y, 1),
                                  round(bb.max.z - bb.min.z, 1)]))
    return dict(rows=rows, plaza_instances=sum(counts.values()),
                plaza_triangles=total_tris, plaza_rank=round(total_rank, 1),
                snapshot_all_rank=SNAPSHOT_ALL_RANK,
                plaza_share_of_snapshot=round(total_rank / SNAPSHOT_ALL_RANK, 4),
                scene_rank_without_plaza=round(SNAPSHOT_ALL_RANK - total_rank, 1))


try:
    result = run()
    (HERE / 'plaza_geometry_cost.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('COST_OK instances=%d triangles=%d rank=%.0f share_of_scene=%.1f%%'
          % (result['plaza_instances'], result['plaza_triangles'], result['plaza_rank'],
             result['plaza_share_of_snapshot'] * 100))
    print('SCENE_RANK_WITHOUT_PLAZA %.0f  (snapshot reported %.0f)'
          % (result['scene_rank_without_plaza'], result['snapshot_all_rank']))
    for r in result['rows']:
        print('  %-28s n=%-4d tris/inst=%-8d tris_total=%-10d slots=%d  %s'
              % (r['mesh'], r['instances'], r['triangles'], r['triangles_total'],
                 r['material_slots'], r['size_cm']))
except Exception:
    (HERE / 'plaza_geometry_cost_error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    print('COST_FAILED')
    raise
