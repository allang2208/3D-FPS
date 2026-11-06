"""Build the sword from the actual gem-side contact ring to the existing 110 cm tip."""
from pathlib import Path
import json
import math
import sys
import bpy
import numpy as np
from mathutils import Vector,Matrix,geometry
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parent
WORK=P.parents[2]/'Saved/RidgeLowSeat'
sys.path.insert(0,str(P))
from grind import PINS,Z,broadside,ease
from guard_seat import seat_z

bpy.ops.wm.open_mainfile(filepath=str(WORK/'FittedGuardAssembly.blend'))
scene=bpy.context.scene
name='SM_Highland_Blade_RidgePiercer_V1'
icon='ue_highland_claymore_blade_1_highland_ridge_piercer.png'
ring_source=json.loads((WORK/'socket_ring.json').read_text())
native=np.array(ring_source['points'])
native_norm=np.array(ring_source['normals'])
points=native.tolist()
uvs=[(0,0)]*len(points)
faces=[]
sharp=set()
custom={}
corner_uv={}
def vertex(pt,uv):
    idx=len(points)
    points.append(tuple(pt))
    uvs.append(uv)
    return idx
def crease(a,b):
    sharp.add((min(a,b),max(a,b)))
def fractions(coords):
    lengths=np.linalg.norm(np.roll(coords,-1,axis=0)-coords,axis=1)
    return np.r_[0.,np.cumsum(lengths)/lengths.sum()]
def sample_cycle(points,f,t):
    return np.array([np.interp(t,f,np.r_[col,col[0]]) for col in points.T]).T
def atlas(p,z):
    return (.41+.39*p,.02+.96*z/1100.)

# Grinds have closely spaced support rails at both lips. The middle of each
# optical plane stays broad enough to read the environment as one reflection.
ps=sorted(set([*PINS,*[p for a,b in zip(PINS,PINS[1:]) for p in np.linspace(a,b,5)[1:-1]],
               *[v+d for v in (.22,.425,.485,.677) for d in (-.014,-.007,.007,.014)],.988]))
cross=ps[::-1]+[-p for p in ps[1:]]
around=[(p,1) for p in cross]+[(p,-1) for p in cross[::-1]]
def section(z):
    section_cache={p:broadside(z,p) for p in ps}
    return np.array([section_cache[abs(p)]*[1 if p>=0 else -1,side,1] for p,side in around])
perimeter=fractions(section(16)[:,:2])
native_f=fractions(native[:,:2])
# Register the front/back centres and the four edge turns independently. A
# whole-ring length match shifts the central arris to one side of the gem.
front=np.flatnonzero(native[:,1]>=0)
back=np.flatnonzero(native[:,1]<0)
source_marks=[0,front[np.argmin(abs(native[front,0]))],
              front[np.argmin(native[front,0])],back[np.argmin(native[back,0])],
              back[np.argmin(abs(native[back,0]))],back[np.argmax(native[back,0])],len(native)]
target_marks=[0,len(ps)-1,len(cross)-1,len(cross),
              len(cross)+len(ps)-1,len(around)-1,len(around)]
perimeter=np.interp(perimeter,perimeter[target_marks],native_f[source_marks])
contact=sample_cycle(native,native_f,perimeter[:-1])
normals=sample_cycle(native_norm,native_f,perimeter[:-1])
normals/=np.maximum(1.e-12,np.linalg.norm(normals,axis=1)[:,None])
# Extend the actual guard tangent into the blade. The quintic correction dies
# with its slope/curvature at 58 mm, so the existing shoulder is untouched.
base=section(16)
derivative=(section(16.01)-section(15.99))/.02
curvature=(section(16.01)-2*base+section(15.99))/.0001
rise=np.zeros_like(normals)
rise[:,2]=.001
rise-=normals*normals[:,2,None]*.001
span=42.
def seated_section(z):
    coords=section(z)
    t=float(np.clip((z-16.)/span,0.,1.))
    h0=1.-10*t**3+15*t**4-6*t**5
    h1=t-6*t**3+8*t**4-3*t**5
    h2=.5*(t*t-3*t**3+3*t**4-t**5)
    return coords+h0*(contact-base)+span*h1*(rise-derivative)-span*span*h2*curvature
for i,f in enumerate(native_f[:-1]):
    p=np.interp(f,perimeter,[*[k[0] for k in around],around[0][0]])
    uvs[i]=atlas(p,16)
    custom[i]=(native_norm[i],1.)

def join_native(ring):
    i=j=0
    while i<len(native) or j<len(ring):
        a=native_f[i+1] if i<len(native) else 2.
        b=perimeter[j+1] if j<len(ring) else 2.
        low=i%len(native)
        high=ring[j%len(ring)]
        if abs(a-b)<1.e-8:
            faces.append((low,(i+1)%len(native),ring[(j+1)%len(ring)],high))
            i+=1
            j+=1
        elif a<b:
            faces.append((low,(i+1)%len(native),high))
            i+=1
        else:
            faces.append((low,ring[(j+1)%len(ring)],high))
            j+=1

rim=[Vector((v[0],v[1],0)) for v in native]
for tri in geometry.tessellate_polygon([rim]):
    tri=tuple(reversed(tri))
    corner_uv[len(faces)]=[(.08+1.8*native[i,0],.04+2*native[i,1]) for i in tri]
    faces.append(tri)
cap_count=len(faces)
levels=sorted(set([16.20,16.55,17.,17.6,18.5,*np.arange(19.,61.,.75),*np.arange(62.,150.,2.),*np.arange(154.,319.,5.),
                    *np.arange(325.,1085.,10.),*Z[1:-1],68.55,69.45,1090.,1095.,1098.5,1099.4]))
prev=None
for z in levels:
    coords=seated_section(z)
    ring=[]
    for j,(p,side) in enumerate(around):
        idx=vertex(coords[j],atlas(p,z))
        ring.append(idx)
    if prev is None:
        join_native(ring)
    else:
        for j,(p,side) in enumerate(around):
            k=(j+1)%len(ring)
            quad=[prev[j],prev[k],ring[k],ring[j]]
            if around[k][1]!=side:
                low,hi=uvs[prev[j]][1],uvs[ring[j]][1]
                corner_uv[len(faces)]=[(.805,low),(.815,low),(.815,hi),(.805,hi)]
            faces.append(quad)
            if abs(p) in (0.,1.):
                crease(prev[j],ring[j])
    prev=ring
tip=vertex((0,0,1.1),atlas(0,1100))
for i,a in enumerate(prev):
    faces.append((a,prev[(i+1)%len(prev)],tip))

# Sample the finished cheeks including their oblique sweep. No floating wire
# across the root curve, even where the cross-section changes fastest.
surface=BVHTree.FromPolygons(points,faces)
def on_face(x,z,side):
    hit=surface.ray_cast(Vector((x,side*.08,z)),Vector((0,-side,0)),.14)[0]
    if hit is None:
        raise RuntimeError(f'Inlay leaves metal at x={x}, z={z}')
    return hit.y
def wire(side,curve,half,gold=False):
    count=178 if not gold else 105
    prev=None
    shape=[(-1.,-.00016),(-.97,.00002),(-.76,.00022),(-.46,.00028),
           (.42,.00028),(.76,.00022),(.97,.00003),(1.,-.00016),(0.,-.00028)]
    for t in np.linspace(0.,1.,count):
        x,z,lift=curve(t)
        delta=.00015
        a=curve(max(0.,t-delta));b=curve(min(1.,t+delta))
        dx,dz=b[0]-a[0],b[1]-a[1]
        length=math.hypot(dx,dz)
        taper=.015+.985*min(ease(0,.055,t),1-ease(.93,1.,t))
        row=[]
        for q,h in shape:
            xx=x+dz/length*q*half*taper
            zz=z-dx/length*q*half*taper
            yy=on_face(xx,zz,side)+side*(lift+h*taper)
            row.append(vertex((xx,yy,zz),((.962 if gold else .875)+.024*q,.12+.76*t)))
        if prev is None:
            faces.append(row if side>0 else row[::-1])
            # Endgrain UVs have an area even at a nearly invisible taper.
            corner_uv[len(faces)-1]=[(.875+.014*q,.12+.012*h/.00042) for q,h in (shape if side>0 else shape[::-1])]
        else:
            for j in range(len(row)):
                k=(j+1)%len(row)
                quad=[prev[j],prev[k],row[k],row[j]]
                faces.append(quad if side<0 else quad[::-1])
                if j in (0,2,5,7):
                    crease(prev[j],row[j])
        prev=row
    faces.append(prev if side<0 else prev[::-1])
    corner_uv[len(faces)-1]=[(.875+.014*q,.87+.012*h/.00042) for q,h in (shape if side<0 else shape[::-1])]

def plait(t,i):
    # The paired border feet grow from the gem bed; the woven strands begin
    # inside that frame, leaving a clean piece of forged steel at the joint.
    envelope=.0121*(1.-.28*t)*max(.00005,1.-t**2.25)**.80
    ph=2*math.pi*(2.51*t+i/3.)+.45
    x=envelope*(.81*math.sin(ph) if i<3 else (1 if i==3 else -1))
    if i>=3:
        x+=(1 if i==3 else -1)*.0014*(1-ease(0.,.18,t))
    foot=.039 if i<3 else seat_z(x)+.0045
    z=(1.-t)*foot+t*.278
    lift=(.00002+.00064*(.5+.5*math.cos(ph))) if i<3 else -.00007
    lift*=ease(0.,.065,t)*(1-ease(.93,1.,t))
    return x,z,lift
def fillet(t,s):
    # Warm hairline along the fitting, running outward from the gem setting
    # and back into the blue-steel lip. The two curves are mirrored.
    x=s*(.0135+.0098*math.sin(.60*math.pi*t)**.9)
    z=(1-t)*(seat_z(x)+.0050)+t*.151
    return x,z,-.00020
for side in (-1,1):
    for i in range(5):
        wire(side,lambda t:plait(t,i),.00106 if i<3 else .00076)
    for s in (-1,1):
        wire(side,lambda t:fillet(t,s),.00044,True)

mesh=bpy.data.meshes.new(name)
mesh.from_pydata(points,[],faces)
mesh.update()
obj=bpy.data.objects.new(name,mesh)
scene.collection.objects.link(obj)
uv=mesh.uv_layers.new(name='SteelFinish')
ids=np.empty(len(mesh.loops),dtype=np.int32)
mesh.loops.foreach_get('vertex_index',ids)
tex=np.asarray(uvs,dtype=np.float32)[ids]
for fi,coords in corner_uv.items():
    tex[list(mesh.polygons[fi].loop_indices)]=coords
uv.data.foreach_set('uv',tex.ravel())
for f in mesh.polygons:
    f.use_smooth=f.index>=cap_count
for e in mesh.edges:
    a,b=e.vertices
    if (min(a,b),max(a,b)) in sharp:
        e.use_edge_sharp=True
mesh.update()
shading=np.array([n.vector[:] for n in mesh.corner_normals])
for j in range(mesh.polygons[cap_count].loop_start,len(ids)):
    if ids[j] in custom:
        normal,w=custom[ids[j]]
        shading[j]=(1-w)*shading[j]+w*normal
shading/=np.maximum(1e-12,np.linalg.norm(shading,axis=1)[:,None])
mesh.normals_split_custom_set(shading.tolist())
mat=bpy.data.materials.new('M_RidgeWedgeSteel')
mat.use_nodes=True
nodes,links=mat.node_tree.nodes,mat.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
for i,(key,pin) in enumerate([('BaseColor','Base Color'),('Roughness','Roughness'),('Metallic','Metallic'),('Normal','Normal')]):
    texnode=nodes.new('ShaderNodeTexImage')
    texnode.image=bpy.data.images.load(str(P/'Textures'/('T_RidgeWedge_'+key+'.png')))
    texnode.location=(-620,390-i*260)
    if key!='BaseColor':
        texnode.image.colorspace_settings.name='Non-Color'
    src=texnode.outputs['Color']
    if key=='Metallic':
        channels=nodes.new('ShaderNodeSeparateColor')
        links.new(src,channels.inputs['Color'])
        src=channels.outputs['Red']
    elif key=='Normal':
        normal=nodes.new('ShaderNodeNormalMap')
        links.new(src,normal.inputs['Color'])
        src=normal.outputs['Normal']
    links.new(src,bsdf.inputs[pin])
mesh.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active=obj
fbx=P/'Export'/(name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
                         add_leaf_bones=False,bake_anim=False,mesh_smooth_type='EDGE')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_RidgePiercer_LowSeat_Editable.blend'))
spec={'revision':'WedgeSpineJunctionR4_20261106','junction_revision':'GemBed_TangentR4','surface':
      '/Game/Weapons/HighlandClaymore20260922/RidgePiercer20260927/WedgeSpine/M_RidgeWedgeSteel',
      'fbx':str(fbx),'icon':icon,'etched_rune_mask':True,'native_build_required':False,
      'framed_icon_source':str(P.parents[1]/'HighlandRidgeIcon20261106'/icon),
      'socket_z_range_cm':[float(100*native[:,2].min()),float(100*native[:,2].max())],
      'tip_cm':110,'shoulder_z_cm':6.9,'socket_width_cm':float(100*np.ptp(native[:,0]))}
(P/'authoring.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
from menu_icon import render_icon
render_icon(scene,obj,P/'Icons'/icon)
