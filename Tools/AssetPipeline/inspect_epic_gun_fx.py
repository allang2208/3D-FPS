import unreal
from pathlib import Path
out=Path(unreal.Paths.project_saved_dir())/'EpicGunFX';out.mkdir(exist_ok=True)
s=unreal.load_asset('/Game/NiagaraExamples/FX_Weapons/MuzzleFlashes/NS_MuzzleFlash')
api=unreal.get_default_object(unreal.NiagaraToolset_System)
summary=api.call_method('GetSystemSummary',(s,))
(out/'summary.txt').write_text(summary.export_text())
for e in summary.get_editor_property('emitters'):
 name=str(e.get_editor_property('emitter_name'))
 r=unreal.NiagaraExt_StackItemReference();r.set_editor_property('system',s);r.set_editor_property('emitter_name',name)
 for method in ['GetEmitterTopology','GetEmitterInputValues','GetEmitterData']:
  try:
   result=api.call_method(method,(r,))
   text=result.export_text() if hasattr(result,'export_text') else '\n'.join(v.export_text() for v in result)
   (out/(name+'-'+method+'.txt')).write_text(text)
  except Exception as ex:unreal.log(str(ex))
unreal.log('EPIC_FX_INSPECT_COMPLETE')
