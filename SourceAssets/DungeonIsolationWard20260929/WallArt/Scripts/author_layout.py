"""Wall-art pools and safe mounting rectangles in ward-local UE centimetres."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];WARD=ROOT.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def build():
    cfg=read(WARD/'Config/room.json');sources=read(ROOT/'source_geometry.json')
    by_name={s['mesh'].split('/')[-1]:s for s in sources}
    def entry(series,letter,long_edge):
        s=by_name[f'SM_HospitalPosters_{series}_{letter}']
        scale=long_edge/(max(s['extent'][0],s['extent'][2])*2)
        return dict(id=f'{series}_{letter}',mesh=s['mesh'],origin=s['origin'],extent=s['extent'],scale=scale,materials=s['materials'])
    pools=dict(education=[entry('01',letter,74.4) for letter in 'ABCDEFGHIJKLMNOP'],
        room_numbers=[entry('02',letter,28) for letter in 'DEFG'],
        department=[entry('02','B',45)],decon=[entry('02','U',24)],
        staff=[entry('02','H',45)],shoe_covers=[entry('02','N',45)],exit=[entry('02','O',45)],
        notices=[entry('02',letter,55) for letter in 'IKLM'])
    # Original mesh face is +Y in UE. The source pivot is corrected at runtime.
    def slot(name,x,y,z,yaw=0,half_width=65,half_height=47,jitter=10):
        return dict(id=name,center=[round(x,3),round(y,3),z],yaw=yaw,half_width=half_width,half_height=half_height,jitter=jitter)
    groups=[]
    def group(name,pool,count,slots,**extra):
        groups.append(dict(id=name,pool=pool,min_count=count[0],max_count=count[1],slots=slots,**extra))
    hall=[];numbers=[];bedrooms=[]
    for room in cfg['rooms']:
        north=room['id'].startswith('N');sign=1 if north else -1
        # Concrete is 14 cm from wall centre. Mount 1 cm clear of that face,
        # entirely above the ceramic band and 88–99 cm impact rails.
        wall_y=-435*sign;yaw=0 if north else 180
        spans=[(room['x'][0]*100+50,room['x'][1]*100-50)]
        # Include cover-frame width and a 35 cm clear border around apertures.
        for center,half in [(room['door_x']*100,205),(room['window_x']*100,214)]:
            spans=[segment for a,b in spans for segment in ((a,min(b,center-half)),(max(a,center+half),b)) if segment[1]>segment[0]]
        for i,(a,b) in enumerate(spans):
            if b-a>=90:hall.append(slot(room['id']+f'_solid_{i}',(a+b)/2,wall_y,214,yaw,min(80,(b-a)/2),46,10))
        numbers.append(slot(room['id']+'_number',room['door_x']*100,wall_y,345,yaw,65,20,0))
        # Room-side posters go on the rear wall, outside rear service door reveals.
        x0,x1=room['x'];spans=[(x0*100+65,x1*100-65)]
        if 'rear_door_x' in room:
            c=room['rear_door_x']*100
            spans=[(a,b) for lo,hi in spans for a,b in ((lo,min(hi,c-220)),(max(lo,c+220),hi)) if b-a>=100]
        if spans:
            a,b=max(spans,key=lambda span:span[1]-span[0])
            rear_y=-1235 if north else 1235
            bedrooms.append(slot(room['id']+'_rear',(a+b)/2,rear_y,240,0 if north else 180,min(80,(b-a)/2),46,8))
    group('room_numbers','room_numbers',[4,4],numbers,fallback_pool='department')
    group('decontamination','decon',[1,1],[slot('Decon',2350,435,345,180,40,20,0)])
    group('service','staff',[1,1],[slot('Service',-2500,-435,480,0,45,20,0)])
    # Fit the 80 cm side piers; leave the descending gate and head housing clear.
    group('exit_markers','exit',[2,2],[slot('WestExit',-3285,-195,220,270,23,15,0),
        slot('EastExit',3285,195,220,90,23,15,0)],allow_repeat=True)
    group('hall_education','education',[6,8],hall)
    group('gallery_education','education',[2,3],[slot(f'Gallery{i}',x,-1685,222,0,70,46,12) for i,x in enumerate((-2300,-1400,-500,400,1300,2200))])
    group('bedroom_education','education',[3,4],bedrooms)
    group('decon_shoe_covers','shoe_covers',[1,1],[slot('Shoes',2080,435,192,180,35,19,0)])
    group('service_notices','notices',[1,2],[slot('WestLoopNotice',-2985,-850,215,270,65,45,6),
        slot('DeconNotice',2985,750,220,90,65,45,6)])
    return dict(version=1,source='/Game/HospitalCorridor',source_posters=36,
        source_textures=['/Game/HospitalCorridor/Textures/Objects/T_HospitalPosters_01_A',
                         '/Game/HospitalCorridor/Textures/Objects/T_HospitalPosters_02_A'],
        pools=pools,groups=groups,collision=False,receives_decals=False,
        selection='Seed + module index + group ID, without replacement except required exit signs',
        room_numbers='103..106 shuffled onto four doors, remaining door uses therapist nameplate')

def apply(module):
    result=dict(module)
    result['parts']=[p for p in module['parts'] if not p['mesh'].endswith('/SM_Ward_Wayfinding')]
    result['wall_art']=build()
    paths=set(result.get('runtime_assets',[]))
    for entries in result['wall_art']['pools'].values():
        for item in entries:paths.add(item['mesh']);paths.update(filter(None,item['materials']))
    result['runtime_assets']=sorted(paths)
    return result

if __name__=='__main__':
    write(ROOT/'layout.json',build())
    print('WARD_WALL_ART_LAYOUT_SAVED')
