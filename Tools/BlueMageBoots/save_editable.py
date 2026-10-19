"""Native-rig exports, retained surface masters, and the production inventory icon."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from common import *
import bpy,numpy as np
from mathutils import Matrix,Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0

def constant(name,color,rough,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m

def fabric(name,family):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF'];uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=6.25;l.new(uv.outputs['UV'],scale.inputs[0])
    for channel in ('BaseColor','Normal','ORM'):
        img=bpy.data.images.load(str(R/'Textures'/f'T_MageBoots_{family}_{channel}.png'),check_existing=True)
        if channel!='BaseColor':img.colorspace_settings.name='Non-Color'
        t=n.new('ShaderNodeTexImage');t.image=img;l.new(scale.outputs[0],t.inputs['Vector'])
        if channel=='BaseColor':l.new(t.outputs['Color'],p.inputs['Base Color'])
        elif channel=='Normal':
            nm=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],p.inputs['Normal'])
        else:
            sp=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sp.inputs[0]);l.new(sp.outputs['Green'],p.inputs['Roughness']);l.new(sp.outputs['Blue'],p.inputs['Metallic'])
    return m

mats=[fabric('BlackLeather','Leather'),fabric('CobaltWoven','Cobalt'),constant('SilverEmbroidery',(.46,.49,.55),.38,.85),constant('DarkThread',(.018,.02,.024),.84),fabric('BlackLining','Lining'),fabric('RubberSole','Rubber'),constant('Sapphire',(.009,.05,.28),.14,.25)]
native=read(R/'native_reference.json');bones=native['bones'];reflect=Matrix.Diagonal((1,-1,1));arm=bpy.data.armatures.new('Jason_NativeRig');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for b in bones:
    eb=arm.edit_bones.new(b['name']);axes=Matrix(b['axes']).transposed()
    for i in range(3):axes.col[i]=axes.col[i].normalized()
    matrix=(reflect@axes@reflect).to_4x4();matrix.translation=reflect@Vector(b['position'])*.01;eb.matrix=matrix;eb.length=.025
byid={b['index']:b for b in bones}
for b in bones:
    if b['parent']>=0:arm.edit_bones[b['name']].parent=arm.edit_bones[byid[b['parent']]['name']]
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
iconio=module('mage_boots_icon_io','Tools/BlueMageSetIcons/render_icons.py');models={};exported=[]
for name in VARIANTS+['Jason_BlueMageBoots_Garment','Display']:
    d=read(R/'Authored'/(name+'.json'));ob=iconio.plain_mesh(d,mats,name);ids={i for ws in d['weights'] for i,w in ws};groups={i:ob.vertex_groups.new(name=byid[i]['name']) for i in ids}
    for vi,ws in enumerate(d['weights']):
        for bi,w in ws:groups[bi].add([vi],w,'REPLACE')
    ob.parent=rig;ob.modifiers.new('Native skinning','ARMATURE').object=rig;models[name]=ob
    if name in VARIANTS:
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob;path=R/'Exports'/(name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE');exported.append(str(path))
    ob.hide_render=True;ob.hide_set(True)
high=bpy.data.collections.new('BAKE_ONLY_SurfaceFields');bpy.context.scene.collection.children.link(high);high.hide_render=True;high.hide_viewport=True
for name in ('Leather','Cobalt','Lining','Rubber'):
    d=np.load(R/f'HIGH_{name}.npz');h=d['height_cm'][::4,::4];n=len(h);span=float(d['span_cm']);mesh=bpy.data.meshes.new('HIGH_'+name)
    mesh.from_pydata([(x/(n-1)*span*.01,y/(n-1)*span*.01,float(h[y,x])*.01) for y in range(n) for x in range(n)],[],[(y*n+x,y*n+x+1,(y+1)*n+x+1,(y+1)*n+x) for y in range(n-1) for x in range(n-1)])
    ob=bpy.data.objects.new(mesh.name,mesh);high.objects.link(ob);ob['Usage']='Analytic physical surface master; excluded from all runtime exports'
models[VARIANTS[0]].hide_set(False);models[VARIANTS[0]].hide_render=False
bpy.ops.file.pack_all();blend=R/'Exports/BlueMageBoots_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
iconio.FAMILIES[KEY]=FAMILY
result=iconio.render_current(KEY,models['Display'],R/'Authored/Display.json',item=ITEM,camera_offset=(2.5,-3,1.0))
write(R/'editable_receipt.json',dict(completed=True,blend=str(blend),fbx=exported,icon=result['icon'],runtime_tested=False))
print('MAGE_BOOTS_EDITABLE_EXPORTS_AND_ICON_SAVED',flush=True)
