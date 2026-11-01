"""Render real parts with the approved shared frame as a textured backdrop."""
import bpy,bmesh,math,json,runpy,sys
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent;S=O.parent
G=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
R=[
 ('stock_sniper_skeleton_stock',O/'SkeletonSniperStock_Meshy_Master.blend',['SkeletonSniperStock_Meshy_Master'],'shared'),
 ('ue_m24_bolt_false',S/'M24CarbonBolt20261029/Icons/false_Editable.blend',['M24_bolt','M24_boltrear'],'existing'),
 ('bolt_m24_carbon_light_bolt',S/'M24CarbonBolt20261029/Icons/m24_carbon_light_bolt_Editable.blend',['M24_bolt','M24_boltrear'],'existing'),
 ('ue_m24_reargrip_false',S/'M24RearGrip20261029/Icons/false_Editable.blend',['M24_OriginalGripSurface'],'existing'),
 ('body_m24_advanced_action',S/'M24AdvancedAction20261029/FullBodyV3/Icons/m24_advanced_action_Editable.blend',['M24_AdvancedAction_DetailBody'],'existing'),
 ('ue_m24_body_false',S/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend',['M24_base'],'front'),
 ('stock_m24_cheekrest',S/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend',['M24_base','M24_cheekrest'],'stock'),
 ('ue_svch_stock_false',S/'SVCHReplacement20261018/RealSights20261019/SVCH_RealFoldingSights_Editable.blend',['SVCH_New_stock'],'factory'),
]
records=[]
for key,path,names,mode in R:
    if '--key' in sys.argv and key!=sys.argv[sys.argv.index('--key')+1]:continue
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    for im in bpy.data.images:
        if im.filepath and im.source=='FILE':im.filepath=bpy.path.abspath(im.filepath)
    keep=[bpy.data.objects[n] for n in names]
    if mode in ('front','stock'):
        body=keep[0];wanted={tuple(round(x,4) for x in p) for p in json.loads((S/'M24AdvancedAction20261029/FullBodyV3/factory_front_faces.json').read_text())}
        bm=bmesh.new();bm.from_mesh(body.data)
        selected=[]
        for f in bm.faces:
            c=f.calc_center_median();match=(round(c.x*100,4),round(-c.y*100,4),round(c.z*100,4)) in wanted
            if (mode=='front' and not match) or (mode=='stock' and min(v.co.y for v in f.verts)>=-.11801):selected.append(f)
        bmesh.ops.delete(bm,geom=selected,context='FACES');bm.to_mesh(body.data);bm.free()
    for ob in list(bpy.data.objects):
        if ob not in keep:bpy.data.objects.remove(ob,do_unlink=True)
    for ob in keep:
        world=ob.matrix_world.copy();ob.parent=None;ob.modifiers.clear();ob.data.transform(world);ob.matrix_world=Matrix.Identity(4);ob.hide_render=False;ob.hide_set(False)
        if mode=='shared':ob.data.transform(Matrix.Rotation(-math.pi/2,4,'Z'))
    points=[v.co for ob in keep for v in ob.data.vertices];lo=Vector([min(p[k] for p in points) for k in range(3)]);hi=Vector([max(p[k] for p in points) for k in range(3)]);center=(lo+hi)*.5
    radius=max(math.hypot(p.y-center.y,p.z-center.z) for p in points);scale=.685/radius
    for ob in keep:ob.data.transform(Matrix.Scale(scale,4)@Matrix.Translation(-center));ob.location.x=-.24
    G['apply_grayscale'](keep)
    for mat in {slot.material for ob in keep for slot in ob.material_slots if slot.material}:
        for n in mat.node_tree.nodes:
            if n.type=='MATH' and n.operation=='MULTIPLY_ADD' and abs(n.inputs[1].default_value-.45)<.0001 and abs(n.inputs[2].default_value-.16)<.0001:
                n.inputs[1].default_value=.36;n.inputs[2].default_value=.06
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
    s.render.resolution_x=s.render.resolution_y=1024;s.render.resolution_percentage=100;s.render.film_transparent=True
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0
    s.world=bpy.data.worlds.new('Neutral icon studio');s.world.use_nodes=True
    bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(1,1,1,1);bg.inputs[1].default_value=.18
    def plane(name,x,mat):
        me=bpy.data.meshes.new(name);me.from_pydata([(x,1,-1),(x,-1,-1),(x,-1,1),(x,1,1)],[],[(0,1,2,3)]);me.update();uv=me.uv_layers.new()
        for i,q in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[i].uv=q
        ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(mat);return ob
    # The existing frame remains unchanged. A shader opening removes its old
    # center subject; a separate textured backplate sits behind the actual part.
    frame=bpy.data.materials.new('Approved metal frame');frame.use_nodes=True;n=frame.node_tree.nodes;l=frame.node_tree.links;n.clear()
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(S/'FirearmFramedIcons20260930/muzzle_brake_framed_v2.png'))
    uv=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');l.new(uv.outputs['UV'],sep.inputs[0])
    def op(kind,a,b):
        q=n.new('ShaderNodeMath');q.operation=kind
        for i,v in enumerate((a,b)):
            if hasattr(v,'node'):l.new(v,q.inputs[i])
            else:q.inputs[i].default_value=v
        return q.outputs[0]
    x=op('DIVIDE',op('SUBTRACT',sep.outputs['X'],.5),.393);y=op('DIVIDE',op('SUBTRACT',sep.outputs['Y'],.501),.371)
    mask=op('MULTIPLY',tex.outputs['Alpha'],op('GREATER_THAN',op('ADD',op('MULTIPLY',x,x),op('MULTIPLY',y,y)),1))
    gray=n.new('ShaderNodeRGBToBW');l.new(tex.outputs['Color'],gray.inputs[0]);em=n.new('ShaderNodeEmission');l.new(gray.outputs[0],em.inputs[0]);transparent=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');l.new(mask,mix.inputs[0]);l.new(transparent.outputs[0],mix.inputs[1]);l.new(em.outputs[0],mix.inputs[2]);out=n.new('ShaderNodeOutputMaterial');l.new(mix.outputs[0],out.inputs[0]);plane('Approved shared metal frame',.22,frame)
    backing=bpy.data.materials.new('Textured recessed backplate');backing.use_nodes=True;n=backing.node_tree.nodes;l=backing.node_tree.links;n.clear()
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=420;noise.inputs['Detail'].default_value=2
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.006,.006,.006,1);ramp.color_ramp.elements[1].color=(.022,.022,.022,1);l.new(noise.outputs['Fac'],ramp.inputs[0]);em=n.new('ShaderNodeEmission');l.new(ramp.outputs[0],em.inputs[0]);out=n.new('ShaderNodeOutputMaterial');l.new(em.outputs[0],out.inputs[0]);back=plane('Recessed central plate',.23,backing)
    # Limit the backplate to the circular opening, preserving transparent corners.
    for v in back.data.vertices:v.co.y*=.79;v.co.z*=.75
    bm=bmesh.new();bm.from_mesh(back.data);bmesh.ops.delete(bm,geom=list(bm.verts),context='VERTS');bmesh.ops.create_circle(bm,cap_ends=True,radius=1,segments=192,matrix=Matrix(((0,0,1,.23),(.79,0,0,0),(0,.75,0,0),(0,0,0,1))));bm.to_mesh(back.data);bm.free()
    for f in back.data.polygons:
        for li in f.loop_indices:
            p=back.data.vertices[back.data.loops[li].vertex_index].co;back.data.uv_layers[0].data[li].uv=(.5-p.y/.79*.5,p.z/.75*.5+.5)
    bpy.ops.object.camera_add(location=(-5,0,0));cam=bpy.context.object;cam.rotation_euler=(Vector()-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.02;s.camera=cam
    for loc,power,size in [((-3,-2,3),160,3),((-2,3,1),100,2.5),((0,-1,3),90,2)]:
        bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(Vector()-light.location).to_track_quat('-Z','Y').to_euler()
    G['neutral_output'](s)
    bpy.ops.wm.save_as_mainfile(filepath=str(O/'Icons'/(key+'_Editable.blend')))
    s.render.filepath=str(O/'Icons'/(key+'.png'));bpy.ops.render.render(write_still=True)
    records.append(dict(key=key,source=str(path),objects=names,frame='FirearmFramedIcons20260930/muzzle_brake_framed_v2.png',grayscale=True))
    (O/'Icons/production.json').write_text(json.dumps(records,indent=2))
    print('SNIPER_ICON_SAVED',key,flush=True)
