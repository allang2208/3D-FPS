"""Fit the user-supplied GLB to the existing two-handed hammer contact frame."""
import bpy, hashlib, json, shutil, struct
from pathlib import Path
import numpy as np
from mathutils import Matrix
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
for folder in ('Original','Textures','Export','ModulesV1','Records'):
    (P/folder).mkdir(exist_ok=True)
src=Path(r'C:\Users\allan\Downloads\Meshy_AI_Stormbreaker_Runehamm_1028015020_texture.glb')
original=P/'Original'/src.name
if not original.exists():shutil.copy2(src,original)
raw=original.read_bytes();size=struct.unpack_from('<I',raw,12)[0]
gltf=json.loads(raw[20:20+size]);start=28+size
material=gltf['materials'][0]
for key,index in {'BaseColor':material['pbrMetallicRoughness']['baseColorTexture']['index'],
 'MetallicRoughness':material['pbrMetallicRoughness']['metallicRoughnessTexture']['index'],
 'Normal':material['normalTexture']['index']}.items():
    image=gltf['images'][gltf['textures'][index]['source']]
    view=gltf['bufferViews'][image['bufferView']];offset=start+view.get('byteOffset',0)
    (P/'Textures'/(key+'.jpg')).write_bytes(raw[offset:offset+view['byteLength']])
donor=ROOT/'SourceAssets/SteelWarhammer20261014/SprintDragV1/RigSource/SteelWarhammer_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(donor));bpy.context.preferences.filepaths.save_version=0
old=bpy.data.objects['SM_SteelWarhammer'];rig=old.parent
to_local=rig.data.bones['WPN_root'].matrix_local.inverted()@rig.matrix_world.inverted()@old.matrix_world
old_points=np.array([tuple(to_local@v.co) for v in old.data.vertices])
base=float(old_points[:,2].min())
band=old_points[(old_points[:,2]>.08)&(old_points[:,2]<.37)]
target_center=(band[:,:2].min(0)+band[:,:2].max(0))*.5
target_width=np.ptp(band[:,:2],axis=0)
for o in list(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(original))
hammer=next(o for o in bpy.context.scene.objects if o.type=='MESH')
hammer.data.transform(hammer.matrix_world);hammer.matrix_world=Matrix.Identity(4)
points=np.array([tuple(v.co) for v in hammer.data.vertices])
# Source glTF +Y -> Blender +Z, head width +X. No donor's X-long-axis rotation.
source_z=np.array([points[:,2].min(),-.655,.030,.520,.645,points[:,2].max()])
target_z=np.array([base,-.085,.405,.780,.842,base+1.15])
scale=1.15/np.ptp(points[:,2])
band=points[(points[:,2]>-.50)&(points[:,2]<-.08)]
source_center=(band[:,:2].min(0)+band[:,:2].max(0))*.5
radial_fit=target_width/(np.ptp(band[:,:2],axis=0)*scale)
def remap_z(z):
    i=np.clip(np.searchsorted(source_z,z,side='right')-1,0,len(source_z)-2)
    return target_z[i]+(z-source_z[i])*(target_z[i+1]-target_z[i])/(source_z[i+1]-source_z[i])
def fit(q):
    result=q.copy();result[:,2]=remap_z(q[:,2])
    t=np.clip((result[:,2]-.40)/.30,0,1);t=t*t*(3-2*t)
    result[:,:2]=(q[:,:2]-source_center)*scale*(radial_fit[None,:]*(1-t[:,None])+t[:,None])+target_center
    return result
normals=np.array([tuple(n.vector) for n in hammer.data.corner_normals])
jac=np.empty((len(points),3,3))
for k in range(3):
    shift=np.zeros(3);shift[k]=1.e-5
    jac[:,:,k]=(fit(points+shift)-fit(points-shift))/2.e-5
loops=np.array([l.vertex_index for l in hammer.data.loops])
maps=np.linalg.inv(jac).transpose(0,2,1)
normals=np.einsum('nij,nj->ni',maps[loops],normals)
normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1.e-10)
result=fit(points)
hammer.data.vertices.foreach_set('co',result.astype(np.float32).ravel())
for poly in hammer.data.polygons:poly.use_smooth=True
hammer.data.update();hammer.data.normals_split_custom_set(normals.tolist())
hammer.name='SM_ThunderGodHammer';hammer.data.materials[0].name='M_ThunderGodHammerSurface'
bpy.ops.object.select_all(action='DESELECT');hammer.select_set(True);bpy.context.view_layer.objects.active=hammer
bpy.ops.export_scene.fbx(filepath=str(P/'Export/SM_ThunderGodHammer.fbx'),use_selection=True,
 object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThunderGodHammer_Editable.blend'))
hammer.data.calc_loop_triangles()
receipt={'source':str(original),'source_sha256':hashlib.sha256(raw).hexdigest(),
 'vertices':len(hammer.data.vertices),'triangles':len(hammer.data.loop_triangles),'length_cm':115,
 'source_long_axis':'glTF +Y / Blender +Z','source_z_landmarks':source_z.tolist(),'target_z_landmarks_m':target_z.tolist(),
 'grip_center_m':target_center.tolist(),'grip_radial_fit':radial_fit.tolist(),
 'dimensions_cm':(np.ptp(result,axis=0)*100).tolist(),'base_m':base,
 'animation_policy':'reuse live warhammer motion assets, no copied sequences','tested':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('THUNDER_GOD_HAMMER_AUTHORED '+json.dumps(receipt),flush=True)
