"""Production facility flow; merge into the current recipe, never a stale catalog."""
from pathlib import Path
import json, copy, math, runpy
ROOT=Path(__file__).resolve().parent; SOURCE=ROOT.parent
REVISION='facility_three_pairs_port_seams_20261008'
BASE='/Game/Dungeons/FacilityFlow20261007'

def read(path):return json.loads(path.read_text('utf8'))
def cm(p):return [p[0]*100,-p[1]*100,p[2]*100]
def paths(value):
    if isinstance(value,str) and value.startswith(('/Game/','/Script/')):yield value
    elif isinstance(value,dict):
        for v in value.values():yield from paths(v)
    elif isinstance(value,list):
        for v in value:yield from paths(v)

def runtime_parts(parts):
    # Subject-map drafts omit these fields; the production assembler requires them.
    for part in parts:
        part.setdefault('fluid',False)
        part.setdefault('materials',[])

def light(p):
    d={k:copy.deepcopy(v) for k,v in p.items() if k not in ('position_m','original_intensity','original_radius')}
    d['position']=cm(p['position_m']);d['radius']=p['radius']*100;d['optimized_radius_cm']=d['radius']
    d.setdefault('color',[.85,.92,.84]);d.setdefault('indirect_lighting_intensity',.25)
    d.setdefault('max_draw_distance_cm',3500);d.setdefault('fade_range_cm',500)
    if p.get('type')=='spot':d['intensity']/=.5*(1-math.cos(math.radians(p['outer_cone_degrees'])))
    return d

def exposure(extent,center):
    return dict(type='post_process',position=center,yaw=0,extent=extent,priority=15,blend_radius=120,
        exposure_ev=.95,exposure_bias=-.25,indirect_intensity=.8,saturation=.96,contrast=1.,vignette=.25,bloom=.08)

def glass(p,prefix):
    return dict(type='glass_window',id=p['id'],position=cm(p['position_m']),yaw=-p['yaw_deg'],
        pane=p.get('pane',prefix+p.get('glass_kind','')+'PaneV5'),fracture=p.get('fracture',prefix+p.get('glass_kind','')+'FractureV5'),
        fracture_material='/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassFragmentsV5',
        impact_particles='/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass',sound='/Game/Weapons/GunplayFX/Impacts/S_Impact_Glass_0',
        dimensions_cm=[p['width_m']*100,p['height_m']*100,.8])

def reception_and_entry():
    reception=copy.deepcopy(read(SOURCE/'DungeonReceptionHall20261006/Config/module-draft.json')['modules'][0])
    reception.update(authoring_only=False,selection=dict(chance_per_run=1,max_per_run=1),revision=REVISION,
        route_intent=dict(placement='mandatory first hall via side breach'),walk_polyline=[[-1880,1682,0],[-1880,0,0],[2700,0,0]])
    reception['ports'][0]=dict(id='SideBreach',position=[-1880,1682,0],normal=[0,1,0],width=300,height=280)
    reception['parts']=[p for p in reception['parts'] if not p['mesh'].endswith(('_OuterWalls','_WallTrim','SM_RH2_Signs'))]
    # Move both southern lounge sets as rigid groups to the west wall. Preserve
    # tabletop items and their orientation relative to their own coffee tables.
    for p in reception['parts']:
        x,y,z=p['position']
        if 1200<y<1650 and z<150 and -2250<x<-1520:
            oldx,newy=(-2070,750) if x<-1880 else (-1690,100)
            p['position']=[-2290-(y-1530),newy+(x-oldx),z];p['yaw']=p.get('yaw',0)+90
    entrance=dict(id='FacilityEntrancePassage',family_id='FacilityEntrancePassage',role='entry_passage',
        min=[-277,-1200,-32],max=[277,20,430],cells=[dict(min=[-277,-1200,-32],max=[277,20,430])],
        ports=[dict(position=[0,0,0],normal=[0,1,0],width=300,height=280),dict(position=[0,-1200,0],normal=[0,-1,0],width=300,height=280)],
        port_pairs=[[0,1]],parts=[],lights=[],runtime_actors=[],runtime_assets=[],anchors=[],props=[],walk_polyline=[[0,0,0],[0,-1200,0]])
    for item in read(ROOT/'geometry.json')['meshes']+read(ROOT/'fixture-geometry.json')['meshes']:
        part=dict(mesh=item['mesh'],position=[0,0,0],yaw=0,scale=[1,1,1],collision=item['collision'],cast_shadow=item['cast_shadow'])
        (entrance if item['kind'].startswith('Passage') else reception)['parts'].append(part)
    for y in (-200,-600):entrance['lights'].append(dict(position=[0,y,248],intensity=180,radius=420,optimized_radius_cm=420,
        color=[.75,.83,.78],cast_shadows=False,role='entry',type='point',max_draw_distance_cm=1800,fade_range_cm=400,indirect_lighting_intensity=.12))
    reception.setdefault('runtime_actors',[]).append(exposure([2690,1670,535],[0,0,495]))
    entrance['runtime_actors'].append(exposure([275,610,240],[0,-590,200]))
    polished=ROOT/'EntryPolish20261008/install-receipt.json'
    if polished.exists() and read(polished).get('stage')=='map_saved':
        runpy.run_path(str(polished.parent/'recipe.py'))['apply_modules'](reception,entrance)
    front=ROOT/'FrontEntry20261008/install-receipt.json'
    if front.exists() and read(front).get('stage')=='map_saved':
        runpy.run_path(str(front.parent/'recipe.py'))['apply_module'](reception)
    night=ROOT/'NightStreet20261009/install-receipt.json'
    if night.exists() and read(night).get('stage')=='map_saved':
        runpy.run_path(str(night.parent/'recipe.py'))['apply_module'](reception)
    return reception,entrance

def transit():
    d=read(SOURCE/'DungeonFacilityTransit20261007/Config/module-draft.json')
    bounds=dict(min=[min(c['min'][i] for c in d['cells']) for i in range(3)],max=[max(c['max'][i] for c in d['cells']) for i in range(3)])
    ports=[dict(id=p.get('id',''),position=p['position'],normal=p['normal'],width=p.get('width',p.get('width_cm')),height=p.get('height',p.get('height_cm'))) for p in d['ports']]
    m=dict(id='FacilityTransit',family_id='FacilityTransit',role='junction',revision=REVISION,lighting_revision=d['lighting_revision'],**bounds,
        cells=d['cells'],ports=ports,parts=d['parts'],lights=[light(p) for p in d['lights']],runtime_actors=[],runtime_assets=d['runtime_assets'],anchors=[],props=[])
    n=d['native_interactions'];actors=m['runtime_actors']
    for p in n['containers']:
        a={k:v for k,v in p.items() if k not in ('position_m','yaw_deg','dimensions_m','id')}
        a.update(type='scene_container',container_id='FacilityTransit.'+p['id'],position=cm(p['position_m']),yaw=-p['yaw_deg'],initial_open_fraction=0.)
        actors.append(a)
    for p in n['doors']:actors.append(dict(type='solid_door',id=p['id'],position=cm(p['position_m']),yaw=-p['yaw_deg'],leaf=p['leaf_mesh'],positive_hinge=p['positive_hinge'],open_seconds=.55,auto_close_seconds=0))
    for p in n['glass']:actors.append(glass(p,'/Game/Dungeons/FacilityTransit20261007/Meshes/SM_FT_'))
    display=d['central_display']['assembly']
    for p in display['glass']:actors.append(glass(p,''))
    m['lights'] += [light(p) for p in display['lights']]
    actors.append(exposure([2430,1825,470],[0,0,420]))
    variants={};pair_signs={}
    for gate in d['portal_sockets']:
        pos=cm(gate['position_m']);yaw=-gate['yaw_deg'];a=math.radians(yaw);co,si=math.cos(a),math.sin(a)
        def transform(p):return [pos[0]+p[0]*co-p[1]*si,pos[1]+p[0]*si+p[1]*co,pos[2]+p[2]]
        variants[gate['route']]={};pair_signs[gate['route']]={}
        for sign in read(ROOT/'sign-geometry.json')['meshes']:
            pair_signs[gate['route']][sign['key']]=[dict(mesh=sign['mesh'],position=pos,yaw=yaw,scale=[1,1,1],collision=False,cast_shadow=False)]
        for theme,kit in d['portal_families'].items():
            parts=copy.deepcopy(kit)
            for part in parts:part['position']=transform(part.get('position',[0,0,0]));part['yaw']=part.get('yaw',0)+yaw
            variants[gate['route']][theme]=parts
        portal_lighting=d['portal_lighting']
        for local,lumens in [([0,70,422],portal_lighting['canopy_lumens']),([0,-200,247],portal_lighting['tunnel_lumens'])]:
            m['lights'].append(dict(position=transform(local),intensity=lumens,radius=480,optimized_radius_cm=480,
                type='point',color=[.91,.82,.64],indirect_lighting_intensity=.25,cast_shadows=False,role='portal',max_draw_distance_cm=3200,fade_range_cm=500))
    # All six kits are hard referenced although only the three selected kits are assembled.
    m['runtime_assets']=sorted(set(paths([m['parts'],actors,m['lights'],variants,pair_signs])))
    return m,variants,pair_signs

def extend(catalog):
    result=runpy.run_path(str(SOURCE/'DungeonEcology20261004/Production20261005/Scripts/extend_catalog.py'))['extend'](catalog)
    modules={m['id']:m for m in result['modules']}
    power=read(SOURCE/'DungeonPowerTheme20261004RefineV2/Config/module-drafts.json')
    for m in power['modules']:
        if m['id'] not in power['proposed_sequence']:continue
        m=copy.deepcopy(m);m.update(authoring_only=False,selection=dict(chance_per_run=1,max_per_run=1))
        if m['id']=='AccumulatorControl':
            # The circular shell's conservative cells reach 31.816 cm beyond
            # its chord door plane. Permit only that matched wall seam.
            m['port_seam_depth_cm']=35.
        # Reuse an existing facility encounter roster, anchored to the authored
        # clear walking positions. No new monster class or asset is introduced.
        spawn=copy.deepcopy(modules['AbandonedFlueGasStation']['spawn'])
        spawn.update(theme='power',anchor_roles=['power_combat'],count=[3,5],sealed_encounter=True)
        m['spawn']=spawn;modules[m['id']]=m
    result['modules']=list(modules.values());result['room_ids']=list(dict.fromkeys(result['room_ids']+power['proposed_sequence']))
    rules=result['themed_routes'];rules['routes']=[r for r in rules['routes'] if r['id']!='power']+[dict(id='power',sequence=power['proposed_sequence'])]
    rules.update(version=3,theme_candidates=6,selected_routes_per_run=3,themes_per_route=2,selection='shuffle_without_replacement_then_pair',
        approach_transition_count=[0,0],before_after_transition_count=[0,0],boss_access='any_complete_route_then_archive')
    rules['forward_only']=list(dict.fromkeys(rules['forward_only']+[s for r in rules['routes'] for s in r['sequence']]))
    reception,entry=reception_and_entry();hub,variants,pair_signs=transit()
    fixed=[reception,entry,hub]
    for m in fixed:m['runtime_assets']=sorted(set(m.get('runtime_assets',[]))|set(paths([m['parts'],m['lights'],m['runtime_actors']])))
    replace={m['id'] for m in fixed};result['modules']=[m for m in result['modules'] if m['id'] not in replace]+fixed
    result.update(generator_version=9,facility_flow=dict(revision=REVISION,entrance=entry['id'],reception=reception['id'],junction=hub['id'],
        route_portal_variants=variants,route_pair_signs=pair_signs,entry_style='side_concrete_breach',closed_reception_front=True),
        start_position=[0,0,94],start_normal=[0,-1,0],reserved_min=[-190,21,-32],reserved_max=[190,360,524])
    result.pop('start_connection',None)
    result=runpy.run_path(str(SOURCE/'ThemeThirdRoomTreasure20261007/treasure.py'))['extend'](result)
    promoted={'FacilityEntrancePassage','FacilityReceptionHall','FacilityTransit',
        'EcoNursery','EcoHydroponics','EcoBiosphere',*power['proposed_sequence']}
    for m in result['modules']:
        if m['id'] in promoted:runtime_parts(m['parts'])
    for groups in (variants,pair_signs):
        for route in groups.values():
            for parts in route.values():runtime_parts(parts)
    # Preserve the installed joint-layout policy when rebuilding authored data.
    # A changed geometry/rule contract is rejected by the native bank reader.
    bank_path=ROOT/'Config/layout-bank-v1.json'
    if bank_path.exists():
        bank=read(bank_path)
        if len(bank.get('entries',{}))==120 and len(bank.get('contract_sha1',''))==40 and not bank.get('native_replay_pending',True):
            result['facility_flow']['joint_layout_version']=1
            result['facility_flow']['layout_bank']=bank
    restored=ROOT/'Receipts/original-entry-restore-20261008.json'
    if restored.exists() and read(restored).get('stage')=='map_saved':
        # The installed bank is already in the restored start's coordinate frame.
        # Geometry changes still invalidate its native contract in the usual way.
        result=runpy.run_path(str(ROOT/'restore_entry_recipe.py'))['extend'](result,migrate_bank=False)
    closed_fixture_recipe=ROOT/'SpawnEntries20261009/recipe.py'
    if closed_fixture_recipe.exists():
        result=runpy.run_path(str(closed_fixture_recipe))['reapply_if_installed'](result,
            runpy.run_path(str(ROOT/'restore_entry_recipe.py'))['contract_hash'])
    frame_fit=ROOT/'EntryFrameFit20261009/install-receipt.json'
    if frame_fit.exists() and read(frame_fit).get('stage')=='map_saved':
        result=runpy.run_path(str(frame_fit.parent/'recipe.py'))['extend'](result,
            runpy.run_path(str(ROOT/'restore_entry_recipe.py'))['contract_hash'])
    return result

if __name__=='__main__':
    catalog=extend(read(ROOT/'Sources/production-catalog.json'))
    (ROOT/'Config').mkdir(exist_ok=True)
    (ROOT/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
    print('FACILITY_FLOW_RECIPE_WRITTEN')
