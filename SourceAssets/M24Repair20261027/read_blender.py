import bpy,json
from pathlib import Path
O=Path(__file__).resolve().parent;S=O.parent/'M24CustomScope20261026'
def report():
    out={}
    for ob in bpy.context.scene.objects:
        if ob.type not in {'MESH','ARMATURE'}:continue
        row={'type':ob.type,'matrix':[list(r) for r in ob.matrix_world],'scale':list(ob.scale),'parent':ob.parent.name if ob.parent else None}
        if ob.type=='MESH':
            row['bounds_local']=[[min(v.co[i] for v in ob.data.vertices) for i in range(3)],[max(v.co[i] for v in ob.data.vertices) for i in range(3)]]
            row['vertices']=len(ob.data.vertices);row['polygons']=len(ob.data.polygons)
            row['uvs']=[{'name':x.name,'render':x.active_render} for x in ob.data.uv_layers]
            row['custom_normals']=ob.data.has_custom_normals
            row['materials']=[m.name if m else None for m in ob.data.materials]
        out[ob.name]=row
    return out
out={}
for key,file in [('native',S/'M24_CustomScope_Native_Editable.blend'),('gameplay',S/'M24_V9_Gameplay_Editable.blend'),('modular',O.parent/'M24Modular20261027/M24_Modular_Editable.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(file),use_scripts=False);out[key]=report()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(S/'Original/GLTF/scene.gltf'))
out['gltf']=report()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'OriginalGLTF_Reference.blend'))
(O/'blender_before.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('M24_BLENDER_SOURCE_RECORDED')
