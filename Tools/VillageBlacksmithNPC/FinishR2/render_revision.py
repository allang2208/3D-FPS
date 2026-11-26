"""Produce comparable renders and an editable scene from the original posed smith."""
from pathlib import Path
import gzip
import json
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

project=Path(__file__).resolve().parents[3]
base=project/'SourceAssets/VillageBlacksmithNPC20261118'
finish=base/'FinishR2'
review=finish/'Review'
review.mkdir(parents=True,exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
stage=args[0] if args else 'before'
if stage not in ('before','after','head'):raise ValueError(stage)
bpy.ops.wm.open_mainfile(filepath=str(base/'VillageBlacksmith_R4.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
original_head=bpy.data.objects['SK_Smith_Head']
outfit=bpy.data.objects['SK_Smith_Outfit']
body_data=base/'BodyOutfit'
bones=json.loads((body_data/'outfit.json').read_text())['bones']
rig=bpy.data.objects['Jason_NativeSkeleton']
def pose_position(name):
    bone=rig.pose.bones[name]
    return rig.matrix_world@bone.head

def freeze_cameras():
    # Recover the exact previous portrait framing from the unmodified posed head.
    evaluated=original_head.evaluated_get(bpy.context.evaluated_depsgraph_get())
    corners=[evaluated.matrix_world@Vector(v) for v in evaluated.bound_box]
    center=Vector(tuple((min(p[i] for p in corners)+max(p[i] for p in corners))*.5 for i in range(3)))
    center.z+=.004
    delta=Vector((.38,2.50,.06))
    def shot(target,offset,scale,width,height):
        cam_m=(-offset).to_track_quat('-Z','Y').to_matrix().to_4x4()
        cam_m.translation=target+offset
        return {'world_matrix':[list(row) for row in cam_m],'ortho_scale':scale,'pixels':[width,height]}
    full=scene.camera
    cams={'portrait':shot(center,delta,.49,1290,1230)}
    chest=pose_position('spine_03')
    chest.z=center.z-.43
    cams['workwear']=shot(chest,delta,.88,1080,1170)
    cams['whole']={'world_matrix':[list(row) for row in full.matrix_world],
                   'ortho_scale':full.data.ortho_scale,'pixels':[760,980]}
    return cams
def replace_geometry(ob,positions,faces,weights,normals,uvs,material_ids,per_corner,parts=None):
    old=ob.data
    new=bpy.data.meshes.new(ob.name+' | R2')
    positions=np.asarray(positions,dtype=np.float32)*.01
    faces=np.asarray(faces,dtype=np.int32)[:,::-1].copy()
    new.from_pydata(positions.tolist(),[],faces.tolist())
    for mat in old.materials:new.materials.append(mat)
    new.update()
    new.polygons.foreach_set('material_index',np.asarray(material_ids,dtype=np.int32))
    new.polygons.foreach_set('use_smooth',np.ones(len(faces),dtype=bool))
    uv=np.asarray(uvs,dtype=np.float32)
    corner_uv=uv[:,::-1,:].copy() if per_corner else uv[faces]
    corner_uv[:,:,1]=1-corner_uv[:,:,1]
    new.uv_layers.new(name='UVMap').data.foreach_set('uv',corner_uv.ravel())
    n=np.asarray(normals,dtype=np.float32)
    if per_corner:new.normals_split_custom_set(n[:,::-1].reshape(-1,3).tolist())
    else:new.normals_split_custom_set_from_vertices(n.tolist())
    ob.data=new
    ob.vertex_groups.clear()
    for b in bones:ob.vertex_groups.new(name=b['name'])
    rigid={}
    for i,row in enumerate(weights):
        if len(row)==1 and row[0][1]>.99999:
            rigid.setdefault(row[0][0],[]).append(i)
        else:
            for idx,value in row:
                if value>0:ob.vertex_groups[idx].add([i],value,'REPLACE')
    for idx,ids in rigid.items():ob.vertex_groups[idx].add(ids,1,'REPLACE')
    for name,(start,_,end,_) in (parts or {}).items():
        ob.vertex_groups.new(name='Pattern | '+name).add(list(range(start,end)),1,'REPLACE')
    if old.users==0:bpy.data.meshes.remove(old)
    new.update()

def refresh_maps(ob,folder):
    for material in ob.data.materials:
        if not material or not material.use_nodes:continue
        for node in material.node_tree.nodes:
            if node.type!='TEX_IMAGE' or not node.image:continue
            old=node.image
            candidate=folder/Path(bpy.path.abspath(old.filepath)).name
            if not candidate.is_file():continue
            space=old.colorspace_settings.name
            node.image=bpy.data.images.load(str(candidate),check_existing=True)
            node.image.colorspace_settings.name=space
            if candidate.name=='T_Smith_Face_BC.png':
                node.image.alpha_mode='CHANNEL_PACKED'

camera_file=review/'camera_rig.json'
if stage=='before':
    shots=freeze_cameras()
    camera_file.write_text(json.dumps(shots,indent=2))
else:
    shots=json.loads(camera_file.read_text())
    hf=finish/'HeadHair'
    d=json.loads(gzip.decompress((hf/'face.json.gz').read_bytes()))
    replace_geometry(original_head,d['p'],d['tri'],d['w'],d['n'],d['uv'],d['m'],False)
    refresh_maps(original_head,hf/'Textures')
    if stage=='after':
        gf=finish/'BodyOutfit'
        d=json.loads((gf/'outfit.json').read_text())
        replace_geometry(outfit,d['positions'],d['triangles'],d['weights'],d['normals'],d['uv'],d['triangle_materials'],True,d.get('parts'))
        refresh_maps(outfit,gf/'Textures')
        import runpy
        finish_surfaces=runpy.run_path(str(Path(__file__).parent/'Materials/blender_surface.py'))
        finish_surfaces['apply'](outfit,gf/'Textures')
    bpy.context.view_layer.update()
scene.render.engine='CYCLES'
scene.cycles.samples=76
scene.cycles.seed=19
scene.cycles.use_denoising=True
scene.render.resolution_percentage=100
cameras={}
for slug,shot in shots.items():
    camera_data=bpy.data.cameras.new('Smith '+slug+' R2')
    camera_data.type='ORTHO';camera_data.ortho_scale=shot['ortho_scale']
    cam=bpy.data.objects.new(camera_data.name,camera_data)
    scene.collection.objects.link(cam);cam.matrix_world=Matrix(shot['world_matrix'])
    cameras[slug]=cam
for name,shot in shots.items():
    if stage=='head' and name!='portrait':continue
    scene.camera=cameras[name]
    scene.render.resolution_x,scene.render.resolution_y=shot['pixels']
    scene.render.filepath=str(review/(stage+'_'+name+'.png'))
    bpy.ops.render.render(write_still=True)
if stage=='after':
    scene.camera=cameras['portrait']
    scene.render.resolution_x,scene.render.resolution_y=shots['portrait']['pixels']
    scene.render.filepath=str(review/'after_portrait.png')
    scene['preview_note']='Village blacksmith R2. The J_MM_Idle pose, lighting and review cameras are shared with R1.'
    bpy.ops.wm.save_as_mainfile(filepath=str(finish/'VillageBlacksmith_R4_FinishR2.blend'),relative_remap=True)

