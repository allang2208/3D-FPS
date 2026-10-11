"""Targeted source render with the actual Super90 chainmail skin (not PIE)."""
import sys
from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'r20_core.py').read_text(encoding='utf-8'),str(O/'r20_core.py'),'exec'))
args=sys.argv[sys.argv.index('--')+1:]
tag,branch=args[:2];frames=[int(x) for x in args[2:]]
poses=json.loads((O/(tag+'_poses.json')).read_text(encoding='utf-8'))[branch]
keep={'SK_Super90','Super90_V7_M4_BareArmsV6','Super90_body','Super90_bolt','Super90_loading_gate','Super90_trigger','SM_Super90_LoaderGuide'}
for ob in scene.objects:
    ob.hide_render=ob.name not in keep;ob.hide_set(ob.name not in keep)
rig.animation_data_clear()
guide=bpy.data.objects['SM_Super90_LoaderGuide']
if not any(m.type=='ARMATURE' for m in guide.modifiers):
    vg=guide.vertex_groups.new(name='WPN_root');vg.add(list(range(len(guide.data.vertices))),1.,'REPLACE')
    guide.parent=rig;guide.matrix_parent_inverse=I;guide.matrix_basis=I
    mod=guide.modifiers.new('Socket','ARMATURE');mod.object=rig
native_inv={n:mat(native['rest'][n]).inverted() for n in names}
items=[]
for item in ('ue_chainmail_shirt','ue_original_gloves'):
    cloth=json.loads((S/'BenelliM4Super9020261006/EquipmentAuthored'/('Super90_'+item+'.json')).read_text(encoding='utf-8'))
    pos=np.asarray(cloth['positions']);groups={}
    for n in names:
        ids=np.asarray([i for i,w in enumerate(cloth['weights']) if w.get(n,0)>.00001],dtype=int)
        if len(ids):groups[n]=(ids,np.asarray([cloth['weights'][i][n] for i in ids]),np.asarray(native_inv[n])@np.column_stack((pos[ids],np.ones(len(ids)))).T)
    data=bpy.data.meshes.new(item);data.from_pydata([(0,0,0)]*len(pos),[],cloth['triangles']);data.update()
    ob=bpy.data.objects.new(item,data);scene.collection.objects.link(ob);ob.matrix_world=rig.matrix_world
    for i,color in enumerate(((.32,.39,.45,1),(.13,.16,.2,1),(.06,.07,.09,1))):
        m=bpy.data.materials.new(item+str(i));m.diffuse_color=color;data.materials.append(m)
    for face in data.polygons:face.use_smooth=True
    items.append((ob,groups,len(pos)))
if (O/'camera_current.json').exists():camera=json.loads((O/'camera_current.json').read_text())
CQ=Quaternion(camera['rotation']);CP=Vector(camera['location']);Sinv=Matrix.Diagonal((.01,-.01,.01))
eye=Sinv@(CQ.inverted()@(-CP))
fwd=(Sinv@(CQ.inverted()@Vector((1,0,0)))).normalized()
right=(Sinv@(CQ.inverted()@Vector((0,1,0)))).normalized()
up=right.cross(fwd).normalized();rot=Matrix((right,up,-fwd)).transposed()
camd=bpy.data.cameras.new('R20SourceCamera');camd.sensor_fit='HORIZONTAL';camd.angle=math.radians(112);camd.clip_start=.001
cam=bpy.data.objects.new('R20SourceCamera',camd);scene.collection.objects.link(cam)
cam.matrix_world=rig.matrix_world@Matrix.LocRotScale(eye,rot.to_quaternion(),Vector((1,1,1)));scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1276;scene.render.resolution_y=837;scene.render.resolution_percentage=75
shading=scene.display.shading;shading.light='STUDIO';shading.color_type='MATERIAL';shading.show_cavity=True;shading.cavity_type='BOTH';shading.show_shadows=False
shading.background_type='VIEWPORT';shading.background_color=(.075,.075,.075)
out=O/'Frames'/tag;out.mkdir(parents=True,exist_ok=True)
for f in frames:
    p={n:Matrix(m) for n,m in poses[f].items()}
    for b in rig.pose.bones:
        n=b.name;par=parents[n];b.matrix_basis=local_rest[n].inverted()@p.get(par,I).inverted()@p[n]
    for ob,groups,count in items:
        pts=np.zeros((count,3))
        for n,(ids,w,local) in groups.items():pts[ids]+=(np.asarray(p[n]@K[n])@local).T[:,:3]*w[:,None]
        ob.data.vertices.foreach_set('co',pts.reshape(-1));ob.data.update()
    bpy.context.view_layer.update();scene.render.filepath=str(out/(branch+'_'+str(f)+'.png'));bpy.ops.render.render(write_still=True)
print('SOURCE_ARM_FRAMES',tag,branch,frames,flush=True)
