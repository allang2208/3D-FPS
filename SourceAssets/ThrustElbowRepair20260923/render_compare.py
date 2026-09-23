"""Offline skin diagnostic, using the actual exported arms and weights."""
import bpy,sys,json,math
from pathlib import Path
import numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from diagnose_elbows import matrix,rebuild,PRIOR
OUT=P/'Review';OUT.mkdir(exist_ok=True)
def setup(g,rest):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    mesh=bpy.data.meshes.new('Skin');mesh.from_pydata(g['vertices'],[],g['triangles']);mesh.update()
    ob=bpy.data.objects.new('ActualArms',mesh);scene.collection.objects.link(ob);ob.color=(.45,.57,.68,1)
    for f in mesh.polygons:f.use_smooth=True
    camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(camera);scene.camera=camera
    camera.data.clip_start=.1;camera.data.clip_end=10000
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
    scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
    scene.display.shading.show_backface_culling=True;scene.display.shading.background_type='WORLD'
    scene.world=bpy.data.worlds.new('World');scene.world.color=(.045,.055,.07)
    scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    p=np.array([[*v,1] for v in g['vertices']]);groups={}
    for n in {n for row in g['weights'] for n in row}:
        idx=np.array([i for i,row in enumerate(g['weights']) if n in row])
        groups[n]=(idx,p[idx]@np.linalg.inv(np.array(rest[n])).T,np.array([g['weights'][i][n] for i in idx]))
    return scene,mesh,camera,groups
def skin(mesh,groups,pose):
    v=np.zeros((len(mesh.vertices),3))
    for n,(idx,local,w) in groups.items():v[idx]+=(local@np.array(pose[n]).T)[:,:3]*w[:,None]
    v[:,1]*=-1;mesh.vertices.foreach_set('co',v.ravel());mesh.update()
def render(scene,camera,pose,label):
    camera.data.type='PERSP';camera.location=(0,0,0);camera.rotation_euler=(math.pi/2,0,0)
    vfov=95 if '--wide' in sys.argv else 75
    camera.data.sensor_fit='VERTICAL';camera.data.sensor_height=24;camera.data.lens=24/(2*math.tan(math.radians(vfov/2)))
    if '--wide' in sys.argv:label+='_wide95'
    scene.render.filepath=str(OUT/(label+'_fp.png'));bpy.ops.render.render(write_still=True)
    if '--wide' in sys.argv:return
    for side in ('l','r'):
        target=pose['lowerarm_'+side].translation.copy();target.y*=-1
        camera.data.type='ORTHO';camera.data.ortho_scale=48
        camera.location=target+Vector((0,-65,28));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(OUT/(label+'_'+side+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':
    for variant in (('Standard','LongGrip') if '--sequence' in sys.argv else ('Standard',)):
        d=json.loads((PRIOR/variant/'source.json').read_text());v1=json.loads((PRIOR/variant/'Thrust_patch.json').read_text())
        rest={n:matrix(t) for n,t in d['rest'].items()};g=json.loads((PRIOR/variant/'geometry.json').read_text())
        scene,mesh,camera,groups=setup(g,rest)
        for t in ((.12,.4,.5,.58,.8,1.12) if '--sequence' in sys.argv else (.58,)):
            f=round(t*480);old,cur=rebuild(d['clips']['Thrust']['samples'][f],v1['samples'][f],d['parents'])
            poses={} if '--sequence' in sys.argv else {'before':old,'current':cur}
            if (P/variant/'Thrust_patch.json').exists():
                patch=json.loads((P/variant/'Thrust_patch.json').read_text());_,poses['fixed']=rebuild({'world':{n:__import__('diagnose_elbows').pack(m) for n,m in cur.items()}},patch['samples'][f],d['parents'])
            for label,pose in poses.items():skin(mesh,groups,pose);render(scene,camera,pose,variant+'_'+label+(f'_{t:.2f}' if '--sequence' in sys.argv else ''))
