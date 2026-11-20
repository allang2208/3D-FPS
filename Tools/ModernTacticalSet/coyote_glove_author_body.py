"""Tailor the two third-person skins directly from their intact native hand surfaces."""
import numpy as np


def normalized(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1.e-10)


def build_body_native(d,source):
    p=np.asarray(source["positions"],float)
    f=np.asarray(source["triangles"],int)
    uv=np.asarray(source["uv"],float)
    material=np.asarray(source["triangle_materials"])
    skin_faces=np.flatnonzero(np.isin(material,[source["material_slots"].index(s) for s in ("SkinArms","SkinHands")]))
    native={b["index"]:b["name"] for b in source["bones"]}
    target={b["name"]:b["index"] for b in d["bones"]}
    bone={b["name"]:np.array(b["position"]) for b in d["bones"]}
    # Carry a common offset through the source UV cuts, including fingertip seams.
    weld,group=np.unique(p.round(5),axis=0,return_inverse=True)
    nsum=np.zeros_like(weld)
    face=f[skin_faces]
    cross=-np.cross(p[face[:,1]]-p[face[:,0]],p[face[:,2]]-p[face[:,0]])
    for c in range(3):np.add.at(nsum,group[face[:,c]],cross)
    vn=normalized(nsum)[group]
    out_p=[];out_n=[];out_uv=[];out_f=[];out_w=[];side_ids=[]
    cache={}
    for side in ("r","l"):
        wrist=bone["hand_"+side]
        along=normalized(bone["lowerarm_"+side]-wrist)
        dist=(p-wrist)@along
        limit=4.0
        chosen=skin_faces[(np.linalg.norm(p[face].mean(1)-wrist,axis=1)<25)&(dist[face].min(1)<limit)]
        rim={}

        def vert(i,j,t):
            if t<.000001:j=i;t=0.
            elif t>.999999:i=j;t=0.
            if i>j:i,j,t=j,i,1.-t
            key=(i,j,round(t,7))
            if key in cache:return cache[key]
            pos=p[i]*(1-t)+p[j]*t;n=normalized(vn[i]*(1-t)+vn[j]*t)
            ws={}
            for old,factor in ((i,1-t),(j,t)):
                for bid,w in source["weights"][old]:
                    b=target[native[bid]];ws[b]=ws.get(b,0.)+w*factor
            out_w.append([[k,float(w)] for k,w in sorted(ws.items(),key=lambda z:-z[1]) if w>1.e-9])
            idx=len(out_p);cache[key]=idx
            out_p.append(pos+n*.105);out_n.append(n);side_ids.append(side)
            return idx

        for idx in chosen:
            row=f[idx];poly=[];tc=[];hits=[]
            for c in range(3):
                i,j=row[c],row[(c+1)%3];ti,tj=dist[i]-limit,dist[j]-limit
                if ti<=0:
                    poly.append(vert(i,i,0.));tc.append(uv[idx,c])
                if (ti<=0)!=(tj<=0):
                    t=ti/(ti-tj);k=vert(i,j,t)
                    poly.append(k);tc.append((1-t)*uv[idx,c]+t*uv[idx,(c+1)%3]);hits.append(k)
            for q in range(1,len(poly)-1):
                tri=[poly[0],poly[q],poly[q+1]]
                if len(set(tri))==3:
                    out_f.append(tri);out_uv.append([tc[0],tc[q],tc[q+1]])
            if len(hits)==2 and hits[0]!=hits[1]:
                rim[tuple(sorted(hits))]=hits
        # Roll the cut edge towards the inside and add a short return.
        # This closes the exposed lip when the glove is worn without a sleeve.
        ring_ids=set(i for pair in rim for i in pair)
        lookup={}
        for i in ring_ids:
            for level,depth,height in ((1,.035,.032),(2,.11,.027),(3,.18,-.025),(4,.18,-.32)):
                idx=len(out_p);lookup[(i,level)]=idx;side_ids.append(side)
                out_p.append(out_p[i]-out_n[i]*depth+along*height)
                out_n.append(normalized((out_n[i]+along) if level==1 else (along if level==2 else -out_n[i])))
                out_w.append(out_w[i])
            lookup[(i,0)]=i
        for edge,(a,b) in rim.items():
            for level in range(4):
                v=[lookup[a,level],lookup[b,level],lookup[b,level+1],lookup[a,level+1]]
                for ff in ((v[0],v[1],v[2]),(v[0],v[2],v[3])):
                    points=np.array([out_p[j] for j in ff]);norm=np.mean([out_n[j] for j in ff],axis=0)
                    if np.cross(points[1]-points[0],points[2]-points[0])@norm>0:ff=ff[::-1]
                    out_f.append(ff);out_uv.append([(float(k),level*.02) for k in (0,.05,.10)])
    f=np.array(out_f);n=np.asarray(out_n)
    return np.asarray(out_p),f,n[f],np.array(out_uv),out_w,np.asarray(side_ids)
