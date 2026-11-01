"""Render actual parts as upright grayscale inserts for the approved icon frame."""
import bpy,json,math,runpy,sys
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent;I=O/'IconSources';I.mkdir(exist_ok=True)
G=runpy.run_path('C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py')
M={'m24_factory_mag_5':{'objects':['M24_clip']},'m24_extended_mag_10':{'objects':['M24_Magazine10']}}
R={}
for key,row in M.items():
    iron=False
    source=O/'M24_MotionMagazine_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
    keep=[bpy.data.objects[n] for n in row['objects']]
    for o in keep:
        if iron:o.data=o.data.copy();o.data.transform(o.matrix_world)
        o.parent=None;o.matrix_world=Matrix.Identity(4);o.modifiers.clear();o.hide_render=False;o.hide_set(False)
    for o in list(bpy.data.objects):
        if o not in keep:bpy.data.objects.remove(o,do_unlink=True)
    # Adopt the new surface recipe before the icon-only grayscale conversion.
    if not iron:
        for group in ('Body',):
            m=bpy.data.materials.get('M24_Magazine5')
            if not m:continue
            n=m.node_tree.nodes;l=m.node_tree.links;p=next(x for x in n if x.type=='BSDF_PRINCIPLED')
            region=n.new('ShaderNodeTexImage');region.image=bpy.data.images.load(str(O.parent/'M24Surface20261027/Textures'/('T_M24_'+group+'_Regions.png')));region.image.colorspace_settings.name='Non-Color'
            sep=n.new('ShaderNodeSeparateColor');l.new(region.outputs['Color'],sep.inputs['Color'])
            # The original metallic/roughness sampling retains material identity.
            metal=p.inputs['Metallic'].links[0].from_socket if p.inputs['Metallic'].is_linked else None
            mix=n.new('ShaderNodeMixRGB');l.new(sep.outputs['Green'],mix.inputs[1]);l.new(sep.outputs['Red'],mix.inputs[2])
            if metal:l.new(metal,mix.inputs[0])
            l.new(mix.outputs[0],p.inputs['Roughness'])
            base=p.inputs['Base Color'].links[0].from_socket if p.inputs['Base Color'].is_linked else None
            finish=n.new('ShaderNodeMixRGB');finish.inputs[1].default_value=(.019,.019,.018,1);finish.inputs[2].default_value=(.034,.036,.039,1)
            if metal:l.new(metal,finish.inputs[0])
            color=n.new('ShaderNodeMixRGB');color.inputs[0].default_value=.24;l.new(finish.outputs[0],color.inputs[1])
            if base:l.new(base,color.inputs[2])
            l.new(color.outputs[0],p.inputs['Base Color'])
            for t in n:
                if t.type=='TEX_IMAGE' and t.image and 'normal' in t.image.name.lower():
                    t.image=bpy.data.images.load(str(O.parent/'M24Surface20261027/Textures'/('T_M24_'+group+'_Refined_N.png')));t.image.colorspace_settings.name='Non-Color'
    G['apply_grayscale'](keep)
    pts=[v.co for o in keep for v in o.data.vertices]
    low=Vector([min(v[i] for v in pts) for i in range(3)]);high=Vector([max(v[i] for v in pts) for i in range(3)])
    center=(low+high)*.5;scale=1.4/max(high-low)
    for o in keep:o.data=o.data.copy();o.data.transform(Matrix.Scale(scale,4)@Matrix.Translation(-center))
    s=bpy.context.scene
    bpy.ops.object.camera_add(location=(-3,-1.5 if iron else 1.05,0));c=bpy.context.object;c.rotation_euler=(-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=1.9;s.camera=c
    for pos,power,size in [((-2,1,2),130,2),((-2,-2,.4),70,1.5),((1,1,2),100,1)]:
        bpy.ops.object.light_add(type='AREA',location=pos);a=bpy.context.object;a.data.energy=power;a.data.size=size;a.rotation_euler=(-a.location).to_track_quat('-Z','Y').to_euler()
    s.world=bpy.data.worlds.new('Neutral icon studio');s.world.use_nodes=True
    next(x for x in s.world.node_tree.nodes if x.type=='BACKGROUND').inputs['Strength'].default_value=.35
    s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
    s.render.resolution_x=s.render.resolution_y=1024;s.render.resolution_percentage=100;s.render.film_transparent=True
    s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.use_compositing=False;s.render.use_sequencer=False
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';G['neutral_output'](s)
    s.render.filepath=str(I/(key+'.png'));bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(I/(key+'_Editable.blend')));bpy.ops.render.render(write_still=True)
    R[key]={'source':str(source),'objects':row['objects'],'native_forward':'+Y','native_up':'+Z','camera':list(c.location),'output':s.render.filepath,'frame':'FirearmFramedIcons20260930/muzzle_brake_framed_v2.png','icon_only_grayscale':True}
    (O/'icon_authoring.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('M24_ICON_INSERT_SAVED',key,flush=True)
