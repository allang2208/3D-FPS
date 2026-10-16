"""Offline geometry checks requested by the user; no UE/game execution or rendering."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
manifest=json.loads((ROOT/'asset-manifest.json').read_text('utf8'))
saved=json.loads((ROOT/'asset-check.json').read_text('utf8'))
bounds={x['asset'].rsplit('/',1)[1]:x['bounds'] for x in saved['meshes']}
metadata={x['key']:x for x in manifest['reagents']}
items={'alchemy_pure_base_fluid':'BaseFluid','alchemy_redvein_extract':'RedRoot','alchemy_bluemarrow_crystals':'BlueFungus','alchemy_active_catalyst':'Catalyst'}
seats=[(70,-38,95.02),(86,-38,95.02),(79,-58,95.02)];eye=(145,-185,186)
def box_at(b,pos,s):return [[p[i]*s+pos[i] for i in range(3)] for p in b]
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def raybox(origin,direction,box):
    near=0.;far=1000.
    for i in range(3):
        if abs(direction[i])<1e-8:
            if not box[0][i]<=origin[i]<=box[1][i]:return None
            continue
        a,b=sorted(((box[0][i]-origin[i])/direction[i],(box[1][i]-origin[i])/direction[i]))
        near=max(near,a);far=min(far,b)
        if far<near:return None
    return near
report={'scope':'saved-mesh dimensions, recipe material seats, ray ordering, cap clearance and fluid anchors','runtime_tested':False,'recipes':[]}
recipes=json.loads((PROJECT/'Content/ColdSteelData/alchemy-recipes.json').read_text('utf8'))['recipes']
for recipe in recipes:
    objects=[];targets=[];clearances=[]
    for i,inp in enumerate(recipe['inputs']):
        key=items[inp['item']];body=bounds['SM_Alchemy'+key+'Open'];cap=bounds['SM_Alchemy'+key+'Cap'];meta=metadata[key]
        scale=min(15/meta['height'],9/max(body[1][0]-body[0][0],body[1][1]-body[0][1],1))
        world=box_at(body,seats[i],scale);objects.extend([(i,world),(i,box_at(cap,seats[i],scale))]);targets.append(tuple((a+b)/2 for a,b in zip(*world)))
        # The accepted tray's ceramic support is 95.005 cm; rings are outside the bottle bases.
        assert abs(world[0][2]-95.005)<.03,(recipe['id'],i,'unsupported material')
        lift=max(9,meta['mouth'][2]*scale+2)
        clearance=cap[0][2]*scale+lift-meta['mouth'][2]*scale
        assert clearance>=2-.001,(key,'pipette has not cleared the neck')
        clearances.append(round(clearance,4))
    for i,target in enumerate(targets):
        direction=sub(target,eye);length=math.sqrt(sum(x*x for x in direction));direction=tuple(x/length for x in direction)
        hits=[(t,index) for index,box in objects if (t:=raybox(eye,direction,box)) is not None]
        assert min(hits)[1]==i,(recipe['id'],i,'wrong reagent ray hit',hits)
    report['recipes'].append({'recipe':recipe['id'],'material_slots':len(targets),'correct_nearest_reagent_hits':len(targets),'cap_clearance_cm':clearances})
assert len(recipes)==8
for recipe in recipes:
    if recipe['id'] in ('brew_hp_basic','brew_mp_basic'):
        assert recipe['autoBase'] and [s['action'] for s in recipe['steps']]==['pour','stir']
        assert recipe['steps'][1]['amount']==2 and recipe['steps'][1]['direction']==0
report['basic_recipes']='automatic base; one main ingredient; two circles in either direction; bottle'
report['anchors']={'pour_landing_xy':[225,-106],'bottle_mouth_world_z':128,'stream_enters_bottle_z':127.7,'fixed_bottle_fill_bottom_local_z':-4.4,'heat_control_base_z':94.43}
report['saved_meshes_checked']=len(saved['meshes']);report['max_fbx_bounds_error_cm']=max(x['max_export_error_cm'] for x in saved['meshes'])
(ROOT/'geometry-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print('ALCHEMY_V7_GEOMETRY_CHECK_COMPLETE',sum(x['correct_nearest_reagent_hits'] for x in report['recipes']),'material slots across',len(recipes),'recipes')
