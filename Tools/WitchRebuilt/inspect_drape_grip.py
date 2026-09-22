import bpy,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'DrapeGrip20260922'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Before/Authoring/WitchRebuilt_Walk.blend'))
s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE');o=bpy.data.objects['Witch_OriginalRobe_Render']
rest={b.name:list((r.matrix_world@b.matrix_local).translation) for b in r.data.bones if b.name in ('hand_r','middle_01_r','index_01_r','pinky_01_r','upperarm_r','lowerarm_r','spine_05','neck_01')}
base=[v.co.copy() for v in o.data.vertices];edges=[tuple(e.vertices) for e in o.data.edges];lengths=[(base[a]-base[b]).length for a,b in edges]
result={'reference_bones_m':rest,'walk_seconds':(s.frame_end-s.frame_start)/s.render.fps,'samples':[]}
for f in [1,round(s.frame_end*.25),round(s.frame_end*.5),round(s.frame_end*.75)]:
    s.frame_set(f);ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());verts=[v.co.copy() for v in ev.data.vertices]
    ratios=sorted((verts[a]-verts[b]).length/l for (a,b),l in zip(edges,lengths) if l>.001)
    result['samples'].append({'frame':f,'max_edge_ratio':max(ratios),'p95_edge_ratio':ratios[int(len(ratios)*.95)]})
(OUT/'diagnosis_source.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
