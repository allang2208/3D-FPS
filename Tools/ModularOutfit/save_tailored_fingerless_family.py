"""Save native author scenes, bake only distinct layouts, export matching pickup."""
import sys
import json
import hashlib
from pathlib import Path
import numpy as np
import bpy

P=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
import build_tailored_fingerless_candidate as lib
from tailored_fingerless_candidate import unit
R=P/'SourceAssets/ModularOutfit20260927/TailoredFingerlessV1'
CAND=P/'SourceAssets/ModularOutfit20260927/TailoredFingerlessCandidate'
(R/'Editable').mkdir(exist_ok=True)


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def baked_uv(obj,d):
    layer=obj.data.uv_layers.new(name='BakedTailoringUV')
    for face,coords in zip(obj.data.polygons,d['uv']):
        for loop,(u,v) in zip(face.loop_indices,coords):layer.data[loop].uv=(u,1-v)
    obj.data.uv_layers.active=layer;layer.active_render=True
    return layer


def material(group):
    folder=R/'Textures' if group=='Shared' else R/'Textures'/group
    maps={name:lib.image(folder/('T_TailoredFingerless_'+name+'.png'),'sRGB' if name=='BaseColor' else 'Non-Color') for name in ('BaseColor','Roughness','Normal')}
    return lib.baked_material(maps)


entries=read(R/'author-manifest.json');layouts={};finished=[]
for entry in entries:
    name=entry['profile'];group=entry['material_group'];d=read(entry['fullshell'])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if entry['bake_representative']:
        lib.T=R/'Textures'/group;lib.T.mkdir(parents=True,exist_ok=True)
        mat,col,rough,bsdf,output=lib.authored_material();mat.use_fake_user=True
        obj=lib.make_mesh(d,mat);layer,maps=lib.bake(obj,mat,col,bsdf,output)
        d['uv']=[[(layer.data[i].uv.x,1-layer.data[i].uv.y) for i in f.loop_indices] for f in obj.data.polygons]
        layouts[group]=d['uv'];mat=lib.baked_material(maps)
        obj.data.materials.clear();obj.data.materials.append(mat)
    else:
        if group!='Shared':d['uv']=layouts[group]
        mat=material(group);obj=lib.make_mesh(d,mat);baked_uv(obj,d)
    obj.name=name+'_TailoredFingerless';obj.data.name=obj.name
    lib.rig(obj,d);obj['CandidateOnly']=False;obj['EquipmentItem']='ue_field_gloves'
    obj['AnimationContract']='Native LeaderPose; existing animation files unchanged'
    blend=R/'Editable'/(name+'_TailoredFingerless.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    # Source UV3 remains in the editable scene; saved game mesh needs 3 channels.
    d.pop('uv3',None)
    full=R/'Authored'/(name+'_baked_fullshell.json');full.write_text(json.dumps(d,separators=(',',':')))
    outer=(np.array(d['uv2'])[:,:,1]==0).all(1);faces=np.array(d['triangles'])[outer];used=np.unique(faces)
    mapping=np.full(len(d['positions']),-1,dtype=int);mapping[used]=np.arange(len(used))
    worn=dict(d);worn.update(positions=np.array(d['positions'])[used].tolist(),weights=[d['weights'][i] for i in used],triangles=mapping[faces].tolist(),triangle_materials=[0]*len(faces))
    for key in ('uv','uv1','uv2'):worn[key]=np.array(d[key])[outer].tolist()
    pos=np.array(worn['positions']);tris=np.array(worn['triangles']);norm=np.zeros_like(pos)
    fn=-np.cross(pos[tris[:,1]]-pos[tris[:,0]],pos[tris[:,2]]-pos[tris[:,0]])
    for k in range(3):np.add.at(norm,tris[:,k],fn)
    worn['normals']=unit(norm)[tris].tolist()
    path=R/'Authored'/(name+'.json');path.write_text(json.dumps(worn,separators=(',',':')))
    finished.append(dict(entry,authored=str(path),fullshell=str(full),blend=str(blend),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    print('TAILORED_NATIVE_SOURCE_SAVED',name,group,flush=True)

# Use the selected single empty display geometry for its world pickup too.
# No additional render and no paired overlapping display objects are created.
bpy.ops.wm.open_mainfile(filepath=str(CAND/'TailoredFingerless_Icon.blend'))
obj=next(o for o in bpy.data.objects if o.type=='MESH')
for other in list(bpy.data.objects):
    if other is not obj:bpy.data.objects.remove(other,do_unlink=True)
coords=np.array([v.co[:] for v in obj.data.vertices]);centre=(coords.min(0)+coords.max(0))/2
centre[2]=coords[:,2].min()
for v in obj.data.vertices:v.co-=__import__('mathutils').Vector(centre)
obj.name='SM_TailoredFingerless_Pickup';obj.data.materials.clear();obj.data.materials.append(material('Shared'))
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(R/'SM_TailoredFingerless_Pickup.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Editable/TailoredFingerless_Pickup.blend'))
(R/'manifest.json').write_text(json.dumps(finished,indent=2)+'\n')
print('TAILORED_FAMILY_SOURCES_COMPLETE',len(finished),flush=True)
