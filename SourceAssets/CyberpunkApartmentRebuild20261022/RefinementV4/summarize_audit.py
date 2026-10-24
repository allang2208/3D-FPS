from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
before=json.loads((ROOT/'component-audit-before.json').read_text('utf8'))
after=json.loads((ROOT/'component-audit-after.json').read_text('utf8'))
install=json.loads((ROOT/'installed.json').read_text('utf8'))
source=json.loads((ROOT/'source-model-audit.json').read_text('utf8'))
surfaces=json.loads((ROOT/'surfaces_saved.json').read_text('utf8'))
lookup={(c['actor'],c['component']):c for c in after['components']}
missing=[];preserved=[];covered=0
for component in install['components']:
 actual=lookup[(component['actor'],component['component'])]
 for slot in component['slots']:
  if slot['action']!='PBR upgrade':preserved.append(slot);continue
  found=next((s for s in actual['slots'] if s['name']==slot['slot']),None)
  material=after['materials'].get(found['material'],{}) if found else {}
  normals={p.split('.')[0] for p in material.get('normal_textures',[])}
  if slot['normal'] not in normals:missing.append({'actor':component['actor'],'component':component['component'],'slot':slot['slot'],'expected':slot['normal']})
  else:covered+=1
report=dict(component_count_before=before['component_count'],component_count_after=after['component_count'],
 source_models=source['model_count'],source_geometry_finite=source['finite_all'],
 source_missing_uv=source['missing_uv'],source_zero_area=source['zero_area'],source_zero_uv=source['zero_uv'],
 upgraded_slots_verified=covered,missing_normal_bindings=missing,cabinet_piece_instances_replaced=len(install['mesh_swaps']),
 pbr_families=len(surfaces['materials']),reused_texture_count=len(surfaces['reused_textures']),
 preserved_specialty_slots=len(preserved),inspection='source geometry, saved component material slots and effective normal texture references',
 runtime_tested=False,visual_acceptance_rendered=False)
(ROOT/'inspection-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
