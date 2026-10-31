from pathlib import Path
import runpy,json
R=Path(__file__).resolve().parent;PROJECT=R.parents[1]
runpy.run_path(str(R/'attach_native_attributes.py'),run_name='__main__')
runpy.run_path(str(R/'build_publish_assets.py'),run_name='__main__')
runpy.run_path(str(R/'install_level.py'),run_name='__main__')
runpy.run_path(str(PROJECT/'SourceAssets/CyberpunkNearBank20261028/publish_reflection.py'),run_name='__main__')
report=json.loads((R/'installed.json').read_text());report.update(native_material_attributes_preserved=True,water_reflection='updated_for_native_district')
(R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('NATIVE_MATERIAL_ATTRIBUTES_AND_MAP_SAVED',flush=True)
