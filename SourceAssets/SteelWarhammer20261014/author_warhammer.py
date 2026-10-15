"""Prepare the supplied warhammer, preserving its UV/PBR and the pickaxe pose family."""
import bpy, json, struct, shutil
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector
AUTHOR_SOURCE=Path(__file__).resolve().parent; ROOT=AUTHOR_SOURCE.parents[1]
P=Path(globals().get('WARHAMMER_AUTHOR_ROOT',AUTHOR_SOURCE));P.mkdir(parents=True,exist_ok=True)
for d in ('Original','Textures','Export'): (P/d).mkdir(exist_ok=True)
src=Path(r'C:\Users\allan\Downloads\Meshy_AI_Warhammer_1014043833_texture.glb')
dst=P/'Original'/src.name
if not dst.exists():shutil.copy2(src,dst)
raw=dst.read_bytes();size,kind=struct.unpack_from('<II',raw,12);gltf=json.loads(raw[20:20+size]);start=20+size+8
for key,img in zip(('BaseColor','MetallicRoughness','Normal'),gltf['images']):
    view=gltf['bufferViews'][img['bufferView']];a=start+view.get('byteOffset',0)
    (P/'Textures'/(key+'.jpg')).write_bytes(raw[a:a+view['byteLength']])
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/Pickaxe_BareArmsV7.blend'))
skin=next(o for o in bpy.context.scene.objects if o.type=='MESH');native=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
rest={b.name:(native.matrix_world@b.matrix_local).copy() for b in native.data.bones}
skin_data=skin.data.copy();skin_data.use_fake_user=True
skin_data_name=skin_data.name
skin_groups={g.index:g.name for g in skin.vertex_groups}
skin_weights=[[(skin_groups[g.group],g.weight) for g in v.groups] for v in skin.data.vertices]
skin_matrix=skin.matrix_world.copy()
# Keep the native surface across loading a different author file.
native_file=P/'Export'/'bare_surface.blend'
bpy.data.libraries.write(str(native_file),{skin_data},fake_user=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/RusticPickaxe20260919/RusticPickaxe_TwoHand_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];old=bpy.data.objects['Harvest_Pickaxe'];wpn=rig.data.bones['WPN_root'].matrix_local.copy()
old_pts=[wpn.inverted()@rig.matrix_world.inverted()@old.matrix_world@v.co for v in old.data.vertices]
base=min(v.z for v in old_pts)
target={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
for o in list(bpy.context.scene.objects):
    if o!=rig:bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data_clear();rig.data.pose_position='REST'
with bpy.data.libraries.load(str(native_file),link=False) as (a,b):b.meshes=[skin_data_name]
bare_mesh=b.meshes[0];bare=bpy.data.objects.new('Warhammer_BareArmsV7',bare_mesh);bpy.context.scene.collection.objects.link(bare)
for name in sorted({n for ws in skin_weights for n,w in ws}):bare.vertex_groups.new(name=name)
# Native geometry already uses the author's world positions. The FBX bone-axis
# convention differs from the native skeleton, but their joint positions coincide.
# Applying that basis difference to vertices twists the surface a second time.
transforms={n:skin_matrix.copy() for n in target if n in rest}
bare_mesh.calc_loop_triangles();normals=[n.vector.copy() for n in bare_mesh.corner_normals];maps=[]
for v,ws in zip(bare_mesh.vertices,skin_weights):
    valid=[(n,w) for n,w in ws if n in transforms];total=sum(w for n,w in valid) or 1
    m=Matrix(np.zeros((4,4)).tolist())
    for n,w in valid:
        m+=transforms[n]*(w/total);bare.vertex_groups[n].add([v.index],w/total,'REPLACE')
    if not valid:m=Matrix.Identity(4)
    v.co=m@v.co;maps.append(m.to_3x3().inverted_safe().transposed())
bare_mesh.update();bare_mesh.normals_split_custom_set([(maps[l.vertex_index]@normals[l.index]).normalized() for l in bare_mesh.loops])
# FBX reverses texture V. UV1-3 carry signed native skin coordinates rather than
# picture UVs, so compensate before export to preserve the shared skin shader.
for layer in list(bare_mesh.uv_layers)[1:]:
    for corner in layer.data:corner.uv.y=1.-corner.uv.y
color=bare_mesh.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
for poly in bare_mesh.polygons:
    for li in poly.loop_indices:color.data[li].color=(0. if poly.material_index==2 else 1.,0.,0.,1.)
bare.parent=rig;bare.modifiers.clear();mod=bare.modifiers.new('Accepted native bare arms','ARMATURE');mod.object=rig
bpy.ops.import_scene.gltf(filepath=str(dst));hammer=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o!=bare)
hammer.data.transform(hammer.matrix_world);hammer.matrix_world=Matrix.Identity(4)
points=np.array([tuple(v.co) for v in hammer.data.vertices]);lo=points.min(0);hi=points.max(0);scale=1.15/(hi[2]-lo[2])
points*=scale;points[:,2]+=base-points[:,2].min()
grip_mask=(points[:,2]>base+.07)&(points[:,2]<base+.46)
center=(points[grip_mask,:2].min(0)+points[grip_mask,:2].max(0))*.5;points[:,:2]-=center
old_band=np.array([tuple(v) for v in old_pts if .08<v.z<.37]);new_band=points[grip_mask]
old_center=(old_band[:,:2].min(0)+old_band[:,:2].max(0))*.5
ratios=(old_band[:,:2].max(0)-old_band[:,:2].min(0))/(new_band[:,:2].max(0)-new_band[:,:2].min(0))
def fit(p):
    q=p.copy();t=np.clip((q[:,2]-(base+.52))/.18,0,1);t=t*t*(3-2*t)
    q[:,:2]*=ratios[None,:]*(1-t[:,None])+t[:,None];q[:,:2]+=old_center
    return q
normals=np.array([tuple(n.vector) for n in hammer.data.corner_normals]);jac=np.empty((len(points),3,3));eps=1e-5
for k in range(3):
    shift=np.zeros(3);shift[k]=eps;jac[:,:,k]=(fit(points+shift)-fit(points-shift))/(2*eps)
indices=np.array([l.vertex_index for l in hammer.data.loops]);normal_maps=np.linalg.inv(jac).transpose(0,2,1)
normals=np.einsum('nij,nj->ni',normal_maps[indices],normals);normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-10)
hammer.data.vertices.foreach_set('co',fit(points).astype(np.float32).ravel());hammer.data.update();hammer.data.normals_split_custom_set(normals.tolist())
material=hammer.data.materials[0];material.name='M_SteelWarhammerSurface'
for node in material.node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image:
        node.image.pack()
def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[-1]
def export(name,objects):
    select(objects);bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
hammer.name='SM_SteelWarhammer';export(hammer.name,[hammer])
hammer.data.transform(wpn);hammer.parent=rig
vg=hammer.vertex_groups.new(name='WPN_root');vg.add(list(range(len(hammer.data.vertices))),1,'REPLACE')
mod=hammer.modifiers.new('Rigid warhammer','ARMATURE');mod.object=rig
export('SK_SteelWarhammer_BareArmsV7',[hammer,bare,rig])
bpy.ops.wm.save_as_mainfile(filepath=str(P/'SteelWarhammer_Editable.blend'))
hammer.data.calc_loop_triangles()
report={'overall_length_cm':115,'vertices':len(hammer.data.vertices),'triangles':len(hammer.data.loop_triangles),'grip_radial_fit':ratios.tolist(),'base_in_pickaxe_author_frame_m':base,'weapon_root_author_matrix':[list(r) for r in wpn],'materials':[m.name for m in bare.data.materials],'animation_policy':'Shared existing pickaxe sequences, no duplicated animation assets','source':str(dst),'tested':False}
(P/'authored.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
