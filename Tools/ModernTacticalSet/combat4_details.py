"""Sew the R4 shirt; rounded sleeve pockets, articulated elbow facings, double stitching."""
import sys,copy,math,os,uuid
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write as _write,subset,unit
from combat4_pattern import append_face,boundary,loops_from_edges,weights_mix
from combat3_cloth import normals
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR4';B=S/'CombatShirtR3';MAT='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3/Materials/M_'
def write(path,data):
    path=Path(path);temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');_write(temp,data);os.replace(temp,path)

def slot(d,name):
    path=MAT+name
    if path not in d['materials']:d['materials'].append(path);d['material_slots'].append(name)
    return d['materials'].index(path)

def tube(d,points,nn,ww,radius,material,closed=False):
    if len(points)<2:return
    start=len(d['positions']);n=len(points)
    for j,(q,normal,ws) in enumerate(zip(points,nn,ww)):
        tangent=unit(points[(j+1)%n]-points[j-1] if closed else points[min(j+1,n-1)]-points[max(0,j-1)]);side=unit(np.cross(tangent,normal))
        for k in range(4):
            a=k*math.pi/2;d['positions'].append((q+radius*(normal*np.cos(a)+side*np.sin(a))).tolist());d['weights'].append(copy.deepcopy(ws))
    for j in range(n if closed else n-1):
        for k in range(4):
            a=start+j*4+k;b=start+j*4+(k+1)%4;c=start+((j+1)%n)*4+(k+1)%4;e=start+((j+1)%n)*4+k
            append_face(d,[a,c,b],material);append_face(d,[a,e,c],material)

def seam_line(d,ids,p,n,closed=False):
    if len(ids)<2:return
    material=slot(d,'CombatThread');points=p[ids]+n[ids]*.035;nn=n[ids];ws=[d['weights'][i] for i in ids]
    # One narrow joined seam plus two rows of separate needle stitches.
    tube(d,points,nn,ws,.018,material,closed)
    seq=list(range(len(ids)))+([0] if closed else [])
    for a,b in zip(seq[:-1],seq[1:]):
        line=points[b]-points[a];length=np.linalg.norm(line)
        if length<.16:continue
        tangent=line/length
        for t in np.arange(.12,length-.05,.34):
            fac=t/length;normal=unit(nn[a]*(1-fac)+nn[b]*fac);side=unit(np.cross(tangent,normal));w=weights_mix([ws[a],ws[b]],[1-fac,fac]);c=points[a]+line*fac
            for offset in [-.14,.14]:
                center=c+side*offset+normal*.01;tube(d,np.array([center-tangent*.105,center+normal*.012,center+tangent*.105]),np.tile(normal,(3,1)),[w]*3,.011,material)

def rounded_panels(d):
    bones={b['name']:np.array(b['position']) for b in d['bones']};p=np.array(d['positions']);f=np.array(d['triangles']);tree=BVHTree.FromPolygons(p.tolist(),f.tolist(),all_triangles=True);material=slot(d,'CombatRipstop')
    def sample(center,rad,offset):
        hit,_,fi,_=tree.ray_cast(Vector(center+rad*18),Vector(-rad),18)
        if hit is None:raise ValueError('cropped native sleeve')
        a,b,c=p[f[fi]];q=np.array(hit);t=np.linalg.lstsq(np.column_stack([b-a,c-a]),q-a,rcond=None)[0];coeff=np.clip([1-t.sum(),t[0],t[1]],0,1);coeff/=coeff.sum()
        return q+rad*offset,rad,weights_mix([d['weights'][i] for i in f[fi]],coeff)
    def patch(a,b,out,mid,half_length,angle,power,height):
        axis=unit(b-a);out=unit(out-axis*np.dot(axis,out));cross=unit(np.cross(axis,out));start=len(d['positions']);radials=[];ring_count=9;segments=64
        q,n,w=sample(a+(b-a)*mid,out,height+.045);d['positions'].append(q.tolist());d['weights'].append(w);radials.append(n)
        rings=[]
        for j in range(1,ring_count+1):
            r=j/ring_count;ids=[]
            for k in range(segments):
                phase=2*np.pi*k/segments;u=np.sign(np.cos(phase))*abs(np.cos(phase))**power*r;v=np.sign(np.sin(phase))*abs(np.sin(phase))**power*r
                c=a+(b-a)*(mid+half_length*u);t=angle*v;rad=out*np.cos(t)+cross*np.sin(t)
                q,n,w=sample(c,rad,height+.045*(1-r*r));ids.append(len(d['positions']));d['positions'].append(q.tolist());d['weights'].append(w);radials.append(n)
            rings.append(ids)
        def face(ids):
            q=np.array([d['positions'][i] for i in ids]);normal=-np.cross(q[1]-q[0],q[2]-q[0]);rad=np.mean([radials[i-start] for i in ids],0)
            if np.dot(normal,rad)<0:ids.reverse()
            append_face(d,ids,material)
        outer_face_start=len(d['triangles'])
        for k in range(segments):face([start,rings[0][k],rings[0][(k+1)%segments]])
        for previous,current in zip(rings[:-1],rings[1:]):
            for k in range(segments):
                h=(k+1)%segments;face([previous[k],current[k],current[h]]);face([previous[k],current[h],previous[h]])
        # Smooth the sewn cloth facing itself, while retaining a crisp turned edge.
        panel_points=np.array(d['positions'][start:]);panel_faces=np.array(d['triangles'][outer_face_start:])-start;panel_normals=normals(panel_points,panel_faces)
        d['normals'][outer_face_start:]=panel_normals[panel_faces].tolist()
        outer=rings[-1];inner=[]
        for vi in outer:
            inner.append(len(d['positions']));d['positions'].append((np.array(d['positions'][vi])-radials[vi-start]*(height-.025)).tolist());d['weights'].append(copy.deepcopy(d['weights'][vi]));radials.append(radials[vi-start])
        for k in range(segments):
            h=(k+1)%segments;append_face(d,[outer[k],inner[k],inner[h]],material);append_face(d,[outer[k],inner[h],outer[h]],material)
        pp=np.array(d['positions']);ns=np.zeros_like(pp)
        for vi in outer:ns[vi]=radials[vi-start]
        seam_line(d,outer,pp,ns,True)
    for side,other in [('l','r'),('r','l')]:
        a,b,c=[bones[k+'_'+side] for k in ['upperarm','lowerarm','hand']];out=a-bones['upperarm_'+other]
        # Rounded rectangular upper-arm pocket, rounded flap, oval elbow facing.
        for args in [(a,b,out,.435,.195,.64,.36,.12),(a,b,out,.255,.052,.64,.42,.24),(b,c,out,.145,.145,.72,1.,.075)]:
            lengths={key:len(d[key]) for key in ['positions','weights','triangles','triangle_materials','normals','uv']}
            try:patch(*args)
            except ValueError:
                for key,length in lengths.items():del d[key][length:]
                print('R4_NATIVE_CROPPED_PANEL',d['rig'],side,flush=True)

def shell_and_sew(d):
    p=np.array(d['positions']);f=np.array(d['triangles']);n=normals(p,f);count=len(p);edges=boundary(f);lining=slot(d,'CombatLining');thickness=np.full(count,.10)
    cuff=np.unique(f[np.array(d['triangle_materials'])==2]);thickness[cuff]=.12
    d['positions']+=(p-n*thickness[:,None]).tolist();d['weights']+=copy.deepcopy(d['weights']);d['normals']=n[f].tolist()
    for face,uv in zip(f,list(d['uv'])):
        ids=(face[::-1]+count).tolist();append_face(d,ids,lining,list(reversed(uv)))
    for a,b in edges:
        append_face(d,[a,b,b+count],2);append_face(d,[a,b+count,a+count],2)
    # Seams follow the actual split fabric boundaries, never the old body triangles.
    es={};mats=d['triangle_materials'][:len(f)]
    for face,m in zip(f,mats):
        for a,b in zip(face,np.roll(face,-1)):es.setdefault(tuple(sorted([int(a),int(b)])),set()).add(m)
    seams=[edge for edge,values in es.items() if len(values)>1]
    for loop in loops_from_edges(seams):seam_line(d,loop,p,n,False)
    for loop in loops_from_edges(edges):seam_line(d,loop,p,n,True)
    rounded_panels(d);d['construction']='R4 native-weighted continuous crew/raglan pattern, paired lining, sewn rounded pockets, elliptical elbow panels, real double topstitches'
    return d

def final_clearance(d,rig):
    # Final collision projection is part of cloth authoring, with pinned cuffs retained.
    body=read(B/'Inputs'/f'Body_{rig}.json');head=read(S/'HelmetHairFitR1/Inputs'/f'{rig}_Head.json');bp=np.array(body['positions']+head['positions']);bf=np.array(body['triangles']+[[v+len(body['positions']) for v in face] for face in head['triangles']]);tree=BVHTree.FromPolygons(bp.tolist(),bf.tolist(),all_triangles=True)
    p=np.array(d['positions']);original=p.copy();f=np.array(d['triangles']);pins=np.load(R/'Simulation'/('Pattern_'+rig+'.npz'))['pins'];fixed=pins>=1-1e-8;nn=-np.cross(bp[bf[:,1]]-bp[bf[:,0]],bp[bf[:,2]]-bp[bf[:,0]]);nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-12)
    for _ in range(3):
        for i,q in enumerate(p):
            if fixed[i]:continue
            hit,_,fi,_=tree.find_nearest(Vector(q))
            if hit is None:continue
            distance=np.dot(q-np.array(hit),nn[fi])
            if distance<.23:p[i]+=nn[fi]*(.23-distance)
    d['positions']=p.tolist();d['normals']=normals(p,f)[f].tolist();d['r4_pattern']['final_body_head_clearance_cm']=.23;write(R/'Authored'/f'shirt_outer_{rig}.json',d)

def main():
    for rig in ([] if '--fp-only' in sys.argv else ['Jason','Kaitlin']):
        d=read(R/'Authored'/f'shirt_outer_{rig}.json');final_clearance(d,rig);shell_and_sew(d);write(R/'Authored'/f'shirt_detail_{rig}.json',d);print('R4_SEWN',rig,len(d['triangles']),flush=True)
    if '--world-only' in sys.argv:return
    rows=[]
    for row in read(B/'fp-authored.json')['rows']:
        d=read(row['file']);parts=d['parts'];end=max(x['first_vertex']+x['vertices'] for x in parts);faces=np.array(d['triangles']);d=subset(d,(faces<end).all(1));d.pop('parts',None)
        p=np.array(d['positions']);f=np.array(d['triangles']);is_outer=np.zeros(len(p),bool)
        for part in parts:is_outer[part['first_vertex']:part['first_vertex']+part['vertices']//2]=True
        outer=f[is_outer[f].all(1)];n=normals(p,outer)
        for loop in loops_from_edges(boundary(outer)):seam_line(d,loop,p,n,True)
        # Preserve the accepted native cuff and physical sleeve folds; replace appendages.
        rounded_panels(d);d['r4_revision']='Native FP anchors and cloth retained; rounded sewn pocket/elbow geometry replaces rectangular overlays'
        file=R/'Authored'/('shirt_fp_'+row['rig']+'.json');write(file,d);out=copy.deepcopy(row);out['file']=str(file);rows.append(out);print('R4_FP_SEWN',row['rig'],flush=True)
    write(R/'fp-authored.json',dict(completed=True,rows=rows))
if __name__=='__main__':main()
