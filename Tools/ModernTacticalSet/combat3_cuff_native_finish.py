import sys,runpy,json
from pathlib import Path
T=Path(__file__).parent;C=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1')
runpy.run_path(str(T/'combat3_cuff_native_glove.py'),run_name='__main__')
runpy.run_path(str(T/'combat3_cuff_body_clearance.py'),run_name='__main__')
sys.argv=['combat3_cuff_profile_contact.py','--','Body,Super90']
runpy.run_path(str(T/'combat3_cuff_profile_contact.py'),run_name='__main__')
for rig in ['Body','Super90']:
    report=json.loads((C/'Review'/(rig+'-fitted-glove-contact.json')).read_text(encoding='utf-8'))
    if min(row['min_inner_clearance_cm'] for row in report['contact'].values())<0:raise RuntimeError('Native glove cuff still intersects sleeve: '+rig)
print('LEGACY_NATIVE_CUFF_CONTACT_FINISHED',flush=True)
