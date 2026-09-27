"""Apply the final channel sampler settings to the new material without reimporting meshes."""
from pathlib import Path
import runpy,json,datetime
import unreal as u
ns=runpy.run_path(str(Path(__file__).parent/'install.py'),run_name='anvil_material_completion')
worked={k:u.load_asset(ns['SURF']+'/Textures/T_Anvil_Worked_'+k) for k in ('BaseColor','ORM','Normal')}
mat=ns['material'](worked)
receipt={'revision':'AnvilReferenceV3','material':mat.get_path_name(),'saved':ns['saved'],
    'samplers':'BaseColor: Color; Normal: Normal; AO/Roughness/Metallic/ORM: Masks',
    'runtime_tested':False,'rendered':False}
path=Path(__file__).parent/'Receipts'/('material-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
path.write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('ANVIL_REFERENCE_MATERIAL_SAVED '+json.dumps(receipt),flush=True)
