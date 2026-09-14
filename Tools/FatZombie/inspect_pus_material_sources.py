"""Read local water-material settings for the pus authoring task; no game/preview."""
import json
from pathlib import Path
import unreal as u

out = Path('D:/FPS3D/FPSGAME/Saved/FatZombiePus')
out.mkdir(parents=True, exist_ok=True)
lib = u.MaterialEditingLibrary
paths = [
    '/Game/JVAD3D_SimpleWaterPuddles/Materials/M_JVAD3D_SimpleWaterPuddles',
    '/Game/JVAD3D_SimpleWaterPuddles/Materials/MI_JVAD3D_SimpleWaterPuddles_A',
    '/Game/WorldGeneration/TemperateHills/Rivers/M_TemperateRiverWater',
    '/Game/RuralAustralia/Water/M_Water_01',
]
report = []
for path in paths:
    obj = u.load_asset(path)
    if not obj:
        report.append({'path': path, 'missing': True})
        continue
    row = {'path': path, 'class': obj.get_class().get_name()}
    instance = isinstance(obj, u.MaterialInstanceConstant)
    prefix = 'get_material_instance_' if instance else 'get_material_default_'
    for kind in ('scalar', 'vector', 'texture'):
        values = {}
        for name in getattr(lib, 'get_'+kind+'_parameter_names')(obj):
            value = getattr(lib, prefix+kind+'_parameter_value')(obj, name)
            if kind == 'vector': value = [value.r, value.g, value.b, value.a]
            if kind == 'texture': value = value.get_path_name() if value else None
            values[str(name)] = value
        row[kind] = values
    if instance:
        row['parent'] = obj.get_editor_property('parent').get_path_name()
    else:
        row['domain'] = str(obj.get_editor_property('material_domain'))
        row['blend'] = str(obj.get_editor_property('blend_mode'))
        row['textures'] = [x.get_path_name() for x in lib.get_used_textures(obj)]
    report.append(row)
death = u.load_asset('/Game/Monsters/FatZombieMeshy/Animations/A_FatZombie_Death')
result = {'materials': report, 'death_clip_seconds': death.get_play_length() if death else None}
(out/'material_sources.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('PUS_MATERIAL_SOURCES_RECORDED')
