"""Tune owned Epic muzzle candidates; preserve the imported source pack."""
import unreal,json
from pathlib import Path
out=Path(unreal.Paths.project_saved_dir())/'EpicGunFX'
api=unreal.get_default_object(unreal.NiagaraToolset_System)
report={}
for kind in ['Muzzle','BarrelSmoke']:
 src='/Game/NiagaraExamples/FX_Weapons/MuzzleFlashes/NS_MuzzleFlash'
 dest=f'/Game/Weapons/GunplayFX/NS_FPS_{kind}EpicV5'
 if '-MuzzleRebuildProbe' in unreal.SystemLibrary.get_command_line():dest+='RebuildProbe'
 s=unreal.load_asset(dest) or unreal.EditorAssetLibrary.duplicate_asset(src,dest)
 assert s
 keep={'Muzzle_Smoke'} if kind=='BarrelSmoke' else {'Flash_Center','MuzzleFlash_Front','MuzzleFlash_Side','Muzzle_Sparks','Muzzle_Smoke'}
 summary=api.call_method('GetSystemSummary',(s,))
 for e in summary.get_editor_property('emitters'):
  en=str(e.get_editor_property('emitter_name'))
  if en not in keep:
   ref=unreal.NiagaraExt_StackItemReference();ref.set_editor_property('system',s);ref.set_editor_property('emitter_name',en)
   api.call_method('RemoveEmitter',(ref,))
 once=unreal.RainAssetEditor.read_input(s,'Muzzle_Smoke','EmitterUpdateScript','EmitterState','Loop Behavior')
 mode=unreal.RainAssetEditor.read_input(s,'Muzzle_Smoke','EmitterUpdateScript','EmitterState','Life Cycle Mode')
 mode=mode.replace('NewEnumerator0','NewEnumerator1').replace('"System"','"Self"')
 for en in keep:
  unreal.RainAssetEditor.set_input(s,en,'EmitterUpdateScript','EmitterState','Life Cycle Mode','/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum',mode)
  assert unreal.RainAssetEditor.set_input(s,en,'EmitterUpdateScript','EmitterState','Loop Behavior','/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum',once)
 def put(en,sc,mod,inp,typ,val):
  assert unreal.RainAssetEditor.set_input(s,en,sc,mod,inp,typ,val),(en,mod,inp)
 def spawn(en,inp,typ,val):put(en,'ParticleSpawnScript','InitializeParticle',inp,typ,val)
 fl='/Script/Niagara.NiagaraFloat'
 spawn('Muzzle_Smoke','UsePositionOffset','/Script/Niagara.NiagaraBool','(Value=0)')
 linked='(LinkedVariable=(Name="User.Smoke Color",Type=(ClassStructOrEnum="/Script/CoreUObject.ScriptStruct\'/Script/CoreUObject.LinearColor\'",UnderlyingType=2)))'
 spawn('Muzzle_Smoke','Color','/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked',linked)
 for inp,val in [('Lifetime Min',.50 if kind=='Muzzle' else .60),('Lifetime Max',.80 if kind=='Muzzle' else .90),('Uniform Sprite Size Min',38),('Uniform Sprite Size Max',55)]:
  spawn('Muzzle_Smoke',inp,fl,f'(Value={val})')
 put('Muzzle_Smoke','ParticleSpawnScript','AddVelocity','Velocity Speed',fl,'(Value=55)')
 put('Muzzle_Smoke','ParticleSpawnScript','AddVelocity','Cone Angle',fl,'(Value=12)')
 if kind=='Muzzle':
  spawn('Flash_Center','UsePositionOffset','/Script/Niagara.NiagaraBool','(Value=0)')
  for inp,val in [('Uniform Sprite Size Min',25),('Uniform Sprite Size Max',38)]:spawn('Flash_Center',inp,fl,f'(Value={val})')
  for en in ['Flash_Center','MuzzleFlash_Front','MuzzleFlash_Side']:
   for inp,val in [('Lifetime Min',.020),('Lifetime Max',.038)]:spawn(en,inp,fl,f'(Value={val})')
   put(en,'ParticleUpdateScript','ScaleColor','ScaleA','/Script/Niagara.NiagaraBool','(Value=-1)')
 assert unreal.RainAssetEditor.compile_rain(s)
 assert unreal.EditorAssetLibrary.save_loaded_asset(s,False)
 report[kind]={inp:unreal.RainAssetEditor.read_input(s,'Muzzle_Smoke','ParticleSpawnScript','InitializeParticle',inp) for inp in ['Color','UsePositionOffset','Lifetime Min','Lifetime Max','Uniform Sprite Size Min','Uniform Sprite Size Max']}
(out/'v5-presentation.json').write_text(json.dumps(report,indent=2))
unreal.log('MUZZLE_V5_COMPLETE')
