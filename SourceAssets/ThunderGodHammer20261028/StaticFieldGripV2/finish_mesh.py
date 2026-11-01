"""Save the close-view geometry precision after the initial texture/mesh import."""
from pathlib import Path
import json,unreal as u
P=Path(__file__).resolve().parent
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
mesh=u.load_asset(receipt['models'][0]['asset'])
if mesh.get_outermost() in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    raise RuntimeError('Preserving unsaved mesh edits')
s=mesh.get_editor_property('nanite_settings')
s.position_precision=10 # Engine: step 2^(-precision) cm, i.e. 9.77 micrometres.
s.normal_precision=15;s.tangent_precision=12
s.keep_percent_triangles=1.;s.trim_relative_error=0.
s.explicit_tangents=True;s.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
s.fallback_percent_triangles=1.;s.fallback_relative_error=0.
mesh.set_editor_property('nanite_settings',s)
if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Mesh save failed')
receipt['models'][0]['precision']=dict(position=10,normal=15,tangent=12,step_cm=2**-10,keep_percent=1.,trim_error=0.,fallback_target='PercentTriangles',fallback_percent=1.)
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'precision_receipt.json').write_text(json.dumps(dict(complete=True,asset=mesh.get_path_name(),settings=receipt['models'][0]['precision'],runtime_tested=False),indent=2),encoding='utf-8')
print('STATIC_FIELD_V2_PRECISION_SAVED')
