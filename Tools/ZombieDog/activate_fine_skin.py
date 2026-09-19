"""Restore fur-based V1 appearance with refined skin in the existing F6 entry."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ZombieDogFineSkinV3')
bp=u.load_asset('/Game/Monsters/ZombieDog/V1/BP_ZombieDog')
dataset=u.load_asset('/Game/Monsters/ZombieDog/FineSkinV3/DA_ZombieDog_FineSkin')
mesh=u.load_asset('/Game/Monsters/ZombieDog/FineSkinV3/SK_ZombieDog_FineSkin')
if not bp or not dataset or not mesh:raise RuntimeError('Import fine-skin assets before activation')
defaults=u.get_default_object(bp.generated_class())
previous=defaults.get_editor_property('animation_set').get_path_name()
defaults.set_editor_property('animation_set',dataset)
defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
u.EditorAssetLibrary.set_metadata_tag(bp,'ZombieDog.Appearance','FineSkinV3')
u.EditorAssetLibrary.remove_metadata_tag(bp,'ZombieDog.SkinOnly')
if not u.EditorAssetLibrary.save_loaded_asset(bp,False):raise RuntimeError('Could not save zombie dog blueprint')
(ROOT/'activation.json').write_text(json.dumps({'blueprint':bp.get_path_name(),'previous_set':previous,
    'current_set':dataset.get_path_name(),'mesh':mesh.get_path_name(),'f6_entry':'ZombieDog / 僵尸犬',
    'runtime_tested':False,'preview_rendered':False},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ZOMBIE_DOG_FINE_SKIN_ACTIVATED')
