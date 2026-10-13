"""Author explicit per-light reach corrections from the requested floor audit."""
from pathlib import Path
import json,math,collections

ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'Receipts/range-audit.json').read_text('utf8'))
geometry=json.loads((ROOT/'Receipts/floor-geometry.json').read_text('utf8'))
modules={m['id']:m for m in geometry['catalog']['modules']}
changes=[]
for row in rows:
    mid=row['module'];key=row['id'];height=row.get('height')
    if mid=='FacilityReceptionHall':row['decision']='reception handled in preceding patch';continue
    if row['intensity']<=0:row['decision']='preserve authored dead lamp';continue
    if any(s in key for s in ('BenchTask','WorkbenchKit_Main','Botanical_Canopy')) or 'PointLight' in row['type']:
        row['decision']='task/display/bare-bulb source; preserve object-directed reach';continue
    if height is None:raise RuntimeError('Unresolved ordinary light floor: '+mid+'/'+key)
    # Keep established adequate lights. For short lights, leave falloff margin
    # beyond the floor; tall main lights also need room-scale lateral coverage.
    high_main=height>=500 and row['role'].lower() in ('key','main')
    threshold=1.65 if high_main else 1.5
    if row['effective_radius']/height>=threshold:
        row['decision']='existing floor reach retained';continue
    radius=math.ceil(height*(2.0 if high_main else 1.75)/50)*50.
    row['decision']='extend high main light' if high_main else 'extend floor reach'
    row['radius_after']=radius
    row['axis_within_range_after']=height<radius
    row['range_height_after']=round(radius/height,3)
    # Widening unshadowed lights would brighten through walls/slabs. These
    # revised emitters use real occlusion; room scheduling/distance caps remain.
    change=dict(module=mid,index=row['index'],id=key,position=row['position'],
        before=dict(radius=row['radius'],effective_radius=row['effective_radius'],cast_shadows=row['shadows']),
        fields=dict(radius=radius,optimized_radius_cm=radius,cast_shadows=True),
        floor=row['floor'],height_cm=height,reason=row['decision'])
    if mid!='FixedStart':change['fixture_mesh']=modules[mid]['lights'][row['index']].get('fixture_mesh')
    changes.append(change)
result=dict(revision='dungeon_floor_reach_20261009',changes=changes,
    policy='General short lights: range/height < 1.5 -> 1.75; main lights >=5m: <1.65 -> 2.0; round up to 50cm. Preserve adequate lights and object lighting.',
    checked_catalog_lights=305,checked_fixed_lights=13,
    missed_floor_before=sum(r.get('axis_within_range')==False and r.get('decision','').startswith('extend') for r in rows),
    brightness_changed=False,directions_changed=False,cones_changed=False,
    additional_shadow_sources=sum(not c['before']['cast_shadows'] for c in changes))
(ROOT/'Config').mkdir(exist_ok=True)
(ROOT/'Config/coverage.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'Receipts/decisions.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print('COVERAGE_PREPARED',len(changes),'changes;',result['missed_floor_before'],'could not reach floor;',result['additional_shadow_sources'],'added occlusion sources')
print(dict(collections.Counter(c['module'] for c in changes)))
