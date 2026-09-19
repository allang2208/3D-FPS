import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
root=Path('D:/FPS3D/FPSGAME');out=root/'SourceAssets/M4Replacement'
bpy.ops.wm.open_mainfile(filepath=str(root/'SourceAssets/ArmsRepair20260909/Integrated/SK_AKM_HandsRepair_Source.blend'))
rig=bpy.data.objects['SK_AKM_Viewmodel']
for o in list(bpy.data.objects):
 if o.type=='MESH' and o.parent==rig and o.name.startswith('AKMR_'):bpy.data.objects.remove(o,do_unlink=True)
with bpy.data.libraries.load(str(out/'M4_Assembled_Candidate.blend'),link=False)as(a,b):b.objects=[n for n in a.objects]
fit=Matrix(((-1,0,0,.097),(0,-1,0,.279),(0,0,1,-.076),(0,0,0,1)))
for o in b.objects:
 if o.type!='MESH':continue
 bpy.context.collection.objects.link(o)
bpy.context.view_layer.update()
for o in b.objects:
 if o.type!='MESH':continue
 o.data.transform(rig.matrix_world.inverted()@fit@o.matrix_world)
 o.parent=rig;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=Matrix.Identity(4)
 for g in list(o.vertex_groups):o.vertex_groups.remove(g)
 bone='WPN_SOCKET_Magazine' if o.name.startswith('Magazine') else 'WPN_Trigger' if o.name.startswith('Trigger') else 'WPN_root'
 g=o.vertex_groups.new(name=bone);g.add(list(range(len(o.data.vertices))),1,'REPLACE')
 m=o.modifiers.new('M4RigidBind','ARMATURE');m.object=rig;o.name='M4_'+o.name
 o.hide_render=False;o.hide_set(False)
a=bpy.data.actions['AKM_idle'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'SK_M4_Candidate_Source.blend'))

