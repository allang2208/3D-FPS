"""Native editable rigs, physical sculpt sources and a single empty-glove icon."""
import json,sys,importlib.util,gc
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Euler
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageGloves20261019';OUT=R/'Exports';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(P/'Tools/ModularOutfit'));sys.path.insert(0,str(Path(__file__).parent));sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
import glove_icon_display as display
from surface_fields import evaluate
import geometry as geo
spec=importlib.util.spec_from_file_location('mage_rig_io',str(P/'Tools/BlueMageRobe/save_editable.py'));io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)

def materials(group):
    m=bpy.data.materials.new('MageClothLeather');m.use_nodes=True;nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes['Principled BSDF'];bs.inputs['Specular IOR Level'].default_value=.3
    for channel in ('BaseColor','Normal','ORM','Relief'):
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'Textures'/group/('T_BlueMageGloves_'+group+'_'+channel+'.png')),check_existing=True)
        if channel!='BaseColor':tex.image.colorspace_settings.name='Non-Color'
        if channel=='BaseColor':links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif channel=='Normal':
            n=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],n.inputs['Color']);links.new(n.outputs[0],bs.inputs['Normal'])
        else:
            s=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],s.inputs[0])
            if channel=='ORM':links.new(s.outputs['Green'],bs.inputs['Roughness'])
            else:
                scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=.3;links.new(s.outputs['Green'],scale.inputs[0]);links.new(scale.outputs[0],bs.inputs['Sheen Weight'])
    return [m,io.material('MageSilver','silver'),io.material('MageSapphire','gem')]

def high_source(ob,group):
    high=ob.copy();high.data=ob.data.copy();high.parent=None;high.modifiers.clear();high.name='HIGH_'+group+'_PhysicalWeaveAndEmbroidery';bpy.context.collection.objects.link(high)
    fields=np.load(R/'Fields'/(group+'.npz'))['fields'];values=np.zeros((len(high.data.vertices),8),np.float32);values[:len(fields)]=fields
    for i in range(2):a=high.data.attributes.new('MageSurface'+str(i),'FLOAT_COLOR','POINT');a.data.foreach_set('color',values[:,i*4:i*4+4].ravel())
    bpy.ops.object.select_all(action='DESELECT');high.select_set(True);bpy.context.view_layer.objects.active=high
    sub=high.modifiers.new('Physical sculpt resolution','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=2;bpy.ops.object.modifier_apply(modifier=sub.name)
    mesh=high.data;count=len(mesh.vertices);f=[]
    for i in range(2):a=np.empty(count*4,np.float32);mesh.attributes['MageSurface'+str(i)].data.foreach_get('color',a);f.append(a.reshape(-1,4))
    height=evaluate(np.concatenate(f,axis=1))['height'];p=np.empty(count*3,np.float32);n=np.empty(count*3,np.float32);mesh.vertices.foreach_get('co',p);mesh.vertices.foreach_get('normal',n)
    p=p.reshape(-1,3)+n.reshape(-1,3)*(height*.01)[:,None];mesh.vertices.foreach_set('co',p.astype(np.float32).ravel());mesh.update()
    high['Usage']='Bake/sculpt source only; same centimetre-scale relief field as the UV textures';high.hide_render=True;high.hide_set(True)
    return dict(vertices=count,polygons=len(mesh.polygons))

def presentation():
    bpy.ops.wm.read_factory_settings(use_empty=True);d=json.loads((R/'Authored/M4.json').read_text());mats=materials('M4');anatomy=json.loads((P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json').read_text())['anatomy']
    posed,selected=display.posed_surface(d,d['bones'],anatomy,'r');faces=np.asarray(d['triangles'])[selected];used=np.unique(faces);remap={int(v):i for i,v in enumerate(used)};rotation=np.array(Euler(np.radians((-10,18,-6)),'XYZ').to_matrix());q=((posed[used]-[0,7.5,0])*.01)@rotation.T
    mesh=bpy.data.meshes.new('BlueMageGlove_Display');mesh.from_pydata(q.tolist(),[],[[remap[int(v)] for v in tri] for tri in faces]);mesh.update();ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
    for m in mats:mesh.materials.append(m)
    uv=mesh.uv_layers.new(name='PhysicalGarmentUV')
    for poly,fi in zip(mesh.polygons,selected):
        poly.use_smooth=True;poly.material_index=d['triangle_materials'][fi]
        for li,(a,b) in zip(poly.loop_indices,d['uv'][fi]):uv.data[li].uv=(a,1-b)
    output=dict(profile='Display',positions=(q*[100,-100,100]).tolist(),triangles=[[remap[int(v)] for v in tri] for tri in faces],weights=[{} for _ in q],uv=[d['uv'][int(fi)] for fi in selected],triangle_materials=[d['triangle_materials'][int(fi)] for fi in selected],material_slots=d['material_slots']);geo.finish(output)
    (R/'Authored/Display.json').write_text(json.dumps(output,separators=(',',':')),encoding='utf-8')
    sys.path.insert(0,str(P/'Tools/BlueMageSetIcons'))
    from render_icons import render_current
    render_current('ue_blue_mage_gloves',ob)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BlueMageGlove_Presentation.blend'))

exports=[];highs={}
for row in json.loads((R/'manifest.json').read_text())['rows']:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;d=json.loads(Path(row['authored']).read_text());mats=materials(row['group']);rig=io.rig_for(d);ob=io.mesh_for(d,rig,mats);ob.name=d['profile']+'_BlueMageGloves'
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
    path=OUT/(d['profile']+'_BlueMageGloves.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE');exports.append(str(path))
    if d['profile'] in ('M4','Body'):highs[d['profile']]=high_source(ob,d['profile'])
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(d['profile']+'_BlueMageGloves.blend')));print('MAGE_GLOVE_EDITABLE_SAVED',d['profile'],flush=True);gc.collect()
presentation();(R/'editable_receipt.json').write_text(json.dumps(dict(completed=True,exports=exports,high_sources=highs,icon=str(R/'ue_blue_mage_gloves.png'),runtime_tested=False),indent=2),encoding='utf-8');print('MAGE_GLOVE_EDITABLE_COMPLETE',flush=True)
