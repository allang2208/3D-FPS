"""Extract physical interface dimensions for authoring, without rendering."""
import bpy, json
from pathlib import Path
from collections import Counter
from mathutils import Matrix
O = Path(__file__).resolve().parent
report = {}
def bounds(points):
    return [[round(min(p[i] for p in points)*100, 6) for i in range(3)], [round(max(p[i] for p in points)*100, 6) for i in range(3)]]
bpy.ops.wm.open_mainfile(filepath=str(O.parent / 'M24ThumbAnatomy20261028/M24_ThumbAnatomy_Editable.blend'), use_scripts=False)
ob=bpy.data.objects['M24_base']
rail=[v.co for v in ob.data.vertices if abs(v.co.x)<.014 and v.co.z>.13]
report['rail']={'bounds_blender_cm':bounds(rail),'crown_bounds_cm':bounds([v for v in rail if v.z>.14482]),'heights_cm':Counter(round(v.z*100,4) for v in rail).most_common(15),'points_cm':[[round(c*100,5) for c in v] for v in rail]}
rig=bpy.data.objects['M24_V9_Rig']
poses=json.loads((O.parent/'M24ThumbAnatomy20261028/final_poses.json').read_text())['fire']
report['grasp_centers_source_cm']={}
for frame in (19,25,30,35,36,40):
    pose=poses[frame]
    into_source=rig.data.bones['WPN_root'].matrix_local @ Matrix(pose['WPN_root']).inverted()
    report['grasp_centers_source_cm'][str(frame)]={n:[round(c*100,4) for c in (into_source @ Matrix(pose[n])).translation] for n in ('thumb_01_r','thumb_02_r','thumb_03_r','index_01_r','hand_r')}
for f in (O/'Sources').glob('*.fbx'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(f))
    obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
    pts=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
    report[f.stem]={'bounds_blender_cm':bounds(pts),'materials':{}}
    for o in obs:
        for i,m in enumerate(o.data.materials):
            indices={v for p in o.data.polygons if p.material_index==i for v in p.vertices}
            ps=[o.matrix_world@o.data.vertices[v].co for v in indices]
            if ps:report[f.stem]['materials'][m.name]={'bounds_cm':bounds(ps),'vertices':len(ps)}
    # Horizontal surfaces below the body expose saddle and clamp contact heights.
    levels=Counter()
    saddle=Counter()
    for o in obs:
        for p in o.data.polygons:
            vs=[o.matrix_world@o.data.vertices[v].co for v in p.vertices]
            if max(v.z for v in vs)-min(v.z for v in vs)<.00001:
                levels[round(vs[0].z*100,4)]+=p.area
                center=sum(vs,vs[0]*0)/len(vs)
                if abs(center.y)<.008 and center.z<.015 and p.normal.z<-.9:
                    saddle[round(vs[0].z*100,4)]+=p.area
    report[f.stem]['horizontal_area_levels']=levels.most_common(12)
    report[f.stem]['saddle_levels']=saddle.most_common(8)
    contacts={'holographic':.1929,'eoth_holographic':.1374,'panoramic_red_dot':.25,'prism_scope_2x':.125,'lpvo_1_6x':.125,'kv_scope_4x':.0065,'thermal_scope':0.}
    if f.stem in contacts:
        foot=[p for p in pts if abs(p.z*100-contacts[f.stem])<.003 and abs(p.y)<.025]
        report[f.stem]['contact_bounds_cm']=bounds(foot)
(O/'interfaces.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_OPTIC_INTERFACES_MEASURED',flush=True)
