"""Scoped offline visual inspection requested for the TS01 repair."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'Integration/QualityR3'
kind,phase=sys.argv[sys.argv.index('--')+1:]
female=kind.endswith('_female')
if female:kind=kind.removesuffix('_female')
source={'vest':'01_KevlarVest','boots':'05_TacticalBoots'}[kind]
bpy.ops.wm.open_mainfile(filepath=str(S/'Models'/f'{source}.blend'))
for ob in list(bpy.data.objects):
    if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True)
    else:
        for mod in list(ob.modifiers):
            if mod.type=='ARMATURE':ob.modifiers.remove(mod)
if female:
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    d=json.loads((S/'Integration/Delivery'/f'{kind}_Kaitlin_Wear.json').read_text(encoding='utf-8-sig'))
    me=bpy.data.meshes.new('Kaitlin_Carrier');me.from_pydata([(p[0]*.01,-p[1]*.01,p[2]*.01) for p in d['positions']],[],d['triangles']);me.update()
    ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob)
    for name in d['material_slots']:
        mat=bpy.data.materials.get(name)
        if mat is None:
            mat=bpy.data.materials.new(name);mat.diffuse_color=(.28,.32,.37,1)
        me.materials.append(mat)
    uv=me.uv_layers.new()
    for f,m,tex in zip(me.polygons,d['triangle_materials'],d['uv']):
        f.material_index=m;f.use_smooth=True
        for li,t in zip(f.loop_indices,tex):uv.data[li].uv=(t[0],1-t[1])
    me.normals_split_custom_set([(n[0],-n[1],n[2]) for row in d['normals'] for n in row])
if kind=='vest':
    d=json.loads((P/('SourceAssets/KaitlinPlayer20261023/NativeGeometry/MHC_Kaitlin_Body.json' if female else 'SourceAssets/JasonPlayer20261003/Jason.json')).read_text(encoding='utf-8-sig'))
    pts=[(p[0]*.01,-p[1]*.01,p[2]*.01) for p in d['positions']]
    faces=[f for f,m in zip(d['triangles'],d['triangle_materials']) if female or m==2]
    me=bpy.data.meshes.new('ActualNativeBody');me.from_pydata(pts,[],faces);me.update()
    ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob)
    mat=bpy.data.materials.new('FitReferenceSkin');mat.diffuse_color=(.28,.32,.37,1);mat.use_nodes=True
    mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.28,.32,.37,1)
    mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.8;me.materials.append(mat)
    for f in me.polygons:f.use_smooth=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type!='CPU'
    scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.13,.15,.18,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
scene.view_settings.view_transform='AgX'
target=Vector((0,0,1.25 if kind=='vest' else .15));scale=.68 if kind=='vest' else .64
for i,(loc,energy,size) in enumerate([((1,-2,3),350,2),((-2,-1,1.5),200,2),((0,2,2),400,1.5)]):
    light=bpy.data.lights.new('ReviewLight'+str(i),'AREA');light.energy=energy;light.shape='DISK';light.size=size
    ob=bpy.data.objects.new(light.name,light);bpy.context.collection.objects.link(ob);ob.location=loc
    ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('ReviewCamera');ob=bpy.data.objects.new(cam.name,cam);bpy.context.collection.objects.link(ob);scene.camera=ob;cam.type='ORTHO';cam.ortho_scale=scale
R.mkdir(exist_ok=True)
for view,direction in [('front',(1,-4,1.0)),('back',(-1,4,.8))] if kind=='vest' else [('front',(2,-4,2)),('side',(4,0,1.8))]:
    ob.location=target+Vector(direction);ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(R/f'{kind}{"-female" if female else ""}-{phase}-{view}.png');bpy.ops.render.render(write_still=True)
print('TS01_REVIEW_RENDERED',kind,phase,flush=True)
