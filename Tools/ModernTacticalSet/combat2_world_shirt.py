"""Construct continuous combat-shirt cloth directly on each native body."""
import sys,copy,math
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write,subset,merge,unit
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR2';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR2'
def smooth(v):v=np.clip(v,0,1);return v*v*(3-2*v)
def outward(p,f):
    n=np.zeros_like(p);cross=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    for k in range(3):np.add.at(n,f[:,k],cross)
    return n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
def build(rig):
    native=read(R/'Inputs'/f'Body_{rig}.json');body=subset(native,[m in [0,1,3,8,9] for m in native['triangle_materials']]);bones={b['name']:b for b in body['bones']};byid={b['index']:b['name'] for b in body['bones']}
    bm=bmesh.new();deform=bm.verts.layers.deform.verify();verts=[bm.verts.new(v) for v in body['positions']]
    for v,ws in zip(verts,body['weights']):
        for bi,w in ws:v[deform][bi]=w
    for f in body['triangles']:bm.faces.new([verts[i] for i in f])
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0005)
    clav=(bones['clavicle_l']['position'][2]+bones['clavicle_r']['position'][2])*.5;neck=clav+2.9
    # The native head opening is already an anatomical neck loop. A global
    # horizontal cut would also cut the shoulder caps at a crew-neck height.
    # Shape only that existing neck rim, retaining the continuous shoulders.
    for v in bm.verts:
        if abs(v.co.x)<7.5 and v.co.z>clav+1 and any(e.is_boundary for e in v.link_edges):v.co.z-=.60
    for side in ['l','r']:
        elbow=np.array(bones['lowerarm_'+side]['position']);wrist=np.array(bones['hand_'+side]['position']);axis=unit(wrist-elbow)
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=Vector(wrist-axis*.55),plane_no=Vector(-axis),clear_inner=True,clear_outer=False,dist=.00001)
    # Level the actual open hem, retaining all native interpolation and topology.
    for v in bm.verts:
        if v.co.z<108 and any(e.is_boundary for e in v.link_edges) and abs(v.co.x)<23:v.co.z=94.5 if rig=='Jason' else 93.5
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
    p=np.array([v.co[:] for v in bm.verts]);f=np.array([[v.index for v in face.verts] for face in bm.faces]);ws=[]
    for v in bm.verts:
        rows=sorted(v[deform].items(),key=lambda t:-t[1])[:8];total=sum(w for _,w in rows);ws.append([[bi,w/total] for bi,w in rows])
    boundary=[(e.link_loops[0].vert.index,e.link_loops[0].link_loop_next.vert.index) for e in bm.edges if e.is_boundary];bm.free();n=outward(p,f)
    arm=np.array([sum(w for bi,w in weights if any(s in byid[bi] for s in ['upperarm','lowerarm','hand_','twist'])) for weights in ws]);arm=np.clip(arm,0,1)
    clearance=np.full(len(p),.32);uv=np.zeros((len(p),2));uv[:,0]=p[:,0]/8;uv[:,1]=p[:,2]/8;arm_uv=uv.copy();elbows=np.zeros(len(p));cuffs=np.zeros(len(p))
    for side,sign in [('l',1),('r',-1)]:
        ids=np.flatnonzero(p[:,0]*sign>0);a,e,w=[np.array(bones[k+'_'+side]['position']) for k in ['upperarm','lowerarm','hand']];upper,lower=unit(e-a),unit(w-e)
        longitudinal=(p[ids]-e)@lower;mix=smooth((longitudinal+4)/8);axis=(1-mix[:,None])*upper+mix[:,None]*lower;axis/=np.linalg.norm(axis,axis=1,keepdims=True)
        seed=np.cross(upper,lower)
        if np.linalg.norm(seed)<.1:seed=np.array([0.,1.,0.])
        seed=unit(seed);cross=np.cross(axis,seed);q=p[ids]-e;theta=np.arctan2(np.einsum('ij,ij->i',q,cross),q@seed);along=np.linalg.norm(e-a)+np.einsum('ij,ij->i',q,axis);wrist_dist=-(p[ids]-w)@lower
        elbow=np.exp(-(longitudinal/6.)**2);cuff=1-smooth((wrist_dist-2)/4);elbows[ids]=elbow;cuffs[ids]=cuff
        # Compression folds are confined to real elbow and cuff loading zones.
        fold=(.36*np.sin(longitudinal*1.18+.75*np.cos(theta))+.12*np.sin(longitudinal*.62-theta*2))*elbow
        fold+=.22*np.sin(wrist_dist*1.7+.55*np.sin(theta*2))*np.exp(-((wrist_dist-6)/3.1)**2)
        ease=.76+.18*np.cos(theta)**2-.48*cuff+fold
        clearance[ids]+=arm[ids]*ease
        arm_uv[ids]=np.column_stack([theta*5.8/8,along/8])
    side=np.clip((abs(p[:,0])-8)/10,0,1);hem=smooth((111-p[:,2])/14)
    clearance+=(1-arm)*(.13*np.sin((p[:,2]-98)*1.2+abs(p[:,0])*.3)*hem*side)
    outer=p+n*clearance[:,None];thickness=.09+.035*cuffs;inner=outer-n*thickness[:,None]
    # Each opening has a real return, matched weights and a solid edge, no caps.
    count=len(p);d=dict(source=native['source'],rig=rig,bones=native['bones'],positions=outer.tolist()+inner.tolist(),weights=ws+copy.deepcopy(ws),triangles=[],normals=[],uv=[],triangle_materials=[],material_slots=['CombatRipstop','CombatStretch','CombatCuff','CombatLining'],materials=[DEST+'/Materials/M_'+m for m in ['CombatRipstop','CombatStretch','CombatCuff','CombatLining']])
    for face in f:
        a=float(arm[face].mean());is_arm=a>.30;mi=2 if cuffs[face].mean()>.72 and is_arm else 0 if is_arm or (p[face,2].mean()>clav-3 and abs(p[face,0].mean())>7) else 1
        tex=(arm_uv if is_arm else uv)[face].copy()
        if is_arm and np.ptp(tex[:,0])>2:tex[tex[:,0]<0,0]+=2*math.pi*5.8/8
        for ids,coords,slot in [(face,tex,mi),(face[::-1]+count,tex[::-1],3)]:d['triangles'].append(ids.tolist());d['uv'].append(coords.tolist());d['triangle_materials'].append(slot)
    for a,b in boundary:
        ids=[b,a,a+count,b+count];length=np.linalg.norm(p[a]-p[b]);tex=[[0,0],[length/8,0],[length/8,.012],[0,.012]]
        for tri in [(0,1,2),(0,2,3)]:d['triangles'].append([ids[i] for i in tri]);d['uv'].append([tex[i] for i in tri]);d['triangle_materials'].append(2)
    dp=np.array(d['positions']);df=np.array(d['triangles']);dn=outward(dp,df);d['normals']=dn[df].tolist();d['contract']='New continuous native-body garment with shaped raglan volume, anatomically placed compression folds, paired inner cloth and actual turned openings; independent male/female source'
    write(R/'Authored'/f'shirt_cloth_{rig}.json',d)
    # Keep the actual neck between the new crew opening and the unchanged head seam.
    neckpatch=subset(native,[m==3 and max(native['positions'][i][2] for i in face)>neck-.8 for face,m in zip(native['triangles'],native['triangle_materials'])]);neckpatch['materials']=[native['materials'][3]];neckpatch['material_slots']=['NATIVE:'+native['materials'][3]];neckpatch['triangle_materials']=[0]*len(neckpatch['triangles'])
    write(R/'Authored'/f'neck_skin_{rig}.json',neckpatch)
    write(R/'Authored'/f'shirt_construction_{rig}.json',dict(vertices=len(dp),triangles=len(df),boundary_edges=len(boundary),neck_height_cm=neck,clearance_cm=[float(clearance.min()),float(clearance.max())],thickness_cm=[float(thickness.min()),float(thickness.max())],native_source=native['source']))
    print('TS01_R2_CONTINUOUS_SHIRT',rig,len(dp),len(df),flush=True)
for rig in ['Jason','Kaitlin']:build(rig)
