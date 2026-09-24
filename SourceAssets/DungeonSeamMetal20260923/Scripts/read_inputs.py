"""Read the reported connector/material inputs from the owning UE process."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
for d in ('Sources','Receipts','Config','Authored'):(ROOT/d).mkdir(parents=True,exist_ok=True)
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=(ue.get_game_world() or ue.get_editor_world()) if ue else None
out=dict(project=u.Paths.project_dir(),world=world.get_path_name() if world else '',pie=bool(ue and ue.get_game_world()),materials={},textures=[])
gs=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator) if world else []
if gs:
    (ROOT/'Sources/current-catalog.json').write_text(gs[0].get_editor_property('module_catalog_json'),encoding='utf-8')
    (ROOT/'Sources/current-layout.json').write_text(gs[0].get_editor_property('layout_manifest_json'),encoding='utf-8')
roots=['/Game/SD_Art/Industrial_Infrastructure/Materials/Rust',
       '/Game/SD_Art/Industrial_Infrastructure/Materials/Metal',
       '/Game/SD_Art/Industrial_Infrastructure/Assets/Wall_Panels']
for base in roots:
    for path in u.EditorAssetLibrary.list_assets(base,recursive=True,include_folder=False):
        name=path.rsplit('/',1)[-1]
        if ('Tiling_Rust_' in name or 'Metal_Trim_01_' in name or name.startswith('MI_Tiling_Beams_Rusted.')):
            obj=u.load_asset(path)
            if isinstance(obj,u.Texture2D):
                out['textures'].append(dict(path=path,srgb=obj.get_editor_property('srgb'),compression=str(obj.get_editor_property('compression_settings'))))
            elif isinstance(obj,u.MaterialInstanceConstant):
                out['materials'][path]=dict(parent=obj.get_editor_property('parent').get_path_name(),
                    textures=[dict(name=str(p.parameter_info.name),value=p.parameter_value.get_path_name() if p.parameter_value else None) for p in obj.get_editor_property('texture_parameter_values')],
                    scalars=[dict(name=str(p.parameter_info.name),value=p.parameter_value) for p in obj.get_editor_property('scalar_parameter_values')])
# Reuse the original texture assets directly. TGA does not support every packed
# source format; forcing that exporter asserts inside UnrealEditor.
(ROOT/'Receipts/inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('SEAM_METAL_INPUTS',json.dumps(out),flush=True)
