"""Serialize the saved ward assets and gameplay recipes into one rigid room."""
import json,math,copy,runpy
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def point(p):return [round(p[0]*100,4),round(-p[1]*100,4),round(p[2]*100,4)]
def direction(p):return [p[0],-p[1],p[2]]
def box(lo,hi):
    a,b=point(lo),point(hi)
    return dict(min=[min(a[i],b[i]) for i in range(3)],max=[max(a[i],b[i]) for i in range(3)])
def part(mesh,p=(0,0,0),collision=True,yaw=0,**extra):
    return dict(mesh=mesh,position=point(p),scale=[1,1,1],yaw=yaw,collision=collision,
                affects_navigation=collision,fluid=False,materials=[],**extra)
def actor(kind,p=(0,0,0),yaw=0,**extra):return dict(type=kind,position=point(p),yaw=yaw,**extra)
def asset(path):
    result=u.load_asset(path)
    if not result:raise RuntimeError('Missing saved ward dependency '+path)
    return result

def build():
    cfg=read(ROOT/'Config/room.json');man=read(ROOT/'Authored/manifest.json');receipt=read(ROOT/'Receipts/install.json')
    if receipt['revision']!=cfg['revision']:raise RuntimeError('Import the current ward architecture first')
    pieces=[];actors=[];lights=[];base=cfg['ue_base']
    for obj in man['objects']:
        if obj['sample_only'] or obj['kind']=='ObservationGlass':continue
        p=part(base+'/Meshes/'+obj['name'],collision=obj['collision'])
        if obj['kind'] in ('Walls','FloorSlabs'):p['blood_receiver']=True
        pieces.append(p)
    glass=cfg['glass_breakage']
    common={k:glass[k] for k in ('fracture_material','impact_particles','sound')}
    for door in cfg['glass_doors']:
        fb=asset(door['frame']).get_bounds();lb=asset(door['leaf']).get_bounds()
        fe,fo,le=fb.box_extent,fb.origin,lb.box_extent
        p=door['position'];angle=math.radians(door['yaw'])
        pieces.append(part(door['frame'],[p[0],p[1],p[2]+(fe.z-fo.z)/100],True,door['yaw'],ward_frame=door['id']))
        for side in (-1,1):
            offset=side*(fe.y-8.-le.y)/100
            lp=[p[0]-math.sin(angle)*offset,p[1]-math.cos(angle)*offset,p[2]+(fe.z-le.z)/100]
            actors.append(actor('glass_door',lp,door['yaw'],**glass['door'],**common,
                leaf=door['leaf'],frame_id=door['id'],positive_hinge=side>0,
                open_seconds=door['open_seconds'],auto_close_seconds=door['auto_close_seconds']))
    for window in glass['windows']:
        actors.append(actor('glass_window',window['position'],window['yaw'],**glass['window'],**common))
    for lamp in cfg['lights']:
        fixture='/Game/Dungeons/IndustrialV1/Meshes/SM_CeilingLamp_'+('Warm' if lamp['warm'] else 'Cool')
        p=part(fixture,lamp['position'],False)
        key=lamp['id'] if lamp['fault']!='steady' else 'Warm' if lamp['warm'] else 'Cool'
        diffuser=base+'/Materials/MI_Diffuser_'+key
        for slot in asset(fixture).get_editor_property('static_materials'):
            identity=str(slot.material_slot_name)+' '+(slot.material_interface.get_name() if slot.material_interface else '')
            p['materials'].append(diffuser if any(s in identity.lower() for s in ('glass','emiss','light','tube')) else '')
        pieces.append(p)
        if lamp['fault']=='dead':continue
        lp=lamp['position'][:];lp[2]-=.125
        light=dict(position=point(lp),intensity=lamp['lumens'],radius=lamp['radius_cm'],optimized_radius_cm=lamp['radius_cm'],
            color=[1,.78,.53] if lamp['warm'] else [.72,.86,1],role=lamp['role'],type='point',
            cast_shadows=lamp['cast_shadows'],max_draw_distance_cm=lamp['max_draw_distance_cm'],fade_range_cm=lamp['fade_range_cm'])
        if lamp['fault']=='flicker':light['light_function']=base+'/Materials/MI_LampFunction_'+lamp['id']
        lights.append(light)
    benches=cfg['bench_layout']
    for b in benches['entries']:
        north=b['side']=='N'
        pieces.append(part(benches['mesh'],[b['center_x_m'],benches['center_abs_y_m']*(1 if north else -1),
            (benches['floor_top_cm']+benches['floor_gap_cm'])/100],True,0 if north else 180))
    beds=actor('beds',**{k:cfg['bed_scatter'][k] for k in ('mesh','min_beds_per_room','max_beds_per_room','wall_clearance','bed_clearance')},
        rooms=[],keep_clear=[],poses=read(ROOT/'BedScatter/bed-manifest.json')['poses'],room_props=cfg['room_props'])
    for r in cfg['rooms']:
        lo=[r['x'][0]*100,-r['y'][1]*100,4.2];hi=[r['x'][1]*100,-r['y'][0]*100,400]
        beds['rooms'].append(dict(id=r['id'],min=lo,max=hi))
        dx=r['door_x']*100;north=r['id'].startswith('N');front=-450 if north else 450
        beds['keep_clear'] += [dict(min=[dx-90,lo[1],0],max=[dx+90,hi[1],400]),
            dict(min=[dx-220,front-225 if north else front,0],max=[dx+220,front if north else front+225,400])]
        if 'rear_door_x' in r:
            rx=r['rear_door_x']*100;mid=(lo[1]+hi[1])/2
            beds['keep_clear'] += [dict(min=[rx-90,lo[1],0],max=[rx+90,hi[1],400]),
                dict(min=[min(dx,rx)-90,mid-90,0],max=[max(dx,rx)+90,mid+90,400])]
    actors.append(beds)
    blood=cfg['blood_scatter']
    for group in blood['groups']:
        surfaces=[dict(center=point(s['center_m']),normal=direction(s['normal']),axis_u=direction(s['axis_u']),
                    half_size=[v*100 for v in s['half_size_m']],wall=s['wall']) for s in group['surfaces']]
        actors.append(actor('blood',material=blood['material'],floor_count=group['floor_count'],wall_count=group['wall_count'],
            scanned_size_range_cm=blood['scanned_size_range_cm'],floor_size_scale=blood['floor_size_scale'],surfaces=surfaces))
    cells=[box(c['min'],c['max']) for c in cfg['cells_m']]
    ports=[dict(id=p['id'],position=point(p['position']),normal=direction(p['normal']),width=p['width']*100,height=p['height']*100) for p in cfg['ports']]
    policy=cfg['pool']
    spawn=dict(source='IsolationWard20260929',count=policy['spawn_count'],sealed_encounter=True,theme='abandoned_isolation_ward',
        anchor_roles=['ward_combat'],pool=[
            dict(id='NurseZombie',**{'class':'/Script/FPSGAME.NurseZombie'},weight=4,level=10,rank='elite'),
            dict(id='FatZombie',**{'class':'/Script/FPSGAME.FatZombie'},weight=2,level=12,rank='elite'),
            dict(id='Mutant3',**{'class':'/Script/FPSGAME.Mutant3'},weight=1,level=14,rank='elite')])
    walk=[box([-30,-3.3,-.05],[30,3.3,2.8]),box([-33,-1.45,-.05],[-30,1.45,2.8]),box([30,-1.45,-.05],[33,1.45,2.8])]
    module=dict(id=cfg['id'],family_id=cfg['id'],role='room',encounter_role='special_combat',revision=cfg['revision'],
        min=[min(c['min'][i] for c in cells) for i in range(3)],max=[max(c['max'][i] for c in cells) for i in range(3)],
        cells=cells,ports=ports,port_pairs=[[0,1]],parts=pieces,lights=lights,runtime_actors=actors,
        anchors=[dict(position=point(p),role='ward_combat') for p in policy['spawn_anchors_m']],
        walk_mask=walk,walk_polyline=[point(p) for p in policy['walk_polyline_m']],spawn=spawn,selection=policy['selection'])
    # Explicit hard references and staged preloading cover runtime-only dependencies too.
    def paths(value):
        if isinstance(value,str) and value.startswith(('/Game/','/Script/')):yield value
        elif isinstance(value,dict):
            for v in value.values():yield from paths(v)
        elif isinstance(value,list):
            for v in value:yield from paths(v)
    module['runtime_assets']=sorted(set(paths(actors)))
    module=runpy.run_path(str(ROOT/'WallArt/Scripts/author_layout.py'))['apply'](module)
    return module
