"""Preserve supplied reduced Meshy model and extract anatomical authoring data."""
import bpy,json,shutil,hashlib
import numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V01')
SOURCE=Path('C:/Users/allan/Downloads/Meshy_AI_Gray_Full_Body_Manneq_1009014620_texture.glb')
for folder in ['Source','Authoring','Delivery','Textures','Motion','Logs']:(ROOT/folder).mkdir(parents=True,exist_ok=True)
shutil.copy2(SOURCE,ROOT/'Source'/SOURCE.name)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'Source'/SOURCE.name))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
source_rigs=[o.name for o in bpy.context.scene.objects if o.type=='ARMATURE']
if len(meshes)!=1 or source_rigs:raise RuntimeError('Input has multiple surfaces or an existing rig; use its own structure: '+str(([o.name for o in meshes],source_rigs)))
body=meshes[0];body.name='Researcher_SourceBody';bpy.context.view_layer.objects.active=body;body.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
points=np.array([body.matrix_world@v.co for v in body.data.vertices]);lo=points.min(0);hi=points.max(0)
points=(points-np.array([(lo[0]+hi[0])/2,0,lo[2]]))*(1.88/(hi[2]-lo[2]))
body.matrix_world.identity()
for v,p in zip(body.data.vertices,points):v.co=p
source_images=[]
for im in bpy.data.images:
    if im.type=='IMAGE' and im.size[0]>0:
        im.filepath_raw=str(ROOT/'Textures'/('Source_'+im.name+'.png'));im.file_format='PNG';im.save();source_images.append(Path(im.filepath_raw).name)
report={'source':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'source_has_skeleton':False,
    'vertices':len(body.data.vertices),'triangles':sum(len(f.vertices)-2 for f in body.data.polygons),
    'bounds':[points.min(0).tolist(),points.max(0).tolist()],'materials':[m.name for m in body.data.materials],
    'images':source_images,'sections':[]}
for z in np.arange(.04,1.87,.04):
    p=points[abs(points[:,2]-z)<.008]
    if not len(p):continue
    # Distinct horizontal islands give arms/legs and torso without a preview.
    xs=np.sort(p[:,0]);cuts=np.flatnonzero(np.diff(xs)>.016);groups=np.split(xs,cuts+1)
    parts=[]
    for xs in groups:
        q=p[(p[:,0]>=xs[0])&(p[:,0]<=xs[-1])]
        parts.append({'min':q.min(0).tolist(),'max':q.max(0).tolist(),'center':q.mean(0).tolist(),'count':len(q)})
    report['sections'].append({'z':round(float(z),3),'parts':parts})
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath='D:/FPS3D/FPSGAME/Saved/NurseZombie/ANMS_ZombieFemaleWalk01Forward.fbx',use_anim=False)
rig=next(o for o in set(bpy.data.objects)-before if o.type=='ARMATURE');rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
report['source_rig_bones']={b.name:{'head':list(rig.matrix_world@b.head_local),'tail':list(rig.matrix_world@b.tail_local)} for b in rig.data.bones}
(ROOT/'Authoring/input_structure.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/Inputs.blend'))
print('RESEARCHER_INPUT_SAVED '+json.dumps({k:v for k,v in report.items() if k not in ['sections','source_rig_bones']}),flush=True)
