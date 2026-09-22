"""Dependency inputs for retiring the two obsolete selectable Witch variants."""
import unreal as u,json,os
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME');out=root/'SourceAssets/WitchRebuilt20260921/Revision10';out.mkdir(exist_ok=True)
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=root/'FPSGAME.uproject':raise RuntimeError('Wrong project')
ar=u.AssetRegistryHelpers.get_asset_registry()
opts=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,include_searchable_names=False,include_soft_management_references=True,include_hard_management_references=True)
assets={}
for folder in ('/Game/Monsters/WitchMeshy/OriginalRobeV05','/Game/Monsters/WitchMeshy/SpellSupportV07','/Game/Monsters/WitchFoundation'):
 for a in ar.get_assets_by_path(folder,recursive=True):
  p=str(a.package_name)
  assets[p]={'class':str(a.asset_class_path),'referencers':list(map(str,ar.get_referencers(p,opts))),'dependencies':list(map(str,ar.get_dependencies(p,opts)))}
old_actors=[]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
 if a.get_class().get_path_name() in ('/Script/FPSGAME.WitchMonster','/Script/FPSGAME.WitchMotionCandidate'):
  old_actors.append({'path':a.get_path_name(),'class':a.get_class().get_path_name()})
blueprints=[]
for a in ar.get_assets_by_class(u.TopLevelAssetPath('/Script/Engine','Blueprint'),search_sub_classes=True):
 parent=str(a.get_tag_value('NativeParentClass'))
 if 'WitchMonster' in parent or 'WitchMotionCandidate' in parent:blueprints.append({'package':str(a.package_name),'parent':parent})
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result={'pid':os.getpid(),'packages':assets,'placed_old_actors':old_actors,'old_blueprints':blueprints,'play_world':world.get_path_name() if world else None,
 'dirty_packages':[p.get_path_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())]}
(out/'retirement_inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'pid':os.getpid(),'packages':len(assets),'placed_old_actors':old_actors,'old_blueprints':blueprints,'play_world':result['play_world'],'dirty_packages':result['dirty_packages']}))
