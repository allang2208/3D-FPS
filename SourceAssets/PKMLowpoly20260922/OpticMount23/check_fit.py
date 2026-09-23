"""Requested mount-only dimensional check; no game or animation playback."""
import json
from pathlib import Path
O=Path(__file__).parent
source=json.loads((O/'source_geometry.json').read_text())
fit=json.loads((O/'fit_measurements.json').read_text())
author=json.loads((O/'authoring.json').read_text())
receipt=json.loads((O/'import_receipt.json').read_text())
rail_min,rail_max=author['rail_y_m'];top=author['rail_top_gun_z_m']
rear=next(p for p in source['parts'] if p['name']=='PKM_Part_050')
rows=[]
for key,foot in fit['optic_feet'].items():
 low,high=foot['mounted_foot_y']
 rows.append({'optic':key,'foot_y_m':[low,high],
  'rail_margin_front_rear_mm':[(low-rail_min)*1000,(rail_max-high)*1000],
  'conservative_rear_sight_height_clearance_mm':(top+foot['base_source_min'][2]-rear['max'][2])*1000})
report={'scope':'Source geometry and saved import bindings; no game/ADS/reload test',
 'rail_to_rear_sight_longitudinal_gap_mm':(rear['min'][1]-rail_max)*1000,
 'fitted_foot_contact_samples':len(author['contacts']),
 'foot_bottom_design_overlap_mm':.12,'optics':rows,
 'imported_size_cm':receipt['size_cm'],'saved_material_slots':receipt['actual_slots'],
 'saved_wet_material':receipt['wet'],'shader_compiler_errors':receipt['compiler_errors']}
if any(min(r['rail_margin_front_rear_mm'])<0 or r['conservative_rear_sight_height_clearance_mm']<=0 for r in rows):
 raise RuntimeError('Mount/optic fit outside measured envelope')
(O/'fit_after.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=1))
