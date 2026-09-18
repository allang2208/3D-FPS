"""Check which UV channel the installed extended-magazine materials sample."""
import unreal as u
import json

MESHES = ['/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_QBZ40',
          '/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_M440']
MATERIALS = ['/Game/Weapons/ExtMagUniversal20260917/Materials/M_QBZ191_ext_mag_Receiver_0',
             '/Game/Weapons/ExtMagUniversal20260917/Materials/M_M4_ext_mag']

report = {}
for path in MESHES + MATERIALS:
    asset = u.load_asset(path)
    if not asset:
        report[path] = 'MISSING'
        continue
    if isinstance(asset, u.StaticMesh):
        try:
            report[path] = {'uv_channels': asset.get_editor_property('uv_channel_count')}
        except Exception as err:
            report[path] = {'uv_channels': 'unavailable: %s' % err}
        continue
    entry = {'coordinate_indices': [], 'samples': []}
    for expression in u.MaterialEditingLibrary.get_material_expressions(asset):
        name = expression.get_class().get_name()
        if name == 'MaterialExpressionTextureCoordinate':
            entry['coordinate_indices'].append(expression.get_editor_property('coordinate_index'))
        if name == 'MaterialExpressionTextureSample' and expression.texture:
            entry['samples'].append(expression.texture.get_name())
    report[path] = entry

u.log('FINISH_UV_PROBE ' + json.dumps(report, indent=1))
with open(r'D:\FPS3D\FPSGAME\SourceAssets\ExtMagUniversal20260917\Reference\finish_uv_probe.json',
          'w', encoding='utf-8') as handle:
    json.dump(report, handle, indent=1, ensure_ascii=False)
