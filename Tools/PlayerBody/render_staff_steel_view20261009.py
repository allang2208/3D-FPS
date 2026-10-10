"""Offline authoring view, separate plate/liner colors; not an Unreal preview."""
import bpy,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
root=Path('D:/FPS3D/FPSGAME');out=root/'SourceAssets/ThirdPersonStaffThumbSteel20261009'
label=sys.argv[sys.argv.index('--')+1]
d=json.loads((out/(label+'-view.json')).read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(name,color,metal=0,rough=.5):
    x=bpy.data.materials.new(name);x.use_nodes=True
    b=x.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
    return x
def mesh(name,p,t,mats,ids=None):
    # UE clockwise triangles become Blender CCW with this handedness reflection.
    p=np.array(p)*[1,-1,1]
    me=bpy.data.meshes.new(name);me.from_pydata(p.tolist(),[],t);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    for m in mats:me.materials.append(m)
    for i,f in enumerate(me.polygons):
        f.use_smooth=True
        if ids is not None:f.material_index=ids[i]
    return ob
mesh('Jason steel',d['positions'],d['triangles'],[mat('Dark mail',(.035,.055,.07),.5),mat('Steel plates',(.45,.5,.55),.7,.32)],d['materials'])
surface=json.loads((root/'SourceAssets/ApprenticeStaff20260927/BowBasedGripV12/grip-surfaces.json').read_text())
r=np.array(surface['variants']['false']['radii']);z=np.array(surface['z'])-32
a=-np.arange(r.shape[1])*2*np.pi/r.shape[1]
p=np.stack((r*np.cos(a)[None,:],r*np.sin(a)[None,:],np.broadcast_to(z[:,None],r.shape)),axis=-1).reshape(-1,3)
N=r.shape[1];t=[]
for j in range(len(z)-1):
    for i in range(N):
        a=j*N+i;b=j*N+(i+1)%N;c=b+N;dd=a+N;t.extend([(a,b,c),(a,c,dd)])
mesh('Measured staff',p,t,[mat('Wood',(.23,.11,.04))])
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=24
s.render.resolution_x=720;s.render.resolution_y=720;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.color=(.4,.4,.4);s.view_settings.view_transform='AgX'
center=Vector((-2,-1,-.5))
for i,pos in enumerate([(5,-15,25),(-20,8,15),(0,20,8)]):
    li=bpy.data.lights.new('Area'+str(i),'AREA');li.energy=6500;li.size=15
    ob=bpy.data.objects.new(li.name,li);s.collection.objects.link(ob);ob.location=center+Vector(pos)
    ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('Author camera');ob=bpy.data.objects.new('Author camera',cam);s.collection.objects.link(ob);s.camera=ob
cam.type='ORTHO';cam.ortho_scale=22;cam.clip_start=.01;cam.clip_end=500
for name,offset in [('back',(18,-30,13)),('thumb',(-22,26,13))]:
    ob.location=center+Vector(offset);ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(out/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/(label+'.blend')))
