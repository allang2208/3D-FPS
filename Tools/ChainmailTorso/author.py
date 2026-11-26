"""Repair the mail shell once, deriving its lining from the same native binding.

Background Blender authoring. Only the torso families are produced here.
"""
import copy, gc, json, math, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path('D:/FPS3D/FPSGAME'); R=P/'SourceAssets/ChainmailTorsoRepair20261021'
ITEM='ue_chainmail_shirt'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
from geometry import unit, smooth, norm_weights, blend_weights, normals, boundary, vertex, face, tube, read, write

def loops(fs):
    adj={}
    for a,b in boundary(fs):adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
    remaining=set(adj);result=[]
    while remaining:
        start=min(remaining);ring=[start];previous=None;current=start
        while True:
            nxt=next(v for v in adj[current] if v!=previous)
            if nxt==start:break
            ring.append(nxt);previous,current=current,nxt
        remaining.difference_update(ring);result.append(ring)
    return result

def bary(p,tri):
    a,b=tri[1]-tri[0],tri[2]-tri[0];q=p-tri[0]
    aa,ab,bb=a@a,a@b,b@b;den=max(aa*bb-ab*ab,1e-12)
    v=(bb*(q@a)-ab*(q@b))/den;w=(aa*(q@b)-ab*(q@a))/den
    values=np.maximum([1-v-w,v,w],0);return values/max(sum(values),1e-12)

def adjacency(fs,n):
    e=np.unique(np.sort(np.concatenate([fs[:,[0,1]],fs[:,[1,2]],fs[:,[2,0]]]),axis=1),axis=0)
    rows=np.r_[e[:,0],e[:,1]];cols=np.r_[e[:,1],e[:,0]];count=np.bincount(rows,minlength=n)
    def mean(v):
        out=np.zeros_like(v);np.add.at(out,rows,v[cols]);return out/np.maximum(count,1).reshape((-1,)+(1,)*(v.ndim-1))
    return mean

def unwrap(ps,fs,source_uv):
    # Preserve the old tailoring seam locations, but solve their UVs on the
    # repaired surface instead of stretching the donor's body atlas.
    mesh=bpy.data.meshes.new('MailMetricCharts');mesh.from_pydata([(p[0],-p[1],p[2]) for p in ps],[],fs.tolist());mesh.update()
    ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
    layer=mesh.uv_layers.new(name='MetricMail');edge_uv={};seams=set()
    for poly,uv in zip(mesh.polygons,source_uv):
        for ci,li in enumerate(poly.loop_indices):layer.data[li].uv=(uv[ci][0],1-uv[ci][1])
        for ci in range(3):
            a,b=int(fs[poly.index,ci]),int(fs[poly.index,(ci+1)%3]);va,vb=uv[ci],uv[(ci+1)%3]
            key=tuple(sorted((a,b)));value=np.array([va,vb] if a<b else [vb,va])
            if key in edge_uv and np.max(np.abs(edge_uv[key]-value))>1e-5:seams.add(key)
            else:edge_uv[key]=value
    for e in mesh.edges:e.use_seam=tuple(sorted(e.vertices)) in seams
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.unwrap(method='ANGLE_BASED',margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
    layer=mesh.uv_layers.active
    uv=np.array([[[layer.data[i].uv.x,1-layer.data[i].uv.y] for i in f.loop_indices] for f in mesh.polygons])
    sys.path.insert(0,str(P/'Tools/ModularOutfit'))
    from author_chainmail_shirt import mail_uv
    uv,charts=mail_uv(ps,fs,uv)
    bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(mesh)
    return uv,charts

def repair(profile):
    source=read(R/'Sources'/(profile+'.json'));canonical=read(P/'SourceAssets/ChainmailInterlace20260929/Authored/Body.json')
    cp=np.array(canonical['positions']);cf=np.array(canonical['triangles']);n=len(cp)//2
    outer_ids=np.flatnonzero(cf.max(1)<n);fs=cf[outer_ids].copy();srcp=np.array(source['positions']);srcf=np.array(source['triangles'])
    mapping={}
    for a,b in zip(cf,srcf):
        for ca,cb in zip(a,b):
            if ca in mapping and np.linalg.norm(srcp[mapping[ca]]-srcp[cb])>1e-5:raise RuntimeError('Source topology no longer matches mail master')
            mapping[int(ca)]=int(cb)
    old=np.array([srcp[mapping[i]] for i in range(2*n)]);ps=old[:n].copy();ws=[copy.deepcopy(source['weights'][mapping[i]]) for i in range(n)]
    ns=normals(ps,fs);gap=np.sum((ps-old[n:])*ns,axis=1);upper=(ps[:,2]>128)&(abs(ps[:,0])<32)
    diagnostic=dict(source=source['source'],source_sha256=source['source_sha256'],inverted_layer_pairs=int(sum(gap<0)),chest_shoulder_inverted_pairs=int(sum((gap<0)&upper)),original_all_faces_used_mail_material=all(m==0 for m in source['triangle_materials']))
    rings=loops(fs);neck_ring=next(l for l in rings if len(l)==52);slit=next(l for l in rings if len(l)==8)
    # Fill the obsolete donor-shirt chest slit with a single shared fan point.
    center=ps[slit].mean(0);ci=len(ps);ps=np.vstack((ps,center));ws.append(norm_weights({k:sum(ws[i].get(k,0) for i in slit)/len(slit) for k in set().union(*(ws[i] for i in slit))}))
    tex=[source['uv'][i] for i in outer_ids];new=[]
    for a,b in zip(slit,np.roll(slit,-1)):
        tri=[a,b,ci]
        if np.cross(ps[b]-ps[a],center-ps[a])[1]>0:tri.reverse()
        new.append(tri);tex.append([[ps[v,0]/25,ps[v,2]/25] for v in tri])
    fs=np.vstack((fs,new));n=len(ps);average=adjacency(fs,n)
    neck=np.array(source['bones']['neck_01']['position']);canonical_neck=np.array(canonical['bones']['neck_01']['position'])
    theta=np.arctan2(cp[neck_ring,0]-canonical_neck[0],cp[neck_ring,1]-canonical_neck[1])
    skin=read(R/'Sources/NativeSkin_Jason.json') if profile=='Jason' else read(P/'SourceAssets/JasonPlayer20261003/NativeSkin.json')
    sp=np.array(skin['positions']);sf=np.array(skin['triangles']);sm=np.array(skin['triangle_materials']);sf=sf[np.isin(sm,[1,2] if profile=='Jason' else [0,1,2,3,4])]
    tree=BVHTree.FromPolygons([Vector(p) for p in sp],sf.tolist(),all_triangles=True)
    targets=[]
    for angle in theta:
        direction=np.array([math.sin(angle),math.cos(angle),0]);z=neck[2]+.4-1.8*math.cos(angle)
        c=np.r_[neck[:2],z];hit,_,_,_=tree.ray_cast(Vector(c+direction*24),Vector(-direction),24)
        if hit is None:raise RuntimeError('Neck skin sample missed '+profile)
        radius=max(0,float((np.array(hit)-c)@direction))+.5
        targets.append(c+direction*radius)
    targets=np.array(targets)
    # The fitted old neckline had fallen down onto the clavicles. Spread its
    # correction continuously through the upper shirt; do not add a cover patch.
    active=(ps[:,2]>neck[2]-25)&(abs(ps[:,0]-neck[0])<30)
    delta=np.zeros_like(ps);delta[neck_ring]=targets-ps[neck_ring];fixed=delta[neck_ring].copy()
    for _ in range(360):
        delta=.35*delta+.65*average(delta);delta[~active]=0;delta[neck_ring]=fixed
    ps+=delta;area=smooth((ps[:,2]-(neck[2]-25))/12)*smooth((33-abs(ps[:,0]-neck[0]))/7);area[neck_ring]=0
    for _ in range(24):
        ps+=.30*area[:,None]*(average(ps)-ps)
        ps-=.29*area[:,None]*(average(ps)-ps)
    # Project the OUTER surface once. The inner surface is never independently
    # projected or rebound; this is the source of the previous layer inversion.
    clearance_ids=np.flatnonzero(active)
    skin_names={b['index']:b['name'] for b in skin['bones']} if isinstance(skin['bones'],list) else None
    def skin_weight(i):return {skin_names[b]:v for b,v in skin['weights'][i]} if skin_names else skin['weights'][i]
    for _ in range(4):
        corrections=np.zeros_like(ps)
        for i in clearance_ids:
            hit,nn,ti,dist=tree.find_nearest(Vector(ps[i]));out=-np.array(nn);signed=float((ps[i]-np.array(hit))@out)
            if signed<.46:corrections[i]=out*(.46-signed)
        corrections=.75*corrections+.25*average(corrections);ps+=corrections;ps[neck_ring]=targets
    if profile=='Jason':
        for i in clearance_ids:
            hit,_,ti,_=tree.find_nearest(Vector(ps[i]));tri=sf[ti];bc=bary(np.array(hit),sp[tri]);skin_ws=[skin_weight(v) for v in tri]
            projected=norm_weights({k:sum(w.get(k,0)*a for w,a in zip(skin_ws,bc)) for k in set().union(*skin_ws)})
            ws[i]=blend_weights(ws[i],projected,float(smooth((old[min(i,len(old)-1),2]-(neck[2]-24))/10)))
    # The narrow donor slit was locally folded. Decide its patch orientation
    # after the folds have been relaxed, in the final chest surface frame.
    for fi in range(len(outer_ids),len(fs)):
        tri=fs[fi]
        if np.cross(ps[tri[1]]-ps[tri[0]],ps[tri[2]]-ps[tri[0]])[1]>0:
            fs[fi]=tri[::-1];tex[fi]=tex[fi][::-1]
    ns=normals(ps,fs);uv,charts=unwrap(ps,fs,tex)
    d=dict(profile=profile,binding_source=source['binding_source'],skeleton=source['skeleton'],bones=source['bones'],positions=[],weights=[],triangles=[],uv=[],normals=[],triangle_materials=[],materials=source['materials'],material_slots=source['material_slots'],contract='ChainmailTorsoRepair20261021: closed chest slit; native skin fitted continuous neckline and shoulders; shared outer/lining skin weights; metric unwrap; original grey steel ring PBR')
    for amount in (0.,-.18):
        for p,normal,w in zip(ps,ns,ws):vertex(d,p+normal*amount,w)
    for tri,tex in zip(fs,uv):
        face(d,tri,0,tex);d['normals'].append(ns[tri].tolist())
        face(d,[int(i+n) for i in tri[::-1]],2,tex[::-1]);d['normals'].append((-ns[tri[::-1]]).tolist())
    for a,b in boundary(fs):
        ids=[b,a,a+n,b+n];length=float(np.linalg.norm(ps[a]-ps[b]))/25;tex=[[0,0],[length,0],[length,.18/25],[0,.18/25]]
        for t in ((0,1,2),(0,2,3)):
            tri=[ids[i] for i in t];face(d,tri,2,[tex[i] for i in t]);pp=np.array([d['positions'][i] for i in tri]);normal=unit(-np.cross(pp[1]-pp[0],pp[2]-pp[0]));d['normals'].append([normal.tolist()]*3)
    # A fine rolled dark binding closes the edge rather than a floating collar.
    first=len(d['triangles']);start=len(d['positions']);path=ps[neck_ring]-ns[neck_ring]*.045
    tube(d,path,.115,2,lambda p:ws[neck_ring[int(np.argmin(np.linalg.norm(path-p,axis=1)))]],closed=True,sides=8)
    added=np.array(d['triangles'][first:]);vns=normals(np.array(d['positions']),added);d['normals'].extend(vns[added].tolist())
    diagnostic.update(closed_chest_slit_vertices=len(slit),paired_shell_thickness_cm=.18,shared_layer_weights=True,neck_binding_radius_cm=.115,metric_uv_charts=len(charts),output_vertices=len(d['positions']),output_triangles=len(d['triangles']),max_neckline_correction_cm=float(np.linalg.norm(fixed,axis=1).max()))
    d['repair']=diagnostic;write(R/'Authored'/ITEM/(profile+'.json'),d)
    print('CHAINMAIL_TORSO_AUTHORED',profile,diagnostic,flush=True)
    return d

def owner(d):
    result=copy.deepcopy(d);result['profile']='Owner_Jason';nslots=len(d['material_slots']);result['materials']*=2
    result['material_slots']+=['OwnerHidden_'+s for s in d['material_slots']]
    for k in ('triangles','normals','uv','triangle_materials'):result[k]=[]
    names={v['index']:k for k,v in d['bones'].items()};arms=set()
    for name in d['bones']:
        cur=name
        while cur in d['bones']:
            if cur in ('upperarm_l','upperarm_r'):arms.add(name);break
            cur=names.get(d['bones'][cur]['parent'])
    mass=np.array([sum(v for k,v in w.items() if k in arms) for w in d['weights']]);ps=np.array(d['positions']);lookup={}
    for fi,tri in enumerate(d['triangles']):
        vals=mass[tri];slot=d['triangle_materials'][fi]
        if min(vals)>=.4 or max(vals)<=.4:
            face(result,tri,slot+(nslots if min(vals)>=.4 else 0),d['uv'][fi]);result['normals'].append(d['normals'][fi]);continue
        for hidden in (False,True):
            part=[];poly=[(np.eye(3)[i],vals[i]) for i in range(3)]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                ia=a[1]>=.4 if hidden else a[1]<=.4;ib=b[1]>=.4 if hidden else b[1]<=.4
                if ia:part.append(a[0])
                if ia!=ib:part.append(a[0]+(.4-a[1])/(b[1]-a[1])*(b[0]-a[0]))
            for j in range(1,len(part)-1):
                indices=[];tex=[];ns=[]
                for bc in (part[0],part[j],part[j+1]):
                    point=bc@ps[tri];key=tuple(np.round(point,7))
                    if key not in lookup:lookup[key]=vertex(result,point,norm_weights({k:sum(d['weights'][v].get(k,0)*a for v,a in zip(tri,bc)) for k in set().union(*(d['weights'][v] for v in tri))}))
                    indices.append(lookup[key]);tex.append(bc@np.array(d['uv'][fi]));ns.append(unit(bc@np.array(d['normals'][fi])).tolist())
                if len(set(indices))<3:continue
                face(result,indices,slot+(nslots if hidden else 0),tex);result['normals'].append(ns)
    write(R/'Authored'/ITEM/'Owner_Jason.json',result)
    print('CHAINMAIL_TORSO_AUTHORED Owner_Jason',len(result['triangles']),flush=True)

def main():
    reports=[]
    for profile in ('Body','Jason'):
        bpy.ops.wm.read_factory_settings(use_empty=True);d=repair(profile);reports.append(d['repair'])
        if profile=='Jason':owner(d)
        del d;gc.collect()
    write(R/'authored.json',dict(completed=True,profiles=['Body','Jason','Owner_Jason'],diagnosis=reports,first_person_sleeves_changed=False,runtime_tested=False))
if __name__=='__main__':main()
