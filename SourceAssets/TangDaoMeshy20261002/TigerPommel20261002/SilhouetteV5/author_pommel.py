"""Volumetric roaring tiger, closed mouth bowl, separate teeth/gems and real hilt seat."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from collections import deque,Counter
from mathutils import Vector
P=Path(__file__).resolve().parent;BASE=P.parent;sys.path.insert(0,str(BASE))
from surface_recipe import SOURCE,sample,face_height,body_height,cloud,smooth,connector_field
NAME='SM_TangDao_Pommel_tiger_mountain_SilhouetteV5'
UE='/Game/Weapons/TangDao20261002/TigerPommel20261002/SilhouetteV5'
FAMILIES=['BronzeFace','Gilt','Garnet','Mouth','ChasedBody','Connector']
MATS=['M_TangDaoTigerPommel_'+f for f in FAMILIES]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
V=[];F=[];UV=[];MI=[];SM=[]

def add(verts,faces,uv=None,mat=1,sm=True):
    offset=len(V);V.extend([tuple(p) for p in verts])
    for j,f in enumerate(faces):
        F.append([offset+i for i in f]);MI.append(mat);SM.append(sm)
        UV.append(uv[j] if uv is not None else [(.5+verts[i][0]*8,.5+verts[i][2]*8) for i in f])

# Sculpt coordinates: x=head width, y=outward face, z=crown up.
# In TangDao local space the tiger faces away from the grip along -Z.
HEAD_LOCAL_Z=-.108
def tiger(p):return Vector((p[2]+.002,p[0],HEAD_LOCAL_Z-p[1]))

def ellipsoid(center,radii,mat=1,segments=32,rings=18,transform=tiger):
    vs=[];fs=[];uv=[]
    for j in range(rings+1):
        a=math.pi*j/rings
        for k in range(segments):
            b=2*math.pi*k/segments
            local=Vector((radii[0]*math.sin(a)*math.cos(b),radii[1]*math.sin(a)*math.sin(b),radii[2]*math.cos(a)))+Vector(center)
            vs.append(transform(local))
    for j in range(rings):
        for k in range(segments):
            kk=(k+1)%segments
            if j==0:f=[k,(j+1)*segments+kk,(j+1)*segments+k]
            elif j==rings-1:f=[j*segments+k,j*segments+kk,(j+1)*segments+k]
            else:f=[j*segments+k,j*segments+kk,(j+1)*segments+kk,(j+1)*segments+k]
            fs.append(f)
            uv.append([((i%segments if i%segments else segments if k==segments-1 else 0)/segments,1-(i//segments)/rings) for i in f])
    add(vs,fs,uv,mat)

def tube(points,radius,mat=1,closed=False,nr=12,transform=lambda p:Vector(p),section=None):
    pts=[Vector(p) for p in points];vs=[];fs=[];uv=[]
    distance=[0.]
    for i in range(1,len(pts)):distance.append(distance[-1]+(pts[i]-pts[i-1]).length)
    total=distance[-1]+((pts[0]-pts[-1]).length if closed else 0)
    for i,p in enumerate(pts):
        tangent=(pts[(i+1)%len(pts)]-pts[(i-1)%len(pts)]).normalized() if closed else (pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        axis=Vector((0,1,0)) if abs(tangent.y)<.85 else Vector((1,0,0))
        a=tangent.cross(axis).normalized();b=tangent.cross(a).normalized()
        r=radius[i] if isinstance(radius,(list,np.ndarray)) else radius
        for k in range(nr):
            q=2*math.pi*k/nr
            h=float(body_height(np.asarray(distance[i]/max(total,1e-8)),np.asarray(k/nr)))*.14 if section=='cloud' else 0
            vs.append(transform(p+a*((r+h)*math.cos(q))+b*((r+h)*math.sin(q))))
    for j in range(len(pts) if closed else len(pts)-1):
        jj=(j+1)%len(pts)
        for k in range(nr):
            kk=(k+1)%nr;f=[j*nr+k,j*nr+kk,jj*nr+kk,jj*nr+k];fs.append(f)
            u=distance[j]/max(total,1e-8);un=distance[jj]/max(total,1e-8) if jj else 1.
            uv.append([(u,k/nr),(u,(k+1)/nr),(un,(k+1)/nr),(un,k/nr)])
    if not closed:
        for j,rev in [(0,True),(len(pts)-1,False)]:
            cap=[j*nr+k for k in range(nr)];fs.append(cap[::-1] if rev else cap)
            uv.append([(.5+.45*math.cos(2*math.pi*k/nr),.5+.45*math.sin(2*math.pi*k/nr)) for k in (range(nr-1,-1,-1) if rev else range(nr))])
    add(vs,fs,uv,mat)

def loft(rings,mat=1,us=None,v_coords=None,span_mats=None):
    n=len(rings[0]);vs=[p for ring in rings for p in ring];fs=[];uv=[]
    us=us if us is not None else np.arange(n)/n
    v_coords=v_coords if v_coords is not None else np.arange(len(rings))/(len(rings)-1)
    for j in range(len(rings)-1):
        for k in range(n):
            kk=(k+1)%n;fs.append([j*n+k,j*n+kk,(j+1)*n+kk,(j+1)*n+k])
            a,b=us[k],us[kk] if kk else 1.
            uv.append([(a,v_coords[j]),(b,v_coords[j]),(b,v_coords[j+1]),(a,v_coords[j+1])])
    for j,rev in [(0,True),(len(rings)-1,False)]:
        indices=[j*n+k for k in range(n)];fs.append(indices[::-1] if rev else indices)
        rr=rings[j];axes=sorted(range(3),key=lambda axis:max(p[axis] for p in rr)-min(p[axis] for p in rr),reverse=True)[:2]
        a,b=axes;cx=sum(p[a] for p in rr)/n;cy=sum(p[b] for p in rr)/n
        extent=max(max(abs(p[a]-cx),abs(p[b]-cy)) for p in rr)+1e-7
        uv.append([(.5+.45*(rr[k][a]-cx)/extent,.5+.45*(rr[k][b]-cy)/extent) for k in (range(n-1,-1,-1) if rev else range(n))])
    start=len(MI);add(vs,fs,uv,mat)
    if span_mats is not None:
        for j,material in enumerate(span_mats):
            for k in range(n):MI[start+j*n+k]=material

# Copy the actual native pommel cut, including its off-center contour.
raw=json.loads((BASE.parent/'interfaces.json').read_text(encoding='utf-8'))['parts']['pommel']['cut_boundary_loops_local_m'][0]
n=len(raw);center=Vector((-.0030715,.000018,0))
lengths=[math.hypot(raw[(i+1)%n][0]-p[0],raw[(i+1)%n][1]-p[1]) for i,p in enumerate(raw)]
arc=np.r_[0,np.cumsum(lengths[:-1])]/sum(lengths)
area=sum(p[0]*raw[(i+1)%n][1]-raw[(i+1)%n][0]*p[1] for i,p in enumerate(raw));sign=1 if area>0 else -1
a0=math.atan2((raw[0][1]-center.y)/.024882,(raw[0][0]-center.x)/.025445)
def dense_profile(knots,spacing=.00030):
    profile=[knots[0]]
    for a,b in zip(knots,knots[1:]):
        steps=max(1,math.ceil(abs(b[0]-a[0])/spacing))
        for t in np.linspace(0,1,steps+1)[1:]:profile.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
    return profile

# Short decorated hilt-end socket and narrow connecting shank, replacing the
# old broad, smooth funnel. The first two rings retain the exact host cut.
native_profile=dense_profile([(.0015,1),(0,1),(-.0008,1.016),(-.0016,1.016),(-.0026,.985),
    (-.0086,.985),(-.0092,1.005),(-.0101,1.005),(-.0106,.97),(-.0116,.86),(-.0132,.63),
    (-.0148,.40),(-.0162,.25),(-.0170,.23),(-.021,.23),(-.022,.21)])
rings=[];native_v=[]
for z,r in native_profile:
    q=float(smooth(.0015,.0045,-z));shift=float(smooth(.0060,.0144,-z));rr=[]
    shoulder=z<=-.0106
    v=float(np.clip((-.0106-z)/.0056 if shoulder else (-.0026-z)/.006,0,1));native_v.append(v)
    carved= -.0086<z<-.0026 or -.0162<z<-.0106
    heights=.00055*connector_field(arc,np.full(n,v),True) if carved else np.zeros(n)
    for i,(x,y,_) in enumerate(raw):
        a=a0+sign*2*math.pi*arc[i]
        rr.append((((x-center.x)*(1-q)+.025445*math.cos(a)*q)*r+center.x*(1-shift)+heights[i]*math.cos(a),
                   ((y-center.y)*(1-q)+.024882*math.sin(a)*q)*r+center.y*(1-shift)+heights[i]*math.sin(a),z))
    rings.append(rr)
native_mats=[5 if -.0086<(a[0]+b[0])/2<-.0026 or -.0162<(a[0]+b[0])/2<-.0106 else 1 for a,b in zip(native_profile,native_profile[1:])]
loft(rings,us=arc,v_coords=native_v,span_mats=native_mats)
ring=[(.016*math.sin(a),0,-.036+.016*math.cos(a)) for a in np.linspace(0,2*math.pi,192,endpoint=False)]
tube(ring,.0032,mat=4,closed=True,nr=24,section='cloud')
for y in [-.0024,.0024]:tube([(x,y,z) for x,_,z in ring],.00055,closed=True,nr=12)
# Ring/head junction: narrow shank, turned collar, relief sleeve, inset ruby
# band and a bevelled stop rim fitted into the rounded rear skull.
socket_profile=dense_profile([(-.0488,.0048),(-.0548,.0048),(-.0553,.0052),(-.0558,.0072),
    (-.0565,.0078),(-.0578,.0078),(-.0584,.0068),(-.0585,.0092),(-.0592,.0118),
    (-.0601,.0128),(-.0612,.0138),(-.0673,.0148),(-.0676,.0158),(-.0683,.0175),
    (-.0690,.0180),(-.0710,.0180),(-.0720,.0198),(-.0736,.0220),(-.0745,.0232)])
angles=np.linspace(0,math.tau,192,endpoint=False);socket_u=np.arange(192)/192
socket_rings=[];socket_v=[]
for z,r in socket_profile:
    v=float(np.clip((-.0612-z)/.0061,0,1));socket_v.append(v)
    heights=.00055*connector_field(socket_u,np.full(192,v),True) if -.0673<z<-.0612 else np.zeros(192)
    offset=.0005*float(smooth(.0585,.0745,np.asarray(-z)))
    socket_rings.append([(offset+(r+heights[k])*math.cos(a),(r+heights[k])*math.sin(a),z) for k,a in enumerate(angles)])
socket_mats=[5 if -.0673<(a[0]+b[0])/2<-.0612 else 1 for a,b in zip(socket_profile,socket_profile[1:])]
loft(socket_rings,v_coords=socket_v,span_mats=socket_mats)
# Fine rolled rims frame the red inset band without covering the sleeve.
for z,r in [(-.0690,.0181),(-.0710,.0181)]:
    offset=.0005*float(smooth(.0585,.0745,np.asarray(-z)))
    tube([(offset+r*math.cos(a),r*math.sin(a),z) for a in angles],.00036,closed=True,nr=10)
for a in np.linspace(0,math.tau,18,endpoint=False):
    z=-.0700;offset=.0005*float(smooth(.0585,.0745,np.asarray(-z)))
    setting=(offset+.01805*math.cos(a),.01805*math.sin(a),z)
    ruby=(offset+.01865*math.cos(a),.01865*math.sin(a),z)
    ellipsoid(setting,(.00110,.00110,.00110),mat=1,segments=24,rings=12,transform=lambda p:Vector(p))
    ellipsoid(ruby,(.00080,.00080,.00080),mat=2,segments=24,rings=12,transform=lambda p:Vector(p))

SKULL_RX=.044;SKULL_RY=.044;SKULL_RZ=.044;SKULL_CZ=-.0015;SKULL_CY=.004
head_vertex_start=len(V)

def front_y(x,z):
    u=x/.082+.5;v=.5-z/.09
    dome=math.sqrt(max(.005,1-(x/SKULL_RX)**2-((z-SKULL_CZ)/SKULL_RZ)**2))
    muzzle=.0085*(math.exp(-(((x-.006)/.0105)**2+((z-.005)/.0065)**2))+math.exp(-(((x+.006)/.0105)**2+((z-.005)/.0065)**2)))*.65
    nose=.003*math.exp(-((x/.007)**2+((z-.009)/.007)**2))
    jaw=.007*math.exp(-((x/.017)**2+((z+.023)/.008)**2))
    sockets=.0033*sum(math.exp(-(((x-sign*.0126)/.0047)**2+((z-.0176)/.0037)**2)) for sign in [-1,1])
    bridge=.0014*math.exp(-((x/.0045)**2+((z-.016)/.009)**2))
    return SKULL_CY+SKULL_RY*dome+muzzle+nose+jaw+bridge-sockets+float(face_height(np.asarray(u),np.asarray(v)))
def skull(theta,beta,raised=0):
    """Smooth ellipsoid rear hemisphere, with decorations following its normals."""
    x=SKULL_RX*math.cos(beta)*math.sin(theta)
    z=SKULL_CZ+SKULL_RZ*math.cos(beta)*math.cos(theta)
    y=SKULL_CY-SKULL_RY*math.sin(beta)
    normal=Vector((x/SKULL_RX**2,(y-SKULL_CY)/SKULL_RY**2,(z-SKULL_CZ)/SKULL_RZ**2)).normalized()
    return Vector((x,y,z))+normal*raised

# Adaptive mask topology: front and rounded rear skins share a sealed perimeter.
# The open mouth is a separate recessed closed bowl connected to the front lip.
N=420;u,v=np.meshgrid(np.linspace(0,1,N),np.linspace(0,1,N));lum=sample(SOURCE,u,v)
solid=lum>.085;outside=np.zeros_like(solid);queue=deque()
for k in range(N):
    for j,i in [(0,k),(N-1,k),(k,0),(k,N-1)]:
        if not solid[j,i] and not outside[j,i]:outside[j,i]=True;queue.append((j,i))
while queue:
    j,i=queue.popleft()
    for jj,ii in [(j-1,i),(j+1,i),(j,i-1),(j,i+1)]:
        if 0<=jj<N and 0<=ii<N and not solid[jj,ii] and not outside[jj,ii]:outside[jj,ii]=True;queue.append((jj,ii))
outer=~outside
mouth=((u-.5)/.115)**2+((v-.605)/.125)**2<1
front=outer&~mouth
sv=[];sf=[];suv=[];front_ids={}
for mask,ids,back in [(front,front_ids,False)]:
    for j,i in np.argwhere(mask):
        x=(i/(N-1)-.5)*.082;z=(.5-j/(N-1))*.09
        ids[(int(j),int(i))]=len(sv)
        sv.append(tiger((x,front_y(x,z),z)))
    for j in range(N-1):
        for i in range(N-1):
            for points in [[(j,i),(j,i+1),(j+1,i+1)],[(j,i),(j+1,i+1),(j+1,i)]]:
                if all(k in ids for k in points):
                    face=[ids[k] for k in points];coords=[(k[1]/(N-1),1-k[0]/(N-1)) for k in points]
                    if back:face.reverse();coords.reverse()
                    sf.append(face);suv.append(coords)
    if not back:front_faces=len(sf)
edges=Counter()
for f in sf[:front_faces]:
    for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((a,b)))]+=1
inverse={id:key for key,id in front_ids.items()};inner=[];outer_edges=[]
for (a,b),count in edges.items():
    if count!=1:continue
    ka,kb=inverse[a],inverse[b]
    # The nearest outer boundary is far outside the authored mouth oval.
    mid=((ka[1]+kb[1])/(2*(N-1)),(ka[0]+kb[0])/(2*(N-1)))
    if ((mid[0]-.5)/.16)**2+((mid[1]-.605)/.17)**2<1.08:inner.append((a,b))
    else:outer_edges.append((a,b))
outer_adj={}
for a,b in outer_edges:outer_adj.setdefault(a,[]).append(b);outer_adj.setdefault(b,[]).append(a)
# Relax subpixel contour stair steps without changing the authored fur outline.
for iteration in range(8):
    changes={}
    for a,neighbors in outer_adj.items():
        p=Vector(sv[a]);q=sum((Vector(sv[b]) for b in neighbors),Vector())/len(neighbors)
        changes[a]=p*.62+q*.38
    for a,p in changes.items():sv[a]=p
start=max(outer_adj,key=lambda a:sv[a][0]);ordered_outer=[start];prev=None;cur=start
while True:
    neighbors=[b for b in outer_adj[cur] if b!=prev]
    nxt=(max(neighbors,key=lambda a:sv[a][1]) if prev is None else neighbors[0])
    if nxt==start:break
    ordered_outer.append(nxt);prev,cur=cur,nxt
distance=[0.]
for a,b in zip(ordered_outer,ordered_outer[1:]):distance.append(distance[-1]+(Vector(sv[b])-Vector(sv[a])).length)
total=distance[-1]+(Vector(sv[ordered_outer[-1]])-Vector(sv[start])).length
theta_start=math.atan2(sv[start][1]/SKULL_RX,(sv[start][0]-.002-SKULL_CZ)/SKULL_RZ)
direction=1 if sv[ordered_outer[1]][1]>sv[start][1] else -1
natural=np.unwrap([math.atan2(sv[a][1]/SKULL_RX,(sv[a][0]-.002-SKULL_CZ)/SKULL_RZ) for a in ordered_outer])
progress=np.clip(np.maximum.accumulate(direction*(natural-theta_start)),0,math.tau)
# Follow the actual angular position; a small arclength term keeps every
# interval positive around undercut curls without shifting the whole cheek.
phase=.98*progress+.02*np.asarray(distance)/total*math.tau
shell_angles={a:theta_start+direction*s for a,s in zip(ordered_outer,phase)}
shell_betas={}
for a in ordered_outer:
    radius=math.hypot(sv[a][1]/SKULL_RX,(sv[a][0]-.002-SKULL_CZ)/SKULL_RZ)
    shell_betas[a]=-math.acos(min(1.,radius))
outer_edges=list(zip(ordered_outer,ordered_outer[1:]+ordered_outer[:1]))
outer_layers=[{a:a for a in outer_adj}]
# Keep the approved face; its irregular hair outline blends into a genuinely
# rounded skull, instead of extruding every front-side fur valley backwards.
LAYERS=112
for layer in range(1,LAYERS):
    t=layer/LAYERS;ids={}
    for a in outer_adj:
        p=Vector(sv[a]);artist=Vector((p.y,HEAD_LOCAL_Z-p.z,p.x-.002))
        theta=shell_angles[a]
        beta=shell_betas[a]+(math.pi/2-shell_betas[a])*t
        bv=(beta+math.pi/2)/math.pi
        base=skull(theta,shell_betas[a])
        raised=float(body_height(np.asarray(theta/math.tau+.5),np.asarray(bv)))*float(smooth(.015,.08,np.asarray(t)))*(1-float(smooth(.93,.995,np.asarray(bv))))
        point=skull(theta,beta,raised)
        blend=(1-float(smooth(0,.055,np.asarray(t))))
        point+=(artist-base)*blend
        point=tiger(point)
        ids[a]=len(sv);sv.append(point)
    outer_layers.append(ids)
rear_pole=len(sv);sv.append(tiger((0,SKULL_CY-SKULL_RY,SKULL_CZ)))
for a,b in outer_edges:
    ua=(shell_angles[a]/math.tau+.5)%1
    ub=(shell_angles[b]/math.tau+.5)%1
    if abs(ua-ub)>.5:
        if ua<ub:ua+=1
        else:ub+=1
    for layer in range(LAYERS-1):
        lower,upper=outer_layers[layer],outer_layers[layer+1]
        sf.append([lower[a],lower[b],upper[b],upper[a]])
        va=1-(shell_betas[a]+(math.pi/2-shell_betas[a])*layer/LAYERS+math.pi/2)/math.pi
        vb=1-(shell_betas[b]+(math.pi/2-shell_betas[b])*layer/LAYERS+math.pi/2)/math.pi
        van=1-(shell_betas[a]+(math.pi/2-shell_betas[a])*(layer+1)/LAYERS+math.pi/2)/math.pi
        vbn=1-(shell_betas[b]+(math.pi/2-shell_betas[b])*(layer+1)/LAYERS+math.pi/2)/math.pi
        suv.append([(ua,va),(ub,vb),(ub,vbn),(ua,van)])
    sf.append([outer_layers[-1][a],outer_layers[-1][b],rear_pole])
    suv.append([(ua,1/LAYERS),(ub,1/LAYERS),((ua+ub)/2,0)])
outer_front_count=len(sf)
face_start=len(F)
add(sv,sf,suv,mat=0)
for i in range(face_start+front_faces,len(F)):MI[i]=4
# Mouth wall has exact lip vertices and finite dark inner depth; no unsealed hole.
adj={}
for a,b in inner:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
first=next(iter(adj));ordered=[first];previous=None;current=first
while True:
    nxt=next(x for x in adj[current] if x!=previous)
    if nxt==first:break
    ordered.append(nxt);previous,current=current,nxt
base_offset=len(V)-len(sv)
rounded_skin_indices=[]
skin_ids=[base_offset+i for i in ordered]
last=skin_ids
for step in range(1,11):
    t=step/10;ids=[]
    for id in ordered:
        j,i=inverse[id];x=(i/(N-1)-.5)*.082;z=(.5-j/(N-1))*.09
        cz=(.5-.605)*.09;x*=1-.70*t;z=cz+(z-cz)*(1-.70*t)
        yy=front_y((i/(N-1)-.5)*.082,(.5-j/(N-1))*.09)*(1-t)-.007*t
        ids.append(len(V));V.append(tuple(tiger((x,yy,z))))
    for k in range(len(last)):
        kk=(k+1)%len(last);F.append([last[k],last[kk],ids[kk],ids[k]]);MI.append(3);SM.append(True)
        UV.append([(k/len(last),(step-1)/11),((k+1)/len(last),(step-1)/11),((k+1)/len(last),step/11),(k/len(last),step/11)])
    last=ids
center_id=len(V);V.append(tuple(tiger((0,-.007,(.5-.605)*.09))))
for k in range(len(last)):
    kk=(k+1)%len(last);F.append([last[k],last[kk],center_id]);MI.append(3);SM.append(True)
    UV.append([(.5+.45*math.cos(2*math.pi*k/len(last)),.5+.45*math.sin(2*math.pi*k/len(last))),
               (.5+.45*math.cos(2*math.pi*(k+1)/len(last)),.5+.45*math.sin(2*math.pi*(k+1)/len(last))),(.5,.5)])

# Anatomical accents extend out of the relief skin, providing real side silhouette.
for iteration in range(5):
    relaxed=[Vector(V[a])*.55+(Vector(V[skin_ids[(i-1)%len(skin_ids)]])+Vector(V[skin_ids[(i+1)%len(skin_ids)]]))*.225 for i,a in enumerate(skin_ids)]
    for a,p in zip(skin_ids,relaxed):V[a]=tuple(p)
tube([Vector(V[a])+Vector((0,0,-.00008)) for a in skin_ids],.00048,closed=True,nr=12)
for sign in [-1,1]:
    ex=sign*.0126;ez=.0176;ey=front_y(ex,ez)+.0005
    eye_ring=[(ex+.0039*math.cos(a),ey,ez+.00235*math.sin(a)+sign*.00065*math.cos(a)) for a in np.linspace(0,2*math.pi,80,endpoint=False)]
    tube(eye_ring,.00048,closed=True,transform=tiger)
    ellipsoid((ex,ey+.00055,ez),(.0030,.00115,.00185),mat=2,segments=40,rings=20)
    ellipsoid((ex,ey+.00164,ez),(.00063,.00019,.00063),mat=3,segments=24,rings=12)
    lid=[]
    for a in np.linspace(0,math.pi,70):
        xx=ex+.00415*math.cos(a);zz=ez+.00175*math.sin(a)+sign*.0008*math.cos(a)
        lid.append((xx,front_y(xx,zz)+.00025,zz))
    tube(lid,.00062,transform=tiger,nr=14)
    # Two long upper canines and two shorter rising lower canines.
    for lower in [False,True]:
        x=sign*(.0113 if not lower else .0098);z=.0003 if not lower else -.0208
        pts=[];rad=[]
        for t in np.linspace(0,1,28):
            pts.append((x-sign*.0016*t,front_y(x,z)+.0001+.0025*math.sin(t*math.pi),z+(.0055 if lower else -.0145)*t))
            rad.append((.00145 if lower else .00175)*(1-t)**.78+.00008)
        tube(pts,rad,mat=1,nr=20,transform=tiger)
    # Rounded muzzle lobes merge into the driven skin, with small metal whisker pits.
    for k in range(7):
        x=sign*(.005+.00125*k);z=.006-.0021*(k%3)
        ellipsoid((x,front_y(x,z)+.00004,z),(.00038,.00023,.00030),mat=3,segments=12,rings=8)
for lower in [False,True]:
    for k in range(7):
        x=(k-3)*.0021;z=-.0196 if lower else .0000
        yy=front_y(x,z)+.0001
        length=.0027+.00065*abs(k-3)/3
        pts=[(x,yy,z),(x,yy+.0008,z+length*.6*(1 if lower else -1)),(x,yy+.0011,z+length*(1 if lower else -1))]
        tube(pts,[.00082,.00066,.00024],nr=14,transform=tiger)
ellipsoid((0,.020,-.017),(.009,.006,.0030),mat=3,segments=36,rings=20)

# Rounded triangular nose stands proud of the sculpted muzzle.
triangle=[]
anchors=[(-.006,.011),(-.003,.012),(0,.011),(.003,.012),(.006,.011),(.005,.006),(0,.002),(-.005,.006)]
for i,p in enumerate(anchors):
    a=Vector(anchors[i-1]);b=Vector(p);c=Vector(anchors[(i+1)%len(anchors)]);d=Vector(anchors[(i+2)%len(anchors)])
    for t in np.linspace(0,1,10,endpoint=False):
        q=.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)
        triangle.append(q)
nose_base=front_y(0,.008)
loft([[tiger((p.x*scale*.80,nose_base+y,.008+(p.y-.008)*scale*.70)) for p in triangle]
      for y,scale in [(-.0015,1),(0,1.04),(.0023,.94),(.0036,.68),(.0043,.30),(.0045,.03)]])
for side in [-1,1]:
    ellipsoid((side*.0029,nose_base+.0027,.0069),(.0010,.00035,.00052),mat=3,segments=28,rings=14)

# Reference-driven whole-head warp: shared seams, mouth walls, teeth and inset
# gems receive the same continuous field. The native mount and ring are excluded.
def curve(values, xs, ys):
    xs=np.asarray(xs);ys=np.asarray(ys);sec=np.diff(ys)/np.diff(xs)
    slopes=np.r_[sec[0],2*sec[:-1]*sec[1:]/(sec[:-1]+sec[1:]),sec[-1]]
    ix=np.clip(np.searchsorted(xs,values)-1,0,len(xs)-2)
    width=xs[ix+1]-xs[ix];t=np.clip((values-xs[ix])/width,0,1)
    return (2*t**3-3*t*t+1)*ys[ix]+(t**3-2*t*t+t)*width*slopes[ix]+(-2*t**3+3*t*t)*ys[ix+1]+(t**3-t*t)*width*slopes[ix+1]

h=np.asarray(V[head_vertex_start:],dtype=float)
x=h[:,1].copy();y=HEAD_LOCAL_Z-h[:,2];z=h[:,0]-.002
front_weight=smooth(.004,.030,y)
mouth_band=np.exp(-((z+.008)/.019)**4)
abs_x=np.abs(x)
expanded=curve(abs_x,[0,.006,.0126,.018,.027,.035,.050],[0,.0080,.0163,.0221,.0300,.0357,.0460])
wide_mouth=curve(abs_x,[0,.006,.0126,.018,.027,.035,.050],[0,.0094,.0180,.0232,.0300,.0357,.0460])
expanded=expanded+(wide_mouth-expanded)*mouth_band
xx=x*.94+(np.sign(x)*expanded-x*.94)*front_weight
# The reference's larger gape carries both tooth rows, sockets and nose with it.
front_z=curve(z,[-.060,-.045,-.034,-.026,-.0196,-.0095,0,.009,.0176,.029,.044,.060],
                [-.051,-.043,-.037,-.033,-.027,-.011,.005,.0165,.024,.035,.044,.060])
zz=z+(front_z-z)*front_weight
# Lift the rear underside into a round belly; only the forward beard is pointed.
low=smooth(.014,.042,-z)
zz+=.0080*low*(1-smooth(0,.018,y))
# Broad lateral skull is softened; the beard and mandibular corners gather forward.
xx*=1-.11*low*(1-.25*front_weight)
yy=y+.024*low*(1-smooth(.031,.052,y))
# Side reference has a forward cheek/jaw, not a flat face on a pointed ball.
yy+=front_weight*(.0048*np.exp(-((abs_x-.024)/.012)**2-((z+.006)/.029)**2)
                  +.0048*np.exp(-(x/.020)**2-((z+.022)/.011)**2))
h[:,0]=zz+.002;h[:,1]=xx;h[:,2]=HEAD_LOCAL_Z-yy
V[head_vertex_start:]=[tuple(v) for v in h]
print('V5_REFERENCE_HEAD_AND_ANATOMY_AUTHORED',flush=True)

# Taller continuous domed crown with a broad lower ruby belt. Crown is authored
# in final coordinates, so raising brows cannot flatten the crown or shift gems.
helmet=[]
for z,r in dense_profile([(.0305,.0290),(.032,.0300),(.033,.0300),(.034,.0290),(.039,.0276),(.040,.0278),(.041,.0265),(.044,.0240),(.047,.0208),(.050,.0165),(.052,.0120),(.0536,.0070),(.0543,.0020)],spacing=.00028):
    ring=[]
    for k,a in enumerate(np.linspace(0,2*math.pi,160,endpoint=False)):
        hh=float(body_height(np.asarray(k/160),np.asarray((z-.0305)/.024)))*.20
        ring.append(tiger(((r+hh)*math.cos(a),.001+(r+hh)*.88*math.sin(a),z)))
    helmet.append(ring)
loft(helmet,mat=4)
for z,r in [(.0323,.0301),(.034,.0291),(.0396,.0280),(.044,.0241),(.050,.0166),(.0535,.0073)]:
    tube([(r*math.cos(a),.001+r*.88*math.sin(a),z) for a in np.linspace(0,2*math.pi,144,endpoint=False)],.00055,closed=True,transform=tiger)
ellipsoid((0,.001,.0553),(.0026,.0024,.0017),segments=36,rings=18)
for a in np.linspace(0,2*math.pi,24,endpoint=False):
    x=.0284*math.cos(a);y=.001+.0284*.88*math.sin(a);z=.0367
    ellipsoid((x,y,z),(.0011,.0011,.0011),mat=2,segments=20,rings=12)
    tube([(x+.0014*math.cos(q)*math.cos(a),y+.0014*math.cos(q)*math.sin(a),z+.0014*math.sin(q))
          for q in np.linspace(0,2*math.pi,40,endpoint=False)],.00035,closed=True,transform=tiger,nr=8)

# The head deformation precedes the separately rebuilt crown. The mounting
# seat and tail ring were authored before head_vertex_start and stay unchanged.

head_height_cm=(max(p[0] for p in V[head_vertex_start:])-min(p[0] for p in V[head_vertex_start:]))*100

mesh=bpy.data.meshes.new(NAME);mesh.from_pydata(V,[],F);mesh.update()
for family,name in zip(FAMILIES,MATS):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;nt=mat.node_tree
    bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    for key in ['BaseColor','ORM','Normal']:
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(BASE/'Textures'/f'TangDao_TigerPommel_{family}_{key}.png'))
        if key!='BaseColor':tex.image.colorspace_settings.name='Non-Color'
        if key=='BaseColor':nt.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif key=='ORM':
            sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex.outputs['Color'],sep.inputs[0])
            nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
        else:
            nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
    mesh.materials.append(mat)
layer=mesh.uv_layers.new(name='UVMap')
for p,uv,mat,sm in zip(mesh.polygons,UV,MI,SM):
    p.material_index=mat;p.use_smooth=sm
    for li,co in zip(p.loop_indices,uv):layer.data[li].uv=co
obj=bpy.data.objects.new(NAME+'_LOD0',mesh);bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
mesh=obj.data
bm=bmesh.new();bm.from_mesh(mesh)
# Exact seam welds also collapse sphere poles; no broad remeshing of the sculpt.
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
group=bpy.data.objects.new(NAME+'_LODGroup',None);group['fbx_type']='LodGroup';bpy.context.collection.objects.link(group);obj.parent=group
lods=[obj]
for level,ratio in [(1,.52),(2,.22)]:
    lod=obj.copy();lod.data=obj.data.copy();lod.name=NAME+'_LOD'+str(level);bpy.context.collection.objects.link(lod)
    bpy.context.view_layer.objects.active=lod
    dec=lod.modifiers.new('Sculpt distance LOD','DECIMATE');dec.ratio=ratio;dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
    lods.append(lod)
bpy.ops.object.select_all(action='DESELECT');group.select_set(True)
for o in lods:o.select_set(True)
bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(NAME+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(P/'Export'/(NAME+'.glb')),use_selection=True,export_format='GLB')
for o in lods[1:]:o.hide_set(True);o.hide_render=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'TangDao_TigerPommel_Editable.blend'))
counts=[]
for o in lods:o.data.calc_loop_triangles();counts.append(len(o.data.loop_triangles))
m=json.loads((BASE/'pommel_manifest.json').read_text(encoding='utf-8-sig'))
m.update(ue_root=UE,mesh_name=NAME,mesh=UE+'/Meshes/'+NAME+'.'+NAME,
         source_revision='SilhouetteV5',revision='TangDaoTigerPommelSilhouetteV5_20261003',
         face_revision='ReferenceProportionsV5_20261003',chin_revision='ForwardMandibleV5_20261003',
         head_core_shape='rounded lifted rear belly; forward jaw and localized pointed beard',
         head_width_cm=round((max(v[1] for v in V[head_vertex_start:])-min(v[1] for v in V[head_vertex_start:]))*100,3),
         head_height_with_crown_cm=round(head_height_cm,3),
         length_cm=round((max(v[2] for v in V)-min(v[2] for v in V))*100,3),lod_triangles=counts,
         runtime_tested=False,visual_acceptance=False,
         appearance='较高的穹顶红石冠带、宽张虎口与外展虎目、前探的双颊和下颌、圆厚后脑与局部尖收虎须，保留云环及分层云纹接座。')
m.pop('head_core_diameter_cm',None)
m['chin_shape']={'rear_belly_lift_mm':8,'lower_core_forward_shift_mm':24,'global_conical_taper':False,'uv_preserved':True,'mount_and_ring_preserved':True}
m['connector_shape']['head_shape_preserved']=False
m['face_anatomy'].update(eye_center_spacing_mm=32.6,mouth_height_design_mm=32,
                         upper_canine_height_mm=None,lower_canine_height_mm=None,
                         tooth_shape='same continuous gape deformation as mouth rim and bowl',
                         eye_socket_depth_mm=None,
                         nose_shape='original triangular nose carried with broader muzzle field')
m['features']=['参考正面的宽张虎口与分离牙列','外展虎目和连续双颊','前探下颌、局部尖收虎须与抬高的圆厚后底壳','加高穹顶及红石冠带','沿用六组PBR、完整真实安装端与云环','三层距离LOD']
m['reference_shape']={'reference':'../Reference/TigerPommel_Reference.png','front_ornament':'../Ornament/TigerFace_HeightSource.png','policy':'front and side define overall form; retain existing ornament vocabulary; hidden areas inferred','crown_height_mm':26.5,'crown_base_diameter_mm':60,'side_reference_registration':'same mount, pivot, and crown-up axis; no whole-attachment scaling'}
(P/'pommel_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('TIGER_POMMEL_V5_AUTHORED '+str(counts),flush=True)
