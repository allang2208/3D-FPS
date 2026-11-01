"""Export the designed grip and render its actual grayscale production icon."""
import bpy, math, json, hashlib, sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'StaticField_Design.blend'))
bpy.context.preferences.filepaths.save_version=0
parts=list(bpy.data.collections['StaticField_EditableParts'].objects)

for o in parts:o.hide_render=False;o.hide_set(False)
copies=[]
for o in parts:
    c=o.copy();c.data=o.data.copy();bpy.context.scene.collection.objects.link(c);copies.append(c)
bpy.ops.object.select_all(action='DESELECT')
for o in copies:o.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();joined=bpy.context.object
joined.name='SM_ThunderGodHammer_grip_static_field_V2'
# Same top pivot as the native grip. Runtime reinstates +40.5 cm exactly once.
joined.data.transform(Matrix.Translation((0,0,-.405)));joined.location=(0,0,0)
joined.data.calc_loop_triangles();triangles=len(joined.data.loop_triangles)
fbx=P/'Export'/(joined.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
bpy.ops.export_scene.gltf(filepath=str(P/'Export/StaticFieldGrip.glb'),export_format='GLB',use_selection=True,export_apply=True)
joined.hide_render=True;joined.hide_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'StaticField_Editable.blend'))
manifest=dict(revision='StaticFieldGripV2',mesh=joined.name,fbx=str(fbx),fbx_sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),triangles=triangles,
 materials=json.loads((P/'material_manifest.json').read_text()),interface='thunder_god_hammer_modular_v1',location_cm=[0,0,40.5],
 source='StaticField_Editable.blend',design='../StaticFieldGripV1/Design/StaticField_ThreeViews.png',geometry='Closed skived leather wrap with seam-adaptive topology, two-ply stitches, broad chased silver interlace and curved solid field seals; native end lands retained',normal_maps='4096x8192 leather atlas plus 4096x4096 steel/silver; cellular grain, exact needle sockets, forged grain, directional scratches; OpenGL source, UE flip green',runtime_tested=False)
(P/'runtime_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('IconNeutralStudio');scene.world.use_nodes=True
world=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
world.inputs[0].default_value=(.13,.13,.13,1);world.inputs[1].default_value=.3
scene.view_settings.view_transform='AgX'
def area(name,pos,power,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,0))-o.location).to_track_quat('-Z','Y').to_euler()
area('IconKey',(-.35,-.45,.6),32,.45);area('IconRim',(.3,.15,.2),42,.4);area('IconFill',(.45,-.4,-.3),12,.4)
d=bpy.data.cameras.new('IconCamera');d.type='ORTHO';o=bpy.data.objects.new('IconCamera',d);scene.collection.objects.link(o);scene.camera=o

# Production icon uses a separate grayscale authoring scene.
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
apply_grayscale(parts);scene=bpy.context.scene;neutral_output(scene)
for o in parts:o.location.z-=.16
def mat(name,c,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Base Color'].default_value=(*c,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough;return m
frame=mat('IconForgedFrame',(.22,.22,.22),.9,.39);silver=mat('IconSilverTrim',(.48,.48,.48),.95,.34);back=mat('IconRecess',(.025,.025,.025),.6,.64)
def cube(name,loc,scale,m,bevel):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
    mod=o.modifiers.new('Machined bevel','BEVEL');mod.width=bevel;mod.segments=4
    o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');return o
cube('IconBacking',(0,.046,0),(.65,.018,.65),back,.026)
# One continuous stepped square ring with beveled corners.
def square_ring(name,outer,inner,depth,m):
    vs=[];fs=[]
    for y,r in [(.018,outer),(.018,inner),(.018+depth,outer),(.018+depth,inner)]:
        vs.extend([(-r,y,-r),(r,y,-r),(r,y,r),(-r,y,r)])
    for j in range(4):
        n=(j+1)%4;fs.extend([(j,n,4+n,4+j),(8+j,12+j,12+n,8+n),(j,8+j,8+n,n),(4+j,4+n,12+n,12+j)])
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(m);o=bpy.data.objects.new(name,me);scene.collection.objects.link(o)
    mod=o.modifiers.new('Continuous cast bevel','BEVEL');mod.width=.008;mod.segments=4;o.modifiers.new('Weighted frame normals','WEIGHTED_NORMAL')
square_ring('IconSquareForging',.326,.284,.027,frame)
for x in (-.30,.30):
    for z in (-.30,.30):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.012,location=(x,.009,z));bpy.context.object.scale=(1,.4,1);bpy.context.object.data.materials.append(silver)
bpy.ops.mesh.primitive_torus_add(major_segments=192,minor_segments=12,major_radius=.274,minor_radius=.005,location=(0,.025,0),rotation=(math.pi/2,0,0));bpy.context.object.data.materials.append(silver)
scene.camera.location=(0,-2,0);scene.camera.rotation_euler=(math.pi/2,0,0);scene.camera.data.ortho_scale=.674
scene.render.resolution_x=scene.render.resolution_y=1024;scene.cycles.samples=64;scene.render.film_transparent=True
scene.render.filepath=str(P/'static_field_grip_framed.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'StaticField_Icon.blend'))
bpy.ops.render.render(write_still=True)
print('STATIC_FIELD_EXPORT_AND_ICON_SAVED',triangles,flush=True)
