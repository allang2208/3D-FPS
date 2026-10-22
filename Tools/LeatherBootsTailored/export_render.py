"""Packed native source, FBX, production icon and requested actual model review."""
import importlib.util,json,math,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
rigio=module('boot_native_rig','Tools/BlueMageRobe/save_editable.py')
def material(name,family=None,color=None,rough=.7,metal=0,root=None,tile=1,vertex=True):
    m=bpy.data.materials.new(name);m.use_nodes=True;ns=m.node_tree.nodes;links=m.node_tree.links;bs=ns.get('Principled BSDF');bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal;bs.inputs['Specular IOR Level'].default_value=.28
    if color:bs.inputs['Base Color'].default_value=(*color,1)
    if family:
        uv=ns.new('ShaderNodeTexCoord');scale=ns.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=(tile,tile,1);links.new(uv.outputs['UV'],scale.inputs[0]);vc=ns.new('ShaderNodeVertexColor');vc.layer_name='BootFinish'
        for channel in ('BaseColor','Normal','ORM'):
            img=bpy.data.images.load(str((root or R/'Textures')/(family+'_'+channel+'.png')),check_existing=True);img.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';tex=ns.new('ShaderNodeTexImage');tex.image=img;links.new(scale.outputs[0],tex.inputs['Vector'])
            if channel=='BaseColor':
                if vertex:mul=ns.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;links.new(tex.outputs['Color'],mul.inputs[1]);links.new(vc.outputs['Color'],mul.inputs[2]);links.new(mul.outputs[0],bs.inputs['Base Color'])
                else:links.new(tex.outputs['Color'],bs.inputs['Base Color'])
            elif channel=='Normal':normal=ns.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs[0],bs.inputs['Normal'])
            else:
                split=ns.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],split.inputs[0]);links.new(split.outputs['Blue'],bs.inputs['Metallic'])
                if vertex:mul=ns.new('ShaderNodeMath');mul.operation='MULTIPLY';links.new(split.outputs['Green'],mul.inputs[0]);links.new(vc.outputs['Alpha'],mul.inputs[1]);links.new(mul.outputs[0],bs.inputs['Roughness'])
                else:links.new(split.outputs['Green'],bs.inputs['Roughness'])
    return m
def make(d,name,mats,rig=None,left=False):
    ids=[i for i,f in enumerate(d['triangles']) if not left or sum(d['positions'][v][0] for v in f)>0];used=sorted({v for i in ids for v in d['triangles'][i]});remap={v:i for i,v in enumerate(used)};me=bpy.data.meshes.new(name);me.from_pydata([(d['positions'][i][0]*.01,-d['positions'][i][1]*.01,d['positions'][i][2]*.01) for i in used],[],[[remap[v] for v in d['triangles'][i]] for i in ids]);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    for m in mats:me.materials.append(m)
    uv=me.uv_layers.new(name='PhysicalMaterialScale')
    for face,fi in zip(me.polygons,ids):
        face.material_index=d['triangle_materials'][fi];face.use_smooth=True
        for ci,li in enumerate(face.loop_indices):u,v=d['uv'][fi][ci];uv.data[li].uv=(u,1-v)
    me.normals_split_custom_set([(x,-y,z) for i in ids for x,y,z in d['normals'][i]])
    color_values=np.asarray(d['colors'],np.float32) if d.get('colors') else np.ones((len(d['positions']),4),np.float32)
    c=me.color_attributes.new(name='BootFinish',type='FLOAT_COLOR',domain='POINT');c.data.foreach_set('color',color_values[used].ravel());me.color_attributes.active_color=c
    if rig:
        groups={n:ob.vertex_groups.new(name=n) for n in {n for i in used for n in d['weights'][i]}}
        for vi,src in enumerate(used):
            for n,w in d['weights'][src].items():groups[n].add([vi],w,'REPLACE')
        ob.parent=rig;ob.modifiers.new('Native Jason foot articulation','ARMATURE').object=rig
    ob['SourceJSON']=str(R/'Authored/ue_leather_boots/Jason.json');return ob
def setup():
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=80;scene.cycles.use_denoising=True;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.view_settings.view_transform='AgX';scene.render.film_transparent=False
    world=bpy.data.worlds.new('BootReviewWorld');world.use_nodes=True;world.node_tree.nodes.clear();bg=world.node_tree.nodes.new('ShaderNodeBackground');out=world.node_tree.nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],out.inputs['Surface']);bg.inputs[0].default_value=(.16,.16,.16,1);bg.inputs[1].default_value=.35;scene.world=world
    def point(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
    for name,pos,power,size in [('Key',(-.8,-1.2,1.4),55,1.0),('Fill',(1.2,-.4,.8),25,1.2),('Rim',(.4,1.0,1.1),60,.7)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size;o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=pos;point(o,(0,0,.20))
    data=bpy.data.cameras.new('BootReviewCamera');data.type='ORTHO';cam=bpy.data.objects.new(data.name,data);scene.collection.objects.link(cam);scene.camera=cam
    return scene,cam,point
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;d=read(R/'Authored/ue_leather_boots/Jason.json');surface=read(R/'surfaces.json')
    mats=[material('AgedSteel',color=surface['metal_linear_color'],rough=.48,metal=1),material('BootLeather','BootLeather'),material('RubberOutsole','BootRubber'),material('WaxedThread',color=surface['thread_linear_color'],rough=.82),material('ReinforcedLeather','BootReinforced'),material('StackedWelt','BootWelt'),material('DarkLining','BootLeather')]
    rig=rigio.rig_for(d);ob=make(d,'SK_Jason_LeatherBoots_Continuous',mats,rig);bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
    folder=R/'Exports';folder.mkdir(exist_ok=True);fbx=folder/'Jason_LeatherBoots_Continuous.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
    bpy.ops.file.pack_all();blend=R/'LeatherBoots_Continuous_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));ob.hide_render=True
    if '--export-only' in sys.argv:
        write(R/'editable.json',dict(completed=True,blend=str(blend),fbx=str(fbx),icon=str(R/'ue_leather_boots.png'),review=[str(p) for p in (R/'Review').glob('*.png')],render_engine='Blender Cycles',runtime_tested=False));return
    left=make(d,'New_boot_review',mats,left=True);left.location.x=-.15
    old=read(PREVIOUS/'Authored/ue_leather_boots/Jason.json');old_mats=[material('OldSteel',color=(.22,.23,.24),rough=.48,metal=1),material('OldLeather','BootLeather',root=PREVIOUS/'Textures'),material('OldSole','BootRubber',root=PREVIOUS/'Textures'),material('OldThread',color=(.115,.068,.034),rough=.82),material('OldReinforcement','BootReinforced',root=PREVIOUS/'Textures'),material('OldWelt','BootWelt',root=PREVIOUS/'Textures'),material('OldLining',color=(.025,.018,.012),rough=.91)]
    previous=make(old,'Original_boot_review',old_mats,left=True);previous.location.x=.16
    scene,cam,point=setup();out=R/'Review';out.mkdir(exist_ok=True)
    cam.location=(1.0,-1.8,.55);point(cam,(.16,-.04,.18));cam.data.ortho_scale=.74;scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.filepath=str(out/'Boots_NewLeft_OldRight.png');bpy.ops.render.render(write_still=True)
    previous.hide_render=True;cam.location=(.75,-1.2,.36);point(cam,(.015,-.07,.18));cam.data.ortho_scale=.48;scene.render.resolution_x=1200;scene.render.resolution_y=1500;scene.render.filepath=str(out/'Boots_Detail.png');bpy.ops.render.render(write_still=True)
    cam.location=(.8,.6,.38);point(cam,(.015,-.025,.18));cam.data.ortho_scale=.48;scene.render.filepath=str(out/'Boots_Back.png');bpy.ops.render.render(write_still=True)
    cam.location=(-.8,-.25,.30);point(cam,(.015,-.07,.18));cam.data.ortho_scale=.48;scene.render.filepath=str(out/'Boots_Inner.png');bpy.ops.render.render(write_still=True)
    cam.location=(.7,-.3,.065);point(cam,(.02,-.09,.025));cam.data.ortho_scale=.36;scene.render.resolution_x=1600;scene.render.resolution_y=850;scene.render.filepath=str(out/'Sole_Welt_Close.png');bpy.ops.render.render(write_still=True)
    bottom=bpy.data.lights.new('Underside review fill','AREA');bottom.energy=25;bottom.size=.65;lamp=bpy.data.objects.new(bottom.name,bottom);scene.collection.objects.link(lamp);lamp.location=(-.3,-.4,-.65);point(lamp,(.015,-.09,-.02))
    cam.location=(.015,-.09,-1.1);cam.rotation_euler=(math.pi,0,0);cam.data.ortho_scale=.43;scene.render.resolution_x=1100;scene.render.resolution_y=1500;scene.render.filepath=str(out/'Outsole_Tread.png');bpy.ops.render.render(write_still=True);lamp.hide_render=True
    # Catalog item is the same current model on a transparent background.
    scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA';scene.render.resolution_x=512;scene.render.resolution_y=768;cam.location=(.75,-1.2,.36);point(cam,(.015,-.07,.18));cam.data.ortho_scale=.48;scene.render.filepath=str(R/'ue_leather_boots.png');bpy.ops.render.render(write_still=True)
    write(R/'editable.json',dict(completed=True,blend=str(blend),fbx=str(fbx),icon=scene.render.filepath,review=[str(p) for p in out.glob('*.png')],render_engine='Blender Cycles',runtime_tested=False));print('LEATHER_BOOTS_EXPORTED_AND_RENDERED',flush=True)
if __name__=='__main__':main()
