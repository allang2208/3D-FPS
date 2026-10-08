"""Record the completed production batch without running gameplay checks."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('Retain the partial import receipt; asset saving is incomplete')
exports=json.loads((P/'exports.json').read_text(encoding='utf-8'))
delivery={
    'weapon':'ue_xuanchi_zhenyue','date':'2026-10-05','options':receipt['options'],
    'editable_source':'XuanChi_CommonGrips_Editable.blend','meshes':exports['options'],
    'source':'Current fitted SurfaceV2 grip, preserving exact upper/lower mounting rims, native end UV and normals',
    'finish':'Existing leather/textile PBR plus private bright-copper surface derived from current shared metal; native copper fittings preserved',
    'animation':'Existing shared Sword_LongGrip profile, selected by the long_twohand animation folder; no new animation copies',
    'long_grip_extension_cm':3.5,'pommel_adapter_and_tassel':'Existing modular assembly applies the same -3.5 cm lower-end offset',
    'grip_clearance':'Existing 4.5 cm bone mount correction retained',
    'stats_and_save':'Existing five option IDs and stat definitions; XuanChi added to the two shared-option allowlists',
    'icons':'Existing framed TangDao and Frost grip artwork promoted to common keys, old factory-only XuanChi overrides archived',
    'assets':receipt['assets'],'receipt':'import_receipt.json',
    'native_source_changed':False,'native_build_required':False,
    'tests_run':False,'acceptance_render_run':False,'editor_launched_by_this_task':False,
    'user_testing_required':True}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('XUANCHI_COMMON_GRIPS_DELIVERY_RECORDED')
