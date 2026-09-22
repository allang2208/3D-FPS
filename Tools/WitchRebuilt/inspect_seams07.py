import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'Revision07'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Master.blend'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');r.data.pose_position='REST'
report={'bones':{b.name:list((r.matrix_world@b.matrix_local).translation) for b in r.data.bones if b.name in ('pelvis','spine_01','spine_02','spine_03','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','foot_l','ball_l')}}
for name in ('Witch_UpperRobe','Witch_OriginalRobe_Render','WitchRebuilt_Lining','WitchRebuilt_SimulationProxy','WitchRebuilt_UpperSimulationProxy'):
 o=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(o.data)
 bands=[]
 for lo,hi in ((-.1,.1),(.1,.2),(.8,.9),(.9,1.),(1.,1.1),(1.1,1.2),(1.2,1.3)):
  vv=[v for v in bm.verts if lo<=v.co.z<hi and abs(v.co.x)<.27]
  if vv:bands.append({'z':[lo,hi],'n':len(vv),'min':[min(v.co[i] for v in vv) for i in range(3)],'max':[max(v.co[i] for v in vv) for i in range(3)]})
 report[name]={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'min':[min(v.co[i] for v in bm.verts) for i in range(3)],'max':[max(v.co[i] for v in bm.verts) for i in range(3)],'bands':bands,'materials':[m.name for m in o.data.materials],'matrix':str(o.matrix_world)};bm.free()
(OUT/'seams_before.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
