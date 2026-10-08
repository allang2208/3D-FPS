"""Read the user-selected GLB and preserve its embedded source assets."""
import bpy, json, struct, shutil
import numpy as np
from pathlib import Path
from mathutils import Matrix

P=Path(__file__).resolve().parent
INPUT=Path('C:/Users/allan/Downloads/Meshy_AI_Jade_Dragonblade_1004063309_texture.glb')
(P/'Original').mkdir(exist_ok=True)
(P/'Textures').mkdir(exist_ok=True)
SOURCE=P/'Original'/INPUT.name
if not SOURCE.exists():shutil.copy2(INPUT,SOURCE)
raw=SOURCE.read_bytes();n,t=struct.unpack_from('<II',raw,12)
gltf=json.loads(raw[20:20+n]);bn,bt=struct.unpack_from('<II',raw,20+n);binary=raw[28+n:28+n+bn]
for i,img in enumerate(gltf.get('images',[])):
    view=gltf['bufferViews'][img['bufferView']];start=view.get('byteOffset',0)
    suffix='.png' if img.get('mimeType')=='image/png' else '.jpg'
    (P/'Textures'/('Image_'+str(i)+suffix)).write_bytes(binary[start:start+view['byteLength']])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
rows=[]
for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
    obj.data.transform(obj.matrix_world);obj.matrix_world=Matrix.Identity(4)
    mesh=obj.data;mesh.calc_loop_triangles()
    p=np.array([tuple(v.co) for v in mesh.vertices]);bounds=np.array([p.min(axis=0),p.max(axis=0)])
    axis=int(np.argmax(bounds[1]-bounds[0]));lo,hi=bounds[:,axis];slices=[]
    for value in np.linspace(lo,hi,101):
        mask=np.abs(p[:,axis]-value)<(hi-lo)/250
        if mask.any():slices.append({'at':float(value),'min':p[mask].min(axis=0).tolist(),'max':p[mask].max(axis=0).tolist(),'count':int(mask.sum())})
    rows.append({'name':obj.name,'vertices':len(p),'triangles':len(mesh.loop_triangles),'bounds':bounds.tolist(),'axis':axis,'uv_layers':[x.name for x in mesh.uv_layers],'materials':[x.name for x in mesh.materials],'slices':slices})
report={'source':str(INPUT),'meshes':rows,'gltf_materials':gltf.get('materials',[]),'gltf_images':gltf.get('images',[]),'has_skin':bool(gltf.get('skins'))}
(P/'source_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'XuanChi_Original_Editable.blend'))
print('XUANCHI_SOURCE '+json.dumps({**report,'meshes':[{k:v for k,v in r.items() if k!='slices'} for r in rows]}),flush=True)
