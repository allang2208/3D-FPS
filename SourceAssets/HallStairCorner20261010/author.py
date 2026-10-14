"""Precision stair interfaces and six physically mounted corner fittings; no render."""
from pathlib import Path
import sys,json,math,hashlib,bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Authored'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonFacilityTransit20261007/Scripts'))
import geometry as g
BASE='/Game/Dungeons/HallStairCorner20261010'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
ROLES={
 'Reception':json.loads((PROJECT/'SourceAssets/DungeonReceptionHall20261006/Config/materials.json').read_text('utf8')),
 'Transit':json.loads((PROJECT/'SourceAssets/DungeonFacilityTransit20261007/RefineV3/materials.json').read_text('utf8'))}
ROLES['Transit']['Glow']['existing_ue_path']='/Game/Dungeons/HallLighting20261007/Materials/M_SteadyDiffuser'
records=[];posts_report=[]

def xz_prism(kind,outline,y0,y1,mat):
    n=len(outline);v=[(x,y,z) for y in (y0,y1) for x,z in outline]
    f=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]
    f += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    g.poly(kind,v,f,mat)

def flight(x0,z0,d,yc,width,going,rise,kinds,tread_collision=False):
    tread,nosing,support=kinds
    for i in range(14):
        front=x0+d*i*going;top=z0+(i+1)*rise
        # A real 3 mm recess replaces the old superimposed metal plate.
        pocket=[(0,-.040),(going,-.040),(going,0),(.068,0),(.068,-.003),(.014,-.003),(.014,0),(.003,0),(0,-.003)]
        edge=[(0,-.040),(going,-.040),(going,0),(.003,0),(0,-.003)]
        limits=[yc-width/2,yc-width/2+.06]
        inner_width=width-.12;sections=math.ceil(inner_width/.35)
        limits += [yc-width/2+.06+inner_width*j/sections for j in range(1,sections+1)]
        limits.append(yc+width/2)
        for j,(a,b) in enumerate(zip(limits,limits[1:])):
            profile=edge if j in (0,len(limits)-2) else pocket
            xz_prism(tread,[(front+d*x,top+z) for x,z in profile],a,b,'Stone')
            if j not in (0,len(limits)-2):
                g.box(nosing,(front+d*.041,(a+b)/2,top-.00175),(.053,b-a,.0025),'Dark')
        if tread_collision:g.box(None,(front+d*going/2,yc,top-.020),(going,width,.040),collision=tread)
    end=x0+d*14*going;high=z0+14*rise
    profile=[(x0,z0-.20),(end,high-.20),(end,high-.040)]
    for i in reversed(range(14)):
        profile.append((x0+d*i*going,z0+(i+1)*rise-.040))
        if i:profile.append((x0+d*i*going,z0+i*rise-.040))
    xz_prism(support,profile,yc-width/2,yc+width/2,'Concrete')
    # Retain the original walking supports and clearances.
    if g.ROOM=='Reception':
        v=[(x,y,z) for y in (yc-width/2,yc+width/2) for x,z in ((x0,z0-.20),(end,high-.20),(end,high),(x0,z0+rise))]
    else:
        v=[(x,y,z) for y in (yc-width/2,yc+width/2) for x,z in ((x0,z0-.26),(end,high-.26),(end,high-.06),(x0,z0+.09))]
    g.hull(support,v,g.FACES)

def floor_and_snap(x,y):
    """Snap posts to the actual tread centre, never to a riser or virtual slope."""
    if g.ROOM=='Reception':
        if abs(y)>10.5 or x<-18 or x>16:return x,4.5
        for start,base in ((-8,0),(-1.64,2.25)):
            if start<x<start+4.76-1e-6:
                i=min(13,max(0,int((x-start)/.34)))
                return start+(i+.5)*.34,base+(i+1)*4.5/28
        return x,2.25 if x<-.0 else 4.5
    if x<=-16:return x,4.2
    for start,base in ((-5,0),(-11.3,2.1)):
        if start-4.7+1e-6<x<start:
            i=min(13,max(0,int((start-x)/(4.7/14))))
            return start-(i+.5)*(4.7/14),base+(i+1)*.15
    return x,2.1 if x<-9.7 else 0

def guard(path,kind,height):
    for h,mat,r in ((height,'Yellow',.032),(.50,'Yellow' if g.ROOM=='Reception' else 'Steel',.026)):
        g.tube(kind,[(x,y,z+h) for x,y,z in path],r,mat,24)
    posts={}
    for a,b in zip(path,path[1:]):
        a,b=Vector(a),Vector(b);delta=b-a;count=max(1,math.ceil(delta.length/1.04))
        for i in range(count+1):
            p=a+delta*i/count;x,foot=floor_and_snap(p.x,p.y)
            if abs(delta.x)>1e-5:
                t=(x-a.x)/delta.x
                if t<-.0001 or t>1.0001:continue
                p=a+delta*max(0,min(1,t))
            posts[tuple(round(c,4) for c in p[:2])]=(p,foot)
        side=Vector((-delta.y,delta.x,0)).normalized()*.04
        v=[p+s*side+Vector((0,0,z)) for p in (a,b) for s,z in ((-1,0),(1,0),(1,height+.035),(-1,height+.035))]
        g.hull(kind,v,g.FACES)
    for p,foot in posts.values():
        # Posts stop inside the handrail; their plates rest on full tread/landing area.
        h=p.z+height-foot
        g.box(kind,(p.x,p.y,foot+.025+h/2),(.058,.058,h-.05),'Paint')
        g.box(kind,(p.x,p.y,foot+.015),(.16,.16,.030),'Steel')
        for dx in (-.053,.053):
            for dy in (-.053,.053):g.bolt(kind,(p.x+dx,p.y+dy,foot+.03),(0,0,1),.005)
        posts_report.append(dict(room=g.ROOM,x=p.x,y=p.y,foot=foot,top=p.z+height,base_half=.08))

def reception():
    g.ROOM='Reception';rise=4.5/28
    for s in (-1,1):
        for x,z in ((-8,0),(-1.64,2.25)):flight(x,z,1,s*8.8,3.,.34,rise,('StairTreads','StairNosings','StairCarriages'))
    def path(s,outer):
        y=s*(10.14 if outer else 7.46)
        p=[(-7.83,y,rise),(-3.41,y,2.25),(-1.81,y,2.25),(2.95,y,4.5)]
        x=3.26 if outer else 5.38
        return p+[(x,y,4.5),(x,s*10.64,4.5)]
    # Two continuous paths join all four flights, landings and the gallery.
    west=path(1,True)+[(-18.14,10.64,4.5),(-18.14,-10.64,4.5)]+list(reversed(path(-1,True)))
    east=path(1,False)+[(16.14,10.64,4.5),(16.14,-10.64,4.5)]+list(reversed(path(-1,False)))
    guard(west,'Balustrades',1.10);guard(east,'Balustrades',1.10)
    for s in (-1,1):
        for a,b in ((-18,3.12),(5.52,16)):
            g.box('GalleryFascia',((a+b)/2,s*10.5,4.27),(b-a,.14,.44),'Teal')
            g.box('GalleryFascia',((a+b)/2,s*10.419,4.08),(b-a,.015,.055),'Brass')
    for x in (-18,16):g.box('GalleryFascia',(x,0,4.27),(.14,21,.44),'Teal')

def transit():
    g.ROOM='Transit';going=4.7/14
    for s in (-1,1):
        for x,z in ((-5,0),(-11.3,2.1)):flight(x,z,-1,s*15.9,3.16,going,.15,('Steps','Nosings','StairSupport'),True)
    def path(s,outer):
        y=s*(17.30 if outer else 14.50)
        return [(-5-going/2,y,.15),(-9.7+going/2,y,2.1),(-11.3+going/2,y,2.1),(-16+going/2,y,4.2),(-16.14,y,4.2)]
    guard(path(1,False)+list(reversed(path(-1,False))),'Rails',1.08)
    for s in (-1,1):guard(path(s,True)+[(-16.14,s*17.86,4.2)],'Rails',1.08)
    # The old fascia opening already matches the 3.16 m stair footprint.

def corner_fixtures():
    g.ROOM='Transit'
    for s in (-1,1):
        for x,z,ceiling in ((-22.4,3.70,3.82),(-22.4,7.68,8.40),(23.53,3.50,None)):
            y=s*15.6
            # The top and side walls are opaque; only the inset underside emits.
            w,d=(1.0,.32) if x<0 else (.38,1.0)
            g.box('CornerHousings',(x,y,z+.065),(w,d,.11),'Teal')
            for sy in (-1,1):g.box('CornerHousings',(x,y+sy*(d/2-.012),z-.010),(w,.024,.060),'Steel')
            for sx in (-1,1):g.box('CornerHousings',(x+sx*(w/2-.012),y,z-.010),(.024,d-.048,.060),'Steel')
            g.box('CornerDiffusers',(x,y,z-.014),(w-.060,d-.060,.012),'Glow')
            if ceiling:
                for dx in (-.36,.36):
                    g.cylinder('CornerHousings',(x+dx,y,z+.12),(x+dx,y,ceiling),.012,'Steel',12)
                    g.box('CornerHousings',(x+dx,y,ceiling-.012),(.10,.10,.024),'Steel')
            else:
                for dy in (-.34,.34):
                    g.box('CornerHousings',(23.966,y+dy,z+.03),(.068,.11,.27),'Steel')
                    g.box('CornerHousings',(23.795,y+dy,z+.095),(.35,.060,.050),'Teal')
                    g.bolt('CornerHousings',(23.925,y+dy,z+.12),(-1,0,0),.009)

def export():
    for (room,kind),data in g.G.items():
        name='SM_HSC_'+room+'_'+kind;mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
        roles=list(dict.fromkeys(data['m']));rr=ROLES[room]
        for role in roles:
            key='HSC_'+room+'_'+role;m=bpy.data.materials.get(key)
            if not m:
                m=bpy.data.materials.new(key);m.diffuse_color=(*rr[role].get('basecolor_linear',[.2,.2,.2]),1)
            mesh.materials.append(m)
        mesh.uv_layers.new(name='UVMap');uv=mesh.uv_layers.active
        age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
        for face,role,coords,smooth in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
            face.material_index=roles.index(role);face.use_smooth=smooth
            axes=[a for a in range(3) if a!=max(range(3),key=lambda k:abs(face.normal[k]))]
            scale=rr[role].get('uv_meters_override',rr[role].get('uv_meters',1))
            for j,li in enumerate(face.loop_indices):
                p=mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv=(coords[j][0]/scale,coords[j][1]/scale) if coords else (p[axes[0]]/scale,p[axes[1]]/scale)
                age.data[li].color=(.025,0,0,1)
        obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY');bm.to_mesh(mesh);bm.free()
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        cols=[]
        for i,(vs,fs) in enumerate(g.C.get((room,kind),[])):
            me=bpy.data.meshes.new('UCX_'+name+'_%03d'%i);me.from_pydata(vs,[],fs);me.update()
            bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
            co=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(co);co.select_set(True);cols.append(co)
        fbx=OUT/(name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,colors_type='LINEAR',add_leaf_bones=False,path_mode='STRIP')
        for co in cols:co.hide_set(True);co.hide_render=True
        old=None
        if not kind.startswith('Corner'):
            old=('/Game/Dungeons/ReceptionHall20261006/Meshes/SM_Reception_' if room=='Reception' else '/Game/Dungeons/FacilityTransit20261007/RefineV3/Meshes/SM_FT3_Hall_')+kind
        records.append(dict(room=room,kind=kind,mesh=BASE+'/Meshes/'+name,old=old,fbx=str(fbx),sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),
            materials={'HSC_'+room+'_'+r:rr[r]['existing_ue_path'] for r in roles},collision=bool(cols),collision_hulls=len(cols),
            cast_shadow=kind!='CornerDiffusers',nanite=kind in ('StairTreads','Steps','StairCarriages','StairSupport','GalleryFascia','CornerHousings'),triangles=len(mesh.polygons)))
        print('HALL_STAIR_EXPORTED',name,len(mesh.polygons),flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HallStairCorner.blend'))
    (ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records,posts=posts_report,game_run=False,rendered=False),indent=2),encoding='utf8')

reception();transit();corner_fixtures();export()
