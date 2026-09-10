import bpy
import json
from pathlib import Path
from mathutils import Vector

OUT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMReplacement')
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'D:\迅雷下载\akm.fbx')
report = {'objects': [], 'materials': [], 'images': []}
points=[]
for obj in bpy.data.objects:
    row={'name':obj.name,'type':obj.type,'matrix_world':[list(r) for r in obj.matrix_world]}
    if obj.type=='MESH':
        pts=[obj.matrix_world @ v.co for v in obj.data.vertices]
        points.extend(pts)
        row.update(vertices=len(pts),triangles=sum(len(p.vertices)-2 for p in obj.data.polygons),
                   bounds=[[min(v[i] for v in pts),max(v[i] for v in pts)] for i in range(3)],
                   materials=[m.name if m else None for m in obj.data.materials],
                   groups=[g.name for g in obj.vertex_groups], uv_layers=list(obj.data.uv_layers.keys()))
    if obj.type=='ARMATURE': row['bones']=[b.name for b in obj.data.bones]
    report['objects'].append(row)
for mat in bpy.data.materials:
    report['materials'].append({'name':mat.name,'diffuse':list(mat.diffuse_color), 'nodes':[
        {'name':n.name, 'type':n.type, 'image': n.image.filepath if n.type=='TEX_IMAGE' and n.image else None} for n in mat.node_tree.nodes] if mat.use_nodes else []})
for im in bpy.data.images: report['images'].append({'name':im.name,'path':im.filepath,'size':list(im.size),'packed':bool(im.packed_file)})
(OUT/'akm_replacement_source_inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'akm_replacement_imported.blend'))
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1400
scene.render.resolution_y=600
scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('ReviewWorld')
scene.world.color=(0.15,0.15,0.15)
mn=Vector([min(p[i] for p in points) for i in range(3)])
mx=Vector([max(p[i] for p in points) for i in range(3)])
center=(mn+mx)*.5
length=max(mx-mn)
camera_data=bpy.data.cameras.new('SourceReviewCamera')
camera=bpy.data.objects.new('SourceReviewCamera',camera_data)
bpy.context.collection.objects.link(camera)
scene.camera=camera
camera_data.type='ORTHO'
camera_data.ortho_scale=length*1.16
for idx,offset in enumerate([Vector((1.5,-1.8,2)),Vector((-1.5,1.8,1.2))]):
    light_data=bpy.data.lights.new('SourceLight'+str(idx),'AREA')
    light_data.energy=300*length*length
    light_data.size=length*2
    light=bpy.data.objects.new(light_data.name,light_data)
    bpy.context.collection.objects.link(light)
    light.location=center+offset*length
    light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
for name,offset in [('side_x',(1,0,.12)),('side_y',(0,-1,.1)),('top',(0,0,1))]:
    camera.location=center+Vector(offset)*length*2
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/('akm_replacement_source_'+name+'.png'))
    bpy.ops.render.render(write_still=True)
print('AKM_REPLACEMENT_SOURCE='+json.dumps(report))
