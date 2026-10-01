import json
from pathlib import Path
O=Path(__file__).parent
imports=json.loads((O/'import_receipt.json').read_text())
markers=json.loads((O/'imported_marker_inspection.json').read_text())
rays=json.loads((O/'sight_rays.json').read_text())
build=(O/'build_editor_final.log').read_text(encoding='utf8',errors='replace')
report={
 'weapon':'ue_hk416',
 'issue':'ADS iron-sight markers were below the physical aperture and post tip.',
 'eye_distance_cm':{'before':18,'after':12},
 'authored_source':'../HK416Reworked20260930/author_weapon.py',
 'markers_source_m':imports['markers_source_m'],
 'assets_saved':imports['complete'],'saved_asset_count':len(imports['saved']),
 'compressed_action_marker_inspection':markers['all_corrected_heights'],
 'inspected_action_count':len(markers['clips']),
 'before_centre_ray':rays['before']['rays'][0]['hit'],
 'after_centre_ray':rays['after']['rays'][0]['hit'],
 'editor_build_succeeded':'Editor modules built.' in build,
 'build_log':'build_editor_final.log',
 'runtime_after_tested':False,'editor_or_game_launched':False,
 'checks_scope':'Source sight aperture/post geometry and imported compressed marker positions only.'}
(O/'completion.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
