"""Keep body-shirt coverage and fit the neighbouring native glove wrist straps."""
import sys,runpy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import C,read,write
T=Path(__file__).parent
for rig in ['Jason','Kaitlin']:
    if not (C/'Authored'/f'gloves_{rig}.json').exists():raise RuntimeError('Finish native glove strap fit: '+rig)
runpy.run_path(str(T/'combat3_cuff_world_contact.py'),run_name='__main__')
contact=read(C/'Review/World-native-glove-contact.json')
for rig in ['Jason','Kaitlin']:
    if min(v['min_clearance_cm'] for v in contact[rig].values())<0:raise RuntimeError('Native body wrist contact remains: '+rig)
    raw=read(C/'Authored'/f'shirt_cloth_{rig}.json');raw['cloth_production'].update(glove_tailoring='measured-native-strap-v1',body_cuff_mode='Original native coverage; neighbouring glove webbing fitted to its own surface',contact=contact[rig]);write(C/'Authored'/f'shirt_cloth_{rig}.json',raw)
    detail=read(C/'Authored'/f'shirt_detail_{rig}.json');detail['cloth_production']=raw['cloth_production'];write(C/'Authored'/f'shirt_detail_{rig}.json',detail)
    write(C/'Review'/(rig+'-tailored.json'),dict(native=rig,mode='Retained native cuff length; fitted neighbouring wrist strap',contact=contact[rig],gameplay_tested=False))
print('WORLD_NATIVE_WRIST_COVERAGE_RETAINED',contact,flush=True)
