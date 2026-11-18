"""Fixed-light Blender lookdev and before/after geometry review; no game launch."""
import bpy,math,json,os
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ArtPassR2'
OUT.joinpath('Previews').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Authored/VillageFurniture_R2.blend'))
new={o.name.replace('SM_Village',''):o for o in bpy.context.scene.objects if o.type=='MESH'}
oldpath=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/Authored/VillageFurniture.blend'
with bpy.data.libraries.load(str(oldpath),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('SM_Village')]
old={}
for o in dst.objects:
    bpy.context.collection.objects.link(o);old[o.name.split('.')[0].replace('SM_Village','')]=o
for o in list(new.values())+list(old.values()):o.hide_set(False);o.hide_render=True;o.location=(0,0,0)
chapel=ROOT/'SourceAssets/TemperateHillsOldChapel/Concept01/Surfaces/Prepared';tex=OUT/'Textures'
def pbr(name,color,rough,normal,metal=0,roughchannel=1,tint=None):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    p=n.new('ShaderNodeBsdfPrincipled');o=n.new('ShaderNodeOutputMaterial');l.new(p.outputs['BSDF'],o.inputs['Surface'])
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.82
    def image(path,cs='Non-Color'):
        nn=n.new('ShaderNodeTexImage');nn.image=bpy.data.images.load(str(path),check_existing=True);nn.image.colorspace_settings.name=cs;return nn
    if isinstance(color,tuple):p.inputs['Base Color'].default_value=(*color,1)
    else:
        im=image(color,'sRGB');source=im.outputs['Color']
        if tint:
            mul=n.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(*tint,1);l.new(source,mul.inputs[1]);source=mul.outputs[0]
        l.new(source,p.inputs['Base Color'])
    if rough:
        im=image(rough);split=n.new('ShaderNodeSeparateColor');l.new(im.outputs['Color'],split.inputs[0]);l.new(split.outputs[roughchannel],p.inputs['Roughness'])
    if normal:
        im=image(normal);split=n.new('ShaderNodeSeparateColor');combine=n.new('ShaderNodeCombineColor');inv=n.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1
        l.new(im.outputs['Color'],split.inputs[0]);l.new(split.outputs[1],inv.inputs[1]);l.new(split.outputs[0],combine.inputs[0]);l.new(inv.outputs[0],combine.inputs[1]);l.new(split.outputs[2],combine.inputs[2])
        nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.7;l.new(combine.outputs[0],nm.inputs['Color']);l.new(nm.outputs[0],p.inputs['Normal'])
    return m
oak=pbr('Oak',chapel/'Timber_Color.png',chapel/'Timber_ARH.png',chapel/'Timber_NormalDX.png',tint=(.87,.85,.81))
end=pbr('Endgrain',tex/'Endgrain_Color.png',tex/'Endgrain_ORM.png',tex/'Endgrain_NormalDX.png')
linen=pbr('Linen',tex/'Linen_Color.png',tex/'Linen_ORM.png',tex/'Linen_NormalDX.png')
blanket=pbr('Blanket',tex/'Linen_Color.png',tex/'Linen_ORM.png',tex/'Linen_NormalDX.png',tint=(.48,.42,.32))
iron=pbr('Iron',(.22,.24,.25),None,None,.8)
ns=iron.node_tree.nodes;ls=iron.node_tree.links;p=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
noise=ns.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=160;noise.inputs['Detail'].default_value=3
bump=ns.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.25;bump.inputs['Distance'].default_value=.001;ls.new(noise.outputs['Fac'],bump.inputs['Height']);ls.new(bump.outputs[0],p.inputs['Normal']);p.inputs['Roughness'].default_value=.67
stone_inputs=OUT/'Inputs'
stone_rough=stone_inputs/'T_StoneSurface_01A_RHAOM.png';stone_normal=stone_inputs/'T_StoneSurface_01A_Normal.png'
stone=pbr('Stone',ROOT/'SourceAssets/ChapelShrineForecourt20261116/WallStoneR3/01A-BaseColor.png',
    stone_rough if stone_rough.exists() else None,stone_normal if stone_normal.exists() else None,roughchannel=0)
for name,label in [('Sign','BlacksmithSign'),('Closed','ClosedPlaque')]:
    m=oak.copy();m.name=name+'_Painted';ns=m.node_tree.nodes;ls=m.node_tree.links;p=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
    src=p.inputs['Base Color'].links[0].from_socket;mix=ns.new('ShaderNodeMixRGB');mix.blend_type='MIX';ls.new(src,mix.inputs[1]);mix.inputs[2].default_value=(.52,.42,.26,1)
    uv=ns.new('ShaderNodeUVMap');uv.uv_map='UV1';im=ns.new('ShaderNodeTexImage');im.image=bpy.data.images.load(str(tex/(label+'_Paint.png')));im.image.colorspace_settings.name='Non-Color';ls.new(uv.outputs[0],im.inputs[0]);ls.new(im.outputs[0],mix.inputs[0]);ls.new(mix.outputs[0],p.inputs['Base Color'])
    for obj in new.values():
        for i,mat in enumerate(obj.data.materials):
            if mat.name==name:obj.data.materials[i]=m
clay=pbr('ReviewClay',(.34,.35,.33),None,None)
floor=pbr('ReviewGround',(.14,.16,.14),None,None)
bpy.ops.mesh.primitive_plane_add(size=200);ground=bpy.context.object;ground.data.materials.append(floor);ground.location.z=-.002
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.4
world=bpy.data.worlds.new('Soft rural daylight');scene.world=world;world.use_nodes=True
bg=world.node_tree.nodes.new('ShaderNodeBackground');wo=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs[0].default_value=(.38,.45,.52,1);bg.inputs[1].default_value=.35
def light(name,xyz,power,size,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color;o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=xyz;o.rotation_euler=(Vector((0,0,.5))-o.location).to_track_quat('-Z','Y').to_euler()
light('Broad daylight',(-3,1,5),650,4,(1,.92,.82));light('Sky fill',(3,-2,4),500,4,(.73,.84,1));light('Edge bounce',(-1,-3,2),180,3,(1,.94,.82))
data=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',data);scene.collection.objects.link(cam);scene.camera=cam;data.lens=48
shots=[]
def shot(name,objects,eye,target,claymode=False):
    selected=os.environ.get('VILLAGE_ART_SHOTS','')
    if selected and name.split('-')[0] not in selected.split(','):return
    for o in list(new.values())+list(old.values()):o.hide_render=True
    for o in objects:o.hide_render=False
    scene.view_layers[0].material_override=clay if claymode else None
    cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/'Previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
    shots.append(dict(name=name,renderer='Blender Cycles',eye=eye,target=target,clay=claymode))
shot('01-bed-before-clay',[old['TimberBed']],(2.5,3,2.4),(0,0,.35),True)
shot('02-bed-after-clay',[new['TimberBed']],(2.5,3,2.4),(0,0,.35),True)
shot('03-bed-textile',[new['TimberBed']],(1.9,2.6,1.7),(0,0,.4))
shot('04-table-joinery',[new['OakTable']],(1.65,1.85,1.35),(0,0,.4))
shot('05-rack',[new['OakShelf']],(2,2.8,2.1),(0,0,.82))
new['BlacksmithSign'].location.z=.55
shot('06-shop-sign',[new['BlacksmithSign']],(1.25,2.25,1.5),(0,0,.65))
for i,key in enumerate(['OakTable','OakShelf','TimberBed','OakStool','IronStock','AbandonedTimber','HearthPad','BlacksmithSign','ClosedPlaque']):
    new[key].location=((i%3-1)*2.5,(i//3-1)*2.7,.6 if key in ('BlacksmithSign','ClosedPlaque') else 0)
shot('07-kit-overview',list(new.values()),(9,12,11),(0,0,.4))
(OUT/'Previews/cameras.json').write_text(json.dumps(shots,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authored/VillageFurniture_R2_Lookdev.blend'))
