"""Switch only the existing zombie-dog blueprint to the prepared skin-only set."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ZombieDogSkinOnlyV2')
bp=u.load_asset('/Game/Monsters/ZombieDog/V1/BP_ZombieDog')
dataset=u.load_asset('/Game/Monsters/ZombieDog/SkinOnlyV2/DA_ZombieDog_SkinOnly')
mesh=u.load_asset('/Game/Monsters/ZombieDog/SkinOnlyV2/SK_ZombieDog_SkinOnly')
if not bp or not dataset or not mesh:raise RuntimeError('Skin-only import must finish before activation')
defaults=u.get_default_object(bp.generated_class())
previous=defaults.get_editor_property('animation_set').get_path_name()
defaults.set_editor_property('animation_set',dataset)
defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
u.EditorAssetLibrary.set_metadata_tag(bp,'ZombieDog.SkinOnly','2')
if not u.EditorAssetLibrary.save_loaded_asset(bp,False):raise RuntimeError('Could not save zombie dog blueprint')
(ROOT/'activation.json').write_text(json.dumps({'blueprint':bp.get_path_name(),'previous_set':previous,
    'current_set':dataset.get_path_name(),'mesh':mesh.get_path_name(),
    'f6_entry':'ZombieDog / 僵尸犬','runtime_tested':False,'preview_rendered':False},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ZOMBIE_DOG_SKIN_ONLY_ACTIVATED')
