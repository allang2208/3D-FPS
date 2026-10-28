"""Requested projection check on actual UE LOD0 geometry: old atlas vs centimeter projection."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]/'KukriComponentVariants20261026'))
from asset_tools import make_mat,node,op,tex
geometry=json.loads((P/'runtime-blade-geometry.json').read_text())
layouts=json.loads((P/'projection-layouts.json').read_text())
kinds=['Factory','Swift','HeavyBack','FoldedBalanced','Hunter','Canine']
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8
scene.render.resolution_x=1800;scene.render.resolution_y=1350;scene.render.resolution_percentage=100
scene.render.film_transparent=False;scene.world=bpy.data.worlds.new('Dark background');scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.012,.015,.020,1)
scene.view_settings.view_transform='Standard'
for col,(data,kind,layout) in enumerate(zip(geometry,kinds,layouts)):
    for row in range(2):
        vertices=[tuple(q/100 for q in v) for v in data['vertices']]
        triangles=[data['triangles'][i:i+3] for i in range(0,len(data['triangles']),3)]
        mesh=bpy.data.meshes.new(kind+str(row));mesh.from_pydata(vertices,[],triangles);mesh.update()
        obj=bpy.data.objects.new(kind+str(row),mesh);bpy.context.collection.objects.link(obj)
        obj.location=((col-2.5)*.17-.025,0,.22 if row==0 else -.22)
        layer=mesh.uv_layers.new(name='UVMap')
        for loop in mesh.loops:
            uv=data['uvs'][loop.vertex_index];layer.data[loop.index].uv=(uv[0],1-uv[1])
        mat,nt,bs,out=make_mat(kind+str(row));mesh.materials.append(mat)
        if row==0:
            image=tex(nt,P.parent/'Textures'/('T_KukriMask_'+kind+'_Berserker.png'))
            ink=image.outputs['Color']
        else:
            coord=node(nt,'ShaderNodeTexCoord');sep=node(nt,'ShaderNodeSeparateXYZ');nt.links.new(coord.outputs['Object'],sep.inputs[0])
            x,z=sep.outputs['X'],sep.outputs['Z'];cx,cz=layout['center_cm'];a=layout['angle_radians'];c,s=math.cos(a),math.sin(a)
            dx=op(nt,'SUBTRACT',op(nt,'MULTIPLY',x,100),cx);dz=op(nt,'SUBTRACT',op(nt,'MULTIPLY',z,100),cz)
            u=op(nt,'ADD',op(nt,'DIVIDE',op(nt,'SUBTRACT',op(nt,'MULTIPLY',dx,c),op(nt,'MULTIPLY',dz,s)),layout['width_cm']),.5)
            v=op(nt,'ADD',op(nt,'DIVIDE',op(nt,'ADD',op(nt,'MULTIPLY',dx,s),op(nt,'MULTIPLY',dz,c)),layout['height_cm']),.5)
            uv=node(nt,'ShaderNodeCombineXYZ');nt.links.new(u,uv.inputs[0]);nt.links.new(v,uv.inputs[1])
            image=tex(nt,P.parent/'Art/WolfSigil.png');image.extension='CLIP';nt.links.new(uv.outputs[0],image.inputs['Vector'])
            bw=node(nt,'ShaderNodeRGBToBW');nt.links.new(image.outputs['Color'],bw.inputs[0]);ink=op(nt,'MULTIPLY',bw.outputs[0],image.outputs['Alpha'])
        mix=node(nt,'ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[1].default_value=(.14,.16,.18,1);mix.inputs[2].default_value=(.8,.025,.045,1)
        nt.links.new(ink,mix.inputs[0]);emit=node(nt,'ShaderNodeEmission');nt.links.new(mix.outputs[0],emit.inputs[0]);nt.links.new(emit.outputs[0],out.inputs[0])
        bpy.ops.object.text_add(location=((col-2.5)*.17-.045,-.004,.52 if row==0 else .075),rotation=(math.pi/2,0,0))
        label=bpy.context.object;label.data.body=('OLD ' if row==0 else 'NEW ')+kind;label.data.size=.013
camera=bpy.data.cameras.new('Face comparison');cam=bpy.data.objects.new('Face comparison',camera);bpy.context.collection.objects.link(cam)
cam.location=(0,-4,.14);cam.rotation_euler=(Vector((0,0,.14))-cam.location).to_track_quat('-Z','Y').to_euler()
camera.type='ORTHO';camera.ortho_scale=1.13;scene.camera=cam
scene.render.filepath=str(P/'rune-projection-comparison.png');bpy.ops.render.render(write_still=True)
print('RUNE_PROJECTION_COMPARISON_SAVED',flush=True)
