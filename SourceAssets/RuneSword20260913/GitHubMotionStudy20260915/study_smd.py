import pathlib,re,json,math
import numpy as np

ROOT=pathlib.Path(__file__).parent

def read_smd(path):
    nodes={}; frames=[]; triangles=[]; section=None; frame=None
    lines=path.read_text().splitlines(); i=0
    while i<len(lines):
        s=lines[i].strip();i+=1
        if not s or s.startswith('//'):continue
        if s in ('nodes','skeleton','triangles'):section=s;continue
        if s=='end':section=None;continue
        if section=='nodes':
            m=re.match(r'(\d+) "([^"]+)" (-?\d+)',s)
            nodes[int(m[1])]=(m[2],int(m[3]))
        elif section=='skeleton':
            if s.startswith('time '):frame={};frames.append(frame)
            else:
                p=s.split();frame[int(p[0])]=list(map(float,p[1:7]))
        elif section=='triangles':
            tri=[]
            for k in range(3):
                p=lines[i].split();i+=1
                tri.append(list(map(float,p[1:4])))
            triangles.append(tri)
    return nodes,frames,np.array(triangles)

def matrix(v):
    x,y,z=v[3:];cx,sx=math.cos(x),math.sin(x);cy,sy=math.cos(y),math.sin(y);cz,sz=math.cos(z),math.sin(z)
    m=np.eye(4);m[:3,3]=v[:3]
    m[:3,:3]=np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])@np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])@np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
    return m

def world(nodes,frame):
    out={}
    def at(i):
        if i not in out:
            m=matrix(frame[i]);p=nodes[i][1];out[i]=at(p)@m if p>=0 else m
        return out[i]
    for i in nodes:at(i)
    return out

def rigid_parts(path,bindworld):
    from scipy.spatial import ConvexHull
    groups={}
    text=path.read_text().split('triangles\n',1)[1]
    for line in text.splitlines():
        p=line.split()
        if len(p)<9 or not p[0].lstrip('-').isdigit():continue
        groups.setdefault(int(p[0]),[]).append(list(map(float,p[1:4])))
    parts=[]
    for bone,vertices in groups.items():
        verts=np.unique(np.array(vertices),axis=0); inv=np.linalg.inv(bindworld[bone]);local=(inv@np.c_[verts,np.ones(len(verts))].T).T[:,:3]
        h=ConvexHull(local);ids=np.unique(h.simplices);lookup={old:new for new,old in enumerate(ids)}
        parts.append({'bone':bone,'vertices':local[ids].round(4).tolist(),'faces':[[lookup[i] for i in f] for f in h.simplices]})
    return parts

def run():
    clips=[]; meta=[]
    for weapon in ['bayonet','falchion','stiletto']:
        folder=ROOT/'decompiled'/weapon
        mesh=next(p for p in folder.glob('*.smd'))
        nodes,bind,tri=read_smd(mesh);bm=world(nodes,bind[0]); names={n:i for i,(n,p) in nodes.items()}
        parts=rigid_parts(mesh,bm)
        wid=names['v_weapon.knife']; inverse=np.linalg.inv(bm[wid]);verts=np.unique(tri.reshape(-1,3),axis=0)
        local=(inverse@np.c_[verts,np.ones(len(verts))].T).T[:,:3]
        # Convex hull is a source-mesh silhouette; hand is explicitly a bone proxy.
        from scipy.spatial import ConvexHull
        hull=ConvexHull(local);used=np.unique(hull.simplices);remap={old:new for new,old in enumerate(used)}
        hullverts=local[used];hullfaces=[[remap[x] for x in face] for face in hull.simplices]
        print(weapon,'mesh',mesh.name,'knife_local_bounds',local.min(0).round(2),local.max(0).round(2))
        for action in ['draw','lookat01','lookat02']:
            p=folder/f'v_csgo_{weapon}_anims'/f'{action}.smd'
            if not p.exists():continue
            ns,frames,_=read_smd(p);names={n:i for i,(n,p) in ns.items()}; wn=names['v_weapon.knife']
            sel=[i for i,(n,p) in ns.items() if '_R_' in n]; points=[];weapons=[];localhand=[];localweapon=[];localarm=[];part_transforms=[[] for _ in parts]
            tip_ids=[names['ValveBiped.Bip01_R_Finger'+str(j)+'2'] for j in range(5)]
            for f in frames:
                w=world(ns,f);pos=[w[i][:3,3] for i in sel]
                pos.extend([(w[i]@np.array([.8,0,0,1]))[:3] for i in tip_ids])
                points.append(np.array(pos).round(4).tolist());weapons.append(w[wn].round(6).tolist())
                for j,part in enumerate(parts):part_transforms[j].append(w[part['bone']].round(6).tolist())
                hand=w[names['ValveBiped.Bip01_R_Hand']];arm=w[names['ValveBiped.Bip01_R_Forearm']]
                localhand.append(np.linalg.inv(arm)@hand);localweapon.append(np.linalg.inv(hand)@w[wn]);localarm.append(arm)
            mapping={i:k for k,i in enumerate(sel)}
            edges=[[mapping[ns[i][1]],mapping[i]] for i in sel if ns[i][1] in mapping]
            edges.extend([[mapping[i],len(sel)+j] for j,i in enumerate(tip_ids)])
            clip={'name':weapon+'/'+action,'fps':30,'count':len(frames),'names':[ns[i][0].split('_R_')[-1] for i in sel]+['Tip'+str(j) for j in range(5)],'edges':edges,'points':points,'weapon':weapons,'vertices':hullverts.round(4).tolist(),'faces':hullfaces}
            clip['parts']=[{**part,'matrices':part_transforms[j]} for j,part in enumerate(parts)]
            clips.append(clip)
            def change(seq):
                a=seq[0][:3,:3];return [math.degrees(math.acos(float(np.clip((np.trace(a.T@x[:3,:3])-1)/2,-1,1)))) for x in seq]
            meta.append({'clip':clip['name'],'frames':len(frames),'duration':(len(frames)-1)/30,'wrist_local_from_start_deg':np.round(change(localhand),2).tolist(),'forearm_global_from_start_deg':np.round(change(localarm),2).tolist(),'weapon_relative_to_hand_from_start_deg':np.round(change(localweapon),2).tolist(),'weapon_in_hand_position':np.round([x[:3,3] for x in localweapon],3).tolist()})
            print(clip['name'], 'hand_at_start',points[0][sel.index(names['ValveBiped.Bip01_R_Hand'])], 'hand_at_end',points[-1][sel.index(names['ValveBiped.Bip01_R_Hand'])])
    (ROOT/'motion_data.json').write_text(json.dumps(clips,separators=(',',':')))
    (ROOT/'motion_metadata.json').write_text(json.dumps(meta,indent=2))

if __name__=='__main__':run()
