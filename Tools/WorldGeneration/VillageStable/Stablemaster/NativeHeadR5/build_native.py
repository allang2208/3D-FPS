"""Keep the reference sculpt and skin in the existing centimetre rig, with a shared collar boundary."""
from pathlib import Path
import bpy
import bmesh
import numpy as np
import math
from mathutils import Matrix

project=Path(__file__).resolve().parents[5]
src=project/'SourceAssets/HillsVillageStable/StablemasterMeshyR3'
dst=src.parent/'StablemasterHeadR5'
dst.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.gltf(filepath=str(src/'Rig/Rig.glb'),disable_bone_shape=True)
rig,= [o for o in bpy.context.scene.objects if o.type=='ARMATURE']
body,= [o for o in bpy.context.scene.objects if o.type=='MESH']
def joint(name):
    return rig.matrix_world@rig.data.bones[name].head_local
across=joint('LeftArm')-joint('RightArm')
origin=(joint('LeftFoot')+joint('RightFoot'))*.5
world=body.matrix_world.copy()
zs=[(world@v.co).z for v in body.data.vertices]
origin.z=min(zs)
basis=Matrix.Scale(168./(max(zs)-min(zs)),4)@Matrix.Rotation(-math.atan2(across.y,across.x),4,'Z')@Matrix.Translation(-origin)
body.data.transform(basis@world,shape_keys=True)
arm_world=rig.matrix_world.copy()
rig.parent=None;rig.matrix_world=Matrix.Identity(4);rig.data.transform(basis@arm_world)
rig.name='Armature';rig.animation_data_clear()
body.parent=rig;body.matrix_parent_inverse=Matrix.Identity(4);body.matrix_basis=Matrix.Identity(4)
body.animation_data_clear()
rig.data.pose_position='POSE'
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
body.name='SK_Stablemaster_Body_R5'
body.data.materials[0].name='M_Stablemaster_Body_0'
head=body.copy();head.data=body.data.copy();head.name='SK_Stablemaster_Head_R5';bpy.context.collection.objects.link(head)
# The two sides use complementary subsets of precisely the same original triangles.
# Preserve custom corner normals, UVs and bone weights on both copies.
normal_tag='native_corner'
m=body.data
normals=np.zeros((len(m.loops),3),'f');m.corner_normals.foreach_get('vector',normals.ravel())
def section(obj,top):
    mesh=obj.data
    attr=mesh.attributes.new(normal_tag,'INT','CORNER')
    attr.data.foreach_set('value',np.arange(len(mesh.loops),dtype=np.int32))
    bm=bmesh.new();bm.from_mesh(mesh)
    def is_head(f):
        v=f.calc_center_median()
        return v.z>144.75+.2*v.y or (v.y>7.7 and v.z>141.8 and abs(v.x)<8.)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if is_head(f)!=top],context='FACES')
    bm.to_mesh(mesh);bm.free()
    ids=np.zeros(len(mesh.loops),np.int32);mesh.attributes[normal_tag].data.foreach_get('value',ids)
    mesh.attributes.remove(mesh.attributes[normal_tag])
    mesh.normals_split_custom_set(normals[ids].tolist());mesh.update()
section(body,False);section(head,True)
mat=head.data.materials[0].copy();mat.name='M_Stablemaster_Head_R5';head.data.materials[0]=mat
mesh=head.data;mesh.calc_loop_triangles()
p=np.asarray([v.co[:] for v in mesh.vertices],'f')
tri=np.asarray([t.vertices[:] for t in mesh.loop_triangles],np.int32)
uv=np.asarray([[mesh.uv_layers.active.data[i].uv[:] for i in t.loops] for t in mesh.loop_triangles],'f')
uv[:,:,1]=1-uv[:,:,1]
np.savez_compressed(dst/'HeadSurface.npz',pos=p,tri=tri,uv=uv)
for o in list(bpy.context.scene.objects):
    if o not in (body,head,rig):bpy.data.objects.remove(o,do_unlink=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
bpy.context.view_layer.update()
for obj in (body,head):
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True);obj.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(dst/(obj.name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=False,apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',axis_forward='Y',axis_up='Z',use_mesh_modifiers=False,mesh_smooth_type='FACE',
        path_mode='STRIP',embed_textures=False)
bpy.ops.wm.save_as_mainfile(filepath=str(dst/'StablemasterNative.blend'),compress=True)
