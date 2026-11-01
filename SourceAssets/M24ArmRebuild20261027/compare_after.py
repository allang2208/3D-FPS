"""Compare reloaded UE base + local layer against final authored arm poses."""
from pathlib import Path
O=Path(__file__).resolve().parent
code=(O/'compare_saved.py').read_text()
code=code.replace('source_before.json','source_after.json').replace('ue_before.json','ue_after.json')
code=code.replace('saved_source_comparison.json','saved_after_comparison.json')
code=code.replace("ue['profiles']['base']", "ue['profiles']['mag10' if role.endswith('_mag10') else 'base']")
code=code.replace("errors[n]=100*(comp[n].translation-K@Matrix(expected[n]).translation).length", """errors[n]=100*(comp[n].translation-K@Matrix(expected[n]).translation).length
   if n in owned:
    angle=comp[n].to_quaternion().rotation_difference((K@Matrix(expected[n])@K).to_quaternion()).angle
    rotation_errors[n]=math.degrees(min(angle,2*math.pi-angle))""")
code=code.replace('report={}', "report={};owned=set(json.loads((O/'authoring.json').read_text())['clips']['idle']['owned_bones'])")
code=code.replace('errors={}', 'errors={};rotation_errors={}')
code=code.replace("'frame':int(f),", "'frame':int(f),'max_arm_rotation_deg':max(rotation_errors.values()),'max_arm_position_cm':max(errors[n] for n in owned),")
exec(compile(code,str(O/'compare_saved.py'),'exec'))
