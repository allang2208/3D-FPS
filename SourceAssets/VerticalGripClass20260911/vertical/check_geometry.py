from pathlib import Path
import sys
O=Path(__file__).parent
source=(O/'ReferenceWorkflow/check_geometry.py').read_text(encoding='utf-8')
source=source.replace('A_M4_Foregrip_','A_M4_Vertical_').replace("'FG_'","'VG_'").replace('fit_pose.json','fit_final.json')
if '--empty-only' in sys.argv:
 source=source.replace('report={}',"report=json.loads((O/'geometry_contact_full.json').read_text())")
 source=source.replace('for clip,frames in checks:',"for clip,frames in checks:\n if clip!='reload_empty':continue")
if '--idle' in sys.argv:source=source.replace('for clip,frames in checks:',"for clip,frames in checks:\n if clip!='idle':continue")
exec(compile(source,str(O/'geometry_generated.py'),'exec'))
