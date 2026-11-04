"""Render current meshes directly into a modeled neutral metal modification frame."""
import bpy,sys,json,math,runpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[2]/'KukriComponentVariants20261026'))
from asset_tools import constant_material,cube,torus
gray=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
jobs=[]
for kind in ['SwiftCrescent']:
    bpy.ops.wm.open_mainfile(filepath=str(P/(kind+'_Editable.blend')))
    entry=json.loads((P/(kind+'.json')).read_text('utf-8'));obj=bpy.data.objects[entry['object']]
    for o in list(bpy.context.scene.objects):
        if o!=obj:bpy.data.objects.remove(o,do_unlink=True)
    obj.hide_render=False;obj.hide_set(False)
    gray['apply_grayscale']([obj]);s=bpy.context.scene
    for layer in s.view_layers:layer.material_override=None
    # Preserve installed +Z up / +X cutting edge, camera at +Y points the edge left.
    center=sum((Vector(v) for v in obj.bound_box),Vector())/8
    radius=max(math.hypot(v.co.x-center.x,v.co.z-center.z) for v in obj.data.vertices)
    factor=.332/radius
    for v in obj.data.vertices:v.co=(v.co-center)*factor+Vector((0,.085,0))
    s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    s.cycles.device='GPU'
    s.render.resolution_x=s.render.resolution_y=1024;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.film_transparent=True
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
    s.world=bpy.data.worlds.new('IconWorld');s.world.use_nodes=True
    bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.3,.3,.3,1);bg.inputs[1].default_value=.5
    frame=constant_material('BrushedFrame',(.25,.25,.25),.9,.29)[0]
    inset=constant_material('RecessedPlate',(.033,.033,.033),.65,.44)[0]
    silver=constant_material('SilverInsetRing',(.46,.46,.46),.9,.24)[0]
    dark=constant_material('RivetRecess',(.052,.052,.052),.8,.36)[0]
    cube('RecessedSquare',(0,-.035,0),(.952,.06,.952),inset,.028)
    for x in [-.447,.447]:cube('ThickSideRail',(x,.006,0),(.092,.095,.976),frame,.018)
    for z in [-.447,.447]:cube('ThickHorizontalRail',(0,.006,z),(.87,.095,.092),frame,.018)
    torus('InnerSilverRing',(0,.022,0),.380,.009,silver)
    for x in [-.432,.432]:
        for z in [-.432,.432]:
            bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.046,depth=.018,location=(x,.059,z),rotation=(math.pi/2,0,0))
            mount=bpy.context.object;mount.name='OctagonalRivetMount';mount.data.materials.append(dark)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1,location=(x,.073,z))
            rivet=bpy.context.object;rivet.name='CornerRivet';rivet.scale=(.027,.014,.027);rivet.data.materials.append(silver)
            for f in rivet.data.polygons:f.use_smooth=True
    cam=bpy.data.objects.new('IconCamera',bpy.data.cameras.new('IconCamera'));s.collection.objects.link(cam);s.camera=cam
    cam.location=(0,4,0);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO';cam.data.ortho_scale=1.;cam.data.clip_start=.001
    for name,pos,power,size in [('Key',(-1,2,2),180,2),('Fill',(1,2,-1),90,2),('Top',(0,-1,2),130,1.5)]:
        light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));s.collection.objects.link(light)
        light.location=pos;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler();light.data.energy=power;light.data.size=size
    gray['neutral_output'](s)
    key='blade_1_'+entry['id'];s.render.filepath=str(P/'Icons'/(key+'.png'))
    bpy.ops.wm.save_as_mainfile(filepath=str(P/(kind+'_Icon.blend')))
    bpy.ops.render.render(write_still=True)
    jobs.append({'id':entry['id'],'key':key,'source':s.render.filepath,'model':entry['mesh'],
                 'scene':str(P/(kind+'_Icon.blend')),'method':'direct actual mesh render; modeled metal frame; no concept image',
                 'camera':'+Y orthographic, +Z up, +X cutting edge left','subject_radius':.332,'ring_inner_radius':.371})
(P/'icon_deployments.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CRESCENT_REFERENCE_R4_ICON_RENDERED',flush=True)
