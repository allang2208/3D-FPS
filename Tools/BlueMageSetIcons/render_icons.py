"""Production inventory PNGs and camera-aligned display geometry for the mage set."""
import json,sys,math,shutil,hashlib,importlib.util
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Matrix
P=Path('D:/FPS3D/FPSGAME');OUT=P/'SourceAssets/BlueMageSetIcons20261019'
FAMILIES={'ue_blue_mage_robe':'BlueMageRobe20261018','ue_blue_mage_hat':'BlueMageHat20261019','ue_blue_mage_gloves':'BlueMageGloves20261019'}
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def save_json(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def measure(path):
    im=bpy.data.images.load(str(path),check_existing=False);im.colorspace_settings.name='Non-Color';a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a);w,h=im.size;rgba=a.reshape(h,w,4);bpy.data.images.remove(im)
    rgb=rgba[:,:,:3][rgba[:,:,3]>.98];linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4);yy,xx=np.where(rgba[:,:,3]>.05)
    return dict(size=[w,h],mean_linear=linear.mean(0).tolist(),mean_srgb=(rgb.mean(0)*255).tolist(),fill=max((xx.max()-xx.min()+1)/w,(yy.max()-yy.min()+1)/h),center=[float((xx.min()+xx.max()+1)/(2*w)),float((yy.min()+yy.max()+1)/(2*h))])

def plain_mesh(d,mats,name):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in d['positions']],[],d['triangles']);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    for m in mats:mesh.materials.append(m)
    uv=mesh.uv_layers.new(name='PhysicalGarmentUV')
    for fi,face in enumerate(mesh.polygons):
        face.use_smooth=True;face.material_index=d['triangle_materials'][fi]
        for ci,li in enumerate(face.loop_indices):a,b=d['uv'][fi][ci];uv.data[li].uv=(a,1-b)
    mesh.normals_split_custom_set([(x,-y,z) for row in d['normals'] for x,y,z in row]);return ob

def build(key):
    family=P/'SourceAssets'/FAMILIES[key];bpy.ops.wm.read_factory_settings(use_empty=True)
    if key=='ue_blue_mage_robe':
        source=family/'Authored/Body/Jason.json';d=read(source);io=module('mage_robe_icon_io','Tools/BlueMageRobe/save_editable.py');rig=io.rig_for(d);ob=io.mesh_for(d,rig,io.materials())
    elif key=='ue_blue_mage_hat':
        source=family/'Authored/hat.json';d=read(source);m=module('mage_hat_icon_materials','Tools/BlueMageHat/hat_materials_blender.py');ob=plain_mesh(d,m.make_materials(family),'MageHat_IconOnly')
    else:
        source=family/'Authored/Display.json'
        # The presentation source contains one relaxed empty glove, already using
        # production atlas materials. Reuse those materials without executing its exporter.
        bpy.ops.wm.open_mainfile(filepath=str(family/'Exports/BlueMageGlove_Presentation.blend'))
        ob=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('BlueMageGlove_Display'))
    return ob,source

def export_display(key,ob,camera):
    evaluated=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get());mesh.calc_loop_triangles();view=camera.matrix_world.inverted();normal_matrix=view.to_3x3()@ob.matrix_world.to_3x3().inverted().transposed()
    points=[view@(ob.matrix_world@v.co) for v in mesh.vertices];positions=[[-p.z*100,p.x*100,p.y*100] for p in points];faces=[];normals=[];uv=[];slots=[];layer=mesh.uv_layers.active
    for tri in mesh.loop_triangles:
        faces.append(list(tri.vertices));slots.append(tri.material_index);ns=[];tex=[]
        for li in tri.loops:
            n=(normal_matrix@mesh.corner_normals[li].vector).normalized();ns.append([-n.z,n.x,n.y]);a,b=layer.data[li].uv;tex.append([a,1-b])
        normals.append(ns);uv.append(tex)
    path=OUT/(key+'-display.json');path.write_text(json.dumps(dict(profile=key,positions=positions,triangles=faces,normals=normals,uv=uv,triangle_materials=slots,camera_contract='Final view faces camera -X, screen right +Y, screen up +Z; undo catalog rotation only at UE save'),separators=(',',':')),encoding='utf-8');evaluated.to_mesh_clear();return path

def render_current(key,ob,source=None,item=None,camera_offset=None):
    OUT.mkdir(parents=True,exist_ok=True);bpy.context.preferences.filepaths.save_version=0;family=P/'SourceAssets'/FAMILIES[key];item=item or read(P/'Content/ColdSteelData/items.json')[key]
    for other in list(bpy.context.scene.objects):
        if other.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(other,do_unlink=True)
        elif other.type=='MESH':other.hide_render=other!=ob
    ob.hide_render=False;ob.hide_set(False)
    # Pose changes stay in the independent icon scene, retaining real bone lengths.
    if key=='ue_blue_mage_robe' and ob.parent and ob.parent.type=='ARMATURE':
        for side,angle in [('l',12.),('r',-12.)]:
            bone=ob.parent.pose.bones['upperarm_'+side];h=bone.matrix.translation.copy();bone.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(angle),4,'Y')@Matrix.Translation(-h)@bone.matrix
    bpy.context.view_layer.update();coords=np.array([tuple(ob.matrix_world@v.co) for v in ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]);center=Vector((coords.min(0)+coords.max(0))*.5);span=float(np.max(coords.max(0)-coords.min(0)))
    offset=camera_offset or {'ue_blue_mage_robe':(0,-3,.12),'ue_blue_mage_hat':(.75,3,.85),'ue_blue_mage_gloves':(0,0,3)}[key]
    cd=bpy.data.cameras.new('StandardInventoryCamera');cd.type='ORTHO';cd.clip_start=.001;camera=bpy.data.objects.new(cd.name,cd);scene=bpy.context.scene;scene.collection.objects.link(camera);scene.camera=camera;camera.location=center+Vector(offset)*span;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    width=round(320*item['grid_w']/item['grid_h']);height=320;aspect=width/height;inverse=camera.matrix_world.inverted();projected=np.array([tuple(inverse@Vector(p)) for p in coords]);low,high=projected.min(0),projected.max(0)
    # Blender's ortho_scale spans the larger image dimension; UE OrthoWidth
    # always spans width. Keep the portrait robe's full collar and hem here.
    cd.ortho_scale=float(max((high[0]-low[0])/min(1.,aspect),(high[1]-low[1])*max(1.,aspect))/.91);camera.location+=camera.rotation_euler.to_matrix()@Vector(((low[0]+high[0])*.5,(low[1]+high[1])*.5,0));bpy.context.view_layer.update()
    basis=camera.rotation_euler.to_matrix()
    for name,offset,power,size in [('Key',(-.8,.7,1.5),35.,1.2),('Fill',(.9,.1,1.2),12.,1.5),('Rim',(.2,1.,-.8),20.,.8)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power*span*span;light.size=size*span;lamp=bpy.data.objects.new(name,light);scene.collection.objects.link(lamp);lamp.location=center+basis@(Vector(offset)*span);lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
    world=bpy.data.worlds.new('NeutralInventoryStudio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.35,.35,.35,1);world.node_tree.nodes['Background'].inputs[1].default_value=.12;scene.world=world
    scene.render.engine='CYCLES';scene.cycles.samples=256;scene.cycles.use_denoising=False;scene.cycles.adaptive_threshold=.004;scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0.;scene.view_settings.gamma=1.
    saved=[]
    for mat in ob.data.materials:
        if not mat or not mat.use_nodes:continue
        nodes,links=mat.node_tree.nodes,mat.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
        orm=next((n for n in nodes if n.type=='TEX_IMAGE' and n.image and '_ORM' in n.image.name),None)
        if orm and not mat.get('InventoryAO'):
            split=nodes.new('ShaderNodeSeparateColor');links.new(orm.outputs['Color'],split.inputs[0]);mul=nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1.
            if bs.inputs['Base Color'].is_linked:links.new(bs.inputs['Base Color'].links[0].from_socket,mul.inputs[1])
            else:mul.inputs[1].default_value=bs.inputs['Base Color'].default_value
            links.new(split.outputs['Red'],mul.inputs[2]);links.new(mul.outputs[0],bs.inputs['Base Color']);mat['InventoryAO']=True
        original=out.inputs['Surface'].links[0].from_socket;emission=nodes.new('ShaderNodeEmission')
        if bs.inputs['Base Color'].is_linked:links.new(bs.inputs['Base Color'].links[0].from_socket,emission.inputs['Color'])
        else:emission.inputs['Color'].default_value=bs.inputs['Base Color'].default_value
        links.new(emission.outputs[0],out.inputs['Surface']);saved.append((mat,original,out,emission))
    albedo=OUT/(key+'-albedo.png');scene.cycles.samples=32;scene.render.filepath=str(albedo);bpy.ops.render.render(write_still=True);target=measure(albedo)
    for mat,original,out,emission in saved:mat.node_tree.links.new(original,out.inputs['Surface']);mat.node_tree.nodes.remove(emission)
    scene.cycles.samples=256;icon=OUT/(key+'.png');scene.render.filepath=str(icon);calibration=[];luma=np.array([.2126,.7152,.0722]);target_luma=float(np.array(target['mean_linear'])@luma)
    for attempt in range(3):
        bpy.ops.render.render(write_still=True);value=measure(icon);calibration.append(dict(exposure=scene.view_settings.exposure,**value));delta=math.log2(max(target_luma,1e-7)/max(float(np.array(value['mean_linear'])@luma),1e-7))
        if abs(delta)<.035 or attempt==2:break
        scene.view_settings.exposure=float(np.clip(scene.view_settings.exposure+delta,-6,2))
    display=export_display(key,ob,camera);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(key+'-icon.blend')))
    # Live-preview subjects use Icons/<definition>.png while capture is pending.
    destinations=[family/(key+'.png'),P/'Content/ColdSteelData'/item['ue_icon'],P/'Content/ColdSteelData/Icons'/(key+'.png')]
    for dest in destinations:
        backup=OUT/'Before'/('_'.join(dest.relative_to(P).parts));backup.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists() and not backup.exists():shutil.copy2(dest,backup)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(icon,dest)
    result=dict(item=key,source=str(source or 'Current production author scene'),size=[width,height],icon=str(icon),display=str(display),target_albedo=target,calibration=calibration,installed=[str(p) for p in destinations],icon_sha256=hashlib.sha256(icon.read_bytes()).hexdigest(),runtime_tested=False)
    save_json(OUT/(key+'-production.json'),result);print('MAGE_SET_INVENTORY_ICON_SAVED',key,value['fill'],value['center'],flush=True);return result

if __name__=='__main__':
    keys=[k for k in sys.argv if k in FAMILIES] or list(FAMILIES)
    for key in keys:ob,source=build(key);render_current(key,ob,source)
