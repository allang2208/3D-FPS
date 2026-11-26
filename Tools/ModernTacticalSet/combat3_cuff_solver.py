"""Cloth ease changes spring lengths, never the pinned wrist target positions."""
import sys,json,hashlib,shutil,numpy as np,bpy
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cloth import mesh,normals,smooth
from shirt_geometry import read,write,unit
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR3';C=R/'CuffRepairR1'
def input_signature(p,f,pins,body,frames,allowance):
    digest=hashlib.sha256(b'fixed-cuff-spring-ease-v1')
    for values,dtype in [(p,'<f8'),(f,'<i8'),(pins,'<f8'),(body['positions'],'<f8'),(body['triangles'],'<i8'),([frames,allowance],'<f8')]:
        array=np.asarray(values,dtype=dtype);digest.update(str(array.shape).encode());digest.update(array.tobytes())
    return digest.hexdigest()
def settle(name,p,f,pins,body,frames=36,allowance=.12):
    signature=input_signature(p,f,pins,body,frames,allowance)
    for file in (C/'Review').glob('*-anchors.json'):
        evidence=read(file)
        if evidence.get('input_signature')!=signature:continue
        previous=file.name.removesuffix('-anchors.json');data=np.load(C/'Simulation'/(previous+'.npz'));result=data['after'].copy();data.close()
        if previous!=name:
            for extension in ['.npz','.blend']:shutil.copy2(C/'Simulation'/(previous+extension),C/'Simulation'/(name+extension))
        evidence['identical_inputs_reused_from']=previous;write(C/'Review'/(name+'-anchors.json'),evidence);print('IDENTICAL_CLOTH_INPUT_REUSE',name,previous,flush=True);return result
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    bpy.data.orphans_purge(do_recursive=True)
    collider=mesh('NATIVE_BodyCollider',body['positions'],body['triangles']);collider.modifiers.new('SkinCollision','COLLISION');collider.collision.thickness_outer=.0025;collider.collision.thickness_inner=.001;collider.collision.cloth_friction=8
    ob=mesh('SEWN_Cotton_'+name,p,f);bpy.context.view_layer.objects.active=ob;ob.select_set(True);anchors=ob.vertex_groups.new(name='NativeSewnAnchors');ease=ob.vertex_groups.new(name='SleeveAllowance')
    for i,w in enumerate(pins):
        if w>0:anchors.add([i],float(w),'REPLACE')
        if w<1:ease.add([i],float(1-w),'REPLACE')
    cloth=ob.modifiers.new('OfflineCottonSettling','CLOTH');s=cloth.settings
    s.quality=15;s.mass=.28;s.air_damping=3;s.tension_stiffness=18;s.compression_stiffness=18;s.shear_stiffness=6;s.bending_stiffness=.012;s.tension_damping=6;s.compression_damping=6;s.shear_damping=6;s.bending_damping=.8;s.vertex_group_mass=anchors.name;s.pin_stiffness=1;s.time_scale=.8
    # A rest shape key also relocates Blender's pinned target vertices. Use
    # negative shrinking for material ease so the reference wrist stays fixed.
    s.vertex_group_shrink=ease.name;s.shrink_min=0;s.shrink_max=-allowance
    cc=cloth.collision_settings;cc.use_collision=True;cc.distance_min=.002;cc.collision_quality=5;cc.use_self_collision=True;cc.self_distance_min=.0025;cc.self_friction=8
    scene=bpy.context.scene;scene.gravity=(0,0,-9.81);scene.render.fps=30;scene.frame_start=1;scene.frame_end=frames;cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=frames
    for frame in range(1,frames+1):
        scene.frame_set(frame);bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());result=np.array([v.co[:] for v in ev.data.vertices])*[100,-100,100]
        if not np.isfinite(result).all():raise RuntimeError('Invalid cloth state '+name)
        if frame%6==0:print('FIXED_WRIST_CLOTH',name,frame,float(np.max(np.linalg.norm(result-p,axis=1))),flush=True)
    fixed=pins>=1-1e-8;drift=float(np.linalg.norm(result[fixed]-p[fixed],axis=1).max())
    if drift>.001:raise RuntimeError('Pinned native cuff moved: '+name+' '+str(drift)+' cm')
    ob.hide_render=True;collider.hide_render=True;finished=mesh('SETTLED_'+name,result,f)
    for face in finished.data.polygons:face.use_smooth=True
    bpy.ops.wm.save_as_mainfile(filepath=str(C/'Simulation'/(name+'.blend')));np.savez_compressed(C/'Simulation'/(name+'.npz'),before=p,after=result,triangles=f,pins=pins)
    write(C/'Review'/(name+'-anchors.json'),dict(native_anchor_vertices=int(fixed.sum()),max_anchor_drift_cm=drift,allowance=allowance,rest_shape_key=False,frames=frames,input_signature=signature,gameplay_tested=False));return result
def strip_sleeve_finger_weights(d):
    fingers={b['index'] for b in d['bones'] if b['name'].startswith(('thumb','index','middle','ring','pinky'))};changed=0;maximum=0.
    for i,weights in enumerate(d['weights']):
        removed=sum(w for bi,w in weights if bi in fingers)
        if removed<=0:continue
        kept=[[bi,w] for bi,w in weights if bi not in fingers];total=sum(w for bi,w in kept)
        if total<=0:raise RuntimeError('Sleeve vertex lacks arm support: '+str(i))
        d['weights'][i]=[[bi,w/total] for bi,w in kept];changed+=1;maximum=max(maximum,removed)
    return dict(vertices=changed,max_removed_weight=maximum)

def cuff_weights(d,indices,distance,side):
    names={b['index']:b['name'] for b in d['bones']};byname={b['name']:b['index'] for b in d['bones']};hand=byname['hand_'+side];support=byname.get('lowerarm_twist_01_'+side,byname['lowerarm_'+side])
    for vi,dist in zip(indices,distance):
        influence=float(1-smooth((dist-4)/3))
        if influence<=0:continue
        old=dict(d['weights'][int(vi)]);fore={bi:w for bi,w in old.items() if names[bi].startswith('lowerarm') and names[bi].endswith('_'+side)};den=sum(fore.values());fore={bi:w/den for bi,w in fore.items()} if den>1e-6 else {support:1.}
        hand_mix=.16*float(1-smooth((dist-1)/3));target={bi:w*(1-hand_mix) for bi,w in fore.items()};target[hand]=hand_mix;out={bi:w*(1-influence) for bi,w in old.items()}
        for bi,w in target.items():out[bi]=out.get(bi,0)+w*influence
        pairs=sorted(((bi,w) for bi,w in out.items() if w>1e-7),key=lambda row:-row[1])[:8];total=sum(w for bi,w in pairs);d['weights'][int(vi)]=[[bi,w/total] for bi,w in pairs]
