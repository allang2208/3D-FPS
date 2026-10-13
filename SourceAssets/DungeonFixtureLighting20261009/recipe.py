"""Authoring overlay: bind dungeon light emitters to inspected fixture faces."""
from pathlib import Path
import copy
import json
import math

ROOT=Path(__file__).resolve().parent
REVISION='dungeon_fixture_faces_20261009'
def bindings():return json.loads((ROOT/'Config/bindings.json').read_text('utf8'))
def installed():
    p=ROOT/'Receipts/install.json'
    return p.exists() and json.loads(p.read_text('utf8')).get('stage')=='map_saved'

def effective_policy(module,index,light):
    corridor=module['id']=='Transit';boss=module['id']=='BossPumpHall'
    brightest=sorted(range(len(module['lights'])),key=lambda i:-module['lights'][i]['intensity'])
    role=light.get('role','corridor' if corridor else 'key' if brightest.index(index)<2 else 'fill')
    fill=role=='fill';kind=light.get('type','spot' if fill or corridor else 'point')
    radius=light.get('optimized_radius_cm',min(light['radius']*.8,300) if fill and not boss else light['radius'])
    shadow=boss or not fill
    if fill and not boss:
        x,y,z=light['position'];clearance=0
        for cell in module.get('cells',[]):
            lo,hi=cell['min'],cell['max']
            clearance=max(clearance,min(x-lo[0],hi[0]-x,y-lo[1],hi[1]-y)-35)
        reach=radius*math.sin(math.radians(light.get('outer_cone_degrees',80 if corridor else 65))) if kind=='spot' else radius
        shadow=reach>clearance
    return dict(kind=kind,role=role,cast_shadows=light.get('cast_shadows',shadow),optimized_radius_cm=radius,
        max_draw_distance_cm=light.get('max_draw_distance_cm',5200 if boss else 1400 if fill else 1800 if corridor else 2400),
        fade_range_cm=light.get('fade_range_cm',700 if boss else 400 if fill else 500))

def apply_module(module,rows):
    if module.get('fixture_lighting_revision')==REVISION:return []
    before=copy.deepcopy(module);lights=[];changes=[]
    if len(rows)!=len(before['lights']):raise RuntimeError('Fixture inventory changed: '+module['id'])
    for i,(light,b) in enumerate(zip(before['lights'],rows)):
        if math.dist(light['position'],b['anchor_cm'])>.1:raise RuntimeError('Fixture anchor changed: '+module['id']+'/'+str(i))
        if b.get('remove'):
            changes.append(dict(module=module['id'],index=i,before=light,after=None,reason=b['reason']));continue
        updated=copy.deepcopy(light);policy=effective_policy(before,i,light);old_kind=policy.pop('kind')
        updated.update(policy);updated.update(b['fields'])
        updated.update(fixture_anchor_cm=copy.deepcopy(light['position']),fixture_lighting_revision=REVISION,
            fixture_mesh=b['mesh'],fixture_face_center_cm=b['face_center_cm'],fixture_normal=b['normal'])
        if old_kind=='point' and updated['type']=='rect':updated['intensity']*=.25
        updated['intensity']*=b.get('intensity_scale',1.)
        if updated['type']=='spot':updated.pop('yaw',None);updated.pop('roll',None)
        if updated['type']=='rect':updated.pop('source_radius',None);updated.pop('source_length',None)
        lights.append(updated);changes.append(dict(module=module['id'],index=i,before=light,after=copy.deepcopy(updated),reason=b['reason']))
    module['lights']=lights;module['fixture_lighting_revision']=REVISION
    return changes

def apply_catalog(catalog):
    data=bindings();changes=[]
    for m in catalog['modules']:
        if m['id'] not in data['modules'] or m.get('fixture_lighting_revision')==REVISION:continue
        changes.extend(apply_module(m,data['modules'][m['id']]))
        for part in data['additional_parts'].get(m['id'],[]):
            m['parts'].append(copy.deepcopy(part))
            m['runtime_assets']=sorted(set(m.get('runtime_assets',[]))|{part['mesh']})
        for extra in data['splits'].get(m['id'],[]):
            light=copy.deepcopy(m['lights'][extra['source_index']])
            light.update(extra['fields'],fixture_mesh=extra['mesh'],fixture_face_center_cm=extra['face_center_cm'],fixture_normal=extra['normal'])
            light['id']='FixtureTunnel_'+str(extra['source_index'])+'_B'
            m['lights'].append(light)
            changes.append(dict(module=m['id'],index=len(m['lights'])-1,before=None,after=copy.deepcopy(light),reason='Second half of the existing tunnel light, attached to the second diffuser.'))
    return changes

def apply_fixed_config(config):
    """Preserve inspected fixture poses when rebuilding the original fixed start."""
    data=bindings()['fixed']
    for item in config['actors']:
        b=data.get(item['label'])
        if not b:continue
        if b.get('preserve_transform'):
            if b['fields']['type']=='point' and item.get('light'):
                item['light'].update(source_radius=b['fields']['source_radius'],source_length=0.)
            continue
        if item.get('fixture_lighting_revision')==REVISION:continue
        f=b['fields'];light=item['light']
        if f['type']=='rect':
            if item['class_name']=='PointLight':light['intensity']*=.25
            item['class_name']='RectLight'
            light.pop('source_radius',None);light.pop('source_length',None)
            light.update(source_width=f['source_width_cm'],source_height=f['source_height_cm'])
        item.update(position=f['position'],rotation={k:f.get(k,0) for k in ('pitch','yaw','roll')},fixture_lighting_revision=REVISION)
    coverage=ROOT.parent/'DungeonLightCoverage20261009/recipe.py'
    if coverage.exists():
        import runpy
        reach=runpy.run_path(str(coverage))
        if reach['installed']():reach['apply_fixed_config'](config)
    return config

def reapply_catalog(catalog,contract_hash):
    if not installed():return catalog
    result=copy.deepcopy(catalog);apply_catalog(result)
    result['facility_flow']['layout_bank']['contract_sha1']=contract_hash(result)
    return result
