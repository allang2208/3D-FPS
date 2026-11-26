"""Inspect the actual M4-native TS01 glove against its accepted V7 hand."""
import bpy,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'Integration/QualityR3'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
bpy.ops.wm.open_mainfile(filepath=str(S/'Models/03_TacticalGloves.blend'))
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
d=read(S/'Integration/Delivery/gloves_M4_Wear.json');bare=read(P/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json')
bp={b['name']:np.array(b['position']) for b in d['bones']}
def unit(a):return a/max(np.linalg.norm(a),1e-12)
origin=bp['hand_l'];forward=unit(bp['middle_01_l']-origin);across=bp['index_01_l']-bp['pinky_01_l'];across=unit(across-forward*np.dot(across,forward));normal=unit(np.cross(across,forward));frame=np.stack([across,normal,forward],axis=1)
skin=bpy.data.materials.new('ReferenceSkin');skin.diffuse_color=(.36,.44,.52,1);skin.use_nodes=True;skin.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.36,.44,.52,1)
for name,data in [('ActualNativeGlove',d),('NativeV7Reference',bare)]:
    p=np.asarray(data['positions']);t=np.asarray(data['triangles']);centers=p[t].mean(axis=1)
    selected=np.linalg.norm(centers-origin,axis=1)<20
    if name=='NativeV7Reference':selected&=np.asarray(data['triangle_materials'])==2
    fi=np.flatnonzero(selected);points=(p-origin)@frame*.01
    me=bpy.data.meshes.new(name);me.from_pydata(points.tolist(),[],t[fi].tolist());me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    if name=='NativeV7Reference':me.materials.append(skin)
    else:
        for slot in d['material_slots']:me.materials.append(bpy.data.materials[slot])
        uv=me.uv_layers.new()
        for f,i in zip(me.polygons,fi):
            f.material_index=d['triangle_materials'][i]
            for li,v in zip(f.loop_indices,d['uv'][i]):uv.data[li].uv=(v[0],1-v[1])
    for f in me.polygons:f.use_smooth=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type!='CPU'
scene.cycles.device='GPU';scene.render.resolution_x=800;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('GloveReview');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.17,.19,.23,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
target=Vector((0,0,.055))
for loc in [(1,-1,2),(-1,1,1)]:
    light=bpy.data.lights.new('Softbox','AREA');light.energy=100;light.size=1;ob=bpy.data.objects.new(light.name,light);bpy.context.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('NativeHand');camera.type='ORTHO';camera.ortho_scale=.24;ob=bpy.data.objects.new(camera.name,camera);bpy.context.collection.objects.link(ob);scene.camera=ob
for side in [-1,1]:
    ob.location=target+Vector((.3,side*3,.3));ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(R/f'glove-M4-{side}.png');bpy.ops.render.render(write_still=True)
print('TS01_NATIVE_GLOVE_REVIEWED',flush=True)
