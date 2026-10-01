"""Extend SVD's original stamped panel along its measured lower-body curve.

The original feed/grasp region is immutable. A complete surface band (including
its corner UVs and stamped relief) supplies the added cell. Section differences
are distributed through that cell; the original floorplate moves as one part.
No preview or acceptance rendering is performed by this authoring script.
"""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

O=Path(__file__).parent
E=O/'Meshes';E.mkdir(exist_ok=True)
SOURCE=O/'HK416_Modular_Editable.blend'
CUT=-.0960
PANEL_TOP=-.0480
SLOPE=0.
NORM=math.sqrt(1+SLOPE*SLOPE)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and 'WPN_root' in o.data.bones)
rig.data.pose_position='REST';bpy.context.view_layer.update()
source=bpy.data.objects['Magazine_low']
socket=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
xf=socket.inverted()@source.matrix_world
rot=xf.to_3x3().inverted().transposed()
me=source.data
source_material_names=[m.name for m in me.materials]
positions=[np.array(xf@v.co,dtype=float) for v in me.vertices]
corner_normals=[np.array((rot@n.vector).normalized(),dtype=float) for n in me.corner_normals]
UVS=len(me.uv_layers)
colors=[a for a in me.color_attributes if a.domain=='CORNER']

def height(p):return (p[2]+SLOPE*p[1])/NORM
def along(p):return (p[1]-SLOPE*p[2])/NORM
HC=CUT/NORM;HT=PANEL_TOP/NORM

def lerp(a,b,t):return [x+(y-x)*t for x,y in zip(a,b)]
def clip(poly,h,above):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=height(a[0])-h;db=height(b[0])-h
        ia=da>=-1e-10 if above else da<=1e-10
        ib=db>=-1e-10 if above else db<=1e-10
        if ia:out.append(a)
        if ia!=ib:out.append(lerp(a,b,da/(da-db)))
    return out

faces=[]
for f in me.polygons:
    poly=[]
    for li in f.loop_indices:
        poly.append([positions[me.loops[li].vertex_index].copy(),corner_normals[li].copy(),
                     *[np.array(uv.data[li].uv,dtype=float) for uv in me.uv_layers],
                     *[np.array(c.data[li].color,dtype=float) for c in colors]])
    faces.append((f.material_index,poly))

def section(h):
    seg=[]
    for mat,poly in faces:
        if mat!=0:continue
        pts=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=height(a[0])-h;db=height(b[0])-h
            if da*db<0:pts.append(lerp(a,b,da/(da-db)))
        if len(pts)==2:seg.append(pts)
    return seg

# Fit the front/back shell together in planes parallel to the original base,
# excluding the collar, catch, rolled floorplate and lateral stamped relief.
fit=[]
for h in np.linspace(-.094/NORM,-.050/NORM,45):
    seg=section(h)
    vals=[along(p[0]) for edge in seg for p in edge]
    fit.append((h,(min(vals)+max(vals))*.5))
coef=np.polyfit(np.array(fit)[:,0],np.array(fit)[:,1],2)
curve=lambda h:float(np.polyval(coef,h))
deriv=lambda h:float(2*coef[0]*h+coef[1])
# Arc length, not world-Z spacing, drives the new panel and moved floorplate.
grid=np.linspace(-.25,.12,16001)
speed=np.sqrt(1+np.polyval(np.polyder(coef),grid)**2)
arc=np.r_[0,np.cumsum((speed[1:]+speed[:-1])*.5*np.diff(grid))]
arcat=lambda h:float(np.interp(h,grid,arc))
hfrom=lambda s:float(np.interp(s,arc,grid))
LENGTH=arcat(HT)-arcat(HC)
END=hfrom(arcat(HC)-LENGTH)
bottom=section(HC);top=section(HT)
CX=(min(p[0][0] for e in bottom for p in e)+max(p[0][0] for e in bottom for p in e))*.5

def theta(p,h):return math.atan2(along(p)-curve(h),p[0]-CX)%(2*math.pi)
def polar_section(segments,h):
    aa=np.array([[p[0][0]-CX,along(p[0])-curve(h)] for p,q in segments])
    bb=np.array([[q[0][0]-CX,along(q[0])-curve(h)] for p,q in segments])
    dd=bb-aa
    def intersect(angle):
        ray=np.array([math.cos(angle),math.sin(angle)])
        den=ray[0]*dd[:,1]-ray[1]*dd[:,0]
        valid=abs(den)>1e-12
        distance=np.divide(aa[:,0]*dd[:,1]-aa[:,1]*dd[:,0],den,out=np.zeros(len(den)),where=valid)
        frac=np.divide(aa[:,0]*ray[1]-aa[:,1]*ray[0],den,out=np.zeros(len(den)),where=valid)
        valid&=(frac>=-1e-7)&(frac<=1.0000001)&(distance>0)
        if not valid.any():raise RuntimeError('Factory section is not a closed radial shell')
        i=int(np.argmax(np.where(valid,distance,-1)))
        return distance[i],lerp(segments[i][0],segments[i][1],float(frac[i]))
    return intersect

bottom_ray=polar_section(bottom,HC);top_ray=polar_section(top,HT)
angles=np.linspace(0,2*math.pi,4097)
rb=np.array([bottom_ray(a)[0] for a in angles])
rt=np.array([top_ray(a)[0] for a in angles])
union=sorted(set(round(theta(p[0],h),9) for edges,h in [(bottom,HC),(top,HT)] for e in edges for p in e))

def smooth(t):return t*t*(3-2*t)
def curved(p,hnew,radial_delta=0):
    h=height(p);q=along(p)-curve(h);x=p[0]-CX
    radius=math.hypot(x,q)
    if radius>1e-10:
        x*=1+radial_delta/radius;q*=1+radial_delta/radius
    # Continue the base section orientation along the centre curve.
    angle=math.atan(deriv(hnew))-math.atan(deriv(HC))
    l=curve(hnew)+q*math.cos(angle);hh=hnew-q*math.sin(angle)
    return np.array([CX+x,(l+SLOPE*hh)/NORM,(hh-SLOPE*l)/NORM])

def band_map(p):
    h=height(p);a=theta(p,h)
    phase=(arcat(h)-arcat(HC))/LENGTH
    # Full-length section correction: never squash the mismatch into a seam.
    delta=(float(np.interp(a,angles,rb))-float(np.interp(a,angles,rt)))*smooth(max(0,min(1,phase)))
    return curved(p,hfrom(arcat(h)-LENGTH),delta)

# Rigidly move the old lower collar/base, including its existing curved lip.
target_center=curved(np.array([CX,(curve(HC)+SLOPE*HC)/NORM,(HC-SLOPE*curve(HC))/NORM]),END)
base_center=np.array([CX,(curve(HC)+SLOPE*HC)/NORM,(HC-SLOPE*curve(HC))/NORM])
angle=math.atan(deriv(END))-math.atan(deriv(HC))
base_rotation=np.array(Matrix.Rotation(-angle,3,'X'))
def base_map(p):return target_center+base_rotation@(p-base_center)

def map_normal(p,n,mapper):
    eps=1e-6
    jac=np.column_stack([(mapper(p+np.eye(3)[i]*eps)-mapper(p-np.eye(3)[i]*eps))/(2*eps) for i in range(3)])
    result=np.linalg.inv(jac).T@n
    return result/max(np.linalg.norm(result),1e-12)

def seam_split(poly,h):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        result.append(a)
        if abs(height(a[0])-h)>1e-8 or abs(height(b[0])-h)>1e-8:continue
        start=theta(a[0],h);end=theta(b[0],h)
        delta=(end-start+math.pi)%(2*math.pi)-math.pi
        inserts=[]
        for value in union:
            distance=(value-start+math.pi)%(2*math.pi)-math.pi
            if abs(delta)>1e-9 and 1e-7<distance/delta<1-1e-7:
                # Intersect the section edge with the chosen radial direction;
                # UV interpolation follows that edge rather than its angle.
                v=np.array([math.cos(value),math.sin(value)])
                pa=np.array([a[0][0]-CX,along(a[0])-curve(h)])
                pb=np.array([b[0][0]-CX,along(b[0])-curve(h)])
                edge=pb-pa;den=edge[0]*v[1]-edge[1]*v[0]
                if abs(den)>1e-12:
                    f=-(pa[0]*v[1]-pa[1]*v[0])/den
                    if 1e-7<f<1-1e-7:inserts.append((f,lerp(a,b,f)))
        result.extend(p for f,p in sorted(inserts,key=lambda x:x[0]))
    return result

made=[];counts={'upper':0,'panel':0,'base':0}
for mat,poly in faces:
    upper=clip(poly,HC,True)
    if len(upper)>=3:
        upper=seam_split(upper,HC)
        made.append((mat,upper));counts['upper']+=1
    low=clip(poly,HC,False)
    if len(low)>=3:
        mapped=[]
        for c in low:
            d=[v.copy() for v in c];d[0]=base_map(c[0]);d[1]=base_rotation@c[1];mapped.append(d)
        made.append((mat,mapped));counts['base']+=1
    if mat!=0:continue  # The original inner cavity/follower is never repeated.
    band=clip(clip(poly,HC,True),HT,False)
    if len(band)<3:continue
    band=seam_split(band,HT);mapped=[]
    for c in band:
        d=[v.copy() for v in c]
        if abs(height(c[0])-HT)<1e-8:
            a=theta(c[0],HT);unused,target=bottom_ray(a)
            d[0]=target[0].copy();d[1]=target[1].copy()
        elif abs(height(c[0])-HC)<1e-8:
            d[0]=base_map(c[0]);d[1]=base_rotation@c[1]
        else:d[0]=band_map(c[0]);d[1]=map_normal(c[0],c[1],band_map)
        mapped.append(d)
    made.append((mat,mapped));counts['panel']+=1

triangles=[]
for mat,poly in made:
    # A cut edge can contain several collinear seam vertices. Keep them as
    # explicit fan edges rather than asking FBX to triangulate that polygon.
    clean=[]
    for corner in poly:
        if not clean or np.linalg.norm(corner[0]-clean[-1][0])>1e-8:clean.append(corner)
    if len(clean)>1 and np.linalg.norm(clean[0][0]-clean[-1][0])<1e-8:clean.pop()
    if len(clean)<3:continue
    if len(clean)==3:triangles.append((mat,clean));continue
    center=[np.mean([c[i] for c in clean],axis=0) for i in range(len(clean[0]))]
    for a,b in zip(clean,clean[1:]+clean[:1]):triangles.append((mat,[center,a,b]))
verts=[];indices={};polys=[];attrs=[];mats=[]
for mat,poly in triangles:
    ids=[]
    for corner in poly:
        key=tuple(round(float(v),8) for v in corner[0])
        if key not in indices:indices[key]=len(verts);verts.append(corner[0])
        ids.append(indices[key])
    if len(set(ids))<3:continue
    polys.append(ids);attrs.append(poly);mats.append(mat)
new=bpy.data.meshes.new('HK416_ExtMagazine_FactorySurface')
new.from_pydata(verts,[],polys);new.update()
ob=bpy.data.objects.new('SM_HK416_ext_mag',new);bpy.context.collection.objects.link(ob)
for m in source.data.materials:new.materials.append(m.copy())
for i,old in enumerate(source.data.uv_layers):
    uv=new.uv_layers.new(name=old.name)
    for f,poly in zip(new.polygons,attrs):
        for li,c in zip(f.loop_indices,poly):uv.data[li].uv=c[2+i]
for i,old in enumerate(colors):
    color=new.color_attributes.new(name=old.name,type=old.data_type,domain='CORNER')
    for f,poly in zip(new.polygons,attrs):
        for li,c in zip(f.loop_indices,poly):color.data[li].color=c[2+UVS+i]
normals=[]
for f,mat,poly in zip(new.polygons,mats,attrs):
    f.material_index=mat;f.use_smooth=True
    normals.extend(tuple(c[1]/max(np.linalg.norm(c[1]),1e-12)) for c in poly)
new.normals_split_custom_set(normals)

# Close residual lower-band cut boundaries before export; preserve the original
# open feed mouth above the protected upper segment.
import bmesh
bm=bmesh.new();bm.from_mesh(new)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.0000005)
seams=[e for e in bm.edges if e.is_boundary and all(v.co.z<CUT+0.00001 for v in e.verts)]
if seams:bmesh.ops.holes_fill(bm,edges=seams,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(new);bm.free()
new.transform(socket)
ob.matrix_world=Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
file=E/(ob.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
bpy.data.libraries.write(str(file.with_suffix('.blend')),{ob},fake_user=True)
report=json.loads((O/'models.json').read_text())
report['parts']['ext_mag']={'name':ob.name,'file':str(file),'bindings':{m.name:'/Game/Weapons/HK416/Reworked20260930/Materials/M_HK416_Mag_Silencer_Magazine' for m in new.materials},'sockets':{},'source':'HK416 original magazine; full patterned curved band continuation'}
(O/'models.json').write_text(json.dumps(report,indent=2))
(O/'magazine_authoring.json').write_text(json.dumps({'extension_arc_m':LENGTH,'curve_quadratic':coef.tolist(),'protected_above_root_z_m':CUT,'method':'full surface band, original UVs, matched cut sections, original floorplate','runtime_tested':False},indent=2))
print('HK416_EXTENDED_MAGAZINE_SAVED',LENGTH,flush=True)
