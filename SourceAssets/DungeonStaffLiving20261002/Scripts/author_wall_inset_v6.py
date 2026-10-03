"""Door cut in the original L-wall, interior toilet, wired kettle and true type aspect."""
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent
import json
if json.loads((SCRIPT.parent/'Config/room.json').read_text('utf8')).get('coffee_polish_revision',0)>=7:
    current=SCRIPT/'author_coffee_polish_v7.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
entry=SCRIPT/'author_living.py';_STAFF_REFINEMENT_HELPERS=True
basecode=entry.read_text('utf8')
exec(compile(basecode.split('for key,fn in PROTOTYPES.items():')[0],str(entry),'exec'))
import copy
OUT=ROOT/'WallInsetV6/Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE=CFG['ue_base']+'/WallInsetV6';records=[];prototypes={};architectures=[]
ATLAS=json.loads((OUT/'labels-atlas.json').read_text('utf8'))
NOTICE=json.loads((OUT/'notice-atlas.json').read_text('utf8'))
for key in ('Labels','Notices','Stainless','KettleRubber'):
    MAPPING[key]=BASE+'/Materials/M_Staff_'+key+'_V6';MATS[key]=bpy.data.materials.new('RS_'+key)
for key in ('FreshPlastic','Coffee'):
    MAPPING[key]=CFG['ue_base']+'/RoomDetailsV5/Materials/M_Staff_'+key+'_V5';MATS[key]=bpy.data.materials.new('RS_'+key)
MAPPING['PoolBlue']=CFG['ue_base']+'/ScenePolishV4/Materials/M_Staff_PoolBlue_V4';MATS['PoolBlue']=bpy.data.materials.new('RS_PoolBlue')
v4=SCRIPT/'author_scene_polish_v4.py';v4code=v4.read_text('utf8')
exec(compile(v4code[v4code.index('v3=SCRIPT/'):v4code.index('def emit(')],str(v4),'exec'))
v3=SCRIPT/'author_refinement_v3.py';v3code=v3.read_text('utf8')
exec(compile(v3code[v3code.index('def paper_quad'):v3code.index('PROTOTYPES.update')],str(v3),'exec'))
def curve(points,steps=10):
    ps=[Vector(p) for p in points];out=[]
    for i in range(len(ps)-1):
        a=ps[max(0,i-1)];b=ps[i];c=ps[i+1];d=ps[min(i+2,len(ps)-1)]
        for k in range(steps):
            t=k/steps;out.append(tuple(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)))
    out.append(tuple(ps[-1]));return out
def kettle_v6():
    # Clean stainless shell replaces the rusty shared service-metal finish.
    lathe((0,0,0),[(.032,.072),(.040,.082),(.058,.088),(.083,.092),(.125,.092),(.176,.087),(.222,.075),(.246,.066)],'Stainless',128)
    cylinder((0,0,.017),(0,0,1),.083,.034,'KettleRubber',sides=96)
    detail.ring((0,0,.036),(0,0,1),.084,.073,.011,'Stainless',96,'Body')
    cylinder((0,0,.250),(0,0,1),.068,.012,'Stainless',sides=96)
    detail.ring((0,0,.248),(0,0,1),.070,.067,.009,'KettleRubber',96,'Body')
    rounded_box('Body',(0,.008,.267),(.038,.042,.020),'KettleRubber',.008,8)
    rounded_box('Body',(0,.060,.248),(.026,.022,.017),'Stainless',.005,6)
    spout=curve([(0,-.060,.205),(0,-.094,.206),(0,-.122,.222),(0,-.151,.238)],12)
    detail.sweep('Body',spout,.023,'Stainless',48,.005)
    detail.ring((0,-.151,.238),(0,-.90,.44),.024,.017,.006,'Stainless',64,'Body')
    handle=curve([(0,.064,.229),(0,.128,.245),(0,.163,.226),(0,.176,.189),(0,.176,.119),(0,.151,.085),(0,.080,.079)],12)
    detail.tube('Body',handle,.014,'KettleRubber',32)
    for z in (.086,.225):rounded_box('Body',(0,.083,z),(.032,.032,.027),'KettleRubber',.009,7)
    rounded_box('Body',(0,.132,.062),(.021,.036,.012),'KettleRubber',.003,5)
    cylinder((0,.130,.069),(0,0,1),.0035,.002,'PoolBlue',sides=24)
    # Recessed gauge and measurement marks are fitted to the shell side.
    rounded_box('Body',(.089,0,.139),(.006,.029,.095),'KettleRubber',.002,5)
    box('Body',(.0926,0,.129),(.0008,.015,.053),'PoolBlue')
    for z,w in ((.100,.016),(.125,.010),(.150,.016),(.175,.010)):
        box('Body',(.094,0,z),(.001,w,.0013),'FreshPlastic')
    detail.ring((0,0,.061),(0,0,1),.089,.087,.004,'Stainless',96,'Body')
    rounded_box('Body',(0,.092,.024),(.016,.025,.018),'KettleRubber',.004,5)
def kettle_power():
    # Same fixed kettle transform as the scene configuration; strain relief,
    # countertop contact, climb to wall and plug all form one continuous cable.
    yaw=math.radians(163);x0=10.82-.099*math.sin(yaw);y0=-11.37+.099*math.cos(yaw)
    wire=curve([(x0,y0,.984),(10.88,-11.47,.966),(11.00,-11.57,.966),
        (11.17,-11.67,.966),(11.20,-11.724,1.03),(11.20,-11.724,1.18),(11.20,-11.724,1.241)],14)
    detail.tube('Body',wire,.0035,'KettleRubber',20)
    # Plate back rests on the inside tile face of the existing south wall.
    rounded_box('Body',(11.20,-11.803,1.27),(.16,.023,.102),'FreshPlastic',.009,7)
    rounded_box('Body',(11.20,-11.789,1.27),(.131,.005,.076),'FreshPlastic',.004,5)
    for dx in (-.036,.036):box('Body',(11.20+dx,-11.785,1.264),(.006,.004,.018),'KettleRubber')
    box('Body',(11.20,-11.785,1.286),(.006,.004,.014),'KettleRubber')
    for dx in (-.069,.069):cylinder((11.20+dx,-11.789,1.27),(0,1,0),.003,.003,'Stainless',sides=24)
    rounded_box('Body',(11.20,-11.753,1.274),(.044,.068,.048),'KettleRubber',.007,7)
    detail.tube('Body',[(11.20,-11.724,1.241),(11.20,-11.724,1.256)],.007,'KettleRubber',24)
    for z in (1.243,1.247,1.251):detail.ring((11.20,-11.724,z),(0,0,1),.008,.006,.002,'KettleRubber',24,'Body')
def bathroom_interior():
    # All interior construction is behind the original y=8 protruding face.
    # Its wall/door hole is authored in the original architecture below.
    box('Body',(12,10,-.16),(6,4,.28),'Concrete');collider((12,10,-.16),(6,4,.28))
    # Tile finish with a real square opening for the reused floor-drain grate.
    x0,x1,y0,y1=9.18,14.82,8.18,11.82;cx,cy,r=10.70,10.1,.18
    for xa,xb,ya,yb in ((x0,cx-r,y0,y1),(cx+r,x1,y0,y1),(cx-r,cx+r,y0,cy-r),(cx-r,cx+r,cy+r,y1)):
        box('Body',((xa+xb)/2,(ya+yb)/2,-.009),(xb-xa,yb-ya,.024),'Ceramic')
        collider(((xa+xb)/2,(ya+yb)/2,-.009),(xb-xa,yb-ya,.024))
    detail.grate(cx-r,cx+r,cy)
    box('Body',(12,10,3.47),(5.64,3.64,.14),'Concrete');collider((12,10,3.47),(5.64,3.64,.14))
    box('Body',(12,10,5.64),(6,4,.28),'Concrete')
    # Inner side of the original front and west wall uses the same intact tiles.
    SURFACES.wall(globals(),Vector((9,8)),Vector((1,0)),Vector((0,1)),6,[dict(center=3.2,width=1.12,height=2.32)],None,.28)
    SURFACES.wall(globals(),Vector((9,12)),Vector((0,-1)),Vector((1,0)),4,[],None,.28)
    # Open inward, within the interior bay, never occupying the dining room.
    ang=math.radians(88);co,si=math.cos(ang),math.sin(ang);hx,hy=11.68,8.015
    c=(hx+.52*co,hy+.52*si,1.13)
    rounded_box('Body',c,(1.04,.042,2.24),'OlivePaint',.009,5)
    # The bevel helper has no yaw input: rotate its group around the hinge.
    key='Rounded_'+str(SERIAL)
    for i,(x,y,z) in enumerate(G[key]['v']):
        dx=x-c[0];dy=y-c[1];G[key]['v'][i]=(c[0]+dx*co-dy*si,c[1]+dx*si+dy*co,z)
    collider(c,(1.04,.055,2.24),ang)
    for z in (.35,1.15,1.98):cylinder((hx,hy,z),(0,0,1),.009,.055,'Stainless',sides=32)
    handle=(hx+.90*co,hy+.90*si,1.05)
    cylinder(handle,(-si,co,0),.019,.098,'Stainless',sides=32)
    sign((12.20,7.813,2.59),.45,.19,'Toilet',kind='Body')
    # A single stall separated from the washbasin, with accessible paper roll.
    box('Body',(12.52,11.11,.99),(.040,1.40,1.95),'FreshPlastic');collider((12.52,11.11,.99),(.040,1.40,1.95))
    for y in (10.52,11.65):cylinder((12.52,y,.094),(0,0,1),.024,.18,'Stainless',sides=32)
    detail.tube('Body',[(14.80,11.23,.69),(14.66,11.23,.69),(14.66,11.06,.69)],.008,'Stainless',24)
    cylinder((14.66,11.14,.69),(0,1,0),.052,.115,'FreshPlastic',sides=64)
    rounded_box('Body',(9.191,10.6,2.65),(.028,.36,.24),'FreshPlastic',.009,6)
    for z in [2.55+i*.025 for i in range(9)]:box('Body',(9.21,10.6,z),(.007,.32,.009),'Stainless')
    # Recessed grout joints remain regular; no tile peeling is introduced.
    for x in [9.75+i*.60 for i in range(9)]:box('Body',(x,10,.0035),(.003,3.6,.001),'Mortar')
    for y in (8.75,9.35,9.95,10.55,11.15):
        # Keep the drain opening unobstructed.
        for xa,xb in ((9.18,10.51),(10.89,14.82)):
            box('Body',((xa+xb)/2,y,.0035),(xb-xa,.003,.001),'Mortar')

raw_export=export_mesh;font_geometry=[]
def original_export(name,g,**kw):
    quads=[]
    for face,material,uv in zip(g['f'],g['m'],g['uv']):
        if material not in ('Labels','Notices') or len(face)!=4 or not uv:continue
        w=(Vector(g['v'][face[1]])-Vector(g['v'][face[0]])).length
        h=(Vector(g['v'][face[2]])-Vector(g['v'][face[1]])).length
        tw,th=(ATLAS if material=='Labels' else NOTICE)['size']
        pw=abs(uv[1][0]-uv[0][0])*tw;ph=abs(uv[2][1]-uv[1][1])*th
        if min(w,h,pw,ph)<=0:raise RuntimeError('Degenerate type mapping')
        q=dict(mesh=name,width_m=w,height_m=h,sampled_pixels=[pw,ph],aspect_scale=(w/h)/(pw/ph))
        quads.append(q);font_geometry.append(q)
    raw_export(name,g,**kw);records[-1]['font_quads']=quads
def emit(key,fn,collision=False,nanite=True):
    global G,HULLS
    G={};HULLS=[];fn();name='SM_Staff_'+key+'_V6';original_export(name,merge_groups(),kind='Body',hulls=HULLS,collision=collision,nanite=nanite)
    records[-1]['asset']=BASE+'/Meshes/'+name;prototypes[key]=name
    bpy.data.objects[name].location=(-16+len(records)*4,-84,0)
emit('ElectricKettle',kettle_v6);emit('KettlePower',kettle_power)
emit('Noticeboard',notice_v3);emit('BathroomInterior',bathroom_interior,True)

# Rebuild only the affected architectural layers; furniture remains V5.
cfg=copy.deepcopy(CFG);rec=next(r for r in cfg['rooms'] if r['id']=='StaffRecreation')
cfg_before=CFG;CFG=copy.deepcopy(CFG)
next(r for r in CFG['rooms'] if r['id']=='StaffRecreation')['outline']=[[-15,-12],[15,-12],[15,8],[9,8],[9,12],[-15,12]]
def wall(a,b,height,openings=(),tiles=True):
    if ROOM['id']=='StaffRecreation' and list(a)==[15,8] and list(b)==[9,8]:
        openings=[dict(center=2.8,width=1.12,height=2.32)]
    wall_segment(a,b,height,openings,tiles)
def neck(x0,x1,y,height=3.4):
    paving(x0,y-2,x1,y+2);wall((x0,y-2),(x1,y-2),height);wall((x1,y+2),(x0,y+2),height)
    outside=x0 if x0<0 else x1;wall((outside,y-2),(outside,y+2),height,[dict(center=2,width=3,height=2.8)])
    box('Roof',((x0+x1)/2,y,height+.14),(x1-x0+.28,4.28,.28),'Concrete')
def export_mesh(name,g,room_id=None,kind='',**kwargs):
    if kind!='Signs' and not (room_id=='StaffRecreation' and kind in ('Walls','Tiles','Frames')):return
    name6=name+'_V6';original_export(name6,g,room_id=room_id,kind=kind,collision=kind=='Walls',nanite=kind not in ('Signs',))
    r=records[-1];r.update(asset=BASE+'/Meshes/'+name6,actor_label='StaffSubject_'+room_id+'_'+kind)
    architectures.append(r)
    bpy.data.objects[name6].location=cfg['preview_placements_m'][[q['id'] for q in cfg['rooms']].index(room_id)]
begin=basecode.index("for room in CFG['rooms']:\n    G={};HULLS=[];ROOM['id']")
end=basecode.index('# A shared four-metre link')
architecture_code=basecode[begin:end].replace('    for kind,g in G.items():',
    "    if rid=='StaffRecreation':\n        wall((15,8),(15,12),h)\n        wall((15,12),(9,12),h)\n    for kind,g in G.items():")
exec(compile(architecture_code,str(entry),'exec'));CFG=cfg_before
rec['furniture']=[p for p in rec['furniture'] if p['prototype']!='BathroomShell' and p['id'] not in ('KettlePower','BathroomInterior')]
rec['furniture'].extend([dict(id='BathroomInterior',prototype='BathroomInterior',position=[0,0,0],yaw_blender_deg=0),
    dict(id='KettlePower',prototype='KettlePower',position=[0,0,0],yaw_blender_deg=0)])
for p in rec['furniture']:
    if p['id']=='Toilet':p['position']=[13.75,11.44,.003]
    elif p['id']=='BathroomSink':p['position']=[10.30,11.587,.003]
    elif p['id']=='BathroomMirror':p['position']=[10.30,11.754,1.32]
    elif p['id']=='BathroomLamp':p['position']=[12.20,10.10,3.365]
rec['outline']=[[-15,-12],[15,-12],[15,12],[-15,12]]
cell=dict(min=[9,8,0],max=[15,12,5.5])
if cell not in rec['room_cells']:rec['room_cells'].append(cell)
for rect in [[9.25,8.25,14.75,11.75],[11.55,7.60,12.85,8.45]]:
    if rect not in rec['walk_rects_m']:rec['walk_rects_m'].append(rect)
rec['lights']=[l for l in rec['lights'] if l['id']!='Bathroom']
rec['lights'].append(dict(id='Bathroom',position=[12.20,10.10,3.25],lumens=440,radius_cm=370,
    cast_shadows=False,max_draw_distance_cm=1400,fade_range_cm=300,indirect=.10,tint=[.79,.87,.82],role='Fill'))
cfg.update(wall_inset_revision=6,revision='staff_wall_inset_typography_v6_20261002',
    toilet_location='inside original northeast protruding wall: x9..15, y8..12; entrance at y8',
    current_authored_source='WallInsetV6/Authored/StaffLivingTheme_WallInsetV6.blend')
removed_names={r['name'].removesuffix('_V6') for r in architectures}
removed_names.add('SM_Staff_Recreation_Tiles_V4')
with bpy.data.libraries.load(str(ROOT/'RoomDetailsV5/Authored/StaffLivingTheme_RoomDetailsV5.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n not in removed_names and n!='StaffRecreation_BathroomShell' and n!='SM_Staff_BathroomShell_V5']
for obj in dst.objects:
    if obj:bpy.context.scene.collection.objects.link(obj)
for room,off in zip(cfg['rooms'],cfg['preview_placements_m']):
    for p in room['furniture']:
        if p['prototype'] not in prototypes and p['id'] not in ('Toilet','BathroomSink','BathroomMirror','BathroomLamp'):continue
        name=room['id']+'_'+p['id'];obj=bpy.data.objects.get(name)
        source=bpy.data.objects.get(prototypes.get(p['prototype'],''))
        if not obj and source:obj=source.copy();obj.data=source.data;obj.name=name;bpy.context.scene.collection.objects.link(obj)
        if not obj:raise RuntimeError('Missing complete source instance '+name)
        if source:obj.data=source.data
        obj.location=Vector(off)+Vector(p['position']);obj.rotation_euler.z=math.radians(p['yaw_blender_deg'])
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StaffLivingTheme_WallInsetV6.blend'))
(OUT/'room-inset.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,prototypes=prototypes,architectures=architectures,
    revision=6,tests_run=False,rendered=False,door_clear_width_m=1.12,toilet_bounds_m=[9,8,15,12]),ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'typography-geometry-audit.json').write_text(json.dumps(dict(font_quads=font_geometry,
    anisotropic_quads=[q for q in font_geometry if abs(q['aspect_scale']-1)>.005],
    requested_audit=True,game_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_WALL_INSET_V6_AUTHORED',len(records),flush=True)
