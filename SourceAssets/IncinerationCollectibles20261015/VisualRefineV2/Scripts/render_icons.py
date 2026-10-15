"""Production inventory icons only from the delivered GLBs."""
from pathlib import Path
import bpy,sys,json,math
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from collection_icon_orientation import orient_collection_camera
SPEC=json.loads((ROOT/'model_manifest.json').read_text(encoding='utf8'))
OUT=ROOT/'Icons';ICONS=OUT
OUT.mkdir(parents=True,exist_ok=True);ICONS.mkdir(parents=True,exist_ok=True)
GRIDS={k:tuple(v['grid']) for k,v in SPEC['assets'].items()}
ONLY_ICON=None
VIEWS={k:[((7,-11,11),'icon')] for k in SPEC['assets']}
report={'stage':'rendering','source':'Delivered GLB geometry and PBR textures','renderer':'Blender Cycles',
        'requested_preview':True, 'requested_inventory_icons':True,'ue_runtime_capture':False,'views':[],'icons':[]}
if ONLY_ICON:
    report=json.loads((ROOT/'presentation.json').read_text(encoding='utf8'))
    report['icons']=[x for x in report['icons'] if x['key']!=ONLY_ICON]
    report['stage']='rendering'
def record():(ROOT/'presentation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def point_at(obj,p):obj.rotation_euler=(Vector(p)-obj.location).to_track_quat('-Z','Y').to_euler()
def bounds(obs):
    pts=[o.matrix_world@Vector(v) for o in obs for v in o.bound_box]
    lo=Vector([min(v[i] for v in pts) for i in range(3)]);hi=Vector([max(v[i] for v in pts) for i in range(3)])
    return lo,hi,pts
def camera_fit(obj,points,aspect,margin=1.12):
    bpy.context.view_layer.update();inv=obj.matrix_world.inverted();pts=[inv@v for v in points]
    lo=Vector((min(v.x for v in pts),min(v.y for v in pts),0));hi=Vector((max(v.x for v in pts),max(v.y for v in pts),0))
    centre=(lo+hi)*.5
    obj.location+=obj.matrix_world.to_3x3()@centre
    width=hi.x-lo.x;height=hi.y-lo.y
    fit=max(width,height*aspect)*margin
    obj.data.ortho_scale=fit if aspect>=1 else fit/aspect
    bpy.context.view_layer.update()
def light(scene,name,pos,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=pos;point_at(o,(0,0,0))
def render(scene,path,res):
    scene.render.resolution_x,scene.render.resolution_y=res;scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    print('INCINERATION_PRESENTATION_SAVED',str(path),flush=True)

for key,spec in SPEC['assets'].items():
    if ONLY_ICON and key!=ONLY_ICON:continue
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=spec['glb'])
    objects=[o for o in scene.objects if o.type=='MESH']
    transforms=[(o,o.matrix_world.copy()) for o in objects]
    for o,mat in transforms:o.parent=None;o.matrix_world=mat
    bpy.context.view_layer.update();lo,hi,_=bounds(objects)
    scale=Matrix.Scale(2.8/max(hi-lo),4)
    for o in objects:o.matrix_world=scale@o.matrix_world
    bpy.context.view_layer.update();lo,hi,_=bounds(objects);offset=-(lo+hi)*.5
    for o in objects:o.matrix_world.translation+=offset
    bpy.context.view_layer.update();lo,hi,_=bounds(objects)
    # Use the visible geometry, not the corners of an enclosing cuboid. A probe
    # and curved lead leave most of that cuboid empty, biasing the icon's centre.
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    scene.render.engine='CYCLES';scene.cycles.samples=256;scene.cycles.use_denoising=True
    scene.cycles.adaptive_threshold=.009;scene.cycles.max_bounces=8;scene.cycles.device='CPU'
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        if any(d.type=='OPTIX' for d in prefs.devices):
            for d in prefs.devices:d.use=d.type=='OPTIX'
            scene.cycles.device='GPU'
    except Exception as exc:print('CYCLES_CPU',str(exc),flush=True)
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8'
    scene.render.film_transparent=True
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=.1
    scene.world=bpy.data.worlds.new('Freight tools neutral studio');scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.52,.56,.62,1);bg.inputs['Strength'].default_value=.42
    light(scene,'Large key',(-3.5,-4,6),700,4)
    light(scene,'Soft fill',(4,-1.5,4),280,3.5)
    light(scene,'Rear strip',(1,4.5,5),900,3)
    # A fourth soft source also lights the exposed rear face of the meter.
    light(scene,'Underside softbox',(-1,1,-5),100,3)
    camera=bpy.data.cameras.new('Asset presentation');camera.type='ORTHO'
    cam=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(cam);scene.camera=cam
    for direction,label in []:
        cam.location=Vector(direction).normalized()*10;point_at(cam,(0,0,0));camera_fit(cam,points,1280/1040)
        path=OUT/f'{key}_{label}.png';render(scene,path,(1280,1040))
        report['views'].append({'key':key,'label':label,'file':str(path),'source':spec['glb']});record()
    direction=VIEWS[key][0][0]
    cam.location=Vector(direction).normalized()*10;point_at(cam,(0,0,0))
    gw,gh=GRIDS[key]
    orientation=orient_collection_camera(cam,gw,gh,forward=(0,0,1) if key=='IndustrialFilter' else (-1,0,0),dimensions=spec['actual_dimensions_cm'])
    res=(gw*512,gh*512);camera_fit(cam,points,res[0]/res[1],1.10)
    path=ICONS/(spec['id']+'.png');render(scene,path,res)
    report['icons'].append({'key':key,'id':spec['id'],'name':spec['name'],'file':str(path),
       'grid_w':gw,'grid_h':gh,'pixel_size':list(res),'ue_icon':'Icons/IncinerationCollectibles20261015/'+path.name,
       'orientation':orientation,'source':spec['glb'],'inventory_registered':False});record()
report['stage']='inventory_icons_saved';record()
print('INCINERATION_PRESENTATION_COMPLETE',flush=True)
