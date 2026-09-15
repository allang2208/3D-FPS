"""Remove the inherited explosion cutout from the fireball's new sprite layers."""
import json
import shutil
import sys
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
source = root / 'SourceAssets/FireballFluidBurn20260914'
sys.path.insert(0, str(root / 'Tools/Skills'))
from build_fireball_assets import API, ref, emitters, setdata, save

backup = root / 'trash/skills-magic-20260915/SourceAssets/FireballFluidBurn20260914/BeforeCutoutFix'
backup.mkdir(parents=True, exist_ok=True)
report = {}
for name in ['NS_FireballSlowBurnCore','NS_FireballVelocityTrail']:
    target = backup / (name + '.uasset')
    if not target.exists():
        shutil.copy2(root / 'Content/Skills/Fireball' / target.name, target)
    system = unreal.load_asset('/Game/Skills/Fireball/'+name)
    for emitter in emitters(system):
        r = ref(system, emitter, renderer=0)
        setdata('SetRendererData',unreal.NiagaraExt_RendererData,r,
                {'bUseMaterialCutoutTexture':False,'CutoutTexture':None})
        props = json.loads(API.call_method('GetRendererData',(r,)).get_editor_property('property_values'))
        report[name+'/'+emitter] = {key:props.get(key) for key in ['bUseMaterialCutoutTexture','CutoutTexture']}
    save(system)
(source/'cutout-fix.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
integration_path = source / 'integration.json'
integration = json.loads(integration_path.read_text(encoding='utf-8'))
integration['sprite_cutout'] = 'Inherited explosion CutoutTexture cleared on every core/trail renderer; flame alpha controls coverage'
integration['cutout_fix'] = 'fix_flame_cutout.py; renderer readback in cutout-fix.json'
integration_path.write_text(json.dumps(integration,indent=2),encoding='utf-8')
unreal.log('FIREBALL_CUTOUT_FIX_SAVED')
