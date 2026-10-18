"""Render factory parts from the saved native geometry, retaining WS1 surface identity."""
import bpy,bmesh,json,sys,re
from pathlib import Path
from mathutils import Vector,Matrix
R=Path('D:/FPS3D/FPSGAME');O=Path(__file__).parent;S=R/'SourceAssets/Super90WS1Surface20261007'
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
bpy.ops.wm.open_mainfile(filepath=str(O/'NativeSource.blend'));bpy.context.preferences.filepaths.save_version=0
native=next(o for o in bpy.context.scene.objects if o.type=='MESH')
islands=json.loads((O/'source_islands.json').read_text())['islands']
groups={'optic':[20,23,24,25,26,29], 'foreend':[45], 'reargrip':[59],
        'muzzle':[21,22,27,28,30,31,49,52], 'magazine':[47,48,50,51,53,54,55]}
parts={};report={}
for key,indices in groups.items():
    ids={j for i in indices for j in islands[i]['face_ids']}
    ob=native.copy();ob.data=native.data.copy();bpy.context.collection.objects.link(ob);ob.name='Super90 factory '+key
    bm=bmesh.new();bm.from_mesh(ob.data);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in ids],context='FACES');bm.to_mesh(ob.data);bm.free()
    parts[key]=ob;report[key]={'source_islands':indices,'faces':len(ob.data.polygons)}
bpy.data.objects.remove(native,do_unlink=True)
with bpy.data.libraries.load(str(R/'SourceAssets/Super90CommonStocks20261013/FactoryStock.blend'),link=False) as (_,d):d.objects=['Super90_FactoryStock']
parts['stock']=d.objects[0];bpy.context.collection.objects.link(parts['stock']);report['stock']={'source':'SourceAssets/Super90CommonStocks20261013/FactoryStock.blend','faces':len(parts['stock'].data.polygons)}
recipe=json.loads((S/'authoring.json').read_text())['recipe']
normal_file=R/'SourceAssets/BenelliM4Super9020261006/Original/Source/textures/TTI_Benelli_M4_Normal_brand_friendly.png'
normal_image=bpy.data.images.load(str(normal_file));normal_image.colorspace_settings.name='Non-Color';normal_image.pack()
materials={}
for role,info in recipe.items():
    mat=bpy.data.materials.new('Icon_WS1_'+role);mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bs.inputs['Base Color'].default_value=(*info['color'],1);bs.inputs['Metallic'].default_value=info['metallic'];bs.inputs['Roughness'].default_value=info['roughness']
    if role=='TTI_Benelli_M4':
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(S/'Textures/T_Super90_CleanReceiver.png'));tex.image.pack();links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    tex=nodes.new('ShaderNodeTexImage');tex.image=normal_image
    convert=nodes.new('ShaderNodeVectorMath');convert.operation='MULTIPLY_ADD';convert.inputs[1].default_value=(1,-1,1);convert.inputs[2].default_value=(0,1,0)
    norm=nodes.new('ShaderNodeNormalMap');norm.inputs['Strength'].default_value=1
    links.new(tex.outputs['Color'],convert.inputs[0]);links.new(convert.outputs['Vector'],norm.inputs['Color']);links.new(norm.outputs['Normal'],bs.inputs['Normal'])
    materials[role]=mat
for key,ob in parts.items():
    for i,mat in enumerate(list(ob.data.materials)):
        name=re.sub(r'(_\d+|\.\d{3})$','',mat.name.removeprefix('MI_Super90_'))
        if name in materials:ob.data.materials[i]=materials[name]
    used={p.material_index for p in ob.data.polygons}
    report[key]['material_roles']=[ob.data.materials[i].name for i in used]
    ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
    lo=Vector([min(v.co[k] for v in ob.data.vertices) for k in range(3)]);hi=Vector([max(v.co[k] for v in ob.data.vertices) for k in range(3)])
    rotation=Matrix(((0,-1,0),(1,0,0),(0,0,1))).to_4x4()
    ob.data.transform(Matrix.Scale(1.6/max(hi-lo),4)@rotation@Matrix.Translation(-(lo+hi)/2))
    apply_grayscale([ob]);ob.hide_render=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
scene.world=bpy.data.worlds.new('Neutral studio');scene.world.use_nodes=True;next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.3
cam=bpy.data.objects.new('Part camera',bpy.data.cameras.new('Part camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
for loc,power,size in [((-2,-3,4),220,3),((2,-2,1),80,2),((0,2,3),150,2)]:
    lamp=bpy.data.lights.new('Neutral softbox','AREA');lamp.energy=power;lamp.size=size
    ob=bpy.data.objects.new(lamp.name,lamp);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
neutral_output(scene);(O/'References').mkdir(exist_ok=True)
for key,ob in parts.items():
    ob.hide_render=False
    # Horizontal camera; modest azimuth reveals rear aperture and bore without a 2D mirror.
    cam.location=Vector((2.8,-4,0)) if key=='optic' else Vector((-.8,-4,0)) if key in ('foreend','muzzle','magazine') else Vector((-.5,-4,0))
    cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    points=[cam.matrix_world.inverted()@v.co for v in ob.data.vertices]
    low=Vector([min(v[k] for v in points) for k in range(3)]);high=Vector([max(v[k] for v in points) for k in range(3)])
    cam.data.ortho_scale=max(high.x-low.x,high.y-low.y)/.82
    cam.location+=cam.matrix_world.to_3x3()@Vector(((low.x+high.x)/2,(low.y+high.y)/2,0))
    report[key].update(camera_location=list(cam.location),camera_rotation=list(cam.rotation_euler),resolution=[1024,1024],forward='native +Y -> image left',up='native +Z -> image up',runtime='/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7',surface='WS1 current recipe and registered source normal, grayscale in authoring only')
    scene.render.filepath=str(O/'References'/(key+'.png'));bpy.ops.render.render(write_still=True);ob.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(O/'FactoryIconSources.blend'))
(O/'source_manifest.json').write_text(json.dumps(report,indent=2))
print('SUPER90_FACTORY_SOURCES_SAVED',list(report))
