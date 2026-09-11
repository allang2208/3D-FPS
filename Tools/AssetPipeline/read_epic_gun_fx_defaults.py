import unreal
from pathlib import Path
out=Path(unreal.Paths.project_saved_dir())/'EpicGunFX'
api=unreal.get_default_object(unreal.NiagaraToolset_System)
s=unreal.load_asset('/Game/NiagaraExamples/FX_Weapons/MuzzleFlashes/NS_MuzzleFlash')
(out/'defaults.txt').write_text(api.call_method('GetUserVariables',(s,)).export_text())
for key in ['MI_Flipbook_Pyro_Muzzle','MI_Flipbook_Smoke_Muzzle']:
 m=unreal.load_asset('/Game/NiagaraExamples/FX_Weapons/MuzzleFlashes/Materials/Instances/'+key)
 vals={str(n):unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(m,n) for n in unreal.MaterialEditingLibrary.get_scalar_parameter_names(m)}
 (out/(key+'.txt')).write_text(str(vals))
unreal.log('EPIC_DEFAULTS_COMPLETE')
