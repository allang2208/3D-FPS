"""Produce actual-part grayscale catalog art with a modeled metal frame."""
import bpy,json,math,runpy
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent
G=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
manifest=json.loads((O/'authoring.json').read_text())
(O/'Icons').mkdir(exist_ok=True)
for key in [*manifest['models'],'none']:
    bpy.ops.wm.open_mainfile(filepath=str(O/'M24_Modular_Editable.blend'),use_scripts=False)
    wanted=manifest['models'].get(key,{}).get('objects',[])
    keep=[bpy.data.objects[n] for n in wanted]
    for ob in keep:ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
    for ob in list(bpy.data.objects):
        if ob not in keep:bpy.data.objects.remove(ob,do_unlink=True)
    s=bpy.context.scene
    if keep:
        pts=[v.co for o in keep for v in o.data.vertices]
        lo=Vector(tuple(min(v[i] for v in pts) for i in range(3)));hi=Vector(tuple(max(v[i] for v in pts) for i in range(3)))
        center=(lo+hi)/2;scale=1.23/max(hi.y-lo.y,hi.z-lo.z)
        for ob in keep:
            ob.data=ob.data.copy();ob.data.transform(Matrix.Scale(scale,4)@Matrix.Translation(-center))
            ob.location.x=-.17
        G['apply_grayscale'](keep)
    def mat(name,value,metal,rough):
        m=bpy.data.materials.new(name);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        p.inputs['Base Color'].default_value=(value,value,value,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
        return m
    steel=mat('Icon frame brushed silver',.33,.85,.28);dark=mat('Icon recessed graphite',.022,.25,.7)
    def cube(name,pos,size,material,bevel):
        bpy.ops.mesh.primitive_cube_add(size=1,location=pos);ob=bpy.context.object;ob.name=name;ob.dimensions=size
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.data.materials.append(material)
        mod=ob.modifiers.new('Machined edge','BEVEL');mod.width=bevel;mod.segments=3
        ob.modifiers.new('Weighted normals','WEIGHTED_NORMAL');return ob
    cube('Recessed backplate',(.19,0,0),(.06,1.82,1.82),dark,.07)
    for y in [-.87,.87]:cube('Vertical frame rail',(.10,y,0),(.13,.10,1.82),steel,.024)
    for z in [-.87,.87]:cube('Horizontal frame rail',(.10,0,z),(.13,1.82,.10),steel,.024)
    bpy.ops.mesh.primitive_torus_add(major_segments=96,minor_segments=12,location=(.11,0,0),rotation=(0,math.pi/2,0),major_radius=.735,minor_radius=.014)
    bpy.context.object.name='Silver inner ring';bpy.context.object.data.materials.append(steel)
    for y in [-.865,.865]:
        for z in [-.865,.865]:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.034,location=(.018,y,z))
            bpy.context.object.scale.x=.35;bpy.context.object.data.materials.append(steel)
    if key=='none':cube('Neutral removal minus',(-.10,0,0),(.05,.65,.10),steel,.025)
    bpy.ops.object.camera_add(location=(-3,0,0));cam=bpy.context.object
    cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO';cam.data.ortho_scale=1.91;s.camera=cam
    for pos,power,size in [((-2,-1,2),100,2),((-2,1,.2),60,1.5),((-.5,0,2),75,1.2)]:
        bpy.ops.object.light_add(type='AREA',location=pos);lamp=bpy.context.object;lamp.data.energy=power;lamp.data.size=size
        lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
    s.world=bpy.data.worlds.new('M24 icon studio');s.world.use_nodes=True;next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.3
    s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
    s.render.resolution_x=s.render.resolution_y=1024;s.render.resolution_percentage=100
    s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
    s.render.use_compositing=False;s.render.use_sequencer=False
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
    G['neutral_output'](s)
    s.render.filepath=str(O/'Icons'/(key+'.png'))
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(O/'Icons'/(key+'_Editable.blend')))
    bpy.ops.render.render(write_still=True)
    print('M24_ATTACHMENT_ICON_SAVED',key,flush=True)
