"""Compare the exact final payload passed to SavePackage with the authored source."""
from pathlib import Path
O=Path(__file__).resolve().parent
code=(O/'compare_after.py').read_text()
needle="exec(compile(code,str(O/'compare_saved.py'),'exec'))"
replacement="""code=code.replace("names=list(source['rest'])", "ue['profiles']['base']=json.loads((O/'support_profile.json').read_text())['clips'];ue['profiles']['mag10']=json.loads((O/'mag10_profile.json').read_text())['clips'];names=list(source['rest'])")
code=code.replace('saved_after_comparison.json','saved_payload_comparison.json')
exec(compile(code,str(O/'compare_saved.py'),'exec'))"""
exec(compile(code.replace(needle,replacement),str(O/'compare_after.py'),'exec'))
