"""Scoped source-geometry review of the reported exposed calf band."""
import bpy,json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR1';D=S/'Integration/Delivery'
args=sys.argv[sys.argv.index('--')+1:];rig=args[0] if args else 'Jason';phase=args[1] if len(args)>1 else 'before'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
boot=read(D/f'boots_{rig}_Wear.json');pant=read((R/'Authored'/f'pants_tactical_{rig}.json') if phase!='before' else D/f'pants_boot_{rig}_Wear.json')
bp=np.array(boot['positions']);bf=np.array(boot['triangles']);skin=np.unique(bf[[s.startswith('NATIVE:') for s in [boot['material_slots'][i] for i in boot['triangle_materials']]]])
diagnosis=[]
for k in (['pants','pants_boot'] if phase=='before' else ['pants_tactical']):
    d=read(D/f'{k}_{rig}_Wear.json') if phase=='before' else pant
    f=np.asarray(d['triangles']);m=np.array(d['triangle_materials']);slots=d['material_slots'];tree=BVHTree.FromPolygons(d['positions'],f[[not slots[i].startswith('NATIVE:') for i in m]].tolist(),all_triangles=True)
    bones={b['name']:np.array(b['position']) for b in boot['bones']};gap=[]
    for q in bp[skin]:
        side='l' if q[0]>0 else 'r';a=bones['foot_'+side];b=bones['calf_'+side];center=a+(b-a)*((q[2]-a[2])/(b[2]-a[2]));direction=q-center;direction[2]=0;radius=np.linalg.norm(direction);direction/=radius
        hit=tree.ray_cast(Vector(center+direction*30),Vector(-direction),30)[0]
        if hit is not None:gap.append(float(np.dot(np.array(hit)-q,direction)))
    diagnosis.append(dict(kind=k,samples=len(gap),skin_outside_count=int(sum(v<-.05 for v in gap)),radial_clearance_quantiles_cm=np.quantile(gap,[0,.1,.5,.9,1]).tolist()))
(R/'Review'/f'lower-{rig}-{phase}.json').write_text(json.dumps(diagnosis,indent=2),encoding='utf-8');print('CALF_PAIR',diagnosis,flush=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'Models/04_TacticalTrousers.blend'))
with bpy.data.libraries.load(str(S/'Models/05_TacticalBoots.blend'),link=False) as (source,dest):dest.materials=[n for n in source.materials if n not in bpy.data.materials]
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
skinmat=bpy.data.materials.new('CalfReferenceSkin');skinmat.use_nodes=True;skinmat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.48,.25,.18,1);skinmat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.7
for name,d in [('Pants',pant),('Boots',boot)]:
    me=bpy.data.meshes.new(name);me.from_pydata([(p[0]*.01,-p[1]*.01,p[2]*.01) for p in d['positions']],[],d['triangles']);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    for s in d['material_slots']:me.materials.append(skinmat if s.startswith('NATIVE:') else bpy.data.materials.get(s))
    uv=me.uv_layers.new()
    for face,mi,tex in zip(me.polygons,d['triangle_materials'],d['uv']):
        face.material_index=mi;face.use_smooth=True
        for li,t in zip(face.loop_indices,tex):uv.data[li].uv=(t[0],1-t[1])
    me.normals_split_custom_set([(n[0],-n[1],n[2]) for f in d['normals'] for n in f])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type!='CPU'
    scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=900;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('LowerStudio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.14,.15,.17,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
target=Vector((0,0,.51));scene.view_settings.view_transform='AgX'
for loc,energy in [((1,-2,2),350),((-2,1,2),300),((1,2,2),300)]:
    light=bpy.data.lights.new('Area','AREA');light.energy=energy;light.size=2;ob=bpy.data.objects.new('Area',light);bpy.context.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('Camera');ob=bpy.data.objects.new('Camera',cam);bpy.context.collection.objects.link(ob);scene.camera=ob;cam.type='ORTHO';cam.ortho_scale=1.10
for view,pos in [('front',(1,-5,1.5)),('back',(-1,5,1.5))]:
    ob.location=target+Vector(pos);ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(R/'Review'/f'lower-{rig}-{phase}-{view}.png');bpy.ops.render.render(write_still=True)
