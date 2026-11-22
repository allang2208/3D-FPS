"""Construct the editable in-engine display mesh, plus actual model icon inputs."""
from pathlib import Path
from collections import Counter
import json
import os
import sys
import bpy
import numpy as np
from mathutils import Vector

HERE=Path(__file__).resolve().parent
PROJECT=Path(os.environ['FPSGAME_PROJECT'])
HOST=PROJECT/'SourceAssets/OneHandAxe20261101/ModulesV1'
sys.path.insert(0,str(HERE))
from author_finish import make_palette

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
palette=make_palette()
src=np.load(HERE/'surface.npz')
points=src['points']
vertices=np.concatenate([src['front'],src['back']])
if not np.isfinite(vertices).all(): raise ValueError('Invalid surface position')
n=len(points)
tris=src['faces']
front=[tuple(reversed(t)) for t in tris]
back=[tuple(t+n) for t in tris]
links=Counter()
for a,b,c in tris:
    for i,j in ((a,b),(b,c),(c,a)):
        if (j,i) in links:del links[j,i]
        else:links[i,j]=1
sides=[(a,b,b+n,a+n) for a,b in links if points[a,1]<939.999 or points[b,1]<939.999]
mesh=bpy.data.meshes.new("Crescent with recessed cheek and three leaf ridges")
mesh.from_pydata(vertices.tolist(),[],front+back+sides)
mesh.update()
obj=bpy.data.objects.new('SM_TacticalHatchet_Head_SwiftCrescent_Leaf',mesh)
bpy.context.collection.objects.link(obj)
uv=mesh.uv_layers.new(name="CrescentFaces")
for poly in mesh.polygons:
    poly.use_smooth=True
    is_side=poly.index>=2*len(tris)
    for index in poly.loop_indices:
        v=mesh.loops[index].vertex_index
        x,y=points[v%n]
        if is_side:
            u=x/2048+(0.0009 if v>=n else 0.)
            t=1-y/1024+(0.00055 if v>=n else 0.)
        else:u=x/2048 if v<n else 1-x/2048;t=1-y/1024
        uv.data[index].uv=(u,t)
flat_normals=src['normals']
mesh.normals_split_custom_set([flat_normals[mesh.loops[li].vertex_index] if poly.index<2*len(tris) else poly.normal[:]
                               for poly in mesh.polygons for li in poly.loop_indices])

mat=bpy.data.materials.new('M_TacticalHatchet_Head_SwiftCrescent_Leaf')
mat.use_nodes=True
mesh.materials.append(mat)
tree=mat.node_tree
shader=tree.nodes.get('Principled BSDF')
shader.location=(440,80)
tree.nodes.get('Material Output').location=(730,80)
imgs={}
for row,role in enumerate(('BaseColor','ORM','Normal')):
    image=bpy.data.images.load(str(HERE/'Textures'/('T_SwiftCrescent_Leaf_'+role+'.png')))
    if role!='BaseColor':image.colorspace_settings.name='Non-Color'
    image.pack()
    t=tree.nodes.new('ShaderNodeTexImage');t.image=image;t.location=(-400,340-row*275);imgs[role]=t
tree.links.new(imgs['BaseColor'].outputs['Color'],shader.inputs['Base Color'])
ch=tree.nodes.new('ShaderNodeSeparateColor');ch.location=(-85,65)
tree.links.new(imgs['ORM'].outputs['Color'],ch.inputs[0])
tree.links.new(ch.outputs['Green'],shader.inputs['Roughness'])
tree.links.new(ch.outputs['Blue'],shader.inputs['Metallic'])
nm=tree.nodes.new('ShaderNodeNormalMap');nm.location=(-85,-210)
tree.links.new(imgs['Normal'].outputs['Color'],nm.inputs['Color']);tree.links.new(nm.outputs['Normal'],shader.inputs['Normal'])
obj['design']='Swift Crescent Concept01, reduced leaf relief'
obj['surface_palette']=', '.join(m.name for m in palette)
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
exports=HERE/'Export';exports.mkdir(exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(exports/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
                         mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP',apply_unit_scale=True,
                         bake_space_transform=False,add_leaf_bones=False)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'SwiftCrescent_Editable.blend'),compress=True)

scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=36;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for dev in prefs.devices:dev.use=dev.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except TypeError:pass
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Soft studio fill');scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background')
bg.inputs[0].default_value=(.38,.40,.44,1);bg.inputs[1].default_value=.55
def area(name,position,power,size,target):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    light=bpy.data.objects.new(name,data);scene.collection.objects.link(light)
    light.location=position;light.rotation_euler=(Vector(target)-light.location).to_track_quat('-Z','Y').to_euler()
area('Broad softbox',(.42,.46,.72),8,.42,(.04,0,.23))
area('Raking strip',(-.30,.22,.38),2.7,.16,(.02,0,.23))
area('Silver rim',(.24,-.12,.42),5,.18,(.08,0,.22))
camera=bpy.data.objects.new('Icon camera',bpy.data.cameras.new('Icon camera'));scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.clip_start=.01
def frame(objects,width,height,direction,filename,fill):
    corners=[o.matrix_world@Vector(v) for o in objects for v in o.bound_box]
    rotation=(-Vector(direction)).to_track_quat('-Z','Y')
    projected=[rotation.inverted()@v for v in corners]
    bounds=[(min(p[i] for p in projected),max(p[i] for p in projected)) for i in range(3)]
    center=rotation@Vector([(a+b)*.5 for a,b in bounds])
    camera.location=center+Vector(direction).normalized();camera.rotation_euler=rotation.to_euler()
    scene.render.resolution_x=width;scene.render.resolution_y=height
    aspect=width/height
    factor=max(aspect,1.)
    camera.data.ortho_scale=max((bounds[0][1]-bounds[0][0])*factor/aspect,(bounds[1][1]-bounds[1][0])*factor)/fill
    scene.render.filepath=str(HERE/filename);bpy.ops.render.render(write_still=True)
frame([obj],900,900,(.09,1,.09),'SwiftCrescent_Model.png',.86)

with bpy.data.libraries.load(str(HOST/'TacticalHatchet_Modules_Editable.blend'),link=False) as (available,loaded):
    loaded.objects=['SM_TacticalHatchet_Grip_Factory','SM_TacticalHatchet_Pommel_Factory']
for o in loaded.objects:
    scene.collection.objects.link(o);o.hide_set(False);o.hide_render=False
bpy.context.view_layer.update()
frame([obj,*loaded.objects],256,768,(.065,1,.08),'ue_tactical_hatchet_axe_swift_crescent.png',.91)
(HERE/'model.json').write_text(json.dumps({'mesh':obj.name,'material':mat.name,'id':'axe_swift_crescent',
    'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),'selection':'Concept01, reduce the three leaf ridges',
    'inventory_icon':'ue_tactical_hatchet_axe_swift_crescent.png','runtime_tested':False},indent=2),encoding='utf8')
