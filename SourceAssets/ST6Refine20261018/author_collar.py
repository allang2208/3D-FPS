"""Fit the ST6 neckline to Jason's original neck, preserving native binding."""
import json, math, copy
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np

O=Path(__file__).parent; R=O.parents[1]; OLD=O.parent/'ST6Reset20261017'
DEST='/Game/Characters/ModularOutfit20260924/Super90Source20261006/ST6Refine20261018'
TOP=151.2

def write(name,d):
    (O/name).write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')

def normals(p,f):
    p=np.asarray(p); f=np.asarray(f); n=np.zeros_like(p)
    cross=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    for j in range(3):np.add.at(n,f[:,j],cross)
    # UE source winding is clockwise relative to outward split normals.
    return -n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)

def mix_weights(a,b,t):
    keys=a.keys()|b.keys();d={k:a.get(k,0)*(1-t)+b.get(k,0)*t for k in keys}
    d=dict(sorted(d.items(),key=lambda kv:kv[1],reverse=True)[:8]);s=sum(d.values())
    return {k:v/s for k,v in d.items() if v>1e-7}

def append(dst,src):
    off=len(dst['positions']);moff=len(dst['materials'])
    for k in ('positions','weights','uv','normals'):dst[k].extend(src[k])
    dst['triangles'].extend([[v+off for v in f] for f in src['triangles']])
    dst['triangle_materials'].extend([m+moff for m in src['triangle_materials']])
    dst['materials'].extend(src['materials']);dst['material_slots'].extend(src['material_slots'])

def make_hem(native):
    """A narrow, continuous fold covers the coarse native material boundary."""
    bottom,top=95.0,100.5
    points=[];weights=[];faces=[];cache={}
    for fi,face in enumerate(native['triangles']):
        if native['triangle_materials'][fi] not in (3,8,9,10,14):continue
        poly=[(np.array(native['positions'][v]),native['weights'][v]) for v in face]
        if min(v[0][2] for v in poly)>top or max(v[0][2] for v in poly)<bottom:continue
        for limit,keep_above in ((bottom,True),(top,False)):
            clipped=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                ina=a[0][2]>=limit if keep_above else a[0][2]<=limit
                inb=b[0][2]>=limit if keep_above else b[0][2]<=limit
                if ina:clipped.append(a)
                if ina!=inb:
                    t=float((limit-a[0][2])/(b[0][2]-a[0][2]))
                    clipped.append((a[0]+(b[0]-a[0])*t,mix_weights(a[1],b[1],t)))
            poly=clipped
        indices=[]
        for point,w in poly:
            key=tuple(np.round(point,5))
            if key not in cache:cache[key]=len(points);points.append(point.tolist());weights.append(w)
            indices.append(cache[key])
        for j in range(1,len(indices)-1):faces.append([indices[0],indices[j],indices[j+1]])
    p=np.array(points);ns=normals(p,faces)
    fade=np.clip((top-p[:,2])/.75,0,1);p+=ns*(.025+.085*fade)[:,None]
    points=p.tolist()
    edges=Counter(tuple(sorted((int(a),int(b)))) for face in faces for a,b in zip(face,np.roll(face,-1)))
    low=[e for e,count in edges.items() if count==1 and max(p[list(e),2])<bottom+.15]
    ring={}
    for v in sorted({v for e in low for v in e}):
        ring[v]=len(points);points.append((p[v]-ns[v]*.14+np.array([0,0,.25])).tolist());weights.append(dict(weights[v]))
    directed={tuple(sorted((int(a),int(b)))):(int(a),int(b)) for face in faces for a,b in zip(face,np.roll(face,-1))}
    for edge in low:
        a,b=directed[edge];faces.extend([[b,a,ring[a]],[b,ring[a],ring[b]]])
    ns=normals(points,faces);p=np.array(points)
    return dict(positions=points,weights=weights,triangles=faces,
                normals=[[ns[v].tolist() for v in face] for face in faces],
                uv=[[[float(math.atan2(p[v,1],p[v,0])/(2*math.pi)+.5),float((p[v,2]-bottom)/10)] for v in face] for face in faces],
                triangle_materials=[0]*len(faces),materials=[DEST+'/Materials/MI_ST6Torso_Jason.MI_ST6Torso_Jason'],material_slots=['ST6HemFabric'])

def main():
    native=json.loads((OLD/'Read/Jason.json').read_text())
    src=json.loads((O.parent/'JasonPlayer20261003/Jason.json').read_text())
    p=np.array(src['positions']);f=np.array(src['triangles']);m=np.array(src['triangle_materials'])
    head_faces=f[m==1]
    n=normals(p,head_faces)
    ids=np.unique(head_faces[np.min(p[head_faces,2],axis=1)<TOP])
    remap={int(v):i for i,v in enumerate(ids)}
    pos=[p[i].tolist() for i in ids]
    weights=[]
    for vi in ids:
        w={}
        for bi,value in src['weights'][vi]:
            bone=src['bones'][bi]['name']
            while bone not in native['bones']:
                bi=src['bones'][bi]['parent'];bone=src['bones'][bi]['name']
            w[bone]=w.get(bone,0)+value
        weights.append(mix_weights(w,w,0))
    # Clip triangles at the new collar top; shared edges share new vertices/weights.
    edges={};faces=[]
    for face in head_faces:
        if p[face,2].min()>=TOP:continue
        poly=[]
        for a,b in zip(face,np.roll(face,-1)):
            a=int(a);b=int(b);ina=p[a,2]<=TOP;inb=p[b,2]<=TOP
            if ina:poly.append(remap[a])
            if ina!=inb:
                key=tuple(sorted((a,b)))
                if key not in edges:
                    t=float((TOP-p[a,2])/(p[b,2]-p[a,2]))
                    edges[key]=len(pos);pos.append((p[a]+(p[b]-p[a])*t).tolist())
                    weights.append(mix_weights(weights[remap[a]],weights[remap[b]],t))
                poly.append(edges[key])
        for j in range(1,len(poly)-1):faces.append([poly[0],poly[j],poly[j+1]])
    used=sorted({v for face in faces for v in face});r={v:i for i,v in enumerate(used)}
    pos=np.array([pos[v] for v in used]);weights=[weights[v] for v in used];faces=[[r[v] for v in face] for face in faces]
    ns=normals(pos,faces)
    edge_count=Counter(tuple(sorted((a,b))) for face in faces for a,b in zip(face,np.roll(face,-1)))
    boundary=[e for e,count in edge_count.items() if count==1]
    top_edges=[e for e in boundary if min(pos[list(e),2])>TOP-.001]
    bottom={v for e in boundary if e not in top_edges for v in e}
    # Keep the original matching neckline weights and close the old join.
    # The surface eases to 1.8 mm cloth clearance; the original body stays unchanged.
    bp=pos[sorted(bottom)]
    distance=np.min(np.linalg.norm(pos[:,None,:]-bp[None,:,:],axis=2),axis=1)
    t=np.clip(distance/1.2,0,1);t=t*t*(3-2*t)
    # The independent head has its own facial neck weights. Match its common
    # neck ancestors while retaining the exact native body weights at the join.
    head_path=O/'NeckClosure/native_head_neck.json'
    head=json.loads(head_path.read_text())
    head_ids={v['index']:k for k,v in head['bones'].items()}
    head_positions=np.array(head['positions']);near=np.empty(len(pos),dtype=int);near_dist=np.empty(len(pos))
    for start in range(0,len(pos),256):
        delta=pos[start:start+256,None,:]-head_positions[None,:,:]
        squared=np.sum(delta*delta,axis=2);index=np.argmin(squared,axis=1)
        near[start:start+len(index)]=index;near_dist[start:start+len(index)]=np.sqrt(squared[np.arange(len(index)),index])
    for vi,hi in enumerate(near):
        if near_dist[vi]>.03:continue
        mapped={}
        for name,value in head['weights'][hi].items():
            while name not in native['bones']:name=head_ids[head['bones'][name]['parent']]
            mapped[name]=mapped.get(name,0)+value
        weights[vi]=mix_weights(weights[vi],mapped,float(t[vi]))
    # A quarter-millimetre at the old join and 1.8 mm at the throat were too
    # close to the separate facial skin. Give the throat bounded movement room.
    front=np.clip((-ns[:,1]-.1)/.6,0,1)
    throat=np.exp(-np.power(pos[:,0]/5.0,4))*front
    offset=.18+.14*t+.14*throat*t
    pos=pos+ns*offset[:,None]
    top_ids=sorted({v for e in top_edges for v in e})
    # A rounded return lip uses the same weights; no opaque cap across the neck hole.
    outpos=pos.tolist();outer_count=len(outpos)
    rings=[{v:v for v in top_ids}]
    for inward,down in ((.18,.045),(.72,.16),(1.0,.95)):
        ring={}
        for v in top_ids:
            thickness=max(.12,float(offset[v])-.025)
            ring[v]=len(outpos);outpos.append((pos[v]-ns[v]*thickness*inward-np.array([0,0,down])).tolist());weights.append(dict(weights[v]))
        rings.append(ring)
    directed={tuple(sorted((a,b))):(a,b) for face in faces for a,b in zip(face,np.roll(face,-1))}
    for a,b in top_edges:
        a,b=directed[tuple(sorted((a,b)))]
        for ra,rb in zip(rings,rings[1:]):
            faces.extend([[ra[b],ra[a],rb[a]],[ra[b],rb[a],rb[b]]])
    # Overlap the neckline-to-chest join instead of leaving two exposed edges.
    # This strip uses the matching body-edge weights and never spans the neck hole.
    underlap={}
    for v in sorted(bottom):
        underlap[v]=len(outpos)
        outpos.append((pos[v]-np.array([0,0,.65])).tolist())
        weights.append(dict(weights[v]))
    for a,b in boundary:
        if a not in bottom or b not in bottom:continue
        a,b=directed[tuple(sorted((a,b)))]
        faces.extend([[b,a,underlap[a]],[b,underlap[a],underlap[b]]])
    faces=[[int(v) for v in face] for face in faces]
    nn=normals(outpos,faces);outpos=np.array(outpos)
    d=dict(positions=outpos.tolist(),triangles=faces,weights=weights,
           uv=[[[float(math.atan2(outpos[v,1]+1,outpos[v,0])/(2*math.pi)+.5),float((TOP-outpos[v,2])/18)] for v in face] for face in faces],
           normals=[[nn[v].tolist() for v in face] for face in faces],triangle_materials=[0]*len(faces),
           materials=[DEST+'/Materials/MI_ST6Torso_Jason.MI_ST6Torso_Jason'],material_slots=['ST6NeckFabric'],
           binding_source=native['source'],bones=native['bones'])
    collar_vertices=len(d['positions']);collar_triangles=len(d['triangles'])
    hem=make_hem(native);append(d,hem)
    d['materials']=d['materials'][:1];d['material_slots']=['ST6NeckAndHemFabric'];d['triangle_materials']=[0]*len(d['triangles'])
    write('collar.json',d)
    sleeve=json.loads((OLD/'Authored/Jason_ue_st6_sleeves.json').read_text());append(sleeve,d);write('world_shirt.json',sleeve)
    pickup=json.loads((OLD/'pickup.json').read_text())
    # Recover the original presentation recentering exactly from its pelvis origin.
    center=np.array(native['bones']['pelvis']['position'])-np.array(pickup['body_origin'])
    pc=copy.deepcopy(d);pc['positions']=(np.array(d['positions'])-center).tolist();pc['materials']=[DEST+'/Materials/MI_ST6Torso_Pickup.MI_ST6Torso_Pickup']
    append(pickup,pc)
    pickup['materials'][1]=DEST+'/Materials/MI_ST6Torso_Pickup.MI_ST6Torso_Pickup'
    pickup['materials'][2]=DEST+'/Materials/M_ST6Fabric.M_ST6Fabric'
    pickup['collar_top']=float(TOP-center[2]);write('pickup.json',pickup)
    bounds=outpos[top_ids]
    report=dict(profile='Jason',native_neck_source=src['source'],old_neck_width_cm=float(np.ptp(bp[:,0])),
                new_neck_width_cm=float(np.ptp(bounds[:,0])),collar_top_cm=TOP,
                collar_vertices=collar_vertices,collar_triangles=collar_triangles,hem_triangles=len(hem['triangles']),hem_bottom_cm=95,
                clearance_cm=[float(offset.min()),float(offset.max())],inner_return_cm=.95,chest_underlap_cm=.65,
                neck_weight_source=head['source'],
                original_sleeves_preserved=True,original_body_preserved=True,game_tested=False)
    write('author_receipt.json',report);print(json.dumps(report,indent=2))

if __name__=='__main__':main()
