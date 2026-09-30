import bpy,sys,json,numpy as np
args=sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=args[0],use_anim=False,ignore_leaf_bones=False,automatic_bone_orientation=False)
inp=json.loads(open(r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothFeed33\inputs.json').read())['meshes']['201'];ue={n:v[:3] for n,v in zip(inp['names'],inp['rest'])}
arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
print('ARM',arm.name,tuple(arm.location),tuple(arm.rotation_euler),tuple(arm.scale))
for o in bpy.context.scene.objects: print('OBJ',o.name,o.type,o.parent and o.parent.name,tuple(round(x,3) for x in o.rotation_euler),tuple(round(x,4) for x in o.scale))
for n in ['SK_M4_Infima','VM_Root','root','head','hand_l','hand_r','WPN_root','LMG201_Cover','LMG201_Box','New_LMG201_Box','interaction','center_of_mass','ik_hand_gun','WPN_SOCKET_Muzzle']:
  b=arm.data.bones.get(n)
  if b: print('BONE',n,'blender',tuple(round(x,4) for x in (arm.matrix_world@b.head_local)),'ue',tuple(round(x,3) for x in ue.get(n,[0,0,0])))
