"""Read saved light data back in a fresh process; no gameplay or rendering."""
from pathlib import Path
import json
import runpy
import unreal as u

ROOT=Path(__file__).resolve().parent
R=runpy.run_path(str(ROOT/'recipe.py'))
I=runpy.run_path(str(ROOT/'install.py'))
report=dict(scope='Saved reception lamp data and imported diffuser geometry',game_run=False,rendered=False)
world=u.EditorLoadingAndSavingUtils.load_map(I['TARGET'])
g=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
catalog=json.loads(g.get_editor_property('module_catalog_json'))
module=next(m for m in catalog['modules'] if m['id']==R['MODULE_ID'])
assert module['fixture_lighting_revision']==R['REVISION']
report['production']=I['fixture_rows'](module)
before=json.loads((ROOT/'Receipts/catalog-before.json').read_text('utf8'))
assert [m for m in before['modules'] if m['id']!=R['MODULE_ID']]==[m for m in catalog['modules'] if m['id']!=R['MODULE_ID']]
assert before['facility_flow']['layout_bank']['entries']==catalog['facility_flow']['layout_bank']['entries']
hash_contract=runpy.run_path(str(I['FLOW']/'restore_entry_recipe.py'))['contract_hash']
assert catalog['facility_flow']['layout_bank']['contract_sha1']==hash_contract(catalog)
world=u.EditorLoadingAndSavingUtils.load_map(I['SUBJECT'])
aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
actors=aa.get_all_level_actors()
lights=[a for a in actors if a.get_actor_label().startswith('Reception_') and a.get_component_by_class(u.LocalLightComponent)]
assert len(lights)==23
report['subject']=[]
for p in R['layout']()['lights']:
    matches=[a for a in lights if a.get_actor_label()=='Reception_'+p['id']]
    assert len(matches)==1,p['id']
    actor=matches[0];light=actor.get_component_by_class(u.LocalLightComponent)
    pos=light.get_world_location();forward=light.get_forward_vector()
    expected=R['anchor'](p);expected[2]+=R['EMITTER_OFFSET_CM']
    assert all(abs(a-b)<.05 for a,b in zip([pos.x,pos.y,pos.z],expected)),p['id']
    assert forward.z<-.9999,p['id']
    local=p['role']!='main'
    assert isinstance(light,u.RectLightComponent if local else u.SpotLightComponent),p['id']
    assert abs(light.intensity-p['intensity']*(.25 if local else 1))<.01,p['id']
    assert bool(light.light_function_material)==bool(p.get('light_function')),p['id']
    if light.light_function_material:
        assert light.light_function_material.get_path_name().split('.')[0]==p['light_function'],p['id']
    if local:
        assert abs(light.source_width-123)<.01 and abs(light.source_height-32)<.01,p['id']
    report['subject'].append(dict(id=p['id'],type=light.get_class().get_name(),position_cm=[pos.x,pos.y,pos.z],forward=[forward.x,forward.y,forward.z],intensity=light.intensity,passed=True))
report.update(saved_readback_passed=True,other_modules_unchanged=True,layout_placements_unchanged=True,
    bank_contract_valid=True,production_lights=len(report['production']),subject_lights=len(report['subject']))
(ROOT/'Receipts/saved-readback.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('RECEPTION_SAVED_READBACK_OK',report['production_lights'],report['subject_lights'],'lamps; no gameplay/render')
