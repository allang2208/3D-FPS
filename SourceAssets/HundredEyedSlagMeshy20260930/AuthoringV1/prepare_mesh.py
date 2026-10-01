"""Prepare the actual Meshy source in authoring coordinates for fitted skinning.
This is asset construction: no pose tests, screenshots, renders or UE operations.
"""
import bpy
import json
import math
import numpy as np
from pathlib import Path
from mathutils import Matrix

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1.0
scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(ROOT/'Meshy/body/downloads/model_urls_glb.glb'))
objects=[o for o in scene.objects if o.type=='MESH']
# The service's front (+Z glTF) imports as -Y in Blender. Rotate it to +X.
rotation=Matrix.Rotation(math.pi/2,4,'Z')
for obj in objects:
    transform=rotation@obj.matrix_world
    obj.data.transform(transform)
    obj.matrix_world=Matrix.Identity(4)
allv=np.concatenate([np.asarray([tuple(v.co) for v in o.data.vertices],dtype=np.float64) for o in objects])
lo=allv.min(axis=0);hi=allv.max(axis=0)
scale=1.2/(hi[2]-lo[2])
offset=Matrix.Translation((-(lo[0]+hi[0])/2,-(lo[1]+hi[1])/2,-lo[2]))
matrix=Matrix.Scale(scale,4)@offset
for obj in objects:
    obj.data.transform(matrix)
    obj.name='SK_HundredEyedSlag_Source'
    obj.data.name='HundredEyedSlag_Meshy_Surface'
if len(objects)>1:
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.join()
obj=next(o for o in scene.objects if o.type=='MESH')
v=np.asarray([tuple(p.co) for p in obj.data.vertices],dtype=np.float64)
low=v[v[:,2]<.14]
# Fit four foot support centres from the actual low surface, by spatial clustering.
centres=np.asarray([[v[:,0].max()*.63,v[:,1].max()*.64,.05],
                    [v[:,0].max()*.63,v[:,1].min()*.64,.05],
                    [v[:,0].min()*.68,v[:,1].max()*.62,.05],
                    [v[:,0].min()*.68,v[:,1].min()*.62,.05]])
for _ in range(35):
    label=((low[:,None,:2]-centres[None,:,:2])**2).sum(axis=2).argmin(axis=1)
    centres=np.asarray([np.mean(low[label==i],axis=0) if np.any(label==i) else centres[i] for i in range(4)])
feet={}
for labelname,signx,signy in [('front.L',1,1),('front.R',1,-1),('rear.L',-1,1),('rear.R',-1,-1)]:
    candidates=[c for c in centres if c[0]*signx>0 and c[1]*signy>0]
    if not candidates:
        candidates=sorted(centres,key=lambda c: -(c[0]*signx+c[1]*signy))
    feet[labelname]=[float(z) for z in candidates[0]]
# Cross sections support limb pivot placement; full surface remains unchanged.
sections=[]
for z0,z1 in [(0,.14),(.14,.30),(.30,.50),(.50,.70),(.70,.90),(.90,1.21)]:
    band=v[(v[:,2]>=z0)&(v[:,2]<z1)]
    if not len(band):continue
    sections.append({'z':[z0,z1],'bounds':[band.min(axis=0).tolist(),band.max(axis=0).tolist()]})
textures=OUT/'Textures';textures.mkdir(exist_ok=True)
image_files=[]
for image in bpy.data.images:
    if image.type!='IMAGE' or not image.has_data:continue
    name=''.join(c if c.isalnum() or c in '_-' else '_' for c in image.name)
    file=textures/(name+'.png')
    image.filepath_raw=str(file);image.file_format='PNG';image.save()
    image.pack();image.filepath='//Textures/'+file.name
    image_files.append(file.name)
report={'source_task':'01a0f0ba-cf66-72c4-8d8e-61c55a3480d8',
        'source_vertices':len(v),'polygons':len(obj.data.polygons),
        'bounds_m':[v.min(axis=0).tolist(),v.max(axis=0).tolist()],
        'feet_centres_m':feet,'height_sections_m':sections,'scale_from_source':float(scale),
        'forward_axis':'+X','up_axis':'+Z','textures':image_files,
        'source_topology_preserved':True,'tested':False}
(OUT/'source_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
np.save(OUT/'source_vertices.npy',v.astype(np.float32))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_Source.blend'))
print('SOURCE_PREPARED '+json.dumps(report),flush=True)
