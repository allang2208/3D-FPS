"""Repair only random hashes in the saved warm V11/V12 graphs."""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools/Fluids'))
from author_flame_armor_v2 import API,ref,put
from build_fireball_assets import emitters
from flame_expression_compat import nonnegative_random_hashes
paths=['/Game/Skills/FlameArmor20261108/SwordRestoreV11/NS_FlameArmorSword',
 '/Game/Skills/FlameArmor20261108/AllWeaponsV12/NS_FlameArmorWeapon']
if '-run=' not in u.SystemLibrary.get_command_line().lower():
 if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(): raise RuntimeError('Preserve PIE')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in paths): raise RuntimeError('Preserve unsaved flame assets')
changes=[]
for path in paths:
 system=u.load_asset(path)
 if system is None: raise RuntimeError(path)
 for name in emitters(system):
  for script in ['EmitterSpawnScript','EmitterUpdateScript','ParticleSpawnScript','ParticleUpdateScript']:
   for module in API.call_method('GetScriptStackInputValues',(ref(system,name,script),)):
    mn=str(module.get_editor_property('module_name'))
    for item in module.get_editor_property('inputs'):
     key=str(item.get_editor_property('name'));value=str(u.RainAssetEditor.read_input(system,name,script,mn,key))
     if 'HlslExpression' not in value: continue
     corrected=nonnegative_random_hashes(value)
     if corrected!=value:
      put(system,name,script,mn,key,corrected,'/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
      changes.append(dict(asset=path,emitter=name,script=script,module=mn,input=key))
 if not u.RainAssetEditor.compile_rain(system,True): raise RuntimeError('Compile failed '+path)
 u.EditorAssetLibrary.set_metadata_tag(system,'FlameArmor.CpuRandomRepair','NonnegativeSineHash-20261109')
 if not u.EditorAssetLibrary.save_loaded_asset(system,False): raise RuntimeError('Save failed '+path)
(OUT/'random-repair-receipt.json').write_text(json.dumps(dict(saved_assets=paths,changes=changes,blue_charge_modified=False),indent=2),encoding='utf-8')
print('WARM_FLAME_RANDOM_REPAIRED',len(changes),'inputs')
