"""Save the dimensional interface, portal variants and future integration contract."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent;cfg=json.loads((ROOT/'Config/layout.json').read_text('utf8'));man=json.loads((ROOT/'manifest.json').read_text('utf8'))
def cm(p):return [p[0]*100,-p[1]*100,p[2]*100]
parts=[];families={t['id']:[] for t in cfg['themes']}
for m in man['meshes']:
 if m['room']=='PPE':continue
 if m['preview_only'] or m['kind'] in ('Glass','Fracture'):continue
 if cfg.get('central_display') and m['room']=='Hall' and m['kind']=='FloorGuidance':continue
 p=dict(mesh=m['mesh'],position=[0,0,0],yaw=0,scale=[1,1,1],collision=m['collision'],cast_shadow=m['cast_shadow'])
 if m['kind']=='Rails':p['guardrail_drop']=True
 (parts if m['room']=='Hall' else families[m['room']]).append(p)
for p in cfg['parts']:parts.append(dict(mesh=p['mesh'],position=cm(p['position_m']),yaw=-p['yaw_deg'],scale=p['scale'],collision=p['collision'],cast_shadow=p['cast_shadow']))
doc=dict(status='subject_only_not_registered',revision=cfg['revision'],id='FacilityTransit',intended_generator_role='Junction',parts=parts,
 cells=[dict(min=[-2432,-1832,-40],max=[2432,1832,870]),dict(min=[-3200,-182,-32],max=[-2400,182,328]),dict(min=[2400,-380,-32],max=[2800,380,540]),dict(min=[420,-2200,-32],max=[1180,-1800,540]),dict(min=[420,1800,-32],max=[1180,2200,540])],
 ports=[dict(id=p['id'],position=cm(p['position']),normal=cm(p['normal']),width_cm=p['width']*100,height_cm=p['height']*100) for p in cfg['ports']],
 portal_families=families,portal_sockets=cfg['gates'],native_interactions=dict(containers=cfg['containers'],doors=cfg['doors'],glass=cfg['glass']),lights=cfg['lights'],
 route_binding=dict(source='FAuthoredPlan.RouteThemes',mapping='Route1 -> port 1; Route2 -> port 2; Route3 -> port 3',adapter='compose_portals.py:compose',random_draw=False,preview_sets=cfg['preview_sets']),
 reception_connection=dict(source_map=cfg['reception_source'],hall_offset_ue_cm=cm(cfg['offset_m']),source_exit_cm=[2700,0,0],approach_length_cm=800),
 runtime_activation=False,production_catalog_modified=False,preview_caps_included=False,tests_run=False)
for p in doc['ports']:p['normal']=[v/100 for v in p['normal']]
if cfg.get('central_display'):
 ref=cfg['central_display'];assembly=json.loads(Path(ref['assembly']).read_text('utf8'));meshes=json.loads(Path(ref['manifest']).read_text('utf8'))
 doc['central_display']=dict(reference=ref,assembly=assembly,mesh_assets=meshes['meshes'],placement_space='hall_local_blender_metres',installed_subjects=assembly['maps'])
 for m in meshes['meshes']:
  if m['kind']=='Fracture' or (m['kind']=='Glass' and not m.get('roof')):continue
  doc['parts'].append(dict(mesh=m['mesh'],position=[0,0,0],yaw=0,scale=[1,1,1],collision=m['collision'],cast_shadow=m['cast_shadow']))
 for p in assembly['plants']:
  part=dict(mesh=p['mesh'],position=cm(p['position_m']),yaw=-p['yaw_deg'],scale=p['scale'],collision=p['collision'],cast_shadow=p['cast_shadow'])
  if p.get('material_overrides'):part['material_overrides']=p['material_overrides']
  doc['parts'].append(part)
import runpy
doc=runpy.run_path(str(ROOT.parent/'HallLighting20261007/profile.py'))['extend_draft'](doc,'Transit',cfg)
(ROOT/'Config/module-draft.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf8')
print('FACILITY_TRANSIT_DRAFT_SAVED',len(parts),'hall parts',len(families),'portal families')
