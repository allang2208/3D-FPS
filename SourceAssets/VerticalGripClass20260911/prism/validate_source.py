from pathlib import Path
import sys
O=Path(__file__).parent
source=(O/'ReferenceWorkflow/validate_source.py').read_text(encoding='utf-8')
source=source.replace('A_M4_Foregrip_','A_M4_Prism_').replace('FOREGRIP_','PRISM_')
if '--empty-only' in sys.argv:
 source=source.replace('report={}',"report=json.loads((O/'source_validation.json').read_text())")
 source=source.replace("for clip,info in json.loads((O/'animation_build.json').read_text()).items():", "for clip,info in json.loads((O/'animation_build.json').read_text()).items():\n if clip!='reload_empty':continue")
exec(compile(source,str(O/'validate_generated.py'),'exec'))
