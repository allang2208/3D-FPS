"""Actual Blender model review explicitly requested by the user."""
import json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=Path(globals().get('ROOT_OVERRIDE',P/'SourceAssets/RangerLeatherPants20261021'));PREVIEW_ONLY=globals().get('PREVIEW_ONLY',False);OUT=R/('Preview' if PREVIEW_ONLY else 'Review');OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'RangerLeatherPants_Editable.blend'))
source=bpy.data.objects['SK_Jason_RangerLeatherPants'];rig=source.parent
for ob in bpy.data.objects:
    if ob.type=='MESH':ob.hide_render=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=128 if PREVIEW_ONLY else 64;scene.cycles.use_denoising=True;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.film_transparent=False;scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
world=bpy.data.worlds.new('ReviewNeutralWorld');world.use_nodes=True
nodes=world.node_tree.nodes;nodes.clear();bg=nodes.new('ShaderNodeBackground');output=nodes.new('ShaderNodeOutputWorld');world.node_tree.links.new(bg.outputs[0],output.inputs['Surface']);bg.inputs[0].default_value=(.18,.18,.18,1);bg.inputs[1].default_value=.30;scene.world=world
def point(ob,p):ob.rotation_euler=(Vector(p)-ob.location).to_track_quat('-Z','Y').to_euler()
for name,position,power,size in [('Key',(-1.5,-2,2.3),250,1.8),('Fill',(1.8,-1.3,1),80,2.0),('Rim',(.5,1.4,1.9),180,1.5)]:
    data=bpy.data.lights.new('Review'+name,'AREA');data.energy=power;data.size=size;ob=bpy.data.objects.new(data.name,data);scene.collection.objects.link(ob);ob.location=position;point(ob,(0,0,.58))
cam_data=bpy.data.cameras.new('ReviewCamera');cam_data.type='ORTHO';cam=bpy.data.objects.new(cam_data.name,cam_data);scene.collection.objects.link(cam);scene.camera=cam
copies=[]
for label,x,angle in [('Front',-.49,0),('Side',0,math.pi/2),('Back',.49,math.pi)]:
    ob=source.copy();ob.data=source.data;ob.name='Review_'+label;ob.parent=None
    for modifier in list(ob.modifiers):ob.modifiers.remove(modifier)
    scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False);ob.location=(x,0,0);ob.rotation_euler=(0,0,angle);copies.append(ob)
cam.location=(0,-4,.56);point(cam,(0,0,.56));cam_data.ortho_scale=1.58;scene.render.resolution_x=1800;scene.render.resolution_y=1200
scene.render.filepath=str(OUT/'Model_FrontSideBack.png');bpy.ops.render.render(write_still=True)
for ob in copies:ob.hide_render=True
source.hide_render=False;source.hide_set(False);rig.hide_set(False)
cam.location=(.22,-2,.60);point(cam,(.08,0,.60));cam_data.ortho_scale=.54;scene.render.resolution_x=1200;scene.render.resolution_y=1400
scene.render.filepath=str(OUT/'Model_KneePocketDetail.png');bpy.ops.render.render(write_still=True)
cam.location=(.17,-2,.49);point(cam,(.12,0,.49));cam_data.ortho_scale=.22
scene.render.filepath=str(OUT/'Model_LeatherGrainClose.png');bpy.ops.render.render(write_still=True)
if PREVIEW_ONLY:
    cam.location=(.10,-2,.945);point(cam,(.03,0,.945));cam_data.ortho_scale=.29;scene.render.resolution_x=1400;scene.render.resolution_y=1000
    scene.render.filepath=str(OUT/'Model_WaistDetail.png');bpy.ops.render.render(write_still=True)
    (OUT/'render_receipt.json').write_text(json.dumps(dict(source=str(R/'RangerLeatherPants_Editable.blend'),views=['Model_FrontSideBack.png','Model_KneePocketDetail.png','Model_LeatherGrainClose.png','Model_WaistDetail.png'],engine='Blender Cycles',samples=128,scope='User requested actual model render; current native-bound mesh and packed PBR, bake-only high mesh excluded; no game testing'),indent=2),encoding='utf-8')
    print('RANGER_CURRENT_MODEL_PREVIEW_RENDERED',flush=True)
    sys.exit(0)
# A single isolated bend checks garment continuity, not the game's animation set.
for name,angle in [('thigh_l',-48),('calf_l',80)]:
    bone=rig.pose.bones[name];h=bone.matrix.translation.copy();bone.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-h)@bone.matrix
bpy.context.view_layer.update();cam.location=(1.6,-2,.64);point(cam,(0,0,.61));cam_data.ortho_scale=1.13;scene.render.resolution_x=1300;scene.render.resolution_y=1300
scene.render.filepath=str(OUT/'Model_BendPose.png');bpy.ops.render.render(write_still=True)
# Actual existing tall-boot shell supplies both a static assembly view and a
# geometry clearance sample; material display here is neutral inspection gray.
for name in ('thigh_l','calf_l'):rig.pose.bones[name].matrix_basis=Matrix.Identity(4)
source.hide_render=True;fit=bpy.data.objects['SK_Jason_HighBootsFit_RangerLeatherPants'];fit.hide_render=False;fit.hide_set(False);fit.parent.hide_set(False)
boot=json.loads((P/'SourceAssets/BrownLeatherSet20261004/Jason_LeatherBoots.json').read_bytes());mesh=bpy.data.meshes.new('ActualLeatherBoots');mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in boot['positions']],[],boot['triangles']);mesh.update();boots=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(boots)
mat=bpy.data.materials.new('BootInspectionGray');mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.055,.055,.055,1);bs.inputs['Roughness'].default_value=.72;mesh.materials.append(mat)
for poly in mesh.polygons:poly.use_smooth=True
cam.location=(.8,-3,.50);point(cam,(0,0,.50));cam_data.ortho_scale=1.15;scene.render.resolution_x=1200;scene.render.resolution_y=1300
bpy.context.view_layer.update();scene.render.filepath=str(OUT/'Model_TallBootAssembly.png');bpy.ops.render.render(write_still=True)
(OUT/'render_receipt.json').write_text(json.dumps(dict(source=str(R/'RangerLeatherPants_Editable.blend'),views=['Model_FrontSideBack.png','Model_KneePocketDetail.png','Model_LeatherGrainClose.png','Model_BendPose.png','Model_TallBootAssembly.png'],engine='Blender Cycles',samples=64,scope='User requested model review; isolated 48 degree hip / 80 degree knee bend and actual existing tall boot shell in inspection gray; not game animation validation'),indent=2))
print('RANGER_MODEL_REVIEW_RENDERED',flush=True)
