"""Read exported FBX UVs and relief range; no authoring or rendering."""
import json,math
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
files=[BASE/'DungeonWallDamage20260923/Authored/SM_RS_Distribution_CombatDoor_Damage0_Tiles.fbx',
       BASE/'DungeonSurfaceRepair20260924/Authored/SM_RS_Distribution_CombatDoor_Shell.fbx']
report={}
for path in files:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    slots={}
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        m=ob.data;m.calc_loop_triangles()
        for p in m.loop_triangles:
            name=m.materials[p.material_index].name
            if not any(k in name for k in ('WallRelief','Concrete')):continue
            r=slots.setdefault(name,{'areas':[],'uv_ratio':[],'depth_y':[],'degenerate_uv':0})
            pts=[ob.matrix_world@m.vertices[i].co for i in p.vertices]
            uv=[m.uv_layers[0].data[i].uv for i in p.loops]
            area=(pts[1]-pts[0]).cross(pts[2]-pts[0]).length*.5
            dua=uv[1]-uv[0];dub=uv[2]-uv[0];ua=abs(dua.x*dub.y-dua.y*dub.x)*.5
            r['areas'].append(area)
            if ua>1e-12:r['uv_ratio'].append(math.sqrt(area/ua))
            else:r['degenerate_uv']+=1
            if abs(p.normal.y)>.98:r['depth_y'].extend(v.y for v in pts if abs(v.y)<.2)
    report[str(path)]={name:{'triangles':len(r['areas']),'area_m2':sum(r['areas']),
                     'metres_per_uv_quantiles':np.percentile(r['uv_ratio'],[0,50,100]).tolist() if r['uv_ratio'] else [],
                     'near_y_bounds_m': [min(r['depth_y']),max(r['depth_y'])] if r['depth_y'] else [],
                     'degenerate_uv_triangles':r['degenerate_uv']} for name,r in slots.items()}
(ROOT/'Receipts/source-uv.json').write_text(json.dumps(report,indent=2))
print('WALL_SOURCE_UV',json.dumps(report),flush=True)
