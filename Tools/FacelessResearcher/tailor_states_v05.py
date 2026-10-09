"""Add special-state coat morphs to the accepted V04, preserving its base/keys."""
import bpy,json,math,ast
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009');ROOT=BASE/'V05'
TOOLS=Path('D:/FPS3D/FPSGAME/Tools/FacelessResearcher')
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V04/Authoring/FacelessResearcher_V04.blend'))
rig=bpy.data.objects['root'];body=bpy.data.objects['Researcher_CompleteBody']
coat=bpy.data.objects['Researcher_LabCoat_Continuous'];pants=bpy.data.objects['Researcher_Trousers']
scene=bpy.context.scene;names=[b.name for b in rig.data.bones];ni={n:i for i,n in enumerate(names)}
# Reuse only the pure numerical helpers, not V04's body/weight authoring steps.
module=ast.parse((TOOLS/'tailor_stable_v04.py').read_text(encoding='utf-8'))
needed={'pack','smooth','normalize','sparse','deform','tree','neighbors','average_grid','mapping','interpolate'}
helpers=ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in needed],type_ignores=[])
exec(compile(helpers,'researcher_cloth_field_helpers','exec'))
source=json.loads((ROOT/'state_source.json').read_text(encoding='utf-8'))
cp,cw=pack(coat);half=int(coat['outer_vertex_count'])
coat.data.calc_loop_triangles();ct=np.array([tuple(t.vertices) for t in coat.data.loop_triangles if all(i<half for i in t.vertices)])
coat_tree=tree(cp[:half],ct)
arm_ids=[ni[n] for n in names if n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky','wrist'))]
torso=(1-smooth(.025,.35,cw[:half,arm_ids].sum(1)))*(1-smooth(1.37,1.49,cp[:half,2]))
NZ,NA=40,64;Z0,Z1=.74,1.48;CY=.017
zz=np.linspace(Z0,Z1,NZ);aa=np.arange(NA)*2*math.pi/NA
radial=np.stack((np.sin(aa),-np.cos(aa),np.zeros(NA)),axis=1)
directions=np.tile(radial,(NZ,1));centers=np.column_stack((np.zeros(NZ*NA),np.full(NZ*NA,CY),np.repeat(zz,NA)))
radii=[];gridw=[]
def attachment(point):
    hit=coat_tree.find_nearest(Vector(point));tri=ct[hit[2]]
    abc=np.array(barycentric_transform(hit[0],*(Vector(cp[k]) for k in tri),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))))
    abc=np.maximum(abc,0);abc/=abc.sum()
    return tri,abc
for z in zz:
    rx=float(np.interp(z,[.74,1.05,1.14,1.25,1.36,1.44,1.48],[.252,.208,.183,.164,.191,.186,.153]))
    ry=float(np.interp(z,[.74,1.05,1.20,1.35,1.45,1.48],[.178,.145,.138,.173,.149,.128]))
    center=Vector((0,CY,z))
    for d in radial:
        expected=1/math.sqrt((d[0]/rx)**2+(d[1]/ry)**2)
        hit=coat_tree.ray_cast(center,Vector(d),.36)
        point=hit[0] if hit[0] is not None and abs((hit[0]-center).length-expected)<.06 else center+Vector(d)*expected
        tri,abc=attachment(point);radii.append((point-center).length);gridw.append(abc@cw[tri])
gw=average_grid(np.array(gridw).reshape(NZ,NA,-1),4).reshape(-1,len(names));gw[:,arm_ids]=0;gw=normalize(gw)
gr=average_grid(np.array(radii).reshape(NZ,NA),3).ravel();gp=centers+directions*gr[:,None];gs=sparse(gw)
ci,ca=mapping(cp[:half]);direction=cp[:half].copy();direction[:,1]-=CY;direction[:,2]=0
direction/=np.maximum(np.linalg.norm(direction,axis=1,keepdims=True),1.e-8)
details=[]
for o in scene.objects:
    if o.type!='MESH' or not o.name.startswith(('Researcher_HipPocket','Researcher_ChestPocket','Researcher_ID','Researcher_CentrePlacket','Researcher_CoatButton')):continue
    p,w=pack(o);pairs=[attachment(v) for v in p]
    details.append((o,p,np.array([pair[0] for pair in pairs]),np.array([pair[1] for pair in pairs])))
colliders=[]
for original in [body,pants]:
    temp=original.copy();temp.data=original.data.copy();bpy.context.collection.objects.link(temp)
    temp.hide_set(False);temp.modifiers.clear();temp.shape_key_clear();bpy.context.view_layer.objects.active=temp
    bpy.ops.object.select_all(action='DESELECT');temp.select_set(True)
    count=sum(len(p.vertices)-2 for p in temp.data.polygons)
    modifier=temp.modifiers.new('AuthoringContactProxy','DECIMATE');modifier.ratio=min(1.,14000/max(1,count))
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    p,w=pack(temp);temp.data.calc_loop_triangles();t=np.array([tuple(f.vertices) for f in temp.data.loop_triangles])
    if original==body:
        excluded=w[:,arm_ids].sum(1)>.25
        excluded|=w[:,[ni[n] for n in names if n.startswith(('head','neck'))]].sum(1)>.5
        t=t[~excluded[t].any(1)]
    colliders.append((p,sparse(w),t));bpy.data.objects.remove(temp,do_unlink=True)
offset=len(colliders[0][0]);triangles=np.vstack((colliders[0][2],colliders[1][2]+offset))
rest=np.vstack([p for p,s,t in colliders]);tz=rest[triangles,2];bands=[]
for ring in range(0,NZ,4):
    end=min(ring+4,NZ);included=(tz.min(1)<zz[end-1]+.065)&(tz.max(1)>zz[ring]-.065)
    bands.append((range(ring*NA,end*NA),triangles[included]))
curves={};manifest={}
for role,entry in source['clips'].items():
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=entry['file'],use_anim=True)
    imported=set(bpy.data.objects)-before;donor=next(o for o in imported if o.type=='ARMATURE')
    first,last=map(int,donor.animation_data.action.frame_range);fps=scene.render.fps/scene.render.fps_base
    frames=min(last-first+1,round(entry['duration']*fps)+1);step=max(1,round(fps/15))
    samples=sorted(set(range(0,frames,step))|{frames-1});fields=[]
    inv={n:(donor.matrix_world@donor.data.bones[n].matrix_local).inverted() for n in names}
    for frame in samples:
        scene.frame_set(first+frame);bpy.context.view_layer.update()
        mats=np.array([np.array(donor.matrix_world@donor.pose.bones[n].matrix@inv[n]) for n in names])
        posed=deform(gp,gs,mats);outward=deform(directions,gs,mats,True)
        lengths=np.linalg.norm(outward,axis=1);unit=outward/np.maximum(lengths[:,None],1.e-8)
        positions=np.vstack([deform(p,s,mats) for p,s,t in colliders]);ease=np.zeros(NZ*NA)
        for ids,tri in bands:
            collision=tree(positions,tri)
            for i in ids:
                p,d=posed[i],unit[i];reach=.10*lengths[i]
                hit=collision.ray_cast(Vector(p+d*reach),Vector(-d),reach+gr[i]*lengths[i])[0]
                if hit is not None:ease[i]=max(0.,(np.dot(np.array(hit)-p,d)+.021)/max(lengths[i],.4))
        ease=ease.reshape(NZ,NA)
        for _ in range(3):
            for axis in [0,1]:
                lo,hi=neighbors(ease,axis);ease=np.maximum(ease,np.maximum(lo,hi))
        fields.append(average_grid(ease,6))
        print('M05_SPECIAL_CLOTH',role,frame,flush=True)
    fields=np.array(fields);looping=role=='dizzy'
    def shift(x,k):return np.roll(x,k,axis=0) if looping else x[np.clip(np.arange(len(x))-k,0,len(x)-1)]
    filtered=np.maximum(fields,np.maximum(shift(fields,1),shift(fields,-1)))
    filtered=(shift(filtered,-2)+4*shift(filtered,-1)+6*filtered+4*shift(filtered,1)+shift(filtered,2))/16
    if looping:filtered[0]=filtered[-1]=(filtered[0]+filtered[-1])*.5
    keys=['FRS5_'+role+'_%03d'%f for f in samples]
    curves[role]={key:[float(np.interp(f,samples,[1. if s==sample else 0. for s in samples])) for f in range(frames)] for key,sample in zip(keys,samples)}
    manifest[role]={'fps':fps,'frames':frames,'samples':samples,'duration':entry['duration'],'source':entry['source'],'max_ease_m':float(filtered.max())}
    for key,field in zip(keys,filtered):
        corr=direction*(interpolate(field.ravel(),ci,ca)*torso)[:,None]
        shape=coat.shape_key_add(name=key);shape.data.foreach_set('co',(cp+np.vstack((corr,corr))).astype(np.float32).ravel())
        for o,p,tri,abc in details:
            shape=o.shape_key_add(name=key);shape.data.foreach_set('co',(p+interpolate(corr,tri,abc)).astype(np.float32).ravel())
    for o in imported:bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
for o in [coat]+[d[0] for d in details]:
    for key in o.data.shape_keys.key_blocks:key.value=0
scene.frame_set(0);bpy.context.view_layer.update()
(ROOT/'state_curves.json').write_text(json.dumps(curves),encoding='utf-8')
(ROOT/'state_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessResearcher_V05.blend'))
export=Path('D:/FPS3D/FPSGAME/Tools/FacelessReceptionist/export_v04.py').read_text(encoding='utf-8').replace('FacelessReceptionist20261007','FacelessResearcher20261009').replace('FacelessReceptionist','FacelessResearcher').replace('Receptionist','Researcher').replace('V04','V05')
exec(compile(export,'researcher_v05_export','exec'))
