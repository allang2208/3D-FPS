"""Render the production 3x3 inventory icon and export its editable display source."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;OLD=O.parent/'BenelliM4Super9020261006'
d=json.loads((O/'pickup.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
texdir=OLD/'Original/Source/textures'
image=bpy.data.images.load(str(texdir/'sleeve_st6_generalist_Base_color.png'))
normal=bpy.data.images.load(str(texdir/'sleeve_st6_generalist_Normal_OpenGL.png'));normal.colorspace_settings.name='Non-Color'

def make_material(name,original=False,torso=False):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;t=mat.node_tree;p=t.nodes['Principled BSDF']
    p.inputs['Roughness'].default_value=.72 if original else .78;p.inputs['Specular IOR Level'].default_value=.26
    def link(a,b):t.links.new(a,b)
    def mathop(op,a,b=None):
        n=t.nodes.new('ShaderNodeMath');n.operation=op
        if isinstance(a,(int,float)):n.inputs[0].default_value=a
        else:link(a,n.inputs[0])
        if b is not None:
            if isinstance(b,(int,float)):n.inputs[1].default_value=b
            else:link(b,n.inputs[1])
        return n.outputs[0]
    coord=t.nodes.new('ShaderNodeTexCoord')
    if original:
        c=t.nodes.new('ShaderNodeTexImage');c.image=image;link(coord.outputs['UV'],c.inputs['Vector']);link(c.outputs['Color'],p.inputs['Base Color'])
        n=t.nodes.new('ShaderNodeTexImage');n.image=normal;nm=t.nodes.new('ShaderNodeNormalMap');link(coord.outputs['UV'],n.inputs['Vector']);link(n.outputs['Color'],nm.inputs['Color']);link(nm.outputs['Normal'],p.inputs['Normal'])
        return mat
    mult=t.nodes.new('ShaderNodeVectorMath');mult.operation='MULTIPLY';mult.inputs[1].default_value=(100,-100,100);link(coord.outputs['Object'],mult.inputs[0])
    split=t.nodes.new('ShaderNodeSeparateXYZ');link(mult.outputs['Vector'],split.inputs[0])
    mirrored=[]
    for axis in ('X','Y','Z'):
        frac=mathop('FRACT',mathop('DIVIDE',split.outputs[axis],36.0))
        mirrored.append(mathop('SUBTRACT',1.0,mathop('ABSOLUTE',mathop('SUBTRACT',mathop('MULTIPLY',frac,2.0),1.0))))
    geom=t.nodes.new('ShaderNodeNewGeometry');ns=t.nodes.new('ShaderNodeSeparateXYZ');link(geom.outputs['Normal'],ns.inputs[0])
    weights=[mathop('POWER',mathop('ABSOLUTE',ns.outputs[k]),4.0) for k in ('X','Y','Z')]
    total=mathop('MAXIMUM',mathop('ADD',mathop('ADD',weights[0],weights[1]),weights[2]),.0001)
    samples=[]
    for i,(a,b) in enumerate(((1,2),(0,2),(0,1))):
        uv=t.nodes.new('ShaderNodeCombineXYZ');link(mathop('ADD',.1,mathop('MULTIPLY',mirrored[a],.17)),uv.inputs['X']);link(mathop('SUBTRACT',1.,mathop('ADD',.78,mathop('MULTIPLY',mirrored[b],.15))),uv.inputs['Y'])
        sample=t.nodes.new('ShaderNodeTexImage');sample.image=image;link(uv.outputs[0],sample.inputs['Vector'])
        scale=t.nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';link(sample.outputs['Color'],scale.inputs[0]);link(mathop('DIVIDE',weights[i],total),scale.inputs['Scale']);samples.append(scale.outputs[0])
    a=t.nodes.new('ShaderNodeVectorMath');a.operation='ADD';link(samples[0],a.inputs[0]);link(samples[1],a.inputs[1])
    b=t.nodes.new('ShaderNodeVectorMath');b.operation='ADD';link(a.outputs[0],b.inputs[0]);link(samples[2],b.inputs[1])
    colour=b.outputs[0]
    if torso:
        attr=t.nodes.new('ShaderNodeVertexColor');attr.layer_name='TorsoPanels'
        mix=t.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;link(colour,mix.inputs[1]);link(attr.outputs['Color'],mix.inputs[2]);colour=mix.outputs[0]
    link(colour,p.inputs['Base Color'])
    # Preview micro-relief; UE uses the original texture normals and surface derivatives.
    wave=t.nodes.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction='DIAGONAL';wave.inputs['Scale'].default_value=360
    link(coord.outputs['Object'],wave.inputs['Vector'])
    noise=t.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1100;noise.inputs['Detail'].default_value=2
    link(coord.outputs['Object'],noise.inputs['Vector'])
    weave=mathop('MULTIPLY',wave.outputs['Color'],noise.outputs['Fac'])
    bump=t.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00006;bump.inputs['Strength'].default_value=.32
    link(weave,bump.inputs['Height']);link(bump.outputs['Normal'],p.inputs['Normal'])
    return mat

mesh=bpy.data.meshes.new('ST6_OriginalSleeves_NativeBody_Display')
points=np.array(d['positions']);mesh.from_pydata((points*np.array([.01,-.01,.01])).tolist(),[],d['triangles']);mesh.update()
obj=bpy.data.objects.new(mesh.name,mesh);sc.collection.objects.link(obj)
for material in (make_material('ST6 original sleeves',True),make_material('ST6 native torso',torso=True),make_material('ST6 native arm fabric'),make_material('ST6 collar',torso=True)):mesh.materials.append(material)
uv=mesh.uv_layers.new(name='UVMap');panels=mesh.color_attributes.new(name='TorsoPanels',type='FLOAT_COLOR',domain='CORNER')
origin=np.array(d['body_origin']);shoulder=d['shoulder_height']
def smooth(a,b,x):
    q=np.clip((x-a)/(b-a),0,1);return q*q*(3-2*q)
for face,coords,normals,material in zip(mesh.polygons,d['uv'],d['normals'],d['triangle_materials']):
    face.material_index=material;face.use_smooth=True
    for li,vi,tex,n in zip(face.loop_indices,face.vertices,coords,normals):
        uv.data[li].uv=(tex[0],1-tex[1]);x,y,h=points[vi]-origin
        panel=min(1,float(smooth(12.5,17.5,abs(x))*.50+smooth(shoulder-10,shoulder-5,h)*.32))
        facing=float(smooth(.05,.65,-n[1]));placket=(1-float(smooth(.45,.75,abs(x))))*facing
        band=float(smooth(d['collar_top']-2.8,d['collar_top']-2.3,points[vi,2]));shade=(1-.14*panel)*(1-.16*placket-.12*band)
        panels.data[li].color=(shade,shade,shade,1)
mesh.normals_split_custom_set((np.array(d['normals']).reshape(-1,3)*np.array([1,-1,1])).tolist())
sc.world=bpy.data.worlds.new('ST6Studio');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.24,.28,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.22
for name,pos,power in [('Key',(-.65,1.05,1.25),85),('Fill',(1.1,.6,.25),30),('Rim',(.1,-1.0,.65),45)]:
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.size=.8;lo=bpy.data.objects.new(name,ld);sc.collection.objects.link(lo);lo.location=pos;lo.rotation_euler=(-lo.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('IconCamera');camd.type='ORTHO';cam=bpy.data.objects.new('IconCamera',camd);sc.collection.objects.link(cam);sc.camera=cam
blender_points=points*np.array([.01,-.01,.01]);span=np.ptp(blender_points,axis=0);camd.ortho_scale=max(span[0],span[2])/.91
cam.location=(.12,2.2,.08);cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
sc.render.engine='CYCLES';sc.cycles.samples=48;sc.render.resolution_x=sc.render.resolution_y=320;sc.render.resolution_percentage=100;sc.render.film_transparent=True
sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.view_settings.view_transform='Standard';sc.view_settings.exposure=-.7
sc.render.filepath=str(O/'ue_st6_sleeves.png')
bpy.ops.render.render(write_still=True)
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(O/'SM_ue_st6_sleeves.fbx'),use_selection=True,apply_scale_options='FBX_SCALE_NONE',object_types={'MESH'},use_mesh_modifiers=False,add_leaf_bones=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ST6_NativeBody_Icon.blend'))
(O/'icon_receipt.json').write_text(json.dumps(dict(icon=str(O/'ue_st6_sleeves.png'),size=[320,320],grid=[3,3],source=str(O/'pickup.json'),game_run=False),indent=2))
# Optional offline review is only requested explicitly.
import sys
if '--review' in sys.argv:
    # User requested an overall check: inspect the actual garment in three offline views.
    sc.render.resolution_x=sc.render.resolution_y=900;sc.cycles.samples=32
    sc.render.film_transparent=False;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.045,.052,.065,1)
    for title,location,target,scale in [
        ('front',(0.30,2.2,.25),(0,0,.02),camd.ortho_scale),
        ('back',(-.3,-2.2,.30),(0,0,.02),camd.ortho_scale),
        ('collar',(.24,.85,.62),(0,0,d['collar_top']*.01-.055),.42)]:
        cam.location=location;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camd.ortho_scale=scale
        sc.render.filepath=str(O/('review_'+title+'.png'));bpy.ops.render.render(write_still=True)
    print('ST6_PRODUCTION_ICON_AND_OFFLINE_VIEWS_EXPORTED')
