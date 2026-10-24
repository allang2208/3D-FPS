from pathlib import Path
import json
root=Path(__file__).resolve().parent
audit=json.loads((root/'component-audit-after.json').read_text('utf8'))
components=[c for c in audit['components'] if c['actor'].startswith(('AP_','Door_')) and c['visible'] and not c['hidden_in_game']]
slots=[s for c in components for s in c['slots']]
exempt=[];missing=[]
for c in components:
 for s in c['slots']:
  if audit['materials'].get(s.get('material'),{}).get('normal_textures'):continue
  row=dict(actor=c['actor'],slot=s.get('name'),material=s.get('material'))
  if s.get('name') in ['RS_Coffee','RS_Crema']:row['reason']='existing smooth liquid surface';exempt.append(row)
  else:missing.append(row)
geometry=json.loads((root/'source-model-audit.json').read_text())
doors=json.loads((root/'door-hull-clearance.json').read_text())
installed=json.loads((root/'installed.json').read_text())
before={a['label']:a for a in json.loads((root/'layout-before.json').read_text())}
after={a['label']:a for a in json.loads((root/'layout-after.json').read_text())}
unrelated_changes=[]
for label in before.keys() & after.keys():
 if label.startswith('Door_') or label.startswith('AP_Bath1_') or label.startswith('AP_Container_Vanity_'):continue
 if any(before[label][k]!=after[label][k] for k in ['location','rotation','scale']):unrelated_changes.append(label)
summary=dict(saved_map=installed['map'],stage=installed['stage'],visible_interior_components=len(components),visible_material_slots=len(slots),
 normal_bound_slots=len(slots)-len(exempt)-len(missing),missing_required_normals=missing,smooth_liquid_exemptions=exempt,
 new_source_models=geometry['model_count'],geometry_finite=geometry['finite_all'],missing_uv=geometry['missing_uv'],
 zero_area=geometry['zero_area'],zero_uv=geometry['zero_uv'],door_count=doors['door_count'],blocked_full_open_pockets=doors['blocked'],
 door_saved_hull_check_valid=doors['valid'],door_collision_shapes=doors['collision_hulls_read'],
 unrelated_actor_transform_changes=unrelated_changes,bathroom_area_m2=installed['bathroom_area_after_m2'],
 checks='source geometry, saved material graphs and transforms, saved collision hull intersection with known-wall control; no visual or runtime acceptance',
 game_run=False,rendered=False,performance_measured=False)
(root/'inspection-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print(json.dumps(summary,indent=2))
