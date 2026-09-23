"""Author distinct room shells from footprints and architectural service rules."""
import bpy,json,math,random
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
CFG=json.loads((ROOT/'Config/rooms.json').read_text(encoding='utf-8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
MAPPING={n:'/Game/Dungeons/AtmosphereV2/Materials/M_'+n for n in ['Concrete','IvoryTile','PaintedSteel','BareSteel','AncientStone','CoolGlass','WarmGlass']}
MAPPING['ServicePaint']='/Game/Dungeons/AtmosphereV2/Services/Materials/M_Service_Paint'
MAPPING['ServiceHardware']='/Game/Dungeons/AtmosphereV2/Services/Materials/M_Service_Hardware'
MATS={n:bpy.data.materials.new('RS_'+n) for n in MAPPING}
GROUPS={};RECORDS=[];LIGHTS=[];ANCHORS=[];ROOM=None;R=None
def group(kind):return GROUPS.setdefault(kind,{'v':[],'f':[],'m':[]})
def poly(kind,verts,faces,mat):
    g=group(kind);offset=len(g['v']);g['v'].extend(verts)
    g['f'].extend(tuple(offset+i for i in f) for f in faces);g['m'].extend([mat]*len(faces))
def box(kind,center,size,mat='Concrete',yaw=0):
    x,y,z=center;a,b,c=[s/2 for s in size];co,si=math.cos(yaw),math.sin(yaw)
    vs=[(x+dx*co-dy*si,y+dx*si+dy*co,z+dz) for dx,dy,dz in [(-a,-b,-c),(a,-b,-c),(a,b,-c),(-a,b,-c),(-a,-b,c),(a,-b,c),(a,b,c),(-a,b,c)]]
    poly(kind,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
def bar(kind,a,b,width,height,mat='Concrete'):
    a,b=Vector(a),Vector(b);d=b-a
    box(kind,(a+b)/2,(d.xy.length,width,height),mat,math.atan2(d.y,d.x))
def tube(kind,points,radius,mat='ServicePaint',sides=12):
    ps=[Vector(p) for p in points];verts=[]
    for i,p in enumerate(ps):
        tangent=(ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized()
        helper=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
        a=tangent.cross(helper).normalized();b=tangent.cross(a).normalized()
        verts.extend(tuple(p+radius*(a*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides))) for j in range(sides))
    faces=[tuple(reversed(range(sides))),tuple((len(ps)-1)*sides+j for j in range(sides))]
    for i in range(len(ps)-1):
        for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    poly(kind,verts,faces,mat)
def smooth_pipe(points,radius):
    ps=[Vector(p) for p in points];out=[ps[0]]
    for i in range(1,len(ps)-1):
        p=ps[i];before=(p-ps[i-1]).normalized();after=(ps[i+1]-p).normalized()
        reach=min(.34,(p-ps[i-1]).length*.3,(ps[i+1]-p).length*.3)
        first=p-before*reach;last=p+after*reach
        for j in range(7):
            t=j/6;out.append(first*(1-t)**2+p*2*(1-t)*t+last*t*t)
    out.append(ps[-1]);tube('Services',out,radius)
    for a,b in zip(ps,ps[1:]):
        d=b-a;length=d.length
        for step in range(1,max(1,int(length/1.8))+1):
            p=a+d*step/(max(1,int(length/1.8))+1);n=d.normalized()
            tube('Services',[p-n*.035,p+n*.035],radius*1.4,'ServiceHardware',16)
            # Upper runs are hung from the actual ceiling; lower pipe legs are unbracketed here.
            if abs(d.z)<.01 and p.z>2.5:
                tube('Frames',[p+Vector((0,0,radius)),p+Vector((0,0,max(radius+.1,ROOM['height_m']-p.z)))],.012,'BareSteel',8)
def prism(kind,points,start,direction,normal,depth,mat):
    area=sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))
    if area<0:points=list(reversed(points))
    n=len(points);s=Vector((start[0],start[1],0));d=Vector((direction[0],direction[1],0));no=Vector((normal[0],normal[1],0))
    vs=[tuple(s+d*t+Vector((0,0,z))+no*offset) for offset in (-depth/2,depth/2) for t,z in points]
    # Cross section t/z has normal -interior normal.
    faces=[tuple(range(n)),tuple(n+i for i in reversed(range(n)))]
    faces.extend((i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n));poly(kind,vs,faces,mat)
def wall(start,end,height,openings=(),breach=None,tiles=True,mat='Concrete'):
    start,end=Vector(start),Vector(end);direction=(end-start).normalized();normal=Vector((-direction.y,direction.x));length=(end-start).length
    style=CFG['style'];wall_depth=style['wall_thickness']
    def block(t0,t1,z0,z1,kind='Shell',material=mat,depth=None,offset=0):
        if t1-t0<.001 or z1-z0<.001:return
        if depth is None:depth=wall_depth
        p=start+direction*((t0+t1)/2)+normal*offset
        box(kind,(p.x,p.y,(z0+z1)/2),(t1-t0,depth,z1-z0),material,math.atan2(direction.y,direction.x))
    if breach:
        left=breach['left'];right=breach['right'];h=breach['height']
        leftline=[(left,0),(left+.15,.5),(left-.08,1.05),(left+.21,1.65),(left-.03,2.1),(left+.25,h)]
        rightline=[(right,0),(right-.12,.55),(right+.12,1.2),(right-.18,1.9),(right-.04,2.3),(right-.2,h-.12)]
        prism('Shell',[(0,0)]+leftline+[(left+.25,height),(0,height)],start,direction,normal,.34,mat)
        prism('Shell',rightline+[(length,height),(length,0)],start,direction,normal,.34,mat)
        prism('Shell',[(left+.25,h),(left+.85,h+.2),(left+1.5,h-.04),(right-.6,h+.19),(right-.2,h-.12),(right-.2,height),(left+.25,height)],start,direction,normal,.34,mat)
    else:
        intervals=sorted((o['center']-o['width']/2,o['center']+o['width']/2,o['height']) for o in openings)
        cursor=0
        for a,b,h in intervals:
            block(cursor,a,0,height);block(a,b,h,height);cursor=b
        block(cursor,length,0,height)
    # Individual ceramic tiles preserve the wall skirt scale. Missing patches are localized.
    for row in range(style['tile_rows'] if tiles else 0):
        z=style['tile_bottom']+(row+.5)*style['tile_height'];t=style['tile_width']/2
        while t<length-.04:
            tw=min(style['tile_width']-.005,2*(length-t));inside_open=any(abs(t-o['center'])<o['width']/2+style['tile_width']/2+.005 and z<o['height']+style['tile_height']/2+.001 for o in openings)
            at_breach=breach and breach['left']-.18<t<breach['right']+.18 and z<breach['height']+.15
            missing=(math.sin(t*2.2+row*.28+len(ROOM['id']))>.92 and row<6 and R.random()<.65)
            if not inside_open and not at_breach and not missing:
                half=(style['tile_height']-.008)/2
                block(t-tw/2,t+tw/2,z-half,z+half,'Tiles','IvoryTile',.014,wall_depth/2+.007)
            t+=style['tile_width']
    # Trim is segmented at ports rather than running across them.
    cuts=list(openings)+([{'center':(breach['left']+breach['right'])/2,'width':breach['right']-breach['left'],'height':3}] if breach else [])
    cursor=0
    for opening in sorted(cuts,key=lambda x:x['center']):
        a=opening['center']-opening['width']/2;b=opening['center']+opening['width']/2
        block(cursor,a,0,.14,'Frames','PaintedSteel',.028,wall_depth/2+.02);cursor=b
    block(cursor,length,0,.14,'Frames','PaintedSteel',.028,wall_depth/2+.02)
    for opening in openings:
        for t in [opening['center']-opening['width']/2-.035,opening['center']+opening['width']/2+.035]:
            block(t-.035,t+.035,0,opening['height'],'Frames','BareSteel',.29,0)
        block(opening['center']-opening['width']/2-.07,opening['center']+opening['width']/2+.07,opening['height'],opening['height']+.08,'Frames','BareSteel',.29)
def slab(rect,kind,ceiling=False,mat='Concrete'):
    x0,y0,x1,y1,z=rect
    thickness=.18 if ceiling else CFG['style']['floor_thickness']
    box(kind,((x0+x1)/2,(y0+y1)/2,z+(thickness/2 if ceiling else -thickness/2)),(x1-x0,y1-y0,thickness),mat)
def lamp(spec):
    x,y,z=spec['at']
    box('Fixtures',(x,y,z),(.9,.20,.07),'BareSteel')
    box('Fixtures',(x,y,z-.043),(.78,.13,.02),'WarmGlass' if spec['warm'] else 'CoolGlass')
    # Source is directly under the emitting diffuser.
    LIGHTS.append(dict(room=ROOM['id'],local_m=[x,y,z-.085],origin_m=ROOM['origin_m'],**{k:v for k,v in spec.items() if k!='at'}))
def railing(a,b):
    a,b=Vector(a),Vector(b);length=(b-a).length
    for z in [.52,1.04]:tube('Frames',[a+Vector((0,0,z)),b+Vector((0,0,z))],.023,'PaintedSteel')
    for i in range(max(1,math.ceil(length/1.4))+1):
        p=a+(b-a)*i/max(1,math.ceil(length/1.4));tube('Frames',[p,p+Vector((0,0,1.04))],.026,'PaintedSteel')
def export():
    for kind,g in GROUPS.items():
        name='SM_RS_'+ROOM['id']+'_'+kind;mesh=bpy.data.meshes.new(name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
        obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
        names=list(MATS)
        for n in names:mesh.materials.append(MATS[n])
        uv=mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
        for face,material in zip(mesh.polygons,g['m']):
            face.material_index=names.index(material);axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
            scale=.8 if material=='ServicePaint' else 2
            for li in face.loop_indices:
                co=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(co[dims[0]]/scale,co[dims[1]]/scale)
                age.data[li].color=(.18+.3*max(0,math.sin(co.z*3+co.x)),0,0,1)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        if kind in ('Shell','Frames','Floors','Ceilings'):
            bevel=obj.modifiers.new('Small structural arris','BEVEL');bevel.width=.008;bevel.segments=2;bevel.limit_method='ANGLE'
            bpy.ops.object.modifier_apply(modifier=bevel.name)
        tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
        path=OUT/(name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
        RECORDS.append(dict(name=name,room=ROOM['id'],kind=kind,fbx=str(path),origin_m=ROOM['origin_m'],materials={'RS_'+n:MAPPING[n] for n in names},collision=kind not in ('Fixtures','Debris')))
        # Source shows the assembled plan; FBX remains in room-local coordinates.
        obj.location=ROOM['origin_m']
for index,room in enumerate(CFG['rooms']):
    ROOM=room;GROUPS={};R=random.Random(CFG['seed']+index)
    for rect in room['floors']:slab(rect,'Floors')
    for rect in room['ceilings']:slab(rect,'Ceilings',True)
    outline=room['footprint']
    for edge,(a,b) in enumerate(zip(outline,outline[1:]+outline[:1])):
        wall(a,b,room.get('wall_heights',{}).get(str(edge),room['height_m']),[o for o in room['openings'] if o['edge']==edge],room.get('breach') if room.get('breach',{}).get('edge')==edge else None)
    for x,y in room.get('columns',[]):box('Shell',(x,y,room['height_m']/2),(.36,.36,room['height_m']))
    for a,b in room.get('beams',[]):bar('Shell',a,b,.38,.36)
    for a,b,h in room.get('headers',[]):bar('Shell',a,b,.26,h)
    for pipe in room['pipes']:smooth_pipe(pipe['points'],pipe['radius'])
    for spec in room['lights']:lamp(spec)
    if 'trench' in room:
        x0,y0,x1,y1=room['trench']['rect'];depth=room['trench']['depth'];b0,b1=room['trench']['bridge_y']
        for x in (x0,x1):
            box('Shell',(x,(y0+y1)/2,-depth/2),(.16,y1-y0,depth))
            for start,end in [(y0,b0),(b1,y1)]:railing((x,start,0),(x,end,0))
        for y in (y0,y1):box('Shell',((x0+x1)/2,y,-depth/2),(x1-x0,.16,depth))
        slab([x0,b0,x1,b1,0],'Floors',False,'PaintedSteel')
        for y in (b0+.08,b1-.08):bar('Frames',(x0,y,.025),(x1,y,.025),.08,.05,'BareSteel')
        # A short grate at each trench end leaves the sunken maintenance channel readable.
        for y in (y0+.25,y1-.25):
            for i in range(21):box('Frames',(x0+.06+i*(x1-x0-.12)/20,y,.025),(.035,.5,.05),'BareSteel')
    if 'breach' in room:
        br=room['breach'];x0,y0,x1,y1=br['pocket']
        for a,b in [((x0,y0),(x1,y0)),((x1,y0),(x1,y1)),((x1,y1),(x0,y1))]:wall(a,b,3.35,tiles=False,mat='AncientStone')
        for y in (2.1,5.9):box('Frames',(11.57,y,1.62),(.19,.19,3.24),'PaintedSteel')
        box('Frames',(11.57,4,3.24),(.24,4.1,.25),'PaintedSteel')
        for y,sign in [(2.1,1),(5.9,-1)]:tube('Frames',[(11.57,y,2.55),(11.57,y+sign*.65,3.2)],.036,'BareSteel')
        for y,z,s in [(2.28,.75,1),(2.18,1.7,1),(5.5,.9,-1),(5.5,1.9,-1)]:tube('Services',[(11.97,y,z),(11.6,y+s*.22,z+.05),(11.43,y+s*.35,z-.12)],.011,'BareSteel',8)
        for cx,cy in [(11.45,1.65),(12.55,6.08),(15.6,2.0)]:
            for i in range(16):
                x=cx+R.uniform(-.42,.42);y=cy+R.uniform(-.28,.28);h=R.uniform(.045,.17)
                box('Debris',(x,y,h/2),(R.uniform(.07,.28),R.uniform(.08,.22),h),'Concrete' if i%3 else 'AncientStone',R.uniform(0,math.pi))
    for anchor in room['anchors']:ANCHORS.append(dict(room=room['id'],origin_m=room['origin_m'],**anchor))
    export()
for index,link in enumerate(CFG['links']):
    ROOM={'id':link['id'],'origin_m':link['origin_m'],'height_m':link['height']};GROUPS={};R=random.Random(CFG['seed']+50+index)
    w=link['width'];l=link['length'];h=link['height'];along_x=link['axis']=='x'
    rect=[0,-w/2,l,w/2,0] if along_x else [-w/2,0,w/2,l,0]
    slab(rect,'Floors');slab(rect[:4]+[h],'Ceilings',True)
    if along_x:walls=[((0,-w/2),(l,-w/2)),((l,w/2),(0,w/2))]
    else:walls=[((-w/2,l),(-w/2,0)),((w/2,0),(w/2,l))]
    for a,b in walls:wall(a,b,h)
    lamp({'at':[l/2,0,h-.22] if along_x else [0,l/2,h-.22],'warm':True,'lumens':500,'radius_cm':220})
    export()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Dungeon_DistinctRoomShells.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=RECORDS,lights=LIGHTS,anchors=ANCHORS),indent=2),encoding='utf-8')
print('DISTINCT_ROOM_SHELLS_AUTHORED',len(RECORDS),'meshes',len(LIGHTS),'lights')
