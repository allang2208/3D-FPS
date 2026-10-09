"""Preserve the supplied Meshy source and prepare metric authoring inputs."""
import bpy, json, shutil, hashlib
import numpy as np
from pathlib import Path
ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V01')
SOURCE = Path('C:/Users/allan/Downloads/Meshy_AI_Faceless_Athletic_Man_1008070333_texture.glb')
for sub in ['Source', 'Authoring', 'Delivery', 'Textures', 'Logs']:
    (ROOT / sub).mkdir(parents=True, exist_ok=True)
shutil.copy2(SOURCE, ROOT / 'Source' / SOURCE.name)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'Source' / SOURCE.name))
body = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
body.name = 'Security_SourceBody'
bpy.context.view_layer.objects.active = body
body.select_set(True)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
pts = np.array([body.matrix_world @ v.co for v in body.data.vertices])
lo, hi = pts.min(0), pts.max(0)
pts = (pts - np.array([(lo[0]+hi[0])/2, 0, lo[2]])) * (1.90/(hi[2]-lo[2]))
body.matrix_world.identity()
for v,p in zip(body.data.vertices,pts):
    v.co = p
for im in bpy.data.images:
    if im.type == 'IMAGE' and im.size[0] > 0:
        im.filepath_raw = str(ROOT / 'Textures' / ('Source_' + im.name + '.png'))
        im.file_format = 'PNG'
        im.save()
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath='D:/FPS3D/FPSGAME/Saved/NurseZombie/ANMS_ZombieFemaleWalk01Forward.fbx',use_anim=False)
donors=[o for o in set(bpy.data.objects)-before if o.type=='MESH']
rig=next(o for o in set(bpy.data.objects)-before if o.type=='ARMATURE')
rig.animation_data_clear()
for p in rig.pose.bones:
    p.matrix_basis.identity()
bpy.context.view_layer.update()
report={'source_file':SOURCE.name,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'source_has_skeleton':False,'vertices':len(body.data.vertices),
    'triangles':sum(len(p.vertices)-2 for p in body.data.polygons),
    'bounds':[pts.min(0).tolist(),pts.max(0).tolist()],
    'bones':{b.name:{'head':list(rig.matrix_world@b.head_local),'tail':list(rig.matrix_world@b.tail_local)} for b in rig.data.bones},
    'sections':[]}
for z in np.arange(.05,1.90,.05):
    p=pts[np.abs(pts[:,2]-z)<.012]
    if not len(p): continue
    bodyband=p[np.abs(p[:,0])<.27]
    arm=p[p[:,0]>.26]
    report['sections'].append({'z':round(float(z),3),'min':p.min(0).tolist(),'max':p.max(0).tolist(),
        'torso_y':[float(bodyband[:,1].min()),float(bodyband[:,1].max())] if len(bodyband) else None,
        'arm_center':arm.mean(0).tolist() if len(arm) else None})
(ROOT/'Authoring/input_structure.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/Inputs.blend'))
print('SECURITY_INPUTS '+json.dumps({k:v for k,v in report.items() if k!='bones'}),flush=True)
