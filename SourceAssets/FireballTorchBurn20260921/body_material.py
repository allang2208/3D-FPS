import importlib
import json
import sys
from pathlib import Path
import unreal

sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
import build_fireball_torch_burn as build
importlib.reload(build)
system=unreal.load_asset(build.CORE)
report={'runtime_core':build.CORE,'emitters':{}}
for name in build.emitters(system):
    renderer=json.loads(build.API.call_method('GetRendererData',(
        build.ref(system,name,renderer=0),)).get_editor_property('property_values'))
    report['emitters'][name]={key:renderer.get(key) for key in [
        'Material','Alignment','FacingMode','SpriteAlignmentBinding','SubImageSize']}
report['root_cause']='Previous core contains only short-lived erosion sprites; dust mask is not a continuous body.'
(build.OUT/'body-repair-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BODY_REPAIR_BEFORE',list(report['emitters']))
build.run('body_material')
