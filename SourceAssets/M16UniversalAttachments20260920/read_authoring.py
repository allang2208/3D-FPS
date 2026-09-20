import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
def rows(m):return [list(r) for r in m]
def bounds(pts):return [[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)]
out={'sources':{},'donors':{}}
for key,part in json.loads((O/'sources.json').read_text()).items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=part['fbx'])
 pts=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]
 out['sources'][key]={'bounds':bounds(pts)}
bpy.ops.wm.open_mainfile(filepath=str(S/'M16Gameplay20260919/M16_Manny_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];root=r.data.bones['WPN_root'].matrix_local
out['rest']={b.name:rows(b.matrix_local) for b in r.data.bones}
out['m16_parts']={o.name:bounds([root.inverted()@r.matrix_world.inverted()@o.matrix_world@v.co for v in o.data.vertices]) for o in bpy.context.scene.objects if o.name.startswith('M16A2_')}
out['images']=[{'name':im.name,'file':bpy.path.abspath(im.filepath)} for im in bpy.data.images]
sources={'vertical':'MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend','canted':'VREGripExtensions20260912/Final/m4/canted/A_M4_Canted_idle.blend','prism':'VREGripExtensions20260912/Final/m4/prism/A_M4_Prism_idle.blend','angled':'AngledForegrip20260910/WristNatural/A_M4_Foregrip_idle.blend','drum':'M4DrumContact20260910/M4_DrumContact_Editable.blend'}
for key,file in sources.items():
 bpy.ops.wm.open_mainfile(filepath=str(S/file));r=bpy.data.objects['SK_M4_Infima']
 if key=='angled':r.animation_data.action=bpy.data.actions['A_M4_Foregrip_idle']
 if key=='drum':
  out['drum_actions']=[a.name for a in bpy.data.actions];r.animation_data.action=bpy.data.actions['A_M4_DrumContact_reload']
 a=r.animation_data.action;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
 root=r.pose.bones['WPN_root'].matrix;rear=r.data.bones['WPN_RearSight'].matrix_local;front=r.data.bones['WPN_FrontSight'].matrix_local
 x=(front.translation-rear.translation).normalized();z=rear.to_3x3()@Vector((0,0,1));z=(z-x*x.dot(z)).normalized();F=Matrix((x,z.cross(x),z)).transposed().to_4x4();F.translation=rear.translation
 mount=r.data.bones['WPN_root'].matrix_local.inverted()@F@Matrix.Translation((.27,0,-.0805))
 out['donors'][key]={'source':str(S/file),'action':a.name,'mount':rows(mount),'hand_in_mount':rows((root@mount).inverted()@r.pose.bones['hand_l'].matrix),'pose':{b.name:rows(root.inverted()@b.matrix) for b in r.pose.bones},'finger_basis':{b.name:rows(b.matrix_basis) for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('thumb','index','middle','ring','pinky'))},'rest':{b.name:rows(b.matrix_local) for b in r.data.bones}}
(O/'authoring.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('AUTHORING_INPUTS',json.dumps({'sources':out['sources'],'m16_parts':out['m16_parts'],'images':out['images'],'drum_actions':out['drum_actions']}),flush=True)
