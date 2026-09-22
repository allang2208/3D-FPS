"""Scoped source diagnosis for surface degeneracy and thrown-arm deformation."""
import bpy,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'Refinement20260922'
report={'scope':'Editable-source geometry and arm chain only; no Chaos/gameplay test','meshes':{}}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Master.blend'))
for o in bpy.context.scene.objects:
    if o.type!='MESH' or 'SimulationProxy' in o.name:continue
    o.data.calc_loop_triangles();areas=[]
    for tri in o.data.loop_triangles:
        a,b,c=[o.data.vertices[i].co for i in tri.vertices];areas.append((b-a).cross(c-a).length*.5)
    report['meshes'][o.name]={'triangles':len(areas),'zero_area_triangles':sum(a<1e-12 for a in areas),
        'below_one_microsquaremeter':sum(a<1e-6 for a in areas),'detail_uv_channels':len(o.data.uv_layers)}
for label,path in [('before',OUT/'Before/Authoring/WitchRebuilt_ThrowPoisonBottle.blend'),('after',ROOT/'Authoring/WitchRebuilt_ThrowPoisonBottle.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE')
    lengths=[];hands=[]
    for f in range(s.frame_start,s.frame_end+1):
        s.frame_set(f);pts=[(r.matrix_world@r.pose.bones[n].matrix).translation for n in ('upperarm_r','lowerarm_r','hand_r')]
        lengths.append([(pts[i+1]-pts[i]).length for i in (0,1)]);hands.append(pts[2].copy())
    report[label]={'duration':(s.frame_end-s.frame_start)/s.render.fps,'fps':s.render.fps,
        'max_segment_variation_cm':max(max(v[j] for v in lengths)-min(v[j] for v in lengths) for j in (0,1))*100,
        'start_end_hand_gap_cm':(hands[-1]-hands[0]).length*100}
(OUT/'source_inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
