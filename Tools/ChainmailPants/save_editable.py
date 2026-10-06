"""Save editable native rig, garment parts and baking master in Blender.

No viewport preview or acceptance render. UE asset creation reads the same
geometry JSON; the editable scene preserves pieces and full Jason bind data.
"""
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailPants20261004'
if '--' in sys.argv:
    R=Path(sys.argv[sys.argv.index('--')+1])
bpy.ops.wm.read_factory_settings(use_empty=True)

def textured(name,paths,repeat):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    n=mat.node_tree.nodes;l=mat.node_tree.links;bs=n.get('Principled BSDF')
    uv=n.new('ShaderNodeTexCoord');mul=n.new('ShaderNodeVectorMath');mul.operation='MULTIPLY'
    l.new(uv.outputs['UV'],mul.inputs[0]);mul.inputs[1].default_value=(*repeat,1)
    for channel,path in paths.items():
        img=bpy.data.images.load(str(path),check_existing=True)
        if channel!='BaseColor':img.colorspace_settings.name='Non-Color'
        tex=n.new('ShaderNodeTexImage');tex.image=img;l.new(mul.outputs[0],tex.inputs['Vector'])
        if channel=='BaseColor':l.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif channel=='Normal':
            normal=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
        else:
            split=n.new('ShaderNodeSeparateColor');l.new(tex.outputs['Color'],split.inputs[0]);l.new(split.outputs['Green'],bs.inputs['Roughness']);l.new(split.outputs['Blue'],bs.inputs['Metallic'])
    return mat

mailroot=P/'SourceAssets/ChainmailInterlace20260929/Textures'
mail=textured('Interlaced grey steel - shared production bake',{c:mailroot/('T_ChainmailRelief_'+c+'.png') for c in ['BaseColor','Normal','ORM']},(.25/.048,.25/.0176))
steel=textured('Forged steel - 6.25 cm height-field bake',{c:R/'Textures'/('T_ChainmailPants_Steel_'+c+'.png') for c in ['BaseColor','Normal','ORM']},(4,4))
lining=bpy.data.materials.new('Charcoal padded binding');lining.use_nodes=True
bs=lining.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.028,.033,.038,1);bs.inputs['Roughness'].default_value=.82
materials=[mail,steel,lining]
data=json.loads((R/'Jason_ChainmailPants.json').read_text())
reflection=Matrix.Diagonal((1,-1,1));arm=bpy.data.armatures.new('Jason_NativeReference')
rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for b in data['bones']:
    bone=arm.edit_bones.new(b['name']);axes=Matrix(b['axes']).transposed()
    for i in range(3):axes.col[i]=axes.col[i].normalized()
    matrix=(reflection@axes@reflection).to_4x4();matrix.translation=reflection@Vector(b['position'])*.01
    bone.matrix=matrix;bone.length=.025
for b in data['bones']:
    if b['parent']>=0:arm.edit_bones[b['name']].parent=arm.edit_bones[data['bones'][b['parent']]['name']]
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)

for suffix in ['', '_BootsFit']:
    d=json.loads((R/('Jason_ChainmailPants'+suffix+'.json')).read_text())
    coll=bpy.data.collections.new('GAME_BootsFit' if suffix else 'GAME_Standard');bpy.context.scene.collection.children.link(coll)
    coll.hide_render=bool(suffix);coll.hide_viewport=bool(suffix)
    face_start=0
    for part in d['parts']:
        first=part['first_vertex'];last=first+part['vertices'];nf=part['triangles']
        coords=[(x*.01,-y*.01,z*.01) for x,y,z in d['positions'][first:last]]
        faces=[[i-first for i in f] for f in d['triangles'][face_start:face_start+nf]]
        mesh=bpy.data.meshes.new(part['name']+suffix);mesh.from_pydata(coords,[],faces);mesh.update()
        ob=bpy.data.objects.new(mesh.name,mesh);coll.objects.link(ob);ob.parent=rig
        ob.modifiers.new('Native Jason binding','ARMATURE').object=rig
        mesh.materials.append(materials[part['material']]);uv=mesh.uv_layers.new(name='Physical25cm')
        for fi,poly in enumerate(mesh.polygons):
            poly.use_smooth=True
            for ci,li in enumerate(poly.loop_indices):
                u,v=d['uv'][face_start+fi][ci];uv.data[li].uv=(u,1-v)
        ns=[(n[0],-n[1],n[2]) for face in d['normals'][face_start:face_start+nf] for n in face]
        mesh.normals_split_custom_set(ns)
        ids={i for weights in d['weights'][first:last] for i,w in weights}
        for bi in ids:ob.vertex_groups.new(name=d['bones'][bi]['name'])
        for vi,weights in enumerate(d['weights'][first:last]):
            for bi,w in weights:ob.vertex_groups[d['bones'][bi]['name']].add([vi],w,'REPLACE')
        ob['ProductionItem']='ue_chainmail_pants';ob['Units']='metres; JSON and UE use centimetres'
        face_start+=nf

field=np.load(R/'SteelHighField.npz');height=field['height_cm'][::4,::4];n=len(height);span=float(field['span_cm'])
coords=[(x/(n-1)*span*.01,y/(n-1)*span*.01,float(height[y,x])*.01) for y in range(n) for x in range(n)]
faces=[(y*n+x,y*n+x+1,(y+1)*n+x+1,(y+1)*n+x) for y in range(n-1) for x in range(n-1)]
mesh=bpy.data.meshes.new('HIGH_ForgedSteel_HeightField');mesh.from_pydata(coords,[],faces);mesh.update()
ob=bpy.data.objects.new(mesh.name,mesh);coll=bpy.data.collections.new('BAKE_ONLY');bpy.context.scene.collection.children.link(coll);coll.objects.link(ob);coll.hide_render=True;coll.hide_viewport=True
ob['Usage']='Baking master only; never export to runtime';ob['FullResolutionSource']='SteelHighField.npz'
bpy.context.scene['Concept']='Concept.png - user approved direction, inferred rear construction'
bpy.context.scene['Production']='New geometry and native Jason weights; no cloth simulation or acceptance render'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'ChainmailPants.blend'))
print('CHAINMAIL_PANTS_EDITABLE_SAVED',flush=True)
