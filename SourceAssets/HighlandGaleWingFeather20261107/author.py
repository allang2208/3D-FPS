"""Blender 5.1 authoring in blade-local coordinates. Curves are traced from the lower orthographic elevation."""
from pathlib import Path
import bpy, math, json, numpy as np
from mathutils import Vector,Quaternion
from bisect import bisect_right
from math import sin,cos,pi,exp,sqrt
P=Path(__file__).resolve().parent; PROJECT=P.parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.unit_settings.system='METRIC';bpy.context.preferences.filepaths.save_version=0
K=.000466; TIP=391.0
def Z(y):return -.05+(898-y)*K
def pos(x,d,y):return (x*K,d*.001,Z(y))
def ss(x):x=min(1.,max(0.,x));return x*x*(3.-2*x)
def g(x,w):return exp(-min(45.,(x/w)**2))
def table(p):
    xs,ys=zip(*p);n=len(xs);ds=[(ys[i+1]-ys[i])/(xs[i+1]-xs[i]) for i in range(n-1)];ms=[ds[0]]
    for i in range(1,n-1):
        a,b=ds[i-1:i+1];h=xs[i]-xs[i-1];k=xs[i+1]-xs[i]
        ms.append(0. if a*b<=0 else 3*(h+k)/((2*k+h)/a+(k+2*h)/b))
    ms.append(ds[-1])
    def interp(x):
        if x<=xs[0]:return ys[0]
        if x>=xs[-1]:return ys[-1]
        i=bisect_right(xs,x)-1;h=xs[i+1]-xs[i];t=(x-xs[i])/h
        return (1+2*t)*(1-t)**2*ys[i]+t*(1-t)**2*h*ms[i]+t*t*(3-2*t)*ys[i+1]+t*t*(t-1)*h*ms[i+1]
    return interp
top=table([(0,747),(18,746.6),(40,743),(54,738),(60.3,733),(61.5,734),(63.4,744),(68,754),(79,764),(96,769),(116,770.4),(140,769),(176,763),(218,752),(264,735),(301,717),(328,700),(350,683),(372,671),(389,663.6),(391,663)])
bot=table([(0,891),(33,890.5),(38,887),(42,878),(50,863),(65,847),(82,837),(101,830.7),(120,828.9),(138,830.1),(151,833.4),(153,833.6),(174,829),(223,819),(261,810.5),(291,800),(318,786),(343,764),(361,739),(376,709),(387,679),(391,663)])
crest=table([(0,.31),(48,.23),(67,.25),(97,.41),(125,.51),(154,.47),(220,.52),(283,.59),(332,.63),(363,.66),(391,.6)])
thick=table([(0,14.7),(36,14.1),(61,10.8),(91,7.4),(134,6.0),(200,5.7),(265,5.0),(317,5.3),(350,5.45),(372,4.0),(384,2.4),(389,1.15),(391,0)])
def depth(x,v):
    x=abs(x);v=min(1,max(0,v));w=thick(x)
    # The double grind of the hidden side is also modeled. Taper blended to the terminal leaf.
    c=crest(x);a=ss((x-37)/63)*(1-ss((x-371)/25))
    face=(.80+.12*sin(pi*v)+.07*v)
    topbevel=min(1.,(1-v)/.165);lowbevel=min(1.,v/.156)
    roll=lambda k: (k*(2-k))**.55
    edge=.12+.88*min(roll(topbevel),roll(lowbevel))
    main=2.62*g(v-c,.095)-1.15*g(v-c+.106,.058)
    # Staggered feather troughs have a folded lip and long gentle return; their ends vanish independently.
    q1=.17+.19*ss((x-108)/197);q2=.34+.14*ss((x-169)/172)
    def fold(q,amp):
        # A shallow plane on the handle side, a burnished apex, and a steep shadow wall toward the tip.
        v0=v-q
        return amp*(.54*g(v0+.058,.099)+.43*g(v0+.020,.036)-.82*g(v0-.036,.044)-.23*g(v0-.090,.085))
    f1=ss((x-102)/47)*(1-ss((x-281)/53))
    f2=ss((x-159)/45)*(1-ss((x-319)/44))
    central=(1-ss((x-55)/55))*(1.15*g(v-.42,.37)+.95*g(v-.89,.085))
    return w*face*edge+(a*main+fold(q1,2.48)*f1+fold(q2,2.02)*f2+central)*edge*ss(w/3)
def skew(x,v):
    return ss(abs(x)/300)*(1-ss((abs(x)-371)/20))*(.85+1.9*(v-.5))
def plane(x,v,s): return pos(x,skew(x,v)+s*depth(x,v),bot(abs(x))*(1-v)+top(abs(x))*v)
def faceat(x,y,s):
    a=abs(x);v=(bot(a)-y)/(bot(a)-top(a));return (skew(a,v)+s*depth(a,v))*.001
# One PBR atlas shared by all variants. Bands are smooth metals; quartz crown has its own facets.
def makemat(name):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
    p=n.get('Principled BSDF')
    for ch in ('BaseColor','NormalGL','ORM'):
        im=bpy.data.images.load(str(P/'Textures'/('T_GaleFeather_'+ch+'.png')),check_existing=True)
        im.colorspace_settings.name='sRGB' if ch=='BaseColor' else 'Non-Color'
        t=n.new('ShaderNodeTexImage');t.image=im
        if ch=='BaseColor':l.new(t.outputs[0],p.inputs['Base Color'])
        if ch=='NormalGL':
            nm=n.new('ShaderNodeNormalMap');l.new(t.outputs[0],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
        if ch=='ORM':
            sp=n.new('ShaderNodeSeparateColor');l.new(t.outputs[0],sp.inputs[0]);l.new(sp.outputs[1],p.inputs['Roughness']);l.new(sp.outputs[2],p.inputs['Metallic'])
    return m
surf=makemat('M_GaleFeather_Atelier');seatmat=surf.copy();seatmat.name='M_GaleFeather_BladeSeat'
parts=[]
# Face-loop UVs avoid welded caps or angular seams sharing a degenerate texture coordinate.
def make(name,verts,faces,bands,uvs,smooth=True,material=surf):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update();m.materials.append(material)
    uv=m.uv_layers.new(name='AtelierPBR')
    for f,b,uvset in zip(m.polygons,bands,uvs):
        f.use_smooth=smooth
        for idx,(u,v) in zip(f.loop_indices,uvset):uv.data[idx].uv=(.006+.988*u,(b+.055+.890*v)/16)
    ob=bpy.data.objects.new(name,m);sc.collection.objects.link(ob);parts.append(ob);return ob
def grid(name,rows,band,flip=False,material=surf,flat=False,closed=False):
    R,N=len(rows),len(rows[0]); vs=[v for r in rows for v in r];fs=[];bs=[];us=[]
    def add(f,b,uv):
        if flip:f=f[::-1];uv=uv[::-1]
        fs.append(f);bs.append(b);us.append(uv)
    steps=R if closed else R-1
    for j in range(steps):
        for i in range(N):
            k=(i+1)%N;j2=(j+1)%R
            add([j*N+i,j*N+k,j2*N+k,j2*N+i],band(j,i),[(j/steps,i/N),(j/steps,(i+1)/N),((j+1)/steps,(i+1)/N),((j+1)/steps,i/N)])
    if not closed:
        for j,order in [(0,list(reversed(range(N)))),(R-1,list(range(N)))]:
            # Triangulate each cap fan, including non-planar V-shaped sockets.
            center=tuple(np.mean(rows[j],axis=0));mid=len(vs);vs.append(center)
            for i,k in zip(order,order[1:]+order[:1]):
                add([mid,j*N+i,j*N+k],band(j if j<R-1 else j-1,i),[(.5,.5),(.5+.48*cos(2*pi*i/N),.5+.48*sin(2*pi*i/N)),(.5+.48*cos(2*pi*k/N),.5+.48*sin(2*pi*k/N))])
    return make(name,vs,fs,bs,us,not flat,material)
# A closed cross-section running from left tip through the waist to right tip: no Boolean at either root.
cuts=set(np.arange(0,390,2.5))|{0,38,42,54,60.3,61.5,63.4,68,138,151,153,372,384,389,390,390.75}
xx=sorted(cuts|{-x for x in cuts}); vv=sorted(set([0,.004,.012,.025,.045,.07,.10,.132,.156,.845,.89,.925,.955,.977,.990,.997,1]+[i/62 for i in range(1,62) if .156<i/62<.845]))
layout=[(-1,v) for v in vv]+[(1,v) for v in vv[::-1]]
rows=[[plane(x,v,s) for s,v in layout] for x in xx]
def shellband(j,i):
    x=abs((xx[j]+xx[min(len(xx)-1,j+1)])/2);s,v=layout[i];s2,u=layout[(i+1)%len(layout)];v=(u+v)*.5
    if s!=s2 or v<.029 or v>.96:return 1
    if x>110 and abs(v-crest(x))<.027:return 1
    return 0
# The x-direction of this grid determines the winding of the swept face.
shell=grid('01 | Forged crescent - two continuous feather grinds',rows,shellband,flip=True)
# Continuous blade-face UVs have measured longitudinal x, so the brushed finish and recess temper follow their sculpt.
uv=shell.data.uv_layers.active;N=len(layout)
for f in shell.data.polygons:
    if f.index>=(len(xx)-1)*N:break
    j,i=divmod(f.index,N);s0,v0=layout[i];s1,v1=layout[(i+1)%N]
    if s0!=s1 or xx[j]*xx[j+1]<0:continue
    for li in f.loop_indices:
        vtx=shell.data.loops[li].vertex_index;r,c=divmod(vtx,N)
        uv.data[li].uv=(.006+.988*abs(xx[r])/TIP,.5+.5*(.016+.968*layout[c][1]))
def carved_tube(name,points,radii,n=10,band=3,closed=False):
    rows=[]
    for j,pt in enumerate(points):
        p=Vector(pt);t=Vector(points[(j+1)%len(points) if closed else min(j+1,len(points)-1)])-Vector(points[(j-1)%len(points) if closed else max(j-1,0)])
        t.normalize();ref=Vector((0,1,0)) if abs(t.y)<.91 else Vector((0,0,1))
        v=t.cross(ref).normalized();w=t.cross(v).normalized()
        rx,ry=radii[j];rows.append([tuple(p+v*(rx*cos(2*pi*k/n))+w*(ry*sin(2*pi*k/n))) for k in range(n)])
    return grid(name,rows,lambda j,i:band,closed=closed)
def gold_rail(sign,side):
    # Trace the gold thread from its pointed tail at the shoulder, through one small double eye, into the primary ridge.
    yy=table([(40,843),(52,830),(69,816),(86,806),(101,801),(118,801),(136,803),(152,800),(184,794),(225,782),(263,765),(294,747),(324,726),(352,703),(374,682)])
    for strand,(xa,xb) in enumerate([(40,374),(80,149)]):
        pts=[];rads=[]
        for xx0 in np.linspace(xa,xb,163 if strand==0 else 90):
            t=(xx0-xa)/(xb-xa);x=sign*xx0
            a=ss((xx0-80)/13)*(1-ss((xx0-135)/14))
            phase=pi*(xx0-84)/17
            y=yy(xx0)+(1 if strand==0 else -1)*3.25*a*sin(phase)
            tw=(1 if strand==0 else -1)*.46*a*cos(phase)
            fac=(.09+.91*ss(t*8)*ss((1-t)*7))*(1-.62*ss((xx0-170)/200))
            # Set low feet into the metal, with alternating rise at each knot crossing.
            base=faceat(x,y,side);pts.append((x*K,base+side*(.00020+tw*.001),Z(y)))
            rads.append((.00080*fac,.00053*fac))
        carved_tube('12 | Interwoven wing fillet',pts,rads,10)
for side in (-1,1):
    for sign in (-1,1):gold_rail(sign,side)
# Low diamond with a continuous stepped double bezel. Four crown kites are divided into star and girdle facets.
def diamond(side):
    cy=807.8; outerx,outerh=41.4,49.8
    # Mount to a gentle, uniform plane secured into the breast of the guard rather than projecting individual jewel corners.
    anchor=max(abs(faceat(x,cy+y,side)) for x,y in [(0,0),(0,-outerh),(outerx,0),(0,outerh),(-outerx,0)])+.0001
    shape=[(0,-1),(.49,-.51),(1,0),(.51,.49),(0,1),(-.49,.51),(-1,0),(-.51,-.49)]
    def ring(scale,h):return [(x*outerx*K*scale,side*(anchor+h),Z(cy+y*outerh*scale)) for x,y in shape]
    rows=[ring(sc0,h) for sc0,h in [(1.015,-.0049),(1.016,-.0011),(1,.00025),(.967,.0012),(.92,.0019),(.879,.00195),(.847,.00104),(.833,.00072)]]
    rows[0]=[(px,faceat(px/K,898-(pz+.05)/K,side)-side*.00065,pz) for px,py,pz in rows[0]]
    grid('20 | Stepped champagne collet',rows,lambda j,i:2 if j<2 or j==6 else 3,flip=side<0,flat=True)
    # Piecewise pale blue crown with subtle contrast between the broad cuts, no baked sparkle or emission.
    a=ring(.846,.00126);b=ring(.802,.00215)
    half=[(x*outerx*K*.40,side*(anchor+.00455),Z(cy+y*outerh*.40)) for x,y in shape[::2]]
    verts=a+b+half+[(0,side*(anchor+.00555),Z(cy))];faces=[];bands=[]
    def add(indices,band):
        if side<0:indices=indices[::-1]
        faces.append(indices);bands.append(band)
    for i in range(8):add([i,(i+1)%8,8+(i+1)%8,8+i],7 if i%3 else 6)
    for q in range(4):
        i=8+2*q;mid=i+1;nx=8+(2*q+2)%8;h0=16+q;h1=16+(q+1)%4
        add([i,mid,h0],(5,7,5,6)[q]);add([mid,nx,h1],(7,5,6,5)[q]);add([mid,h1,h0],(5,6,5,7)[q]);add([h0,h1,20],(6,5,7,5)[q])
    add(list(reversed(range(8))),7)
    uvs=[[(.5+verts[i][0]/(.044),.5+(verts[i][2]-Z(cy))/.051) for i in f] for f in faces]
    make('21 | Low cushion-cut glacial lozenge',verts,faces,bands,uvs,False)
for side in (-1,1):diamond(side)


# Extract actual cap boundary vertices instead of inferring contact from mesh bounds.
source=PROJECT/'SourceAssets/HighlandClaymoreMeshy20260922/JunctionBlendV5_20260927/Highland_ContinuousJunctionV5_Editable.blend'
with bpy.data.libraries.load(str(source)) as (src,dst):
    dst.objects=['SM_Highland_Guard_factory_JunctionV5','SM_Highland_Blade_factory_JunctionV5','SM_Highland_Blade_Broadblade_ThickV2_JunctionV5']
guard,blade,heavy=dst.objects
def contact(o,pred):
    ids={p.index for p in o.data.vertices if pred(p.co)}; edges={}
    for f in o.data.polygons:
        if all(i in ids for i in f.vertices):
            for e in f.edge_keys:edges[e]=edges.get(e,0)+1
    r={tuple(o.data.vertices[i].co) for e,count in edges.items() if count==1 for i in e}
    if len(r)<8:raise RuntimeError(o.name+' missing mount boundary')
    return np.array(sorted(r,key=lambda p:math.atan2(p[1],p[0])))
lower=contact(guard,lambda v:abs(v.z+.050)<2e-6)
def elliptical(a,rx,ry,power=2.5):
    co,si=cos(a),sin(a)
    return np.array([rx*math.copysign(abs(co)**(2/power),co),ry*math.copysign(abs(si)**(2/power),si)])
angles=np.arctan2(lower[:,1],lower[:,0])
rows=[lower.tolist()]
for z,blend,rx,ry in [(-.04965,.35,.0192,.0156),(-.0491,.75,.0197,.0160),(-.04825,1,.0199,.0164),(-.0477,1,.0198,.0162),(-.04723,1,.01925,.01575),(-.0467,1,.01925,.01575),(-.0433,1,.01955,.01595),(-.04285,1,.0198,.01623),(-.0423,1,.02005,.01645),(-.0416,1,.02015,.01645),(-.0411,1,.0199,.01605),(-.04065,1,.0194,.01565)]:
    rows.append([(*((1-blend)*v[:2]+blend*elliptical(a,rx,ry)),z) for v,a in zip(lower,angles)])
collar=grid('30 | Native grip contact and turned silver ferrule',rows,lambda j,i:1 if j in (1,2,3,8,9) else (2 if j in (4,7) else 4))
# Two genuinely braided gold ribbons wrap the full perimeter of the ferrule.
for q in range(2):
    points=[];radii=[]
    for t in np.arange(320)/320:
        a=2*pi*t;phase=8*a+q*pi;out=.00017+.00023*cos(phase);x,y=elliptical(a,.01948+out,.0159+out)
        points.append((x,y,-.04508+.00145*sin(phase)));radii.append((.00040,.00033))
    carved_tube('31 | Plait at ferrule',points,radii,8,3,True)
# The entire insert is a dedicated finish slot only on the broadblade. The crest, jewel and both wings are protected by topology.
shared=list(parts)
ring_pred=lambda v:abs(v.z-.058-.95*abs(v.x))<.000003
rings={'Native':contact(blade,ring_pred),'Broadblade':contact(heavy,ring_pred),'Ridge':np.array(json.loads((P/'Inputs/RidgeSocket.json').read_text())['points'])}
spec={'id':'highland_gale_wing','ue_folder':'/Game/Weapons/HighlandClaymore20260922/GaleFeather20261107','variants':[],'reference':'Inputs/GaleWing_ThreeViews.png','interface':'highland_hilt_v1','units':'Blender metres / UE centimetres','grip_ring_vertices':len(lower),'runtime_tested':False}
def objactive(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def collect(name,objs):
    col=bpy.data.collections.new(name);sc.collection.children.link(col)
    for ob in objs:
        for old in list(ob.users_collection):old.objects.unlink(ob)
        col.objects.link(ob)
    return col
inserts=[];games=[]
for key,ring in rings.items():
    # All circumference samples terminate exactly on the authored blade. Last two stations extend its local flat section.
    rows=[]
    for t in [0,.06,.14,.24,.37,.53,.71,.85,.94,.98,1.]:
        row=[]
        for rx,ry,rz in ring:
            width=abs(rx)/K
            tx=rx*(.92+.08*ss(t))
            # A narrow overdraw inside the thicker steel crest closes the assembly without altering the visible body.
            z0=min(Z(top(abs(tx)/K))-.0025,rz-.0038)
            y0=(1.13 if key=='Ridge' else 1.45)*ry
            row.append((tx,y0+(ry-y0)*ss(t),z0+(rz-z0)*t))
        rows.append(row)
    ad=grid('40 | Fitted blade socket '+key,rows,lambda j,i:0,material=seatmat if key=='Broadblade' else surf)
    inserts.append(ad)
    objactive(shell);copies=[]
    for ob in [*shared,ad]:
        cp=ob.copy();cp.data=ob.data.copy();sc.collection.objects.link(cp);copies.append(cp)
    objactive(copies[0])
    for o in copies:o.select_set(True)
    bpy.ops.object.join();game=bpy.context.object;game.name='SM_GaleFeather_'+key
    m=game.modifiers.new('Final tangent triangulation','TRIANGULATE');m.quad_method='FIXED';bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(game.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False,path_mode='STRIP')
    spec['variants'].append(dict(key=key,mesh=game.name,triangles=len(game.data.polygons),ring_vertices=len(ring),fbx='Export/'+game.name+'.fbx'))
    games.append(game)
masters=collect('01 | Atelier - editable ornamental components',shared)
mounts=collect('02 | Fitted seats - select one',inserts)
exports=collect('03 | Joined UE exports - select one',games)
for o in [*inserts,*games]:o.hide_set(True);o.hide_render=True
# Default artist view is the detached ornamental body and ridge seat; other seats/exports available separately.
inserts[-1].hide_set(False);inserts[-1].hide_render=False
objactive(shell)
from mathutils import Euler
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            sp=area.spaces.active;sp.region_3d.view_rotation=Euler((pi/2,0,0)).to_quaternion()
            sp.region_3d.view_distance=.52;sp.region_3d.view_location=(0,0,.003);sp.region_3d.view_perspective='ORTHO';sp.shading.type='MATERIAL'
for o in (guard,blade,heavy):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_GaleWing_Feather.blend'),compress=True)
(P/'model.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
print('FEATHER_EXPORT '+str([(r['key'],r['triangles']) for r in spec['variants']]),flush=True)
