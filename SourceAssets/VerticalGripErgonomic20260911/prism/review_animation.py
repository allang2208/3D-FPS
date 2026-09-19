from pathlib import Path
import sys
O=Path(__file__).parent
source=(O/'ReferenceWorkflow/review_animation.py').read_text(encoding='utf-8')
source=source.replace('A_M4_Foregrip_','A_M4_Prism_').replace("'FG_'","'PH_'").replace('fit_pose.json','fit_final.json')
source=source.replace('Vector((0,0,0))','Vector((0,0,-.025))').replace('ortho_scale=.50','ortho_scale=.32')
if '--idle' in sys.argv:
 source=source.replace("[('idle',[0]),('reload',[0,5,116,126]),('reload_empty',[0,150,162]),('equip',[0,30,38]),('drum_reload_empty',[148])]", "[('idle',[0])]")
if '--transitions' in sys.argv:
 source=source.replace("[('idle',[0]),('reload',[0,5,116,126]),('reload_empty',[0,150,162]),('equip',[0,30,38]),('drum_reload_empty',[148])]", "[('reload',[106,108,126]),('reload_empty',[140,141,142,162]),('drum_reload_empty',[128,148])]")
exec(compile(source,str(O/'review_generated.py'),'exec'))
