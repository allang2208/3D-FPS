"""Save future-first-room data only; never changes a production catalog."""
from pathlib import Path
import json,math
ROOT=Path(__file__).resolve().parent;CFG=json.loads((ROOT/'Config/layout.json').read_text('utf8'));MAN=json.loads((ROOT/'manifest.json').read_text('utf8'))
def cm(p):return [p[0]*100,-p[1]*100,p[2]*100]
parts=[];actors=[];assets=set()
for m in MAN['meshes']:
    if m['kind'] in ('Glass','Fracture','PreviewCaps'):continue
    p=dict(mesh=m['mesh'],position=cm(m.get('position_m',[0,0,0])),yaw=0,scale=[1,1,1],collision=m['collision'],cast_shadow=m['cast_shadow'])
    if m['kind']=='Balustrades':p['guardrail_drop']=True
    parts.append(p);assets.add(m['mesh'])
for p in CFG['parts']:
    parts.append(dict(mesh=p['mesh'],position=cm(p['position_m']),yaw=-p['yaw_deg'],scale=p['scale'],collision=p['collision'],cast_shadow=p['cast_shadow']));assets.add(p['mesh'])
for p in CFG['containers']:
    d={k:v for k,v in p.items() if k not in ('id','position_m','yaw_deg','dimensions_m')};d.update(type='scene_container',container_id='ReceptionHall20261006.'+p['id'],position=cm(p['position_m']),yaw=-p['yaw_deg'],initial_open_fraction=0.)
    actors.append(d);assets.update([d['body'],d['door']])
for p in CFG['doors']:
    actors.append(dict(id=p['id'],type='solid_door',position=cm(p['position_m']),yaw=-p['yaw_deg'],leaf=p['leaf_mesh'],positive_hinge=p['positive_hinge'],open_seconds=.55,auto_close_seconds=0));assets.add(p['leaf_mesh'])
for p in CFG['glass']:
    prefix=CFG['base']+'/Meshes/SM_Reception_'+p['glass_kind']
    d=dict(id=p['id'],type='glass_window',position=cm(p['position_m']),yaw=-p['yaw_deg'],pane=prefix+'PaneV5',fracture=prefix+'FractureV5',
        fracture_material='/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassFragmentsV5',impact_particles='/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass',sound='/Game/Weapons/GunplayFX/Impacts/S_Impact_Glass_0',dimensions_cm=[p['width_m']*100,p['height_m']*100,.8])
    actors.append(d);assets.update(d[k] for k in ('pane','fracture','fracture_material','impact_particles','sound'))
lights=[]
for l in CFG['lights']:
    intensity=l['intensity']/(.5*(1-math.cos(math.radians(l['outer_cone_degrees'])))) if l['type']=='spot' else l['intensity']
    lights.append(dict(position=cm(l['position_m']),type=l['type'],intensity=intensity,radius=l['radius']*100,optimized_radius_cm=l['radius']*100,cast_shadows=l['cast_shadows'],
        color=[1,.92,.79],role=l['role'],max_draw_distance_cm=5500 if l['type']=='spot' else 3800,fade_range_cm=650,pitch=-90 if l['type']=='spot' else 0,
        outer_cone_degrees=l.get('outer_cone_degrees',74),inner_cone_degrees=l.get('inner_cone_degrees',52)))
ports=[dict(id=p['id'],position=cm(p['position']),normal=[p['normal'][0],-p['normal'][1],p['normal'][2]],width=p['width']*100,height=p['height']*100) for p in CFG['ports']]
module=dict(id=CFG['id'],family_id=CFG['id'],role='room',revision=CFG['revision'],min=[-2730,-1680,-40],max=[2730,1680,1030],
    cells=[dict(min=[-2430,-1680,-40],max=[2430,1680,1030]),dict(min=[-2730,-230,-30],max=[-2400,230,366]),dict(min=[2400,-180,-30],max=[2730,180,326])],
    ports=ports,port_pairs=[[0,1]],parts=parts,lights=lights,runtime_actors=actors,runtime_assets=sorted(assets),anchors=[],props=[],
    walk_mask=[dict(min=[-2400,-1650,0],max=[2400,1650,450])],selection=dict(chance_per_run=0,max_per_run=1),authoring_only=True,
    route_intent=dict(registration='pending_user_acceptance',placement='future dungeon first room'))
doc=dict(status='draft_only_not_registered',modules=[module],module_asset_paths=sorted(assets),hard_references_saved=False,runtime_activation=False,
    preview_caps_included=False,container_rewards_deferred=True,navigation_and_spawn_configuration='Reserved for accepted production integration',tests_run=False)
import runpy
doc=runpy.run_path(str(ROOT.parent/'HallLighting20261007/profile.py'))['extend_draft'](doc,'Reception',CFG)
(ROOT/'Config/module-draft.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf8')
print('RECEPTION_MODULE_DRAFT_SAVED',len(parts),'parts',len(actors),'runtime actors')
