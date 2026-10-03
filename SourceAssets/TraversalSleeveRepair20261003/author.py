"""Rebuild traversal chainmail above the cuff from its native V7 arm surface.

Run with Blender in background. Keep original metal rings, cuff binding, UVs,
normals and sway colours below the 13 cm cuff interface. No rendering.
"""
import copy, json, math
from pathlib import Path
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
def unit(a):return a/max(float(np.linalg.norm(a)),1e-10)
def weights(w):
    pairs=sorted(((k,float(v)) for k,v in w.items() if v>1e-8),key=lambda x:-x[1])[:8]
    den=sum(v for _,v in pairs)
    return {k:v/den for k,v in pairs}
def blend(a,b,t):return weights({k:a.get(k,0)*(1-t)+b.get(k,0)*t for k in a.keys()|b.keys()})
def normals(p,f):
    n=np.zeros_like(p);tn=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    for k in range(3):np.add.at(n,f[:,k],tn)
    return n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-10)
def side_of(w):return max(('l','r'),key=lambda s:sum(v for k,v in w.items() if k.endswith('_'+s)))
def loops(bm):
    edges={e for e in bm.edges if e.is_boundary};result=[]
    while edges:
        edge=edges.pop();start,current=edge.verts;row=[start,current]
        while current!=start:
            following=[e for e in current.link_edges if e in edges]
            if not following:raise RuntimeError('Open boundary in authoring input')
            edge=following[0];edges.remove(edge);current=edge.other_vert(current)
            if current!=start:row.append(current)
        result.append(row)
    return result

skin=read(R/'Before/skin.json');saved=read(R/'Before/ue_chainmail_shirt.json')
old=read(P/'SourceAssets/ChainmailInsetBinding20260929/Authored/Traversal.json')
mask=read(P/'SourceAssets/ChainmailSharedSway20260929/Masks/Traversal.json')['colors']
# Match the actual saved source before reusing its UV-rich editable input.
current=KDTree(len(saved['positions']))
for i,p in enumerate(saved['positions']):current.insert(Vector(p),i)
current.balance()
if any(current.find(Vector(p))[2]>.002 for p in old['positions']):
    raise RuntimeError('Current chainmail differs from the cuff authoring source')
names=sorted(skin['rest'])
d=dict(profile='Traversal',binding_source=skin['source'],positions=[],weights=[],triangles=[],
       normals=[],uv=[],colors=[],triangle_materials=[],rest=skin['rest'],
       contract='Native V7 shoulder/elbow surface; open shoulder annulus; paired shell weights; original interlaced cuff and shared sway; full paired LOD topology')
report={'old_asset':saved['source'],'old_sha256':saved['asset_sha256'],'arms':{},'runtime_tested':False}
fresh=[]

def vertex(p,w,color=(0,0,0,1)):
    i=len(d['positions']);d['positions'].append(list(map(float,p)));d['weights'].append(copy.deepcopy(w));d['colors'].append(list(color));return i
def face(row,mat,uv,ns=None):
    i=len(d['triangles']);d['triangles'].append(row);d['triangle_materials'].append(mat);d['uv'].append(np.asarray(uv).tolist())
    d['normals'].append(ns or [[0.,0.,0.]]*3)
    if ns is None:fresh.append(i)

for side in ('l','r'):
    a,e,w=[np.array(skin['rest'][bone+'_'+side]['p']) for bone in ['upperarm','lowerarm','hand']]
    upper=unit(e-a);axis=unit(w-e);seed=unit(np.cross(upper,axis));cross=unit(np.cross(axis,seed))
    def angle(p):
        q=np.asarray(p)-w;return math.atan2(float(q@cross),float(q@seed))%(2*math.pi)
    def uv(p):
        q=np.asarray(p)-e;t=np.clip(((q@axis)+4)/8,0,1);t=t*t*(3-2*t)
        longitudinal=unit(upper*(1-t)+axis*t);radial=np.cross(longitudinal,seed)
        return [math.atan2(float(q@radial),float(q@seed))/(2*math.pi)*1.5,
                (np.linalg.norm(e-a)+q@longitudinal)/25]
    def newface(row,mat,out=None):
        points=np.array([d['positions'][i] for i in row])
        if out is not None and np.dot(np.cross(points[1]-points[0],points[2]-points[0]),out)>0:row=row[::-1]
        tex=np.array([uv(d['positions'][i]) for i in row])
        if np.ptp(tex[:,0])>.75:tex[tex[:,0]<0,0]+=1.5
        face(row,mat,tex)

    # Keep the native joint topology and weights, remove torso-facing geometry.
    bm=bmesh.new();dw=bm.verts.layers.deform.verify()
    fs=[f for f,m in zip(skin['triangles'],skin['materials']) if m in (0,1,3) and all(side_of(skin['weights'][i])==side for i in f)]
    ids=sorted({i for f in fs for i in f});vs={i:bm.verts.new(skin['positions'][i]) for i in ids}
    for i,v in vs.items():
        for n,value in skin['weights'][i].items():v[dw][names.index(n)]=value
    for f in fs:bm.faces.new([vs[i] for i in f])
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
    for point,normal,inside,outside in [(a+upper,upper,True,False),(w-axis*18,axis,False,True)]:
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=Vector(point),plane_no=Vector(normal),dist=.00001,clear_inner=inside,clear_outer=outside)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
    p=np.array([v.co[:] for v in bm.verts]);f=np.array([[v.index for v in face.verts] for face in bm.faces]);n=normals(p,f)
    ws=[weights({names[k]:v for k,v in pt[dw].items()}) for pt in bm.verts]
    rings=loops(bm)
    shoulder=sorted(rings,key=lambda r:np.mean([(np.array(v.co)-a)@upper for v in r]))[:1]
    ends=[ring for ring in rings if np.mean([(np.array(v.co)-w)@axis for v in ring])>-19.]
    if len(shoulder)!=1 or len(ends)!=1 or len(rings)!=2:
        raise RuntimeError('Native openings '+side+' '+str([(len(r),float(np.mean([(np.array(v.co)-a)@upper for v in r])),float(np.mean([(np.array(v.co)-w)@axis for v in r]))) for r in rings]))
    oi=[vertex(pt+nn*.65,wt) for pt,nn,wt in zip(p,n,ws)]
    ii=[vertex(pt+nn*.45,wt) for pt,nn,wt in zip(p,n,ws)]
    for row in f:
        newface([oi[i] for i in row],0)
        newface([ii[i] for i in row[::-1]],2)
    # Only the thickness annulus at the shoulder; no cap across the arm opening.
    for edge in bm.edges:
        if not edge.is_boundary or not all(v in shoulder[0] for v in edge.verts):continue
        loop=edge.link_loops[0];x,y=loop.vert.index,loop.link_loop_next.vert.index
        newface([oi[y],oi[x],ii[x]],2);newface([oi[y],ii[x],ii[y]],2)
    new_outer=[oi[v.index] for v in ends[0]];new_inner=[ii[v.index] for v in ends[0]]
    bm.free()

    # The cuff keeps its authored three material sections and physical rings.
    bm=bmesh.new();dw=bm.verts.layers.deform.verify();cc=bm.verts.layers.float_color.new('sway')
    tex=bm.loops.layers.uv.new('mail_uv');normal_layer=bm.loops.layers.float_vector.new('normal')
    fs=[(j,f) for j,f in enumerate(old['triangles']) if all(side_of(old['weights'][i])==side for i in f)]
    ids=sorted({i for _,f in fs for i in f});vs={i:bm.verts.new(old['positions'][i]) for i in ids}
    for i,v in vs.items():
        v[cc]=mask[i]
        for name,value in old['weights'][i].items():v[dw][names.index(name)]=value
    for j,row in fs:
        fi=bm.faces.new([vs[i] for i in row]);fi.material_index=old['triangle_materials'][j]
        for k,loop in enumerate(fi.loops):loop[tex].uv=old['uv'][j][k];loop[normal_layer]=old['normals'][j][k]
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=Vector(w-axis*13),plane_no=Vector(axis),dist=.00001,clear_inner=True,clear_outer=False)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
    rings=[r for r in loops(bm) if abs(np.mean([(np.array(v.co)-w)@axis for v in r])+13)<.02]
    if len(rings)!=2:raise RuntimeError('Expected paired cuff interface '+side+': '+str(len(rings)))
    rings.sort(key=lambda r:np.mean([np.linalg.norm((np.array(v.co)-w)-axis*((np.array(v.co)-w)@axis)) for v in r]),reverse=True)
    mapping={v.index:vertex(v.co,weights({names[k]:value for k,value in v[dw].items()}),v[cc]) for v in bm.verts}
    for fi in bm.faces:
        face([mapping[v.index] for v in fi.verts],fi.material_index,[list(l[tex].uv) for l in fi.loops],
             [unit(np.array(l[normal_layer])).tolist() for l in fi.loops])
    old_outer=[mapping[v.index] for v in rings[0]];old_inner=[mapping[v.index] for v in rings[1]]
    bm.free()

    def ordered(r):return sorted(r,key=lambda i:angle(d['positions'][i]))
    def sample(r,t):
        r=ordered(r);angles=np.array([angle(d['positions'][i]) for i in r]);j=int(np.searchsorted(angles,t))
        left=(j-1)%len(r);right=j%len(r);lo=angles[left];hi=angles[right]
        if left==len(r)-1:lo-=2*math.pi
        if right==0:hi+=2*math.pi;lo+=2*math.pi
        if t<lo:t+=2*math.pi
        z=(t-lo)/(hi-lo)
        return (np.array(d['positions'][r[left]])*(1-z)+np.array(d['positions'][r[right]])*z,
                blend(d['weights'][r[left]],d['weights'][r[right]],z))
    def connect(r1,r2,mat):
        r1=ordered(r1);r2=ordered(r2);i=j=0
        angles1=[angle(d['positions'][k]) for k in r1]+[angle(d['positions'][r1[0]])+2*math.pi]
        angles2=[angle(d['positions'][k]) for k in r2]+[angle(d['positions'][r2[0]])+2*math.pi]
        while i<len(r1) or j<len(r2):
            if j==len(r2) or (i<len(r1) and angles1[i+1]<angles2[j+1]):
                row=[r1[i%len(r1)],r1[(i+1)%len(r1)],r2[j%len(r2)]];i+=1
            else:
                row=[r1[i%len(r1)],r2[(j+1)%len(r2)],r2[j%len(r2)]];j+=1
            mid=np.mean([d['positions'][k] for k in row],axis=0)-w;out=unit(mid-axis*(mid@axis))
            newface(row,mat,out if mat==0 else -out)
    # Five centimetres of paired, fine rings join the two sources continuously.
    # Each inner/outer pair receives one shared interpolated weight field.
    outer=new_outer;inner=new_inner
    for step in range(1,5):
        t=step/5.;next_outer=[];next_inner=[]
        for theta in np.linspace(0,2*math.pi,96,endpoint=False):
            no,nw=sample(new_outer,theta);ni,_=sample(new_inner,theta)
            oo,ow=sample(old_outer,theta);oi,_=sample(old_inner,theta)
            wt=blend(nw,ow,t)
            next_outer.append(vertex(no*(1-t)+oo*t,wt));next_inner.append(vertex(ni*(1-t)+oi*t,wt))
        connect(outer,next_outer,0);connect(inner,next_inner,2);outer,inner=next_outer,next_inner
    connect(outer,old_outer,0);connect(inner,old_inner,2)
    report['arms'][side]={'native_surface_vertices':len(p),'native_surface_triangles':len(f),
                          'cuff_retained_from_cm':13,'transition_start_cm':18,'shoulder_trim_cm':1,
                          'outer_clearance_cm':.65,'thickness_cm':.20}

v=np.array(d['positions']);f=np.array(d['triangles']);ns=normals(v,f)
for i in fresh:d['normals'][i]=ns[f[i]].tolist()
write(R/'authored.json',d)
report.update(vertices=len(v),triangles=len(f),paired_lod_ratios=[1.,1.,1.])
write(R/'authoring.json',report)
print('TRAVERSAL_CHAINMAIL_AUTHORED',len(v),len(f),flush=True)
