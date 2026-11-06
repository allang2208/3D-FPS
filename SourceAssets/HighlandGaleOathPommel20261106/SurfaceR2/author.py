"""Gale Oath: precise Western-fantasy pommel, native Highland seat, editable parts.

Production geometry and texture baking only. No preview or acceptance render.
All author coordinates are metres; socket Z=0, blade +Z, face -Y.
"""
from pathlib import Path
import json
import math
import sys
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
from finish import make_materials,bake_and_export

SOURCE=P.parents[1]/'HighlandClaymoreMeshy20260922/WedgeSpineJunctionR4_20261106/Highland_RidgePiercer_LowSeat_Editable.blend'
REFERENCE=P.parents[1]/'HighlandLightPommelConcept20261106/GaleOathR2/Highland_GaleOath_LightPommel_Concept02.png'
NAME='SM_Highland_Pommel_GaleOath_R2'
for folder in ('Export','Textures'):(P/folder).mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(SOURCE)) as (src,dst):
    dst.objects=['SM_Highland_Pommel_factory','SM_Highland_Grip_factory']
factory,grip=dst.objects
for obj in dst.objects:scene.collection.objects.link(obj)
mount=factory.location.copy()
grip.location-=mount
grip.name='REFERENCE_Highland_Grip_native'
factory.location=(0,0,0)
parts=[]
steel,polish,dark,bronze,enamel=make_materials()

def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=obj

def mesh_object(name,verts,faces,mat,shading=True):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    for f in mesh.polygons:f.use_smooth=shading
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);mesh.materials.append(mat)
    parts.append(obj)
    return obj

def rows_mesh(name,rows,mat,closed=False,smooth=True):
    n=len(rows[0]);verts=[tuple(v) for row in rows for v in row];faces=[]
    for j in range(len(rows) if closed else len(rows)-1):
        k=(j+1)%len(rows)
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,k*n+(i+1)%n,k*n+i))
    if not closed:
        faces.extend((tuple(reversed(range(n))),tuple((len(rows)-1)*n+i for i in range(n))))
    return mesh_object(name,verts,faces,mat,smooth)

def bevel(obj,width,segments=3,weighted=True):
    active(obj)
    mod=obj.modifiers.new('Physical softened edges','BEVEL');mod.width=width;mod.segments=segments;mod.limit_method='ANGLE'
    mod.angle_limit=.40
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for f in obj.data.polygons:f.use_smooth=True
    if weighted:
        mod=obj.modifiers.new('Broad face corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40
        bpy.ops.object.modifier_apply(modifier=mod.name)

def bezier_chain(start,segments,steps=18):
    pts=[np.array(start,dtype=float)]
    for c1,c2,end in segments:
        a=pts[-1];b=np.array(c1);c=np.array(c2);d=np.array(end)
        for t in np.linspace(0,1,steps+1)[1:]:
            pts.append((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d)
    return np.array(pts)

def half_to_loop(half,count=420):
    ring=np.concatenate((half,half[-2:0:-1]*np.array([-1,1])))
    d=np.linalg.norm(np.roll(ring,-1,axis=0)-ring,axis=1)
    f=np.r_[0,np.cumsum(d)];f/=f[-1]
    return np.stack([np.interp(np.linspace(0,1,count,endpoint=False),f,np.r_[ring[:,j],ring[0,j]]) for j in range(2)],axis=1)*.001

# The neck and angular shield shoulders are traced independently from the
# trefoil aperture. Each side has a broad lenticular face and a real inner wall.
outer=half_to_loop(bezier_chain((0,-11.3),[
    ((-4,-11.3),(-10,-11.3),(-12.7,-11.3)),
    ((-12.9,-15.6),(-13.2,-19.8),(-16.7,-24.0)),
    ((-19.6,-27.7),(-27.4,-32.8),(-32.6,-35.8)),
    ((-33.8,-36.4),(-34.8,-36.9),(-35.1,-38.0)),
    ((-35.4,-40.3),(-35.7,-43.2),(-35.8,-45.5)),
    ((-33.0,-53.4),(-25.0,-71.0),(-18.3,-86.0)),
    ((-13.4,-96.7),(-9.4,-104.7),(-5.0,-110.0)),
    ((-3.7,-112.2),(-1.9,-113.6),(0,-113.6))]))
inner=half_to_loop(bezier_chain((0,-34.0),[
    ((-2.3,-33.3),(-4.4,-35.1),(-4.4,-37.2)),
    ((-4.5,-38.6),(-3.5,-39.8),(-2.9,-40.4)),
    ((-2.6,-41.1),(-2.9,-42.1),(-3.5,-42.6)),
    ((-5.1,-39.7),(-8.3,-39.5),(-11.4,-40.6)),
    ((-17.6,-39.7),(-23.6,-42.1),(-24.6,-47.8)),
    ((-25.5,-51.9),(-22.3,-61.6),(-18.8,-70.2)),
    ((-14.2,-81.1),(-9.4,-94.5),(-4.0,-103.3)),
    ((-2.7,-105.1),(-1.2,-105.3),(0,-105.3))]))

def half_depth(z):
    return float(np.interp(-z,[.011,.022,.040,.055,.083,.106,.114],
                          [.0132,.0107,.0085,.0076,.0062,.0046,.0040]))

def face_depth(p,q):
    h=half_depth(p[1])
    # Fixed physical radius, rather than a curve-length dependent bevel.
    # The cap becomes tangent to the inner wall and the broad face smoothly.
    radius=.0012
    distance=min(distance_to(p,outer),distance_to(p,inner))
    t=min(1.,max(0.,distance/radius))
    return h-radius+radius*math.sqrt(max(0.,1.-(1.-t)**2))


def within(p,loop):
    a=loop;b=np.roll(loop,-1,axis=0)
    crossing=((a[:,1]>p[1])!=(b[:,1]>p[1]))
    dz=b[:,1]-a[:,1]
    xx=(b[:,0]-a[:,0])*(p[1]-a[:,1])/np.where(abs(dz)>1e-14,dz,1e-14)+a[:,0]
    return bool(np.count_nonzero(crossing & (p[0]<xx))%2)

def distance_to(p,loop):
    a=loop;b=np.roll(loop,-1,axis=0);d=b-a
    t=np.clip(np.sum((p-a)*d,axis=1)/np.sum(d*d,axis=1),0,1)
    return float(np.min(np.linalg.norm(p-a-t[:,None]*d,axis=1)))

def metal_offset(loop,amount):
    tangent=np.roll(loop,-1,axis=0)-np.roll(loop,1,axis=0)
    normal=np.stack([-tangent[:,1],tangent[:,0]],axis=1)
    normal/=np.linalg.norm(normal,axis=1)[:,None]
    return loop+normal*amount

# A constrained planar triangulation preserves the trefoil's concave cusps.
# Independent outer/inner curve lengths must not be used as a ruled loft.
points=[*outer,*inner];edges=[]
for start,loop in ((0,outer),(len(outer),inner)):
    edges.extend((start+i,start+(i+1)%len(loop)) for i in range(len(loop)))
for loop,sign in ((outer,1),(inner,-1)):
    for offset in (.00008,.00018,.00035,.0006,.0009,.0012,.0018):
        points.extend(p for p in metal_offset(loop,sign*offset) if within(p,outer) and not within(p,inner))
for x in np.arange(-.035,.036,.0012):
    for z in np.arange(-.113,-.011,.0012):
        p=np.array([x,z])
        if within(p,outer) and not within(p,inner):points.append(p)
planar,_,triangles,_,_,_=delaunay_2d_cdt([Vector(p) for p in points],edges,[],1,1e-8,False)
triangles=[f for f in triangles if within(np.mean([planar[i] for i in f],axis=0),outer)
           and not within(np.mean([planar[i] for i in f],axis=0),inner)]
verts=[];faces=[];n=len(planar)
for side in (-1,1):
    for point in planar:
        p=np.array(point);a=distance_to(p,outer);b=distance_to(p,inner)
        q=a/max(a+b,1e-12)
        verts.append((p[0],side*face_depth(p,q),p[1]))
for f in triangles:
    faces.extend((tuple(f),tuple(i+n for i in reversed(f))))
counts={}
for f in triangles:
    for a,b in zip(f,f[1:]+f[:1]):
        key=tuple(sorted((a,b)));counts[key]=counts.get(key,0)+1
for (a,b),count in counts.items():
    if count==1:faces.append((a,b,b+n,a+n))
body=mesh_object('GaleOath_ContinuousKiteShield_Trefoil',verts,faces,steel)

# Preserve the exact first 2 mm of the real mating surface. Weld the new neck
# into that lower loop; the grip, pivot and source weapon are never deformed.
seat=factory.copy();seat.data=factory.data.copy();seat.name='GaleOath_NativeSeat_and_ForgedNeck'
scene.collection.objects.link(seat);parts.append(seat)
bm=bmesh.new();bm.from_mesh(seat.data)
bmesh.ops.bisect_plane(bm,geom=[*bm.verts,*bm.edges,*bm.faces],plane_co=(0,0,-.002),plane_no=(0,0,1),dist=1e-8,clear_inner=True)
rim={tuple(round(c,9) for c in v.co) for v in bm.verts if abs(v.co.z+.002)<1e-7}
ring=sorted(rim,key=lambda p:math.atan2(p[1],p[0]))
bm.to_mesh(seat.data);bm.free();seat.data.materials.clear();seat.data.materials.append(steel)
for poly in seat.data.polygons:poly.material_index=0
angles=[math.atan2(v[1],v[0]) for v in ring]

def oct_radius(a,r):
    delta=(a+math.pi/8)%(math.pi/4)-math.pi/8
    return r*math.cos(math.pi/8)/math.cos(delta)

profiles=[(-.002,None),(-.0028,.0172),(-.0037,.0175),(-.0043,.0173),(-.0050,.0169),
          (-.007,.0169),(-.010,.0169),(-.0112,.0172),(-.0125,.0175),(-.0132,.0169),
          (-.015,.0148),(-.017,.0136),(-.019,.0131)]
rows=[]
for i,(z,r) in enumerate(profiles):
    row=[]
    for point,a in zip(ring,angles):
        if i==0:row.append(point);continue
        radius=oct_radius(a,r)
        blend=min(1.,max(0.,(-z-.002)/.0023));blend=blend*blend*(3-2*blend)
        x=(1-blend)*point[0]+blend*radius*math.cos(a)
        y=(1-blend)*point[1]+blend*radius*math.sin(a)
        if z<-.0132:y*=float(np.interp(-z,[.0132,.019],[1.,.65]))
        row.append((x,y,z))
    rows.append(row)
neck=rows_mesh('GaleOath_NeckTransition',rows,steel)
bm=bmesh.new();bm.from_mesh(neck.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if all(abs(v.co.z+.002)<1e-7 for v in f.verts)],context='FACES_ONLY')
bm.to_mesh(neck.data);bm.free()
active(seat);neck.select_set(True);bpy.ops.object.join();parts.remove(neck)
bm=bmesh.new();bm.from_mesh(seat.data)
seam=[v for v in bm.verts if abs(v.co.z+.002)<1e-7]
bmesh.ops.remove_doubles(bm,verts=seam,dist=1e-7)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(seat.data);bm.free()
active(body)
union=body.modifiers.new('Continuous forged neck joint','BOOLEAN');union.operation='UNION';union.solver='EXACT';union.object=seat
bpy.ops.object.modifier_apply(modifier=union.name)
parts.remove(seat);bpy.data.objects.remove(seat,do_unlink=True)
for f in body.data.polygons:f.use_smooth=True
# The continuous edge fillet is authored above; no bevel across cap triangles.
def outward_normal(p,loop,inward=False):
    edge=np.roll(loop,-1,axis=0)-loop
    t=np.clip(np.sum((p-loop)*edge,axis=1)/np.sum(edge*edge,axis=1),0,1)
    dist=np.linalg.norm(p-loop-t[:,None]*edge,axis=1);i=int(np.argmin(dist))
    tangent=np.roll(loop,-1,axis=0)-np.roll(loop,1,axis=0)
    normal=np.stack([tangent[:,1],-tangent[:,0]],axis=1)
    normal/=np.linalg.norm(normal,axis=1)[:,None]
    result=normal[i]*(1-t[i])+normal[(i+1)%len(loop)]*t[i]
    result/=np.linalg.norm(result)
    return -result if inward else result

# Explicit cap/wall normals remove the triangle-size bias along the thin fillet.
# The native contact seat retains its source geometry and local shading.
body.data.update()
loop_normals=[tuple(n.vector) for n in body.data.corner_normals]
vertex_normals={}
for v in body.data.vertices:
    if v.co.z>-.021:continue
    p=np.array([v.co.x,v.co.z]);do=distance_to(p,outer);di=distance_to(p,inner);d=min(do,di)
    outward=outward_normal(p,outer) if do<di else outward_normal(p,inner,True)
    if d<2e-6:normal=Vector((outward[0],0,outward[1]))
    else:
        t=min(1.,d/.0012)
        slope=(1.-t)/max(1e-6,math.sqrt(max(0.,1.-(1.-t)**2)))
        dz=(half_depth(v.co.z+.00001)-half_depth(v.co.z-.00001))/.00002
        normal=Vector((outward[0]*slope,1. if v.co.y>=0 else -1.,outward[1]*slope-dz)).normalized()
    vertex_normals[v.index]=tuple(normal)
for i,loop in enumerate(body.data.loops):
    if loop.vertex_index in vertex_normals:loop_normals[i]=vertex_normals[loop.vertex_index]
body.data.normals_split_custom_set(loop_normals)
surface=BVHTree.FromPolygons([v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons])

def face(x,z,side,lift=0.):
    p,normal,_,_=surface.ray_cast(Vector((x,side*.055,z)),Vector((0,-side,0)),.11)
    if p is None:raise ValueError(f'Ornament outside the forged face: {x},{z},{side}')
    return Vector((x,p.y+side*lift,z))

def ribbon(name,path,width,height,mat,side=None,closed=False):
    shape=[(-1,-.30),(-1,.04),(-.77,.75),(-.42,1),(.42,1),(.77,.75),(1,.04),(1,-.30),(0,-.52)]
    rows=[]
    for i,p in enumerate(path):
        p=Vector(p)
        prev=Vector(path[i-1] if i or closed else p)
        nxt=Vector(path[(i+1)%len(path)] if i+1<len(path) or closed else p)
        tangent=(nxt-prev).normalized()
        normal=Vector((0,side,0)) if side else Vector((p.x,p.y,0)).normalized()
        normal=(normal-tangent*tangent.dot(normal)).normalized()
        across=tangent.cross(normal).normalized()
        taper=1. if closed else .10+.90*min(1.,i/7.,(len(path)-1-i)/7.)
        rows.append([p+across*(q*width*.5*taper)+normal*(h*height*taper) for q,h in shape])
    return rows_mesh(name,rows,mat,closed)

# Octagonal collar rails and their open raised interlace, with true over/under
# separation. The dark ground remains a physical recessed material band.
def collar_rail(name,profile,mat):
    aa=np.linspace(0,2*math.pi,128,endpoint=False)
    return rows_mesh(name,[[(oct_radius(a,r)*math.cos(a),oct_radius(a,r)*math.sin(a),z) for a in aa] for z,r in profile],mat)

collar_rail('GaleOath_DarkOctagonalBraidBed',[(-.0046,.01693),(-.0109,.01693)],dark)
for label,z in [('Upper',-.0040),('Lower',-.0116)]:
    rail=collar_rail('GaleOath_'+label+'BronzeRail',[(z+.00055,.01710),(z+.00030,.01775),(z-.00030,.01775),(z-.00055,.0171)],bronze)
    bevel(rail,.00012,2)
for strand in (0,1):
    path=[]
    for t in np.linspace(0,2*math.pi,512,endpoint=False):
        w=8*t+strand*math.pi
        r=oct_radius(t,.01708)+.00027+.00030*math.cos(w)
        path.append((r*math.cos(t),r*math.sin(t),-.00775+.00203*math.sin(w)))
    ribbon('GaleOath_CollarCelticWeave_'+str(strand),path,.00092,.00022,polish,closed=True)

# Narrow outer and aperture rims follow the body itself instead of projecting
# a flat drawing across the sloped metal or the Gothic opening.
for side in (-1,1):
    for label,loop,offset,w,mat in [('OuterBronzeHairline',outer,.0008,.00046,bronze),('InnerSilverArris',inner,-.00065,.00048,polish)]:
        contour=metal_offset(loop,offset)
        path=[face(p[0],p[1],side,.00007) for p in contour]
        ribbon('GaleOath_'+label+str(side),path,w,.00014,mat,side,True)
    for sign in (-1,1):
        center=bezier_chain((sign*12.5,-23.),[
            ((sign*17.0,-27.7),(sign*25.8,-31.8),(sign*29.,-40.8))],110)*.001
        # Two interlaced strands per shoulder, on both faces. Their offset is
        # in the local shoulder tangent plane, with conservative rounded feet.
        for strand in (0,1):
            path=[]
            for i,c in enumerate(center):
                t=i/(len(center)-1)
                d=center[min(len(center)-1,i+1)]-center[max(0,i-1)]
                normal=np.array([-d[1],d[0]])/np.linalg.norm(d)
                taper=math.sin(math.pi*t)**.42
                phase=t*math.pi*6+strand*math.pi
                point=c+normal*(.00128*math.sin(phase)*taper)
                lift=.00015+.00043*(.5+.5*math.cos(phase))*taper
                path.append(face(point[0],point[1],side,lift))
            ribbon(f'GaleOath_ShoulderWeave_{side}_{sign}_{strand}',path,.00072,.00018,bronze,side)
        # A clean Gothic brace connects the wind-star base to each shoulder.
        brace=bezier_chain((0,-20.8),[((sign*5.0,-22.4),(sign*13.2,-28.8),(sign*21.3,-33.6))],68)*.001
        path=[face(p[0],p[1],side,.00012) for p in brace]
        ribbon(f'GaleOath_GothicBrace_{side}_{sign}',path,.00065,.00020,bronze,side)

# The front's four-point insignia has a continuous metal bezel, separate
# enamel facets and a real shallow back plate. The reverse has no duplicate gem.
star=np.array([(0,6.7),(1.4,1.35),(4.9,0),(1.4,-1.35),(0,-6.7),(-1.4,-1.35),(-4.9,0),(-1.4,1.35)])*.001
star_z=-.0233
for label,scale,lift,mat in [('ShadowSeat',1.10,.00016,dark),('BronzeBezel',1.,.00060,bronze)]:
    rows=[]
    for zoff,factor in [(0.,1.),(.00018,.99),(.00045,.90)]:
        rows.append([face(x*scale*factor,star_z+z*scale*factor,-1,lift+zoff) for x,z in star])
    obj=rows_mesh('GaleOath_Star_'+label,rows,mat,smooth=False)
    bevel(obj,.00007,2)
edge=[face(x*.78,star_z+z*.78,-1,.00104) for x,z in star]
center=face(0,star_z,-1,.00195)
gemverts=[tuple(v) for v in edge]+[tuple(center)]
gemfaces=[(i,(i+1)%8,8) for i in range(8)]+[tuple(range(7,-1,-1))]
mesh_object('GaleOath_WindStar_PaleEnamelFacets',gemverts,gemfaces,enamel,False)

# Compact rounded polygonal foot, matching the reference's single terminal.
terminal=rows_mesh('GaleOath_FacetedTerminal',[
    [(r*math.cos(a),r*.82*math.sin(a),z) for a in np.linspace(0,2*math.pi,8,endpoint=False)]
    for z,r in [(-.1078,.0051),(-.1092,.0072),(-.1132,.0073),(-.1178,.0045),(-.1183,.0034)]],steel,False,False)
bevel(terminal,.00022,3)
for z,r in [(-.1092,.00722),(-.1132,.00732)]:
    path=[Vector((r*math.cos(a),r*.82*math.sin(a),z)) for a in np.linspace(0,2*math.pi,8,endpoint=False)]
    ribbon('GaleOath_TerminalBronzeArris',path,.00042,.00013,bronze,closed=True)

bpy.data.objects.remove(factory,do_unlink=True)
reference=bpy.data.objects.new('REFERENCE_Approved_GaleOath_Concept',None)
scene.collection.objects.link(reference);reference.empty_display_type='IMAGE'
reference.data=bpy.data.images.load(str(REFERENCE));reference.empty_display_size=.18
reference.location=(.14,.02,-.05);reference.hide_render=True;reference.hide_set(True)
for obj in parts:obj['asset_role']='GaleOath editable production geometry'
grip['asset_role']='Unmodified host interface reference, excluded from exports'
grip.hide_set(True);grip.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_GaleOath_Editable.blend'))
print('GALE_OATH_EDITABLE_SAVED',flush=True)
spec={'name':'风誓轻量配重锤','mesh':NAME,'option_candidate':'highland_gale_oath',
      'reference':str(REFERENCE),'source_blend':str(SOURCE),'donor_object':'SM_Highland_Pommel_factory',
      'ue_folder':'/Game/Weapons/HighlandClaymore20260922/GaleOath20261106/SurfaceR2',
      'interface':{'name':'highland_hilt_v1','location_cm':[float(v)*100 for v in mount],
                   'socket_band_mm':2,'socket_origin':'factory pommel local Z=0','units':'metres; +Z blade, X width, Y depth'},
      'model_only':True,'catalogs_modified':False,'gameplay_stats_set':False,
      'tested':False,'acceptance_rendered':False}
bake_and_export(scene,parts,body,grip,P,spec)
