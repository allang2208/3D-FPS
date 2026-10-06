"""Author tailored mail trousers against Jason's accepted lower-body binding.

All coordinates are centimetres in Jason reference space. The jeans supply
proportions and native weights, not the new garment topology. No game launch.
"""
import json
import math
import shutil
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

P = Path('D:/FPS3D/FPSGAME')
R = P/'SourceAssets/ChainmailPants20261004'
R.mkdir(parents=True, exist_ok=True)
SOURCE = P/'SourceAssets/BootsEquipment20261004/jeans.json'
donor = json.loads(SOURCE.read_text())
dv = np.asarray(donor['positions']); df = np.asarray(donor['triangles'], int)
bones = donor['bones']; bone_ids = {b['name']: b['index'] for b in bones}
parts = []


def write(name, data):
    (R/name).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def add(name, points, faces, uv, material, binding=None):
    points = np.asarray(points, float); faces = np.asarray(faces, int)
    # Authoring normals follow a right-handed mathematical convention. Export
    # reverses triangle winding for UE while preserving these outward normals.
    mesh = trimesh.Trimesh(points, faces, process=False)
    trimesh.repair.fix_normals(mesh, multibody=True)
    if name.startswith('Mail') or name.startswith('Lining'):
        center = points.mean(0)
        n = mesh.vertex_normals
        if np.mean(np.sum(n[:, :2]*(points[:, :2]-center[:2]), axis=1)) < 0:
            mesh.invert()
    parts.append(dict(name=name, positions=points, faces=mesh.faces.copy(),
                      uv=np.asarray(uv, float), material=material, binding=binding))


def grid(name, points, material, binding=None, uv=None, solid=0.):
    points = np.asarray(points, float); h, w = points.shape[:2]
    vertices = points.reshape(-1, 3); faces = []
    for y in range(h-1):
        for x in range(w-1):
            a = y*w+x; faces += [[a, a+1, a+w+1], [a, a+w+1, a+w]]
    if uv is None:
        uv = np.zeros((h, w, 2))
        for y in range(h):
            uv[y, 1:, 0] = np.cumsum(np.linalg.norm(np.diff(points[y], axis=0), axis=1))/25
        for x in range(w):
            uv[1:, x, 1] = np.cumsum(np.linalg.norm(np.diff(points[:, x], axis=0), axis=1))/25
    uv = np.asarray(uv).reshape(-1, 2)
    if solid:
        outer = trimesh.Trimesh(vertices, faces, process=False)
        normals = outer.vertex_normals.copy()
        radial = vertices.copy(); radial[:, 2] = 0
        if np.mean(np.sum(normals*radial, axis=1)) < 0:
            faces = [f[::-1] for f in faces]; normals *= -1
        count = len(vertices)
        vertices = np.vstack([vertices, vertices-normals*solid])
        uv = np.vstack([uv, uv])
        front = list(faces); faces += [[k+count for k in f[::-1]] for f in front]
        boundary = list(range(w))+[y*w+w-1 for y in range(1,h)]+list(range((h-1)*w+w-2,(h-1)*w-1,-1))+[y*w for y in range(h-2,0,-1)]
        for a,b in zip(boundary, boundary[1:]+boundary[:1]):
            faces += [[a,b,b+count],[a,b+count,a+count]]
    add(name, vertices, faces, uv, material, binding)


def torso(z, theta, offset=0):
    rx = np.interp(z, [80,85,90,95,100.2], [18.3,18.7,18.3,17.7,17.1])+offset
    ry = np.interp(z, [80,85,90,95,100.2], [13.8,14.4,14.2,13.7,12.7])+offset
    return np.array([rx*np.sin(theta), 0.8+ry*np.cos(theta), z])


def leg(z, theta, sign=1, boots=False):
    # Extra thigh room and a tapered, non-elastic ankle. The boots variant has
    # a wider lower envelope only, preserving the knee and pelvis construction.
    heights = [11.8,20,30,40,47.35,58,67,72]
    cx = np.interp(z, heights, [14.8,14.2,13.5,12.6,12.04,11.2,10.5,9.8])
    cy = np.interp(z, heights, [-2.5,-2.,-1.2,-.4,.8,1.7,2.3,2.6])
    rx = np.interp(z, heights, [5.65,6.1,6.8,6.7,6.55,7.55,8.6,9.1])
    ry = np.interp(z, heights, [6.5,7.2,8.,8.3,8.55,9.4,10.4,10.6])
    if boots:
        fade = np.clip((29-z)/15,0,1)
        rx += .95*fade; ry += 1.05*fade
    fold = (.22*np.sin(z*.56+1.4*np.sin(theta))+.1*np.sin(5*theta+z*.27))
    fold *= np.clip((z-12)/6,0,1)*np.clip((72-z)/8,0,1)
    return np.array([sign*(cx+(rx+fold)*np.sin(theta)),cy+(ry+fold)*np.cos(theta),z])


def cloth(boots=False):
    start = len(parts); n=64
    theta=np.linspace(0,2*np.pi,n+1)
    grid('Mail_WaistAndSeat',[[torso(z,t) for t in theta] for z in np.linspace(100.2,80,15)],0)
    for sign,side in [(1,'L'),(-1,'R')]:
        top=[]
        for i,t in enumerate(theta):
            if i<=32: top.append(torso(80,sign*t))
            else:
                a=(i-32)/32*np.pi
                top.append(np.array([0.,.8-13.8*np.cos(a),80-8.5*np.sin(a)]))
        top=np.array(top); rows=[top]
        dest=np.array([leg(66,t,sign,boots) for t in theta])
        for blend in [.2,.4,.6,.8,1.]:
            row=top*(1-blend)+dest*blend
            # Keep the inner gusset soft without a tight denim crotch point.
            rows.append(row)
        for z in np.linspace(64.5,11.8,31):rows.append([leg(z,t,sign,boots) for t in theta])
        grid('Mail_Leg_'+side,rows,0)
        hem=np.array(rows[-1]); center=hem[:-1].mean(0)
        lining=[]
        for dz, inset in [(0,0),(.12,.16),(.35,.25),(1.,.27),(2.2,.27)]:
            ring=hem.copy(); radial=ring[:,:2]-center[:2]
            radial/=np.maximum(np.linalg.norm(radial,axis=1),1e-8)[:,None]
            ring[:,:2]-=radial*inset;ring[:,2]+=dz;lining.append(ring)
        grid('Lining_Ankle_'+side,lining,2)
        # A rolled edge produces a real silhouette and inherits seam weights.
        tube('HemBinding_'+side,hem,.16,2)
    waist=np.array([torso(100.2,t) for t in theta]);lining=[]
    for dz,inset in [(0,0),(-.12,.18),(-.35,.28),(-1.5,.3),(-3.2,.3)]:
        row=waist.copy();rad=row[:,:2]-[0,.8];rad/=np.linalg.norm(rad,axis=1)[:,None]
        row[:,:2]-=rad*inset;row[:,2]+=dz;lining.append(row)
    grid('Lining_Waist',lining,2)
    return start


def tube(name, line, radius, material, binding=None, closed=True):
    line=np.array(line,float)
    if closed and np.linalg.norm(line[0]-line[-1])<1e-5:line=line[:-1]
    rings=[]
    for i,p in enumerate(line):
        tangent=line[(i+1)%len(line)]-line[(i-1)%len(line)]
        tangent/=max(np.linalg.norm(tangent),1e-8)
        ref=np.array([0.,0.,1.]) if abs(tangent[2])<.9 else np.array([1.,0.,0.])
        a=np.cross(tangent,ref);a/=np.linalg.norm(a);b=np.cross(tangent,a)
        rings.append([p+radius*(a*np.cos(t)+b*np.sin(t)) for t in np.linspace(0,2*np.pi,9)])
    if closed:rings.append(rings[0])
    grid(name,rings,material,binding)


def rivet(name, center, normal, binding):
    normal=np.array(normal,float);normal/=np.linalg.norm(normal)
    ref=np.array([0.,0.,1.]) if abs(normal[2])<.9 else np.array([1.,0.,0.])
    a=np.cross(normal,ref);a/=np.linalg.norm(a);b=np.cross(normal,a)
    ring=[]
    for phi in np.linspace(.05,np.pi-.05,7):
        ring.append([center+normal*.18*np.cos(phi)+.32*np.sin(phi)*(a*np.cos(t)+b*np.sin(t)) for t in np.linspace(0,2*np.pi,13)])
    grid(name,ring,1,binding)


def armor():
    pelvis={'pelvis':1.}
    for i in range(8):
        a=i*2*np.pi/8+.009;b=(i+1)*2*np.pi/8-.009
        points=[[torso(z,t,.48) for t in np.linspace(a,b,13)] for z in np.linspace(94.5,101.,5)]
        grid('Waist_Plate_%02d'%i,points,1,pelvis,solid=.2)
        for z in [95.6,99.7]:
            t=(a+b)/2;p=torso(z,t,.72);rivet('Waist_Rivet_%02d_%s'%(i,z),p,[np.sin(t),np.cos(t),0],pelvis)
    for z in [94.6,101.]:tube('Waist_RolledRim_'+str(z),[torso(z,t,.55) for t in np.linspace(0,2*np.pi,97)],.13,1,pelvis)
    # Three short overlapping side lames leave the central crotch clear.
    for sign,side,angle in [(1,'L',np.pi/2),(-1,'R',3*np.pi/2)]:
        for i,(top,bottom) in enumerate([(95.,90.2),(91.2,86.5),(87.4,82.8)]):
            span=1.50-i*.08;binding={'pelvis':1.-i*.13,'thigh_'+side.lower():i*.13}
            points=[]
            for v in np.linspace(0,1,6):
                z=top*(1-v)+bottom*v
                points.append([torso(z,t,.85+.25*i) for t in np.linspace(angle-span/2,angle+span/2,19)])
            grid('Hip_'+side+'_Lame_'+str(i),points,1,binding,solid=.18)
            for t in [angle-span*.35,angle+span*.35]:
                p=torso(top-.9,t,1.10+.25*i);rivet('Hip_'+side+'_Rivet_'+str(i)+'_'+str(t),p,[np.sin(t),np.cos(t),0],binding)
    # Small rounded clasp and two strap keepers, no modern denim fly/button.
    for cx in [-2.,2.]:
        path=[]
        for a in np.linspace(0,2*np.pi,41):
            x=cx+1.25*np.sign(np.sin(a))*abs(np.sin(a))**.5
            z=97.8+2.0*np.sign(np.cos(a))*abs(np.cos(a))**.5
            path.append([x,14.45,z])
        tube('Clasp_'+str(cx),path,.18,1,pelvis)
    for sign,side in [(1,'l'),(-1,'r')]:
        center=np.array([sign*12.04,10.0,47.35])
        binding={'thigh_'+side:.45,'calf_'+side:.55}
        rows=[]
        for rho in [.012,.12,.25,.40,.55,.70,.82,.91,.96,1.]:
            row=[]
            for t in np.linspace(0,2*np.pi,49):
                x=7.2*rho*np.cos(t);z=6.8*rho*np.sin(t)
                # Convex shield with a subdued central ridge and rolled rim.
                y=2.65*(1-rho*rho)+.13*np.exp(-((rho-.96)/.04)**2)
                row.append(center+[x,y,z])
            rows.append(row)
        grid('Knee_'+side+'_Cup',rows,1,binding,solid=.22)
        tube('Knee_'+side+'_RolledRim',rows[-1],.15,1,binding)
        for idx,(za,zb) in enumerate([(51.9,56.9),(37.9,42.3)]):
            bind={'thigh_'+side:1.} if idx==0 else {'calf_'+side:1.}
            points=[]
            for v in np.linspace(0,1,6):
                row=[]
                for t in np.linspace(-1.04,1.04,25):
                    z=za+(zb-za)*v+.65*np.cos(t)
                    point=leg(z,t,sign);point[1]+=.75+.25*np.sin(v*np.pi)
                    row.append(point)
                points.append(row)
            grid('Knee_'+side+'_Lame_'+str(idx),points,1,bind,solid=.18)
        for z in [42.,53.]:
            bind={'thigh_'+side:1.} if z>47 else {'calf_'+side:1.}
            grid('Knee_'+side+'_Strap_'+str(z),[[leg(h,t,sign)+np.array([sign*.28*np.sin(t),.28*np.cos(t),0]) for t in np.linspace(0,2*np.pi,65)] for h in np.linspace(z-.65,z+.65,3)],2,bind,solid=.14)
            for x in [-5.8,5.8]:rivet('Knee_'+side+'_Rivet_'+str(z)+'_'+str(x),np.array([sign*12.04+x,11.,z]),[0,1,0],binding)


def native_weights(points):
    centers=dv[df].mean(1);tree=cKDTree(centers);out=[]
    for begin in range(0,len(points),800):
        query=points[begin:begin+800];_,near=tree.query(query,k=24)
        candidates=df[near]
        closest=trimesh.triangles.closest_point(dv[candidates].reshape(-1,3,3),np.repeat(query,24,axis=0)).reshape(-1,24,3)
        best=np.argmin(np.linalg.norm(closest-query[:,None,:],axis=2),axis=1)
        ids=candidates[np.arange(len(query)),best]
        bary=trimesh.triangles.points_to_barycentric(dv[ids],closest[np.arange(len(query)),best])
        bary=np.maximum(bary,0);bary/=bary.sum(1)[:,None]
        for source,mix in zip(ids,bary):
            weights={}
            for vi,amount in zip(source,mix):
                for bi,w in donor['weights'][vi]:weights[bi]=weights.get(bi,0)+w*amount
            selected=[(bi,w) for bi,w in sorted(weights.items(),key=lambda v:-v[1])[:8] if w>1e-5]
            den=sum(w for _,w in selected);out.append([[int(bi),float(w/den)] for bi,w in selected])
    return out


def export(name):
    positions=[];triangles=[];uv=[];normals=[];slots=[];groups=[];weights=[]
    for part in parts:
        pv=part['positions'];faces=part['faces'];off=len(positions)
        # Weld coincident seam positions only for smooth normal construction.
        mesh=trimesh.Trimesh(pv,faces,process=False);rounded=np.round(pv,5)
        _,first,inverse=np.unique(rounded,axis=0,return_index=True,return_inverse=True)
        smooth=trimesh.Trimesh(pv[first],inverse[faces],process=False)
        vn=smooth.vertex_normals[inverse]
        positions.extend(pv.tolist())
        if part['binding'] is None:pw=native_weights(pv)
        else:pw=[[[bone_ids[n],v] for n,v in part['binding'].items() if v>0] for _ in pv]
        weights.extend(pw)
        for face in faces[:,::-1]:
            triangles.append((face+off).tolist());uv.append(part['uv'][face].tolist());normals.append(vn[face].tolist());slots.append(part['material'])
        groups.append(dict(name=part['name'],first_vertex=off,vertices=len(pv),triangles=len(faces),material=part['material']))
    data=dict(source=donor['source'],binding_source=donor['source'],skeleton=donor['skeleton'],bones=bones,
              positions=positions,triangles=triangles,uv=uv,normals=normals,weights=weights,triangle_materials=slots,parts=groups,
              contract='New gusseted mail trousers; native Jason bind and weights; no new runtime simulation')
    write(name+'.json',data)
    return dict(vertices=len(positions),triangles=len(triangles),parts=len(groups))


def main():
    concept=Path('C:/Users/allan/.codex/generated_images/01a10240-fb19-7610-a28b-8a64427608c6/exec-5bae011e-6e62-4a8b-b86e-1b4c045266c4.png')
    if concept.exists() and not (R/'Concept.png').exists():shutil.copy2(concept,R/'Concept.png')
    cloth();armor();standard=export('Jason_ChainmailPants')
    parts.clear();cloth(True);armor();boots=export('Jason_ChainmailPants_BootsFit')
    write('production.json',dict(item='ue_chainmail_pants',source=str(SOURCE),reference='Concept.png',
        standard=standard,boots=boots,units='centimetres',front='+Y',slots=['InterlacedMail','ForgedSteel','CharcoalLining'],
        native_binding=donor['source'],runtime_tested=False,
        design=['reconstructed trousers, separate crotch gusset and tapered legs','closed plate thickness and rolled edges','kneecap and thigh/calf lames use separate native bone regions','boot-specific wider cuffs'],
        mail_source='SourceAssets/ChainmailInterlace20260929: baked periodic steel rings; no per-ring runtime objects',
        hidden_design='Back and interior inferred from the approved front concept; not a scanned reconstruction'))
    print('CHAINMAIL_PANTS_AUTHORED',standard,boots,flush=True)


if __name__=='__main__':main()
