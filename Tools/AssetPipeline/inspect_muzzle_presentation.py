import unreal,json
from pathlib import Path
out=Path(unreal.Paths.project_saved_dir())/'EpicGunFX'
s=unreal.load_asset('/Game/Weapons/GunplayFX/NS_FPS_MuzzleEpicV5')
api=unreal.get_default_object(unreal.NiagaraToolset_System)
results={}
for name in ['Muzzle_Smoke','Flash_Center','MuzzleFlash_Front','MuzzleFlash_Side']:
 r=unreal.NiagaraExt_StackItemReference();r.set_editor_property('system',s);r.set_editor_property('emitter_name',name)
 t=api.call_method('GetEmitterTopology',(r,))
 vals={}
 for sc in ['particle_spawn_script','particle_update_script']:
  script=t.get_editor_property(sc)
  for m in script.get_editor_property('modules'):
   mn=str(m.get_editor_property('module_name'))
   for i in m.get_editor_property('inputs'):
    if i.get_editor_property('is_visible'):
     n=str(i.get_editor_property('name'))
     try:vals[mn+'.'+n]=unreal.RainAssetEditor.read_input(s,name,'ParticleSpawnScript' if sc=='particle_spawn_script' else 'ParticleUpdateScript',mn,n)
     except Exception as ex:vals[mn+'.'+n]=str(ex)
 results[name]=vals
(out/'current-visible-values.json').write_text(json.dumps(results,indent=2))
unreal.log('MUZZLE_INSPECTION_COMPLETE')
