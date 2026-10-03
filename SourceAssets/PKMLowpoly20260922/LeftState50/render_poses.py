"""Inspect actual UE mesh/pose readback in a neutral background render."""
import json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Quaternion
HERE=Path(__file__).resolve().parent;IN=HERE/'Input';OUT=HERE/'Review';OUT.mkdir(exist_ok=True)
group=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'holding'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('InspectionWorld');scene.world.color=(.06,.065,.075)
scene.render.resolution_x=800;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
if group=='surface':scene.display.shading.show_shadows=False
def mat(t):
    q=t['q'];m=np.eye(4);m[:3,:3]=np.array(Quaternion((q[3],q[0],q[1],q[2])).to_matrix())*np.array(t['s']);m[:3,3]=t['p'];return m
def convert(v):return np.array(v)*np.array([.01,-.01,.01])
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
mats={n:material(n,c) for n,c in {'skin':(.66,.47,.33),'gun':(.15,.17,.18),'Brown':(.25,.115,.04),
    'Black':(.035,.04,.045),'Sleeve':(.17,.22,.11),'grip':(.30,.34,.36)}.items()}
surfaces={};objects={};normal_parts={}
for label in ['Weapon','Bare','Brown','Black','Sleeve']:
    data=json.loads((IN/(label+'.json')).read_text());points=np.c_[data['positions'],np.ones(len(data['positions']))]
    weights={}
    for vi,ws in enumerate(data['weights']):
        for name,w in ws.items():weights.setdefault(name,[]).append((vi,w))
    weights={n:(np.array([a for a,b in vs]),np.array([b for a,b in vs])) for n,vs in weights.items()}
    inverse={n:np.linalg.inv(mat(t)) for n,t in data['bones'].items()};parts=[]
    for mi in sorted(set(data['triangle_materials'])):
        faces=[f for f,m in zip(data['triangles'],data['triangle_materials']) if m==mi]
        ids=np.array(sorted({v for f in faces for v in f}));mapping={v:i for i,v in enumerate(ids)}
        mesh=bpy.data.meshes.new(label+str(mi));mesh.from_pydata(convert(np.array(data['positions'])[ids]).tolist(),[],[[mapping[v] for v in f] for f in faces]);mesh.update()
        obj=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(obj)
        mesh.materials.append(mats['gun' if label=='Weapon' else 'skin' if label=='Bare' else label])
        for f in mesh.polygons:f.use_smooth=label!='Weapon'
        slot=data['materials'][mi] if mi<len(data['materials']) else str(mi)
        parts.append((obj,ids,mi,slot))
        if 'normals' in data:
            face_ids=np.where(np.array(data['triangle_materials'])==mi)[0]
            normal_parts[obj.name]=(np.array(data['triangles'])[face_ids].ravel(),np.array(data['normals'])[face_ids].reshape((-1,3)))
    surfaces[label]=(points,weights,inverse,parts);objects[label]=parts
grips={}
for family in ['angled','canted','vertical','prism']:
    data=json.loads((IN/('Grip_'+family+'.json')).read_text());mesh=bpy.data.meshes.new(family)
    mesh.from_pydata(convert(data['positions']).tolist(),[],data['triangles']);mesh.update();mesh.materials.append(mats['grip'])
    obj=bpy.data.objects.new(family,mesh);scene.collection.objects.link(obj);obj.hide_render=True
    grips[family]=(obj,np.c_[data['positions'],np.ones(len(data['positions']))])
camdata=bpy.data.cameras.new('Inspection');cam=bpy.data.objects.new('Inspection',camdata);scene.collection.objects.link(cam);scene.camera=cam
def skin(data,pose):
    points,weights,inverse,parts=data;result=np.zeros((len(points),3));normal_matrix=np.zeros((len(points),3,3))
    for name,(ids,ws) in weights.items():
        transform=mat(pose[name])@inverse[name];result[ids]+=(points[ids]@transform.T)[:,:3]*ws[:,None]
        normal_matrix[ids]+=transform[:3,:3]*ws[:,None,None]
    positions=convert(result)
    for obj,ids,mi,slot in parts:
        obj.data.vertices.foreach_set('co',positions[ids].ravel());obj.data.update()
        if obj.name in normal_parts:
            vi,normal=normal_parts[obj.name];posed=np.einsum('nij,nj->ni',normal_matrix[vi],normal)*np.array([1,-1,1])
            posed/=np.maximum(1.e-10,np.linalg.norm(posed,axis=1))[:,None]
            obj.data.normals_split_custom_set(posed.tolist())
def draw(family,action,time,view='palm',outfit='Brown'):
    name='A_PKM_'+('' if family=='base' else family+'_')+action
    data=json.loads((IN/(name+'.json')).read_text());sample=min(data['renders'],key=lambda r:abs(r['time']-time));pose=sample['pose'];time=sample['time']
    for label,surface in surfaces.items():
        skin(surface,pose)
        for obj,ids,mi,slot in surface[3]:
            visible=True
            if label=='Weapon':
                visible=mi not in [1,2]
                event=lambda t:t-(.9 if action=='reload_empty' and t>=2.3 else 0)
                if '__New' in slot:visible='reload' in action and time>=event(3.55)
                elif '__OldBox' in slot:visible='reload' not in action or time<event(3.2)
                elif '__OldBelt' in slot:visible='reload' not in action or (action!='reload_empty' and time<event(3.2))
            elif label=='Bare':visible=not (mi==2 and outfit!='Bare') and not (mi in [0,1] and outfit=='Sleeve')
            else:visible=label==outfit or (label=='Brown' and outfit=='Sleeve')
            obj.hide_render=not visible
    for f,(obj,points) in grips.items():
        obj.hide_render=f!=family
        if f==family:
            mount=mat(pose['WPN_root']);mount[:3,:3]*=.01
            obj.data.vertices.foreach_set('co',convert((points@mount.T)[:,:3]).ravel());obj.data.update()
    s,e,w=[Vector(convert(pose[n]['p'])) for n in ['upperarm_l','lowerarm_l','hand_l']]
    if view=='palm':target=w+Vector((0,-.02,0));eye=target+Vector((-.36,-.10,-.30));scale=.30
    elif view=='elbow':target=(s+e+w)/3;eye=target+Vector((-.65,-.10,.10));scale=.62
    else:
        anchor=[10,0,-5] if 'reload' in action else [9,9,-11]
        eye=Vector((-anchor[1]*.01,-anchor[0]*.01,-anchor[2]*.01));target=eye+Vector((0,1,0));scale=None
    cam.location=eye;cam.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler()
    if scale:camdata.type='ORTHO';camdata.ortho_scale=scale
    else:camdata.type='PERSP';camdata.sensor_fit='VERTICAL';camdata.angle=np.radians(75.)
    scene.render.resolution_x=960 if view=='fps' else 800;scene.render.resolution_y=540 if view=='fps' else 650
    prefix='unshadowed_' if group=='surface' else ''
    path=OUT/f'{prefix}{family}_{action}_{time:.3f}_{view}_{outfit}.png';scene.render.filepath=str(path);bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
    print('PKM_STATE_RENDERED',path.name,flush=True)
    return {'family':family,'action':action,'time':time,'view':view,'outfit':outfit,'file':str(path)}
jobs=[]
if group in ['holding','all']:
    for family in ['base','angled','canted','vertical','prism']:
        for action,view in [('idle','palm'),('idle','elbow'),('fire','palm'),('aim_fire','palm')]:jobs.append((family,action,0 if action=='idle' else .05,view))
if group in ['reload','all']:
    for action,times in [('reload',[.65,1.05,2.175,2.183333,3.65,4.7,6.5]),('reload_empty',[1.1,2.65,3.65,5.6,6.6])]:
        for time in times:jobs.append(('base',action,time,'elbow'))
    for family in ['angled','canted','vertical','prism']:jobs.append((family,'reload',6.5,'palm'))
    jobs.extend([('base','reload',.65,'palm','Bare'),('base','reload',.65,'elbow','Sleeve'),('vertical','idle',0,'palm','Bare')])
if group in ['framing','all']:
    for family in ['base','angled','canted','vertical','prism']:
        jobs.append((family,'idle',0,'fps'))
        jobs.append((family,'fire',.05,'fps'))
    for action,time in [('reload',.65),('reload',1.05),('reload',2.175),('reload',3.65),('reload_empty',1.1),('reload_empty',5.6)]:
        jobs.append(('base',action,time,'fps'))
if group=='surface':
    jobs=[('base','reload',3.65,'fps'),('base','idle',0,'elbow'),('base','reload',1.05,'elbow')]
rows=[draw(*job) for job in jobs]
(OUT/(group+'_manifest.json')).write_text(json.dumps(rows,indent=2),encoding='utf-8')
