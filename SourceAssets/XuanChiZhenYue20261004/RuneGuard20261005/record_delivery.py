"""Record saved production outputs; no runtime tests or acceptance captures."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
assets=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
icons=json.loads((P/'icon_receipt.json').read_text(encoding='utf-8'))
if not assets.get('complete') or not icons.get('complete'):
    raise RuntimeError('Asset authoring has not completed; retain partial receipts')
delivery={
    'weapon':'ue_xuanchi_zhenyue','date':'2026-10-05',
    'common_runes':['resonance_rune','erosion_rune','conduction_rune'],
    'shared_eastern_runes':['auspicious_cloud_rune','mountain_rune'],
    'common_guards':['bastion_guard','riposte_guard','light_guard'],
    'native_surface':'Private duplicate of the current bright silver steel, preserving BaseColor, ORM, Normal and POM; emission dependency graph reused from installed TangDao cloud/mountain surface',
    'rune_placement':'Blade only; dimensions follow factory, extended, heavy and feather blades',
    'guard_finish':'Existing bright copper, jade decoration, original UV and normals; fitted center and current grip mount retained',
    'gameplay':'Existing option stats and gunsmith_parts save IDs retained; shared permission normalization and rune resource gathering extended to XuanChi',
    'icons':'Eight existing framed TangDao icons promoted to common keys; obsolete XuanChi factory-only guard PNG overrides archived with hashes',
    'assets':assets['assets'],'icon_assets':[r['asset'] for r in icons['icons']],
    'editable_geometry':'XuanChi_CommonGuards_Editable.blend',
    'build':'FPSGAMEEditor Win64 Development: Succeeded (target up to date)',
    'build_log':'native-build.log','import_log':'asset-import.log',
    'tests_run':False,'acceptance_render_run':False,'editor_launched_by_this_task':False,
    'user_testing_required':True
}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('XUANCHI_RUNE_GUARD_DELIVERY_RECORDED')
