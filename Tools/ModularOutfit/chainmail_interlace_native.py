"""Author native-profile cuff links and metric forearm UVs in source centimetres."""
import math
import numpy as np


def unit(v):
    a=np.asarray(v,dtype=float)
    return a/max(float(np.linalg.norm(a)),1.e-12)


def blend_weights(a,b,f):
    values={k:a.get(k,0)*(1-f)+b.get(k,0)*f for k in a.keys()|b.keys()}
    values={k:v for k,v in values.items() if v>1.e-6}
    total=sum(values.values())
    return {k:v/total for k,v in values.items()}


def retarget(master,target):
    """Transport authored cuff with the same native LBS maps as fitted sleeves.

    Some weapon reference poses shear the apparent wrist plane. Deriving a new
    circular cuff in each pose would move it away from the existing sleeve edge.
    """
    def bind(bone):
        m=np.eye(4);m[:3,:3]=np.asarray(bone['axes']).T;m[:3,3]=bone['position'];return m
    sides={s for s in ['l','r'] if any(sum(v for k,v in w.items() if k.endswith('_'+s))>.7 for w in target['weights'])}
    # Match the original fitted-sleeve split: shoulder-cap vertices may carry
    # spine/clavicle weights, so a hand-weight threshold would cut those faces.
    keep=[i for i,p in enumerate(master['positions']) if len(sides)==2 or (p[0]<0 if 'l' in sides else p[0]>0)]
    remap={vi:i for i,vi in enumerate(keep)}
    face_ids=[i for i,f in enumerate(master['triangles']) if all(v in remap for v in f)]
    names={n for i in keep for n in master['weights'][i]}
    transforms={n:bind(target['bones'][n])@np.linalg.inv(bind(master['bones'][n])) for n in names}
    coords=[];normal_maps={}
    for i in keep:
        matrix=sum(transforms[n]*w for n,w in master['weights'][i].items())
        coords.append((matrix@np.r_[master['positions'][i],1.])[:3].tolist())
        normal_maps[i]=np.linalg.inv(matrix[:3,:3]).T
    output=dict(target)
    output.update(positions=coords,weights=[master['weights'][i] for i in keep],
                  triangles=[[remap[v] for v in master['triangles'][fi]] for fi in face_ids],
                  uv=[master['uv'][fi] for fi in face_ids],
                  triangle_materials=[master['triangle_materials'][fi] for fi in face_ids],
                  normals=[[unit(normal_maps[vi]@np.asarray(n)).tolist() for vi,n in zip(master['triangles'][fi],master['normals'][fi])] for fi in face_ids],
                  contract=master['contract'])
    return output,dict(original_triangles=len(target['triangles']),added_triangles=len(face_ids)-len(target['triangles']),
                       cuff_source='M4 authored contour transported through native bind matrices',sides=sorted(sides),native_weights_inherited=True)


def author(data):
    base_count=len(data['triangles'])
    data['triangle_materials']=[0]*base_count
    data['contract']='Original native sleeve envelope and weights; metric forearm mail; attached cuff binding and solid links; no new animation'
    # Body has a different cuff cut. Keep its original shell and UV charts rather
    # than impose the V7 first-person cuff plane on that independently fitted mesh.
    if data['profile']=='Body':
        return data,dict(original_triangles=base_count,added_triangles=0,body_cut_preserved=True)
    positions=np.asarray(data['positions']);faces=np.asarray(data['triangles'])
    vertex_normals=np.zeros_like(positions)
    for corner in range(3):np.add.at(vertex_normals,faces[:,corner],np.asarray(data['normals'])[:,corner])
    vertex_normals/=np.maximum(np.linalg.norm(vertex_normals,axis=1)[:,None],1.e-9)
    reports=[]
    for side in ['l','r']:
        wrist=np.asarray(data['bones']['hand_'+side]['position'])
        elbow=np.asarray(data['bones']['lowerarm_'+side]['position'])
        axis=unit(wrist-elbow)
        seed=np.asarray(data['bones']['hand_'+side]['axes'][2])
        u=unit(seed-axis*np.dot(seed,axis));v=np.cross(axis,u)
        q=positions-wrist;t=q@axis;radial=q-t[:,None]*axis;r=np.linalg.norm(radial,axis=1)
        belongs=np.array([sum(x for k,x in w.items() if k.endswith('_'+side))>.7 for w in data['weights'][:len(positions)]])
        candidates=np.where(belongs & (t>-10) & (t<1) & (r>1.5) & (r<6))[0]
        if not len(candidates):continue
        end=float(t[candidates].max())
        tip=candidates[np.abs(t[candidates]-end)<.025]
        if len(tip)<64:raise RuntimeError('Native cuff does not have the fitted end loop: '+data['profile']+' '+side)
        tip=tip[np.sum(vertex_normals[tip]*radial[tip],axis=1)>.1]
        angle=np.mod(np.arctan2(radial@v,radial@u),2*math.pi)
        # Inner and outer loops share angular samples; retain the outer loop.
        grouped={}
        for i in tip:
            key=round(float(angle[i]),4)
            if key not in grouped or r[i]>r[grouped[key]]:grouped[key]=int(i)
        tip=sorted(grouped.values(),key=lambda i:angle[i])
        # Collapse adjacent near-identical samples introduced by UV splitting.
        tip=[i for k,i in enumerate(tip) if k==0 or angle[i]-angle[tip[k-1]]>.006]
        if len(tip)>1 and 2*math.pi-angle[tip[-1]]+angle[tip[0]]<.006:tip.pop()
        contour=positions[tip];edge=np.roll(contour,-1,axis=0)-contour
        lengths=np.linalg.norm(edge,axis=1);arcs=np.r_[0,np.cumsum(lengths)];perimeter=float(arcs[-1])
        def contour_at(s):
            s=s%perimeter;k=min(int(np.searchsorted(arcs,s,side='right')-1),len(tip)-1)
            f=(s-arcs[k])/max(lengths[k],1.e-9)
            point=contour[k]*(1-f)+contour[(k+1)%len(tip)]*f
            direction=unit(point-wrist-axis*np.dot(point-wrist,axis))
            weights=blend_weights(data['weights'][tip[k]],data['weights'][tip[(k+1)%len(tip)]],float(f))
            return point,direction,unit(edge[k]),weights
        # The existing fitted 13 cm cuff chart used a stretched U/V aspect ratio.
        # Give that chart circumferential centimetres and axial centimetres.
        for fi,face in enumerate(faces):
            if not np.all(belongs[face]) or np.min(t[face])<-13.01:continue
            theta=angle[face].copy()
            if theta.max()-theta.min()>math.pi:theta[theta<math.pi]+=2*math.pi
            data['uv'][fi]=[[float(th/(2*math.pi)*perimeter/25),float(-t[vi]/25)] for vi,th in zip(face,theta)]
            normal=np.mean(np.asarray(data['normals'][fi]),axis=0)
            radial_mid=unit(np.mean(radial[face],axis=0))
            if np.dot(normal,radial_mid)<-.3:data['triangle_materials'][fi]=2
        before=len(data['triangles'])
        def append_grid(points,normals,weights,uvs,rows,cols,slot):
            offset=len(data['positions'])
            data['positions'].extend(np.asarray(points).reshape(-1,3).tolist())
            normals=np.asarray(normals).reshape(-1,3);uvs=np.asarray(uvs).reshape(-1,2)
            data['weights'].extend(weights)
            for i in range(rows):
                for j in range(cols):
                    quad=[i*cols+j,((i+1)%rows)*cols+j,((i+1)%rows)*cols+(j+1)%cols,i*cols+(j+1)%cols]
                    for tri in [quad[:3],[quad[0],quad[2],quad[3]]]:
                        p=np.asarray(points).reshape(-1,3)[tri]
                        if np.dot(np.cross(p[1]-p[0],p[2]-p[0]),normals[tri].sum(0))<0:tri=list(reversed(tri))
                        data['triangles'].append([offset+x for x in tri])
                        data['normals'].append(normals[tri].tolist());data['uv'].append(uvs[tri].tolist())
                        data['triangle_materials'].append(slot)
        # Thin closed binding follows the actual non-circular cuff contour. Its
        # nearest contour weights are used on both sides of the rolled edge.
        profile=np.array([[.00,.01],[.07,.075],[.62,.075],[.70,.01],[.62,-.025],[.07,-.025]])
        pp=[];nn=[];ww=[];uvs=[]
        steps=96
        for k in range(steps):
            point,normal,tangent,weight=contour_at(k/steps*perimeter)
            for j,(axial,rise) in enumerate(profile):
                pp.append(point-axis*axial+normal*rise)
                dp=profile[(j+1)%len(profile)]-profile[(j-1)%len(profile)]
                nn.append(unit(normal*dp[0]+axis*dp[1]));ww.append(dict(weight));uvs.append((k/steps,j/len(profile)))
        append_grid(pp,nn,ww,uvs,steps,len(profile),2)
        link_count=int(round(perimeter/.58))
        major,cross=20,6
        for k in range(link_count):
            center,n,tangent,weight=contour_at((k+.5)/link_count*perimeter)
            center=center-axis*.14+n*.070
            # Follow the sleeve end. No rigid joint or component per link.
            long=unit(tangent);short=-axis;pp=[];nn=[];ww=[];uvs=[]
            for a in range(major):
                theta=a*2*math.pi/major
                outward=unit(long*math.cos(theta)+short*math.sin(theta))
                mid=center+long*(.245*math.cos(theta))+short*(.195*math.sin(theta))
                for b in range(cross):
                    phi=b*2*math.pi/cross
                    normal=unit(outward*math.cos(phi)+n*math.sin(phi))
                    pp.append(mid+normal*.034);nn.append(normal);ww.append(dict(weight));uvs.append((a/major,b/cross))
            append_grid(pp,nn,ww,uvs,major,cross,1)
        reports.append(dict(side=side,links=link_count,added_triangles=len(data['triangles'])-before,
                            end_cm=end,perimeter_cm=perimeter,contour_samples=len(tip),
                            binding_width_cm=.70,metric_uv_from_cm=-13.,native_weights_inherited=True))
    return data,dict(original_triangles=base_count,added_triangles=len(data['triangles'])-base_count,cuffs=reports)
