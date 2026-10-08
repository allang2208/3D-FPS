import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
def summary(obj):
    return {'mesh':obj.name,'vertices':len(obj.data.vertices),'polygons':len(obj.data.polygons),
        'uv_layers':[{'name':l.name,'min':[min(v.uv[i] for v in l.data) for i in range(2)],
                      'max':[max(v.uv[i] for v in l.data) for i in range(2)],
                      'unique':len({tuple(v.uv) for v in l.data})} for l in obj.data.uv_layers]}
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'XuanChi_BladeV3_Editable.blend'))
result={'blend':summary(bpy.data.objects['SM_XuanChi_Blade_V3'])}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(P.parent/'Export/SM_XuanChi_Blade_V3.fbx'))
result['fbx']=[summary(o) for o in bpy.context.scene.objects if o.type=='MESH']
(P/'author_uv.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
