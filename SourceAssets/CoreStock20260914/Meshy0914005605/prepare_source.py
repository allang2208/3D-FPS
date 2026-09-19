"""Load the selected FBX and record source coordinates for mount authoring; no render/test."""
import bpy, json, numpy as np, shutil, hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
source=next((P/'Source').rglob('*.fbx'))
bpy.ops.import_scene.fbx(filepath=str(source))
report={'meshes':[], 'textures':[], 'runtime_tested':False}
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    points=np.array([tuple(o.matrix_world@v.co) for v in o.data.vertices])
    lo=points.min(axis=0);hi=points.max(axis=0)
    rows=[]
    for k in range(12):
        s=points[(points[:,0]>=lo[0]+(hi[0]-lo[0])*k/12)&(points[:,0]<=lo[0]+(hi[0]-lo[0])*(k+1)/12)]
        rows.append({'x_fraction':[k/12,(k+1)/12],'min':s.min(axis=0).tolist(),'max':s.max(axis=0).tolist(),'count':len(s)} if len(s) else {})
    report['meshes'].append({'name':o.name,'vertices':len(o.data.vertices),'triangles':sum(len(f.vertices)-2 for f in o.data.polygons),'world_min':lo.tolist(),'world_max':hi.tolist(),'rotation':list(o.rotation_euler),'scale':list(o.scale),'custom_normals':o.data.has_custom_normals,'uvs':[u.name for u in o.data.uv_layers],'x_sections':rows})
tex=P/'Textures';tex.mkdir(exist_ok=True)
stem=source.with_suffix('')
for key,suffix in [('BaseColor',''),('Metallic','_metallic'),('Roughness','_roughness'),('Normal','_normal')]:
    f=Path(str(stem)+suffix+'.png');dst=tex/(key+'.png');shutil.copy2(f,dst)
    im=bpy.data.images.load(str(dst),check_existing=True)
    report['textures'].append({'role':key,'size':list(im.size),'source':str(f)})
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Imported_Source.blend'))
(P/'source_coordinates.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
zipfile=Path('D:/FPS3D/资产/Meshy_AI_Rifle_Stock_0914005605_image-to-3d-texture_fbx.zip')
(P/'provenance.json').write_text(json.dumps({'source_zip':str(zipfile),'sha256':hashlib.sha256(zipfile.read_bytes()).hexdigest(),'selected_by':'user','replaces':'core_stock appearance only','public_redistribution':'not assessed; source and binaries remain local'},indent=2),encoding='utf-8')
print('SOURCE_LOADED_FOR_AUTHORING',flush=True)
