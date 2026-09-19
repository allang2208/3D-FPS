"""Export local wolf inputs for the authorized zombie-dog reskin; no gameplay run."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/ZombieDogV1/Source')
OUT.mkdir(parents=True, exist_ok=True)
mesh = u.load_asset('/Game/Monsters/Wolf/SK_Wolf_Gameplay')
task = u.AssetExportTask()
task.object = mesh
task.filename = str(OUT / 'SK_Wolf_Source.fbx')
task.automated = True
task.prompt = False
task.replace_identical = True
task.options = u.FbxExportOption()
task.options.set_editor_property('level_of_detail', False)
task.options.set_editor_property('bake_material_inputs', u.FbxMaterialBakeMode.DISABLED)
task.exporter = u.SkeletalMeshExporterFBX()
if not u.Exporter.run_asset_export_task(task):
    raise RuntimeError('Wolf source FBX export failed')
textures = []
for name in ['T_Wolf_BaseColorAlpha','T_WolfDark_BaseColorAlpha','T_Wolf_Nml',
             'T_Wolf_OcclusionRoughnessMetallic','T_Wolf_Specular']:
    texture = u.load_asset('/Game/AnimalVarietyPack/Wolf/Textures/' + name)
    task = u.AssetExportTask()
    task.object = texture
    task.filename = str(OUT / (name + '.png'))
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Source texture export failed: ' + name)
    textures.append({'asset': texture.get_path_name(), 'file': task.filename})
(OUT / 'source_manifest.json').write_text(json.dumps({
    'mesh': mesh.get_path_name(), 'skeleton': mesh.get_editor_property('skeleton').get_path_name(),
    'slots': [{'name': str(x.material_slot_name), 'material': x.material_interface.get_path_name()}
              for x in mesh.get_editor_property('materials')], 'textures': textures,
}, indent=2), encoding='utf-8')
u.log('ZOMBIE_DOG_SOURCE_EXPORT_COMPLETE')
