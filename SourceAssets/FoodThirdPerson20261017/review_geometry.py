"""Scoped final-graph skin/torso intersections and thumb rotations, with review contact sheets."""
import json,sys,math
from pathlib import Path
import numpy as np,bpy
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
tag=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'before'
data=json.loads((O/f'graph_{tag}.json').read_text());skin=json.loads((O/'body_geometry.json').read_text());foods=json.loads((O/'food_geometries.json').read_text())
names=data['names'];parents=data['parents'];ix={n:i for i,n in enumerate(names)}
def mat(t):
    m=Quaternion((t[6],*t[3:6])).to_matrix().to_4x4()
    for j in range(3):
        for i in range(3):m[i][j]*=t[7+j]
    m.translation=Vector(t[:3]);return m
bind=[]
for i,t in enumerate(data['reference']):bind.append(bind[parents[i]]@mat(t) if parents[i]>=0 else mat(t))
inv=np.array([np.array(m.inverted()) for m in bind]);p=np.column_stack((skin['positions'],np.ones(len(skin['positions']))))
weights={n:np.array([w.get(n,0) for w in skin['weights']]) for n in names};weights={n:w for n,w in weights.items() if np.any(w)}
def under(n,root):
    i=ix[n]
    while i>=0:
        if names[i]==root:return True
        i=parents[i]
    return False
arms={s:sum((w for n,w in weights.items() if under(n,'upperarm_'+s)),np.zeros(len(p)))>.8 for s in ['l','r']}
# Exclude the continuous shoulder seam from arm/torso intersection counts.
for s in arms:arms[s]&=np.linalg.norm(p[:,:3]-np.array(bind[ix['upperarm_'+s]].translation),axis=1)>8
bodyweight=sum((w for n,w in weights.items() if n.startswith(('spine_','pelvis','neck_','head'))),np.zeros(len(p)))
bodyfaces=[f for f in skin['triangles'] if all(bodyweight[j]>.8 for j in f)]
edges={}
for s,mask in arms.items():
    ed=set()
    for f in skin['triangles']:
        if all(mask[j] for j in f):ed.update(tuple(sorted((f[j],f[(j+1)%3]))) for j in range(3))
    edges[s]=list(ed)
def deform(pose):
    out=np.zeros((len(p),3));mats=np.array([np.array(mat(t)) for t in pose])@inv
    for n,w in weights.items():out+=(p@mats[ix[n]].T)[:,:3]*w[:,None]
    return out
def crossings(out,tree,side):
    count=0
    for a,b in edges[side]:
        start=Vector(out[a]);d=Vector(out[b])-start;length=d.length
        if length<.001:continue
        hit,_,_,_=tree.ray_cast(start+d.normalized()*.0001,d.normalized(),length-.0002)
        count+=hit is not None
    return count
def mesh(name,verts,faces,color):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);me.materials.append(m)
    for f in me.polygons:f.use_smooth=True
    return ob
def render(row,sample,out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh('Jason final graph',out.tolist(),skin['triangles'],(.52,.39,.30))
    frame=mat(sample['world'][ix['hand_l']])@mat(sample['prop_local']);geo=foods[row['food']]
    mesh('Food',[list(frame@Vector(v)) for v in geo['vertices']],geo['faces'],(.30,.15,.06))
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('world');scene.world.color=(.06,.06,.06);scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.view_settings.view_transform='Standard'
    camera=bpy.data.objects.new('camera',bpy.data.cameras.new('camera'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO'
    h=Vector(sample['world'][ix['hand_l']][:3]);hr=Vector(sample['world'][ix['hand_r']][:3]);center=(h+hr)*.5 if row['food']=='roasted_large_lamb' else h
    for view,offset,span in [('front',(0,180,10),95),('thumb',(60,150,40),48)]:
        camera.data.ortho_scale=span;target=Vector((0,10,center.z-18)) if view=='front' else center
        camera.location=target+Vector(offset);camera.rotation_euler=(-Vector(offset)).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(O/f'{tag}_{row["food"]}_{row["case"]}_{sample["time"]:.2f}_{view}.png');bpy.ops.render.render(write_still=True)
report=[]
for row in data['cases']:
    if '--single-only' in sys.argv and (row['food']=='roasted_large_lamb' or row['case']!='unarmed'):continue
    result={'food':row['food'],'case':row['case'],'samples':[],'thumb_max_roll_deg':{},'max_arm_torso_crossings':{'l':0,'r':0}}
    for sample in row['samples']:
        t=sample['time']
        if sample['weight']<.01:continue
        pose=sample['world']
        for s in ('l','r') if row['food']=='roasted_large_lamb' else ('l',):
            for j in range(1,4):
                n=f'thumb_{j:02}_{s}';b=ix[n];local=mat(pose[parents[b]]).inverted()@mat(pose[b]);delta=mat(data['reference'][b]).inverted()@local;q=delta.to_quaternion()
                if q.w<0:q.negate()
                axis=Vector(data['reference'][ix[f'thumb_{min(3,j+1):02}_{s}']][:3]).normalized();angle=abs(math.degrees(2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)))
                result['thumb_max_roll_deg'][n]=max(result['thumb_max_roll_deg'].get(n,0),angle)
        if round(t*60)%6:continue
        out=deform(pose);bvh=BVHTree.FromPolygons([Vector(v) for v in out],bodyfaces)
        counts={s:crossings(out,bvh,s) for s in ('l','r')}
        result['samples'].append({'time':t,'crossings':counts})
        for s in counts:result['max_arm_torso_crossings'][s]=max(result['max_arm_torso_crossings'][s],counts[s])
    report.append(result);print('FOOD_SKIN_REVIEW',row['food'],row['case'],result['max_arm_torso_crossings'],result['thumb_max_roll_deg'],flush=True)
    if row['case']=='post_off' or '--no-render' in sys.argv:continue
    duration=row['samples'][-1]['time']-.2
    for t in ([.55,2.75,4.65,5.3] if row['food']=='roasted_large_lamb' else [duration*.775]):
        sample=min(row['samples'],key=lambda s:abs(s['time']-t));render(row,sample,deform(sample['world']))
(O/f'geometry_{tag}.json').write_text(json.dumps(report,indent=2))
