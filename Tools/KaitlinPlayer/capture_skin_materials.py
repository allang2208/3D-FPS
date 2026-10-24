"""Export existing albedo inputs for matching V9 hands to Kaitlin's skin tone."""
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
OUT = WORK / 'ViewSkin'
OUT.mkdir(exist_ok=True)
native = json.loads((WORK / 'NativeGeometry/MHC_Kaitlin_Body.json').read_text())
paths = {'kaitlin': native['materials'][0]['asset'],
         'v9': '/Game/Characters/ModularOutfit20260924/BareSkinV9/MI_BareSkinV9.MI_BareSkinV9'}
receipt = {}
for name, path in paths.items():
    material = u.load_asset(path)
    parameters = {}
    for key in u.MaterialEditingLibrary.get_texture_parameter_names(material):
        texture = u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(material, key)
        if not texture:
            continue
        row = {'texture': texture.get_path_name()}
        if any(part in str(key).lower() for part in ('color', 'colour', 'albedo', 'diffuse')):
            file = OUT / (name + '_' + str(key) + '.png')
            task = u.AssetExportTask()
            task.object, task.filename = texture, str(file)
            task.exporter = u.TextureExporterPNG()
            task.automated, task.prompt, task.replace_identical = True, False, True
            if not u.Exporter.run_asset_export_task(task):
                raise RuntimeError('Cannot export skin color input: ' + texture.get_path_name())
            row['file'] = str(file)
        parameters[str(key)] = row
    receipt[name] = {'material': path, 'textures': parameters}
(OUT / 'material_inputs.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
(WORK / 'capture_skin_materials_status.json').write_text(json.dumps({'remaining': 0, 'complete': True}), encoding='utf-8')
print('KAITLIN_SKIN_COLOR_INPUTS_SAVED', flush=True)
