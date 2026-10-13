"""Saved-data overlay for the inspected dungeon light reach. No runtime scans."""
from pathlib import Path
import json,copy,math

ROOT=Path(__file__).resolve().parent
REVISION='dungeon_floor_reach_20261009'
def config():return json.loads((ROOT/'Config/coverage.json').read_text('utf8'))
def installed():
    path=ROOT/'Receipts/install.json'
    return path.exists() and json.loads(path.read_text('utf8')).get('stage')=='maps_saved'

def apply_catalog(catalog):
    modules={m['id']:m for m in catalog['modules']};changes=[]
    for c in config()['changes']:
        if c['module']=='FixedStart':continue
        module=modules[c['module']];light=module['lights'][c['index']]
        if math.dist(light['position'],c['position'])>.1 or light.get('fixture_mesh')!=c.get('fixture_mesh'):
            raise RuntimeError('Light assembly changed since reach audit: '+c['module']+'/'+c['id'])
        before=copy.deepcopy(light)
        light.update(c['fields']);light['coverage_revision']=REVISION
        module['coverage_revision']=REVISION
        changes.append(dict(module=c['module'],index=c['index'],id=c['id'],before=before,after=copy.deepcopy(light)))
    return changes

def reapply_catalog(catalog,contract_hash):
    if not installed():return catalog
    out=copy.deepcopy(catalog);apply_catalog(out)
    out['facility_flow']['layout_bank']['contract_sha1']=contract_hash(out)
    return out

def apply_fixed_config(config_data):
    items={a['label']:a for a in config_data['actors']}
    for c in config()['changes']:
        if c['module']!='FixedStart':continue
        light=items[c['id']]['light']
        light['attenuation_radius']=c['fields']['radius'];light['cast_shadows']=True
    return config_data

def subject_label(index,light_id,labels):
    if index<19:return 'FacilityTransit_Hall_'+light_id
    if index<21:return 'FacilityTransit_'+light_id
    route=(index-21)//2+1;lamp=(index-21)%2
    matches=[s for s in labels if s.startswith('FacilityTransit_') and s.endswith('_Route'+str(route)+'_'+str(lamp))]
    if len(matches)!=1:raise RuntimeError('Ambiguous subject light '+str(index))
    return matches[0]

def apply_subject(world):
    import unreal as u
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    applied=[]
    for c in config()['changes']:
        if c['module']!='FacilityTransit':continue
        label=subject_label(c['index'],c['id'],actors)
        a=actors[label];light=a.get_component_by_class(u.LocalLightComponent)
        before=dict(radius=light.attenuation_radius,cast_shadows=light.cast_shadows,intensity=light.intensity)
        a.modify();light.modify();light.set_attenuation_radius(c['fields']['radius']);light.set_cast_shadows(True)
        applied.append(dict(label=label,before=before,radius_after=light.attenuation_radius,shadows_after=light.cast_shadows))
    return applied
