"""Author the actual current stock as the input for the standard framed icon."""
from pathlib import Path
import bpy,bmesh,sys,json
from mathutils import Vector
O=Path(__file__).resolve().parent
source=O.parent/'M24JointClean20261106/M24_HorizontalJointClean.blend'
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
sys.path.insert(0,str(source.parent))
from joint_geometry import preserve,restore,ATTR
stock=bpy.data.objects['SM_M24_CarbonSpine_Native']
for ob in list(bpy.data.objects):
    if ob!=stock:bpy.data.objects.remove(ob,do_unlink=True)
stock.hide_set(False);stock.hide_render=False
preserve(stock);bm=bmesh.new();bm.from_mesh(stock.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,0),plane_no=(0,1,0),clear_outer=True,dist=1e-8)
bm.to_mesh(stock.data);bm.free();restore(stock)
for mat in stock.data.materials:
    if mat.name=='CS_Receiver':
        mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        bs.inputs['Base Color'].default_value=(.026,.029,.032,1);bs.inputs['Metallic'].default_value=1;bs.inputs['Roughness'].default_value=.48
helper=Path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
palette={};exec(compile(helper.read_text(encoding='utf-8'),str(helper),'exec'),palette);palette['apply_grayscale']([stock])
# Keep the carbon weave and rubber contrast instead of lifting all dark texels
# into the same pale display value. This is isolated to the icon author scene.
for mat in stock.data.materials:
    if not mat or not mat.use_nodes:continue
    for node in mat.node_tree.nodes:
        if node.type=='MATH' and node.operation=='POWER':node.inputs[1].default_value=.60
        if node.type=='MATH' and node.operation=='MULTIPLY_ADD':node.inputs[1].default_value=.48;node.inputs[2].default_value=.025
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';palette['neutral_output'](scene)
scene.world=bpy.data.worlds.new('Neutral studio');scene.world.use_nodes=True
nodes=scene.world.node_tree.nodes;nodes.clear();bg=nodes.new('ShaderNodeBackground');out=nodes.new('ShaderNodeOutputWorld');bg.inputs[0].default_value=(.16,.16,.16,1);scene.world.node_tree.links.new(bg.outputs[0],out.inputs[0])
p=[stock.matrix_world@v.co for v in stock.data.vertices];mid=Vector([(min(v[i] for v in p)+max(v[i] for v in p))*.5 for i in range(3)])
bpy.ops.object.camera_add(location=mid+Vector((-.8,0,0)));cam=bpy.context.object
cam.rotation_euler=(mid-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.clip_start=.001
cam.data.ortho_scale=(max(v.y for v in p)-min(v.y for v in p))/.88;scene.camera=cam
for name,offset,power,size in [('Key',(-.3,.18,.4),5,.3),('Fill',(-.3,-.28,.06),2,.28),('Rim',(.16,0,.25),5,.22)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=mid+Vector(offset);ob.rotation_euler=(mid-ob.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'stock_actual_source.png')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'StockIcon_Editable.blend'))
bpy.ops.render.render(write_still=True)
(O/'source.json').write_text(json.dumps({'model_source':str(source),'stock_object':stock.name,'source_type':'actual current installed stock source','forward':'positive Y; left in the image','up':'+Z','camera':'orthographic negative X side','body_uv_and_normal_map':'retained; icon-only grayscale materials','png':'stock_actual_source.png'},indent=2))
print('M24_ICON_SOURCE_RENDERED')
