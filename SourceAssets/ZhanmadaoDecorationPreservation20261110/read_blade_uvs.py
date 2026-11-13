"""Read exported blade UV coverage without changing any source mesh or scene."""
import json
from pathlib import Path
import bpy

P = Path(__file__).resolve().parent
S = P.parent / 'Zhanmadao20261018'
sources = {
    'factory': S / 'Export/SM_Zhanmadao_Blade_V1.fbx',
    **{key: S / ('CommonModsV2/Export/SM_Zhanmadao_Blade_' + key + '_V2.fbx')
       for key in ['extended_edge', 'heavy_spine', 'feather_edge']},
    **{key: S / ('TangDaoBladesV1/Export/SM_Zhanmadao_Blade_' + key + '_V1.fbx')
       for key in ['yanling_edge', 'tengyun_dragon']},
    'chixiao': S / 'ChixiaoBladeV1/Export/SM_Zhanmadao_Blade_chixiao_V1.fbx',
    'zhufeng': S / 'ZhufengBladeV1/Export/SM_Zhanmadao_Blade_zhufeng_V1.fbx',
}
result = {}
for key, path in sources.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    lod0 = [obj for obj in objects if 'LOD0' in obj.name]
    objects = lod0 or objects
    slots = {}
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        uv = mesh.uv_layers[0].data
        for triangle in mesh.loop_triangles:
            material = mesh.materials[triangle.material_index].name
            slots.setdefault(material, []).append([list(uv[index].uv) for index in triangle.loops])
    result[key] = {'source': str(path), 'objects': [obj.name for obj in objects], 'slots': slots}
(P / 'blade-uvs.json').write_text(json.dumps(result), encoding='utf-8')
print('ZHANMADAO_UV_INPUTS_READ', len(result))
