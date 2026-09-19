"""Read authoring geometry and accepted grasp sources for ASH attachment fitting."""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent; S=O.parent
def rows(m):return [list(v) for v in m]
def bounds(points):return [[min(v[i] for v in points),max(v[i] for v in points)] for i in range(3)]
def pose(r,a):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
 return {b.name:b.matrix.copy() for b in r.pose.bones}
def frame(r):
 rear=r.data.bones['WPN_RearSight'].matrix_local;front=r.data.bones['WPN_FrontSight'].matrix_local
 x=(front.translation-rear.translation).normalized();z=rear.to_3x3()@Vector((0,0,1));z=(z-x*x.dot(z)).normalized()
 m=Matrix((x,z.cross(x),z)).transposed().to_4x4();m.translation=rear.translation
 return m
bpy.ops.wm.open_mainfile(filepath=str(S/'ASH12Surface20260919/ASH12_Surface_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];F=frame(r);inv=F.inverted();gun=bpy.data.objects['ASH12_Export']
out={'rail_frame':rows(F),'root_rest':rows(r.data.bones['WPN_root'].matrix_local),'parts':{},'donors':{}}
for mi,mat in enumerate(gun.data.materials):
 ids={i for f in gun.data.polygons if f.material_index==mi for i in f.vertices}
 pts=[inv@r.matrix_world.inverted()@gun.matrix_world@gun.data.vertices[i].co for i in ids]
 out['parts'][mat.name]={'bounds':bounds(pts)}
 if any(k in mat.name for k in ('Front','Sights','Lower','Upper')):
  out['parts'][mat.name]['points']=[list(p) for p in pts]
out['base_idle']={n:rows(m) for n,m in pose(r,bpy.data.actions['ASH12_idle']).items()}
sources={
 'vertical':S/'MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend',
 'canted':S/'VREGripExtensions20260912/Final/m4/canted/A_M4_Canted_idle.blend',
 'prism':S/'VREGripExtensions20260912/Final/m4/prism/A_M4_Prism_idle.blend',
 'angled':S/'AngledForegrip20260910/WristNatural/A_M4_Foregrip_idle.blend'}
for key,file in sources.items():
 bpy.ops.wm.open_mainfile(filepath=str(file));r=bpy.data.objects['SK_M4_Infima']
 action=bpy.data.actions['A_M4_Foregrip_idle'] if key=='angled' else r.animation_data.action
 p=pose(r,action)
 F=frame(r);G=F@Matrix.Translation((.27,0,-.0805))
 fingers=[b for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('thumb','index','middle','ring','pinky'))]
 out['donors'][key]={'source':str(file),'action':r.animation_data.action.name,'root_rest':rows(r.data.bones['WPN_root'].matrix_local),'rail_frame':rows(F),'mount':rows(G),'hand_in_mount':rows(G.inverted()@p['WPN_root']@r.data.bones['WPN_root'].matrix_local.inverted()@Matrix.Identity(4)) if False else rows((p['WPN_root']@r.data.bones['WPN_root'].matrix_local.inverted()@G).inverted()@p['hand_l']), 'fingers':{b.name:rows(b.matrix_basis) for b in fingers}}
(O/'authoring_inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('ASH_ATTACHMENT_INPUTS_WRITTEN',json.dumps({k:v['bounds'] for k,v in out['parts'].items()}),flush=True)
