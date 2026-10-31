"""Model-source close views with the actual PBR texture sources; no UE/game capture."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
from design import SURFACES
bpy.ops.wm.open_mainfile(filepath=str(R/'BedroomPilot_Source.blend'))
exports=json.loads((R/'Review/texture-exports.json').read_text('utf8'))
assets=json.loads((R/'assets_saved.json').read_text('utf8'))
def texture_file(path):
    return exports[path] if path in exports else str(R/'Textures'/(path.split('/')[-1].split('.')[0]+'.png'))
for mat in bpy.data.materials:
    if mat.name not in SURFACES:continue
    spec=SURFACES[mat.name];details=assets['material_details'][mat.name];nodes=mat.node_tree.nodes;links=mat.node_tree.links;bsdf=nodes.get('Principled BSDF')
    uv=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=1/spec['period'];links.new(uv.outputs['UV'],scale.inputs[0])
    def tex(path,color=False):
        node=nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(texture_file(path),check_existing=True)
        node.image.colorspace_settings.name='sRGB' if color else 'Non-Color';links.new(scale.outputs['Vector'],node.inputs['Vector']);return node
    sources=details['sources'];normal=tex(sources['N']);separate=nodes.new('ShaderNodeSeparateColor');links.new(normal.outputs['Color'],separate.inputs[0])
    invert=nodes.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1;links.new(separate.outputs['Green'],invert.inputs[1])
    combine=nodes.new('ShaderNodeCombineColor');links.new(separate.outputs['Red'],combine.inputs['Red']);links.new(invert.outputs[0],combine.inputs['Green']);links.new(separate.outputs['Blue'],combine.inputs['Blue'])
    n=nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=spec['strength'];links.new(combine.outputs[0],n.inputs['Color']);links.new(n.outputs['Normal'],bsdf.inputs['Normal'])
    if 'ORM' in sources:
        masks=tex(sources['ORM']);split=nodes.new('ShaderNodeSeparateColor');links.new(masks.outputs['Color'],split.inputs[0]);links.new(split.outputs['Green'],bsdf.inputs['Roughness'])
    elif 'R' in sources:
        rough=tex(sources['R']);maprange=nodes.new('ShaderNodeMapRange');maprange.inputs['To Min'].default_value=spec['limits'][0];maprange.inputs['To Max'].default_value=spec['limits'][1];links.new(rough.outputs['Color'],maprange.inputs[0]);links.new(maprange.outputs[0],bsdf.inputs['Roughness'])
    if 'BC' in sources:
        color=tex(sources['BC'],True)
        if 'generated' in spec:links.new(color.outputs['Color'],bsdf.inputs['Base Color'])
        else:
            bw=nodes.new('ShaderNodeRGBToBW');links.new(color.outputs[0],bw.inputs[0]);mult=nodes.new('ShaderNodeVectorMath');mult.operation='SCALE';mult.inputs[0].default_value=spec['color'];links.new(bw.outputs[0],mult.inputs[3]);links.new(mult.outputs[0],bsdf.inputs['Base Color'])
    if 'emission' in spec:bsdf.inputs['Emission Color'].default_value=(*spec['emission'],1);bsdf.inputs['Emission Strength'].default_value=.5
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
scene.world=scene.world or bpy.data.worlds.new('PBR Review World')
scene.world.color=(.2,.2,.2);scene.view_settings.view_transform='AgX'
world=scene.world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.24,.27,.32,1);world.node_tree.nodes['Background'].inputs[1].default_value=.4
for name,pos,power,size in [('Key',(-2,-3,4),500,4),('Fill',(3,-1,2),250,3),('Rim',(0,3,3),400,2)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,.5))-ob.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.clip_start=.001
for name,key,eye,target,size in [('shelf','WallShelf',(1.25,-2.5,1.35),(0,0,.34),1.95),('bed-lamp','BedRefined',(1.45,-.4,1.72),(.88,.96,1.275),.46),('wall-lamp','ReadingFixture',(.4,-.6,-.19),(0,-.12,0),.48),('bedding','BedRefined',(2.3,-3.3,2.8),(0,0,.75),3.0)]:
    for ob in scene.objects:
        if ob.type=='MESH':ob.hide_render=ob.name!='SM_BP_'+key
    cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=size
    scene.render.filepath=str(R/'Review'/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('PBR_MODEL_VIEW',name,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Review/PBR_Source_Review.blend'))
