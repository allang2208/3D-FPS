"""Finish the new materials' existing whirlwind integration and collect authoring state."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D='/Game/Weapons/HighlandClaymore20260922'
L=u.EditorAssetLibrary;E=u.MaterialEditingLibrary
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:raise RuntimeError('Finish PIE before completing the sword assets.')
map_path=ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json'
mapping=json.loads(map_path.read_text(encoding='utf-8-sig'));added={}
for name in ['M_HighlandClaymoreSurface','M_HighlandMountMetal']:
    source=u.load_asset(D+'/Materials/'+name);target=D+'/Materials/'+name+'_Whirlwind'
    material=u.load_asset(target)
    if not material:
        material=L.duplicate_asset(source.get_path_name(),target)
        if not material:raise RuntimeError('Cannot create whirlwind material: '+target)
        output=E.create_material_expression(material,u.MaterialExpressionTemporalResponsivenessOutput,-700,-700)
        value=E.create_material_expression(material,u.MaterialExpressionConstant,-950,-700);value.set_editor_property('r',1.)
        if not E.connect_material_expressions(value,'',output,''):raise RuntimeError('Temporal material output failed')
        E.recompile_material(material)
        # Complete the shader build required by the imported material.
        E.get_statistics(material)
        if not L.save_loaded_asset(material,False):raise RuntimeError('Cannot save '+target)
    mapping[source.get_path_name()]=material.get_path_name();added[source.get_path_name()]=material.get_path_name()
map_path.write_text(json.dumps(mapping,indent=2)+'\n',encoding='utf-8')
clips=[]
for folder in ['/Game/Weapons/AzureRunesword20260913','/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations']:
    for suffix in ['Idle','Walk','Equip','Inspect','Slash1','Slash2','Thrust','PommelStrike','HeavyCharge','HeavyRelease','Guard','GuardHit','GuardBreak','Overhead','WhirlwindV5','TacticalSprint20260921/A_RuneSword_SprintEnter','TacticalSprint20260921/A_RuneSword_SprintLoop','TacticalSprint20260921/A_RuneSword_SprintExit','TacticalSprint20260921/A_RuneSword_SprintOverhead']:
        path=folder+'/'+(suffix if '/' in suffix else 'A_RuneSword_'+suffix)
        clip=u.load_asset(path)
        if not clip:raise RuntimeError('Shared animation required for integration: '+path)
        clips.append({'asset':clip.get_path_name(),'seconds':clip.get_play_length(),'frames':u.AnimationLibrary.get_num_frames(clip)})
(P/'shared_animation_sources.json').write_text(json.dumps(clips,indent=2),encoding='utf-8')
(P/'whirlwind-material-receipt.json').write_text(json.dumps(added,indent=2),encoding='utf-8')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
state={'pie':False,'dirty_packages':[p.get_path_name() for p in dirty],'project':u.Paths.get_project_file_path()}
(P/'editor-build-state.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print('HIGHLAND_ASSETS_FINISHED '+json.dumps(state))
