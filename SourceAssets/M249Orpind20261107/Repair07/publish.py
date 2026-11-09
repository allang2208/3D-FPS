"""Publish the six M249 gunsmith columns and the revised assembly positions."""
from pathlib import Path
import importlib.util,json,shutil,hashlib
r=Path(__file__).resolve().parent;root=r.parent
spec=importlib.util.spec_from_file_location('m249_factory_publish',root/'Repair04/publish_factory.py')
factory=importlib.util.module_from_spec(spec);spec.loader.exec_module(factory)
slots=[part[0] for part in factory.parts]
def columns(old):
    # Keep the retained factory option metadata, removing only retired columns.
    old['allowed']=slots;old['inherit_common_options']=False
    old['options']={slot:old['options'][slot] for slot in slots}
    return old
factory.replace('gunsmith.json',r'(?P<entry>\{\s*"id":\s*"ue_m249",)',columns)
recipe=json.loads((root/'assembly.json').read_text(encoding='utf8'))
factory.replace('gun-assembly.json',r'(?P<entry>\{\s*"id":\s*"assemble_m249",)',lambda old:recipe)
icon=root.parents[1]/'Content/ColdSteelData/Icons/ue_m249.png'
before=json.loads((r/'before_hashes.json').read_text())['Content/ColdSteelData/Icons/ue_m249.png']
if hashlib.sha256(icon.read_bytes()).hexdigest()!=before:raise RuntimeError('M249 icon changed during production')
shutil.copyfile(r/'Icons/weapon.png',icon)
(r/'published.json').write_text(json.dumps({'slots':slots,'slot_labels':['弹夹','枪托','后握把','前握把','枪口','瞄具'],'assembly_parts':len(recipe['parts'])+1,'icon':str(icon),'bipod':'factory hinge retained; legs folded forward'},ensure_ascii=False,indent=2),encoding='utf8')
print('M249_SIX_COLUMNS_PUBLISHED',flush=True)
