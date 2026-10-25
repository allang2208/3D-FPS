"""Append fitted construction details without changing the accepted garment shells."""
import bpy,json,sys,math,copy
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6LowerDetail20261024'
sys.path.insert(0,str(P/'Tools/ST6LowerSet'));import geometry as g
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')

class Surface:
    def __init__(self,d,prefix=None):
        self.d=d;self.points=np.array(d['positions']);faces=np.array(d['triangles'],int)
        if prefix:
            mask=np.zeros(len(self.points),bool)
            for part in d['parts']:
                if part['name'].startswith(prefix):mask[part['first_vertex']:part['first_vertex']+part['vertices']]=True
            faces=faces[np.all(mask[faces],axis=1)]
        if not len(faces):raise RuntimeError('Missing source panel '+str(prefix))
        self.faces=faces[:,::-1];self.tree=BVHTree.FromPolygons(self.points.tolist(),self.faces.tolist(),all_triangles=True)
        pts=self.points[np.unique(faces)];self.lo=pts.min(0);self.hi=pts.max(0)
    def nearest(self,p):
        q,n,idx,_=self.tree.find_nearest(Vector(p));ids=self.faces[idx];a,b,c=self.points[ids];v0=b-a;v1=c-a;v2=np.array(q)-a
        den=(v0@v0)*(v1@v1)-(v0@v1)**2
        if abs(den)<1e-14:w=np.array([1.,0,0])
        else:
            v=((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/den;z=((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/den
            w=np.maximum([1-v-z,v,z],0);w/=w.sum()
        return np.array(q),np.array(n),ids,w
    def project(self,p,off=.05):
        q,n,_,_=self.nearest(p);return q+n*off
    def weights(self,p):
        _,_,ids,ws=self.nearest(p);out={}
        for vi,factor in zip(ids,ws):
            for bi,w in self.d['weights'][vi]:out[bi]=out.get(bi,0)+factor*w
        out=sorted(out.items(),key=lambda t:-t[1])[:8];total=sum(w for _,w in out)
        return [[int(i),float(w/total)] for i,w in out if w>1e-7]

def patch(name,fn,nu,nv,side,slot,thickness=.06):
    points=[fn(u,v) for v in np.linspace(0,1,nv+1) for u in np.linspace(0,1,nu+1)];faces=[]
    for y in range(nv):
        for x in range(nu):a=y*(nu+1)+x;faces.append([a,a+1,a+nu+2,a+nu+1])
    return g.mesh_object(name,points,faces,side,'flex',slot,thickness,.018)

def stitches(name,path,surface,side,spacing=.46,length=.24):
    path=np.asarray(path);dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    points=[];faces=[]
    def at(t):
        i=min(len(path)-2,max(0,np.searchsorted(dist,t)-1));f=(t-dist[i])/max(dist[i+1]-dist[i],1e-8)
        p=path[i]*(1-f)+path[i+1]*f;_,n,_,_=surface.nearest(p);return p,n
    for t in np.arange(.08,dist[-1]-length,spacing):
        row=[];ns=[]
        for j in range(3):
            p,n=at(t+length*j/2);row.append(p+n*(.016+.025*math.sin(math.pi*j/2)));ns.append(n)
        start=len(points)
        for j,p in enumerate(row):
            tangent=g.unit(row[min(j+1,2)]-row[max(0,j-1)]);a=g.unit(np.cross(tangent,ns[j]));b=np.cross(tangent,a)
            points.extend(p+.021*(math.cos(v)*a+math.sin(v)*b) for v in np.linspace(0,math.tau,4,endpoint=False))
        for j in range(2):
            for k in range(4):faces.append([start+j*4+k,start+j*4+(k+1)%4,start+(j+1)*4+(k+1)%4,start+(j+1)*4+k])
    if points:g.mesh_object(name,points,faces,side,'flex',3)

def bartack(name,center,axis,surface,side):
    axis=g.unit(axis)
    for i in range(7):
        p=np.array(center)+axis*(i-3)*.075;_,n,_,_=surface.nearest(p);cross=g.unit(np.cross(n,axis))
        line=[surface.project(p+cross*x,.07+.025*math.sin(t*math.pi)) for x,t in zip(np.linspace(-.26,.26,5),np.linspace(0,1,5))]
        g.tube(name+'_'+str(i),line,.024,side,'flex',3,False,4)

def author_pants(d):
    for side,sign in [('l',1),('r',-1)]:
        cargo=Surface(d,'Flat_CargoPocket_'+side);flap=Surface(d,'Cargo_PocketFlap_'+side)
        x=(cargo.hi[0]+.7) if sign>0 else cargo.lo[0]-.7;ymid=(cargo.lo[1]+cargo.hi[1])*.5
        # Two narrow expansion folds sit on the existing pocket, below the waist interface.
        for i,y in enumerate([ymid-1.7,ymid+1.7]):
            def fold(u,v,y=y):
                p=cargo.project([x,y+(u-.5)*.46,58.1+10*v],.025)
                return p+np.array([sign*.12*math.sin(math.pi*u)*math.sin(math.pi*v),0,0])
            patch('Cargo_ExpansionFold_'+side+'_'+str(i),fold,6,26,side,1,.055)
            stitches('Cargo_FoldEdge_'+side+'_'+str(i),[fold(.08,v) for v in np.linspace(.02,.98,60)],cargo,side)
        z=flap.lo[2]+.85
        for i,f in enumerate([.25,.75]):
            y=flap.lo[1]+(flap.hi[1]-flap.lo[1])*f;q=flap.project([x,y,z],.10)
            g.rivet('Recessed_FlapSnap_'+side+'_'+str(i),q,[sign,0,0],side,'flex',.25)
        for i,(f,z) in enumerate([(.08,58),(.92,58),(.08,69.4),(.92,69.4)]):
            p=cargo.project([x,cargo.lo[1]+np.ptp([cargo.lo[1],cargo.hi[1]])*f,z],.03)
            bartack('Pocket_BarTack_'+side+'_'+str(i),p,[0,1,0],cargo,side)
        knee=Surface(d,'Rounded_HardKnee_'+side);cx=(knee.lo[0]+knee.hi[0])*.5
        for i,z in enumerate([44.1,46.3,48.5,50.7]):
            line=[knee.project([cx+u,knee.hi[1]+.6,z+.14*math.cos(u*.5)],.045) for u in np.linspace(-3.35,3.35,48)]
            g.tube('Molded_KneeGripRib_'+side+'_'+str(i),line,.065,side,'flex',2,False,6)
        # Flexible panel quilting follows the existing knee insert instead of adding a hard plate.
        rear=Surface(d,'Knee_RearStretch_'+side);cx=(rear.lo[0]+rear.hi[0])*.5
        for i,z in enumerate([43.,45.5,48.,50.5]):
            line=[rear.project([cx+x,rear.lo[1]-.6,z],.035) for x in np.linspace(-2.6,2.6,45)]
            stitches('Stretch_Quilt_'+side+'_'+str(i),line,rear,side,spacing=.55)

def author_boots(d):
    for side,sign in [('l',1),('r',-1)]:
        body=Surface(d,'Leather');all_surface=Surface(d)
        # Existing continuous seam cords become a recessed piping beneath discrete curved stitches.
        for part in d['parts']:
            name=part['name']
            if side not in name.split('_') or not name.startswith(('Toe_DoubleSeam','Quarter_Edge','Frame_Stitch')):continue
            pts=np.array(d['positions'][part['first_vertex']:part['first_vertex']+part['vertices']])
            if len(pts)%5:continue
            line=pts.reshape(-1,5,3).mean(1)
            stitches('ArcStitch_'+name,line,body,side)
        tongue=Surface(d,'Padded_GussetedTongue_'+side)
        cx=(tongue.lo[0]+tongue.hi[0])*.5
        for sideedge in [-1,1]:
            line=[]
            for z in np.linspace(14,25.5,48):line.append(tongue.project([cx+sideedge*1.6,tongue.hi[1]+.4,z],.07))
            stitches('Tongue_EdgeStitch_'+side+'_'+str(sideedge),line,tongue,side)
        loop=Surface(d,'Rear_PullLoop_'+side);mid=(loop.lo+loop.hi)*.5
        for j,z in enumerate([25.2,27.2]):
            q=loop.project([mid[0],loop.lo[1]-.4,z],.035);bartack('PullLoop_BarTack_'+side+'_'+str(j),q,[1,0,0],loop,side)
        # Reinforced, fine-grain rubber trim separates the sidewall and outsole layers.
        sole=Surface(d,'LayeredLeatherSole_'+side)
        for flank in [-1,1]:
            line=[]
            for v in np.linspace(-5.5,22.3,90):
                w,_=g.foot_shape(v);line.append(sole.project(g.foot_point(side,flank*(w+.9),v,1.15),.025))
            g.tube('Outsole_SidewallBead_'+side+'_'+str(flank),line,.045,side,'foot',2,False,5)
        # Two short lace tails end in close-fitting gunmetal aglets.
        rings=[p for p in d['parts'] if p['name'].startswith('Tied_LaceLoop_'+side)]
        if rings:
            pts=np.concatenate([np.asarray(d['positions'][p['first_vertex']:p['first_vertex']+p['vertices']]) for p in rings]);center=pts.mean(0)
            for j,sg in enumerate([-1,1]):
                line=[center+np.array([sg*(.5+1.2*t),.3+.17*math.sin(t*math.pi),-1.9*t]) for t in np.linspace(0,1,20)]
                g.tube('Braided_LaceTail_'+side+'_'+str(j),line,.095,side,'calf',5,False,7)
                g.tube('LaceTail_Aglet_'+side+'_'+str(j),line[-5:],.11,side,'calf',0,False,8)

def export_detail(d):
    surface=Surface(d);out={k:[] for k in ('positions','triangles','weights','uv','normals','triangle_materials','parts')}
    for ob in g.objects:
        mesh=ob.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active;start=len(out['positions']);pts=np.array([(v.co.x*100,-v.co.y*100,v.co.z*100) for v in mesh.vertices])
        out['positions'].extend(pts.tolist());out['weights'].extend(surface.weights(p) for p in pts);first=len(out['triangles'])
        for tri in mesh.loop_triangles:
            pos=pts[list(tri.vertices)]
            if np.linalg.norm(np.cross(pos[1]-pos[0],pos[2]-pos[0]))<1e-9:continue
            out['triangles'].append([start+i for i in tri.vertices]);out['triangle_materials'].append(int(ob['material_slot']))
            out['uv'].append(g.valid_uv(np.array([[uv.data[i].uv.x,1-uv.data[i].uv.y] for i in tri.loops]),pos).tolist())
            out['normals'].append([[float(mesh.corner_normals[i].vector.x),float(-mesh.corner_normals[i].vector.y),float(mesh.corner_normals[i].vector.z)] for i in tri.loops])
        out['parts'].append(dict(name=ob.name,first_vertex=start,vertices=len(pts),triangles=len(out['triangles'])-first,material=int(ob['material_slot'])))
    out.update(source=d['source'],skeleton=d['skeleton'],bones=d['bones'],materials=[],contract='ST6 Detail20261024: additive native-weighted trim; accepted waist/cuff/shaft geometry unchanged')
    return out

def paired_detail(detail,original,paired):
    out=copy.deepcopy(detail);surface=Surface(original);points=np.array(paired['positions']);new=[]
    for p in detail['positions']:
        q,n,ids,w=surface.nearest(p);new.append((np.asarray(p)+(points[ids]-surface.points[ids]).T@w).tolist())
    out['positions']=new
    # All new pants trim is above the paired boot transition, so the original
    # normal field remains valid. Existing cuff geometry comes from its actual asset.
    return out

receipts={}
for kind,label in [('pants','ST6Trousers'),('boots','ST6Boots')]:
    bpy.ops.wm.read_factory_settings(use_empty=True);g.objects=[]
    d=read(R/'Inputs'/('Jason_'+label+'_Garment.json'))
    (author_pants if kind=='pants' else author_boots)(d)
    detail=export_detail(d);write(R/'Authored'/('Jason_'+kind+'.json'),detail)
    if kind=='pants':
        for suffix in ('_ShortBootsFit','_HighBootsFit','_ST6BootsFit'):
            paired=read(R/'Inputs'/('Jason_'+label+suffix+'.json'));write(R/'Authored'/('Jason_'+kind+suffix+'.json'),paired_detail(detail,d,paired))
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'Exports'/(label+'_DetailConstruction.blend')))
    receipts[kind]=dict(additional_triangles=len(detail['triangles']),detail_parts=len(detail['parts']),base_geometry_changed=False)
    print('ST6_DETAIL_AUTHORED',kind,receipts[kind],flush=True)
write(R/'authored_details.json',receipts)
