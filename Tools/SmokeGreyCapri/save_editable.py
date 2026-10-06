"""Save a packed editable set with the native rig, packed cotton maps and high-boot cuff variant."""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SmokeGreyCapri20261004'
bpy.ops.wm.read_factory_settings(use_empty=True)
def constant(name,color,rough,metal=0):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal;return mat
def textured(name,root,prefix,tint=(1,1,1)):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;bs=n.get('Principled BSDF')
    uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=4.;l.new(uv.outputs['UV'],scale.inputs[0])
    for channel in ['BaseColor','Normal','ORM']:
        img=bpy.data.images.load(str(root/(prefix+channel+'.png')),check_existing=True)
        if channel!='BaseColor':img.colorspace_settings.name='Non-Color'
        tex=n.new('ShaderNodeTexImage');tex.image=img;l.new(scale.outputs[0],tex.inputs['Vector'])
        if channel=='BaseColor':
            mult=n.new('ShaderNodeVectorMath');mult.operation='MULTIPLY';mult.inputs[1].default_value=tint;l.new(tex.outputs['Color'],mult.inputs[0]);l.new(mult.outputs[0],bs.inputs['Base Color'])
        elif channel=='Normal':
            node=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],node.inputs['Color']);l.new(node.outputs[0],bs.inputs['Normal'])
        else:
            split=n.new('ShaderNodeSeparateColor');l.new(tex.outputs['Color'],split.inputs[0]);l.new(split.outputs['Green'],bs.inputs['Roughness']);l.new(split.outputs['Blue'],bs.inputs['Metallic'])
    return mat
materials=[constant('Gunmetal button',(.065,.073,.075),.57,1),
    textured('Smoke gray cotton twill',R/'Textures','T_SmokeGreyTwill_'),
    constant('Unused slot',(.1,.1,.1),.8),
    constant('Tonal cotton thread',(.067,.070,.062),.88),
    textured('Cotton inner facing',R/'Textures','T_SmokeGreyTwill_',(.84,.85,.83)),
    constant('Native skin - UE uses original Jason skin material',(.38,.23,.16),.55)]
native=json.loads((R/'native_reference.json').read_text());bones=native['bones'];reflection=Matrix.Diagonal((1,-1,1))
arm=bpy.data.armatures.new('Jason_NativeReference');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for b in bones:
    bone=arm.edit_bones.new(b['name']);axes=Matrix(b['axes']).transposed()
    for i in range(3):axes.col[i]=axes.col[i].normalized()
    matrix=(reflection@axes@reflection).to_4x4();matrix.translation=reflection@Vector(b['position'])*.01;bone.matrix=matrix;bone.length=.025
for b in bones:
    if b['parent']>=0:arm.edit_bones[b['name']].parent=arm.edit_bones[bones[b['parent']]['name']]
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
for name,hidden in [('Jason_SmokeGreyCapri',False),('Jason_SmokeGreyCapri_HighBootsFit',True)]:
    d=json.loads((R/(name+'.json')).read_text());coll=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(coll);coll.hide_render=hidden;coll.hide_viewport=hidden
    face_start=0
    for part in d['parts']:
        first=part['first_vertex'];last=first+part['vertices'];nf=part['triangles'];mesh=bpy.data.meshes.new(part['name'])
        mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in d['positions'][first:last]],[],[[i-first for i in f] for f in d['triangles'][face_start:face_start+nf]]);mesh.update()
        ob=bpy.data.objects.new(mesh.name,mesh);coll.objects.link(ob);ob.parent=rig;ob.modifiers.new('Native Jason binding','ARMATURE').object=rig
        mesh.materials.append(materials[part['material']]);uv=mesh.uv_layers.new(name='Physical25cm')
        for fi,poly in enumerate(mesh.polygons):
            poly.use_smooth=True
            for ci,li in enumerate(poly.loop_indices):u,v=d['uv'][face_start+fi][ci];uv.data[li].uv=(u,1-v)
        mesh.normals_split_custom_set([(n[0],-n[1],n[2]) for face in d['normals'][face_start:face_start+nf] for n in face])
        ids={bi for ws in d['weights'][first:last] for bi,w in ws};groups={bi:ob.vertex_groups.new(name=bones[bi]['name']) for bi in ids}
        for vi,ws in enumerate(d['weights'][first:last]):
            for bi,w in ws:groups[bi].add([vi],w,'REPLACE')
        ob['SourceGeometry']=name+'.json';ob['Units']='metres; JSON and UE centimetres';face_start+=nf
field=np.load(R/'TwillHighField.npz');height=field['height_cm'][::2,::2];n=len(height);span=float(field['span_cm'])
mesh=bpy.data.meshes.new('HIGH_CottonTwill');mesh.from_pydata([(x/(n-1)*span*.01,y/(n-1)*span*.01,float(height[y,x])*.01) for y in range(n) for x in range(n)],[],[(y*n+x,y*n+x+1,(y+1)*n+x+1,(y+1)*n+x) for y in range(n-1) for x in range(n-1)])
ob=bpy.data.objects.new(mesh.name,mesh);coll=bpy.data.collections.new('BAKE_ONLY');bpy.context.scene.collection.children.link(coll);coll.objects.link(ob);coll.hide_render=True;coll.hide_viewport=True;ob['Source']='TwillHighField.npz';ob['Usage']='never export to runtime'
bpy.context.scene['MatchingShirt']='ue_field_sweater_charcoal';bpy.context.scene['RuntimeTested']=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'SmokeGreyCapri.blend'))
print('CAPRI_EDITABLE_SAVED',flush=True)
