"""Build and retain the side-rake/body-width revision's authored outputs."""
import json,runpy,sys,shutil
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;P=O.parents[1];SI=O.parent/'PitViper2011SICompensator20261002'
sys.path.insert(0,str(P/'Tools/Weapons'))
from pit_viper_si_extension import derive_interface
raw=json.loads((O.parent/'PitViper2011Integration20261002/canonical_parts.json').read_text(encoding='utf8'))
T=Matrix(json.loads((SI/'authoring_receipt.json').read_text(encoding='utf8'))['source_to_part'])
contract=derive_interface(raw,T)
(O/'fitted_interface.json').write_text(json.dumps(contract,indent=2),encoding='utf8')
print('NATIVE_NOSE_BODY_EXTENSION',contract['body_width_m'],contract['side_rake_from_vertical_deg'],
    'outer',[contract['cap_vertices_m'][i] for i in contract['outer_boundary']],flush=True)
runpy.run_path(str(SI/'author_si_compensator.py'),run_name='__main__')
shutil.copy2(SI/'authoring_receipt.json',O/'authoring_receipt.json')
print('SI_BODY_EXTENSION_SOURCE_AND_EXPORTS_SAVED',flush=True)
