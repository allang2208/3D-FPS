"""Save the actual RuneSword sleeve source with native rig and packed PBR maps."""
import json
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6SleeveRepair20261018';T=P/'SourceAssets/ST6LowerSet20261018/Textures';d=json.loads((R/'Authored/RuneSword.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True)
materials=[]
for name,tint in [('ST6_Ripstop',1.),('ST6_Cuff',.9),('ST6_Lining',.6)]:
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF'];uv=n.new('ShaderNodeTexCoord');mul=n.new('ShaderNodeVectorMath');mul.operation='SCALE';mul.inputs[3].default_value=4;l.new(uv.outputs['UV'],mul.inputs[0])
    for channel in ('BaseColor','Normal','ORM'):
        image=bpy.data.images.load(str(T/('T_ST6_Fabric_'+channel+'.png')),check_existing=True)
        if channel!='BaseColor':image.colorspace_settings.name='Non-Color'
        tex=n.new('ShaderNodeTexImage');tex.image=image;l.new(mul.outputs[0],tex.inputs['Vector'])
        if channel=='BaseColor':
            scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=tint;l.new(tex.outputs['Color'],scale.inputs[0]);l.new(scale.outputs[0],p.inputs['Base Color'])
        elif channel=='Normal':
            nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.6;l.new(tex.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],p.inputs['Normal'])
        else:
            sp=n.new('ShaderNodeSeparateColor');l.new(tex.outputs['Color'],sp.inputs[0]);l.new(sp.outputs['Green'],p.inputs['Roughness'])
    materials.append(m)
bones=d['bones'];ordered=sorted(bones,key=lambda n:bones[n]['index']);byid={b['index']:n for n,b in bones.items()};reflection=Matrix.Diagonal((1,-1,1));arm=bpy.data.armatures.new('RuneSword_NativeRig');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for name in ordered:
    b=bones[name];eb=arm.edit_bones.new(name);axes=Matrix(b['axes']).transposed()
    for i in range(3):axes.col[i]=axes.col[i].normalized()
    matrix=(reflection@axes@reflection).to_4x4();matrix.translation=reflection@Vector(b['position'])*.01;eb.matrix=matrix;eb.length=.025
for name in ordered:
    parent=bones[name]['parent']
    if parent>=0:arm.edit_bones[name].parent=arm.edit_bones[byid[parent]]
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
mesh=bpy.data.meshes.new('ST6_NativeSleeves');mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in d['positions']],[],d['triangles']);mesh.update();ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
for m in materials:mesh.materials.append(m)
uv=mesh.uv_layers.new(name='Physical25cm')
for fi,poly in enumerate(mesh.polygons):
    poly.material_index=d['triangle_materials'][fi];poly.use_smooth=True
    for ci,li in enumerate(poly.loop_indices):u,v=d['uv'][fi][ci];uv.data[li].uv=(u,1-v)
mesh.normals_split_custom_set([(x,-y,z) for face in d['normals'] for x,y,z in face]);groups={n:ob.vertex_groups.new(name=n) for n in {n for ws in d['weights'] for n in ws}}
for vi,ws in enumerate(d['weights']):
    for n,w in ws.items():groups[n].add([vi],w,'REPLACE')
ob.parent=rig;ob.modifiers.new('Native binding','ARMATURE').object=rig;ob['Contract']=d['contract'];bpy.context.scene['RemainingNativeVariants']='Authored/*.json';bpy.context.scene['UECuffDoubleTopstitch']='Tools/ST6SleeveRepair/save_assets.py procedural material'
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'ST6_RuneSword_NativeSleeves.blend'));bpy.ops.export_scene.fbx(filepath=str(R/'ST6_RuneSword_NativeSleeves.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE');print('ST6_NATIVE_EDITABLE_SAVED',flush=True)
