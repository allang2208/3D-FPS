"""Apply the retained Spitter fitting recipe to two donor attacks at source speed.

Outputs are separate actions. The V12 source and all original donor clips remain
unchanged. No render, playback or post-export validation is invoked.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
native = json.loads((ROOT/'native.json').read_text(encoding='utf-8'))
recipe_path = BASE/'AttackD_V12/author_attack_d.py'
recipe = recipe_path.read_text(encoding='utf-8')
report = dict(revision='AttackVariantsV13-20260929', attacks={}, runtime_tested=False,
              preview_rendered=False, selection='random_per_attack_no_immediate_repeat')
for role, spec in native.items():
    seconds = round(spec['seconds']*60)/60
    contact = round(spec['contact_seconds'], 4)
    contact_end = round(spec['contact_end_seconds'], 4)
    text = recipe.replace("NAME = 'A_Spitter_AttackD_V12'", "NAME = 'A_Spitter_AttackV13_"+role+"'")
    # Quintic arithmetic can overshoot an endpoint by a few ulps, producing a
    # tiny negative recovery weight which Blender's strict slerp rejects.
    text = text.replace('return x*x*x*(x*(x*6-15)+10)', 'return max(0., min(1., x*x*x*(x*(x*6-15)+10)))')
    text = text.replace('SECONDS = 2.0', 'SECONDS = '+repr(seconds))
    # The common loader expects an Attack_D role. Only its input dictionary is
    # remapped; its motion is the active donor's exported native retarget.
    marker = "ns = {'__file__': str(helper), '__name__': 'attack_d_source_helpers'}"
    injected = "prefix = prefix.replace(\"metadata=json.loads((ROOT/'native.json').read_text(encoding='utf-8'))\", \"metadata = \"+repr({'Attack_D': "+repr(spec)+"}))\n"+marker
    text = text.replace(marker, injected)
    text = text.replace('range(12, 40)', 'range('+str(max(1, round((contact-.2)*60)))+', '+str(min(round(seconds*60), round((contact_end+.15)*60)))+')')
    text = text.replace('ramp(.06, .22, t)*(1-ramp(1.0, 1.45, t))',
        'ramp(.06, '+repr(max(.22, contact-.25))+', t)*(1-ramp('+repr(contact_end+.25)+', '+repr(seconds-.3)+', t))')
    text = text.replace('ramp(.62, .76, t)*(1-ramp(1.15, 1.5, t))',
        'ramp('+repr(contact_end)+', '+repr(contact_end+.14)+', t)*(1-ramp('+repr(seconds-.7)+', '+repr(seconds-.3)+', t))')
    text = text.replace('1-ramp(1.65, SECONDS, t)', '1-ramp(SECONDS-.35, SECONDS, t)')
    text = text.replace("revision='AttackD_V12-20260929', contact_seconds=.47, contact_end_seconds=.67",
        "revision='AttackVariantsV13-20260929', contact_seconds="+repr(contact)+', contact_end_seconds='+repr(contact_end))
    text = text.replace("attack_mode='physical_melee_attack_d'", "attack_mode='physical_melee_random_variants'")
    text = text.replace("'SpitterZombie_AttackD_V12.blend'", repr('SpitterZombie_AttackV13_'+role+'.blend'))
    text = text.replace("ROOT/'authoring.json'", "ROOT/"+repr('authoring_'+role+'.json'))
    context = {'__file__': str(ROOT/'author_variants.py'), '__name__': '__main__'}
    exec(compile(text, str(recipe_path)+'['+role+']', 'exec'), context)
    result = json.loads((ROOT/('authoring_'+role+'.json')).read_text(encoding='utf-8'))
    result['attack']['source_role'] = role
    result['attack']['provenance'] = spec['provenance']
    report['attacks'][role] = result['attack']
(ROOT/'authoring.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('SPITTER_ATTACK_VARIANTS_AUTHORED '+json.dumps(report), flush=True)
