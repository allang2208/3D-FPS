"""Author one M4 tailoring candidate; never rewrites active equipment or animation.

The native V7 seam and binding remain the fit reference. Tailoring is displaced
outward in the existing surface, so panel edges do not introduce stacked shells.
"""
import json
import hashlib
from pathlib import Path
import numpy as np

P = Path(__file__).resolve().parents[2]
ROOT = P / 'SourceAssets/ModularOutfit20260927/TailoredFingerlessCandidate'
SOURCE = P / 'SourceAssets/ModularOutfit20260926/FingerlessHuntV2/FullShell/M4.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def smooth(a, b, v):
    x = np.clip((v-a)/(b-a), 0, 1)
    return x*x*(3-2*x)


def gauss(x, width):
    return np.exp(-(x/width)**2)


def tailoring(x, y, palm):
    """Centimetre-scale pattern: thumb gusset, curved yoke, closed wrist tab.

    Returns geometry height, fine bump height, thread, panel dye and polish.
    Palm relief is deliberately shallower than the dorsal construction.
    """
    back = 1-palm
    gusset_x = -1.62-.047*(y-3.6)**2
    gusset = np.abs(x-gusset_x) / np.sqrt(1+(.094*(y-3.6))**2)
    gusset_end = smooth(-1.0, -.4, y)*(1-smooth(6.8, 7.5, y))
    yoke_y = 7.25-.045*x*x
    yoke = np.abs(y-yoke_y)/np.sqrt(1+(.09*x)**2)
    yoke_end = smooth(-4.4,-3.6,x)*(1-smooth(3.5,4.3,x))*back
    # Rounded closed leather tab embossed in the same continuous surface.
    qx = np.abs(x+.15)-3.3
    qy = np.abs(y+1.9)-.47
    strap_sdf = np.sqrt(np.maximum(qx,0)**2+np.maximum(qy,0)**2)+np.minimum(np.maximum(qx,qy),0)-.22
    strap = (1-smooth(-.07,.08,strap_sdf))*back
    strap_edge = np.abs(strap_sdf+.16)
    seam = .052*gauss(gusset-.09,.095)*gusset_end*(.45+.55*back)
    seam += .044*gauss(yoke-.10,.09)*yoke_end
    seam += .105*strap
    seam += .024*gauss(strap_sdf,.07)*back
    # Directional folds fan out from the thumb and compress near the wrist.
    folds = np.zeros_like(x)
    for off, amp, width in [(.28,.065,.14),(.98,.044,.13),(1.58,.025,.11)]:
        line = off+.18*x+.065*x*x
        envelope = gauss(x+1.65,1.9)*gauss(y-1.0,2.0)
        folds += amp*gauss(y-line,width)*envelope
    folds += .040*gauss(y-(5.65+.22*x),.16)*gauss(x-2.0,1.3)*back
    folds += .025*gauss(y-(6.22+.15*x),.13)*gauss(x-2.4,1.0)*back
    relief = seam+folds*(.22+.78*back)
    dash_y = 1-smooth(.23,.40,np.abs(np.mod(y/.32,1)-.5))
    dash_x = 1-smooth(.23,.40,np.abs(np.mod(x/.32,1)-.5))
    thread = gauss(gusset-.23,.035)*dash_y*gusset_end
    thread += gauss(yoke-.23,.035)*dash_x*yoke_end
    strap_dash = np.where(qx>qy,dash_y,dash_x)
    thread += gauss(strap_edge,.032)*strap_dash*back
    thread = np.clip(thread,0,1)
    # Stitch dimples and soft seam puckering are material detail, not holes.
    pucker = .006*gauss(gusset-.30,.17)*np.sin(y*19)*gusset_end
    fine = .009*thread+pucker-.012*gauss(gusset,.038)*gusset_end
    fine -= .009*gauss(yoke,.034)*yoke_end
    fine -= .012*gauss(strap_sdf-.025,.04)*back
    panel = 1-.10*(1-smooth(-.05,.08,x-gusset_x))*gusset_end
    panel *= 1-.07*smooth(-.06,.08,y-yoke_y)*back
    panel *= 1-.16*strap
    polish = np.clip(.36*palm+.42*strap+.18*gauss(gusset-.1,.14)*gusset_end,0,1)
    return relief, fine, thread, panel, polish


def frame(bones, anatomy, side):
    wrist=np.array(bones['hand_'+side]['position'])
    z=unit(np.array(anatomy[side]['dorsal']))
    y=np.array(bones['middle_01_'+side]['position'])-wrist
    y=unit(y-z*(y@z))
    x=-np.cross(y,z)
    if side=='l': x=-x
    return np.array([x,y,z]),wrist


def author(source=SOURCE, output_root=ROOT, pattern_local=None):
    output_root.mkdir(parents=True,exist_ok=True)
    d=read(source)
    p=np.array(d['positions']);t=np.array(d['triangles'])
    normals=np.zeros_like(p);fields=np.zeros((len(p),2));inside=np.ones(len(p))
    for k in range(3):
        normals[t[:,k]]=np.array(d['normals'])[:,k]
        fields[t[:,k]]=np.array(d['uv1'])[:,k]
        inside[t[:,k]]=np.minimum(inside[t[:,k]],np.array(d['uv2'])[:,k,1])
    normals=unit(normals)
    anatomy=read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
    local=np.zeros_like(p) if pattern_local is None else np.asarray(pattern_local)
    if pattern_local is None:
        for side in ('l','r'):
            selected=np.array([sum(v for n,v in w.items() if n.endswith('_'+side))>.5 for w in d['weights']])
            f,wrist=frame(d['bones'],anatomy,side)
            local[selected]=(p[selected]-wrist)@f.T
    # One interior refinement pass resolves soft folds. Keep original boundary
    # edges intact so the exposed-skin companion retains its exact shared seam.
    from collections import Counter
    counts=Counter(tuple(sorted((int(f[k]),int(f[(k+1)%3])))) for f in t for k in range(3))
    pos=p.tolist();ns=normals.tolist();loc=local.tolist();fs=fields.tolist();ins=inside.tolist();weights=list(d['weights'])
    mids={}
    outer=(np.array(d['uv2'])[:,:,1]==0).all(1)
    for face in t[outer]:
        for k in range(3):
            a,b=sorted((int(face[k]),int(face[(k+1)%3])))
            if min(fields[a,1],fields[b,1])<1e-5: continue
            if (a,b) in mids: continue
            mids[a,b]=len(pos);pos.append(((p[a]+p[b])/2).tolist());ns.append(unit(normals[a]+normals[b]).tolist())
            loc.append(((local[a]+local[b])/2).tolist());fs.append(((fields[a]+fields[b])/2).tolist());ins.append(0.)
            w={n:(d['weights'][a].get(n,0)+d['weights'][b].get(n,0))/2 for n in d['weights'][a].keys()|d['weights'][b].keys()}
            weights.append(w)
    triangles=[];uvs={k:[] for k in ('uv','uv1','uv2')}
    for fi,face in enumerate(t):
        # Split edges in sequence; barycentric corners retain every source UV.
        polys=[[(int(face[j]),np.eye(3)[j]) for j in range(3)]]
        for j in range(3):
            a,b=int(face[j]),int(face[(j+1)%3]);mid=mids.get(tuple(sorted((a,b))))
            if mid is None: continue
            updated=[]
            for poly in polys:
                split=False
                for k in range(3):
                    v0,v1,v2=poly[k],poly[(k+1)%3],poly[(k+2)%3]
                    if {v0[0],v1[0]}=={a,b}:
                        m=(mid,(v0[1]+v1[1])/2)
                        updated.extend([[v0,m,v2],[m,v1,v2]]);split=True;break
                if not split: updated.append(poly)
            polys=updated
        for poly in polys:
            triangles.append([r[0] for r in poly])
            for key in uvs: uvs[key].append([(r[1]@np.array(d[key][fi])).tolist() for r in poly])
    p=np.array(pos);n=unit(np.array(ns));local=np.array(loc);fields=np.array(fs);inside=np.array(ins)
    height,*_=tailoring(local[:,0],local[:,1],fields[:,0])
    fade=smooth(.18,.6,fields[:,1])*(1-inside)
    p+=n*(height*fade)[:,None]
    t=np.array(triangles)
    # Recompute normals after sculpting; retain smooth normals at shared rims.
    face_n=-np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]])
    vn=np.zeros_like(p)
    for k in range(3):np.add.at(vn,t[:,k],face_n)
    vn=unit(vn)
    d.update(positions=p.tolist(),weights=weights,triangles=triangles,normals=vn[t].tolist(),**uvs)
    d['uv3']=np.stack(((local[t,0]+8)/16,(local[t,1]+5)/18),axis=-1).tolist()
    d['triangle_materials']=[0]*len(t)
    d['family']='TailoredFingerlessCandidate'
    d['contract']='M4 candidate only; shared native bindings and fixed root seams; sculpted leather tailoring; no animation changes'
    (output_root/(d['profile']+'_fullshell.json')).write_text(json.dumps(d,separators=(',',':')))
    recipe=dict(stage='representative_candidate',source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                profile=d['profile'],new_animations=0,active_equipment_changed=False,coverage_root_weight=d['coverage_root_weight'],
                structure=['thumb gusset seam','curved dorsal yoke','closed short wrist tab','directional wrist folds','bound finger openings'],
                geometry='continuous exterior relief; original exposed-skin boundaries and weights retained',
                render_contract='single empty right glove; no skin; transparent 320x320',runtime_tested=False)
    (output_root/(d['profile']+'-design.json')).write_text(json.dumps(recipe,indent=2)+'\n')
    if source==SOURCE and output_root==ROOT:
        (ROOT/'design.json').write_text(json.dumps(recipe,indent=2)+'\n')
    print('TAILORED_CANDIDATE_AUTHORED',d['profile'],len(p),len(t),flush=True)
    return d


if __name__=='__main__': author()
