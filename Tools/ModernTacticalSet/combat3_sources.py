"""Save the actual cloth HIGH/GAME sources and render the requested inventory art."""
import bpy,ast,sys,math,copy
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write,merge
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR3';OUT=R/'Icons';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'Models/01_KevlarVest.blend'))
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
for name in ['CombatRipstop','CombatCarrier','CombatStretch','CombatCuff','CombatLining','CombatThread']:
    mat=bpy.data.materials.new('M_'+name);mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.8;bs.inputs['Specular IOR Level'].default_value=.26;bs.inputs['Sheen Weight'].default_value=.38
    for channel in ['BaseColor','NormalGL','ORM']:
        image=bpy.data.images.load(str(R/'Textures'/(name+'_'+channel+'.png')),check_existing=True)
        if channel!='BaseColor':image.colorspace_settings.name='Non-Color'
        tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT';coords=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=8/28.8;links.new(coords.outputs['UV'],scale.inputs[0]);links.new(scale.outputs['Vector'],tex.inputs['Vector'])
        if channel=='BaseColor':links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif channel=='NormalGL':normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=1.;links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
        else:
            separate=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],separate.inputs['Color']);links.new(separate.outputs['Green'],bs.inputs['Roughness']);links.new(separate.outputs['Blue'],bs.inputs['Metallic'])
def material(path):
    name=path.split('/')[-1].split('.')[0];return bpy.data.materials.get(name) or bpy.data.materials.get('TS01_'+name.removeprefix('M_'))
tree=ast.parse((P/'Tools/ModernTacticalSet/shirt_sources.py').read_text());ns=dict(bpy=bpy,np=np,Vector=Vector,Matrix=Matrix,material=material)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','rig']],type_ignores=[]),'native_source_helpers','exec'),ns)
source_rows=[]
for rig in ['Jason','Kaitlin']:
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    d=read(R/'Authored'/f'shirt_detail_{rig}.json');ob=ns['mesh'](d,'GAME_CombatShirt_'+rig);arm=ns['rig'](d);ob.parent=arm;ob.modifiers.new('NativeBind','ARMATURE').object=arm
    # A distinct author high mesh carries actual cloth micro relief. Its field
    # is also the source for the physically scaled game PBR maps.
    high=ob.copy();high.data=ob.data.copy();high.name='HIGH_CombatShirt_'+rig;bpy.context.collection.objects.link(high)
    for mod in list(high.modifiers):high.modifiers.remove(mod)
    bpy.context.view_layer.objects.active=high;sub=high.modifiers.new('AuthorSubdivision','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
    me=high.data;me.update();field_cache={}
    for mi,mat in enumerate(me.materials):
        f=R/'Bakes'/(mat.name.removeprefix('M_')+'_height_field.npz')
        if f.exists():field_cache[mi]=np.load(f)['height_cm']
    offsets=np.zeros(len(me.vertices));counts=np.zeros(len(me.vertices));uv=me.uv_layers.active
    for face in me.polygons:
        field=field_cache.get(face.material_index)
        if field is None:continue
        size=field.shape[0]
        for li in face.loop_indices:
            vi=me.loops[li].vertex_index;u,v=uv.data[li].uv;u*=8/28.8;v=1-(1-v)*8/28.8;offsets[vi]+=float(field[int((1-v)%1*size)%size,int(u%1*size)%size])*.01;counts[vi]+=1
    # Snapshot normals before changing any coordinate; reading lazy normals
    # after each edit would recompute the complete high mesh per vertex.
    vertex_normals=np.array([v.normal[:] for v in me.vertices])
    for v in me.vertices:
        if counts[v.index]:v.co+=Vector(vertex_normals[v.index])*(offsets[v.index]/counts[v.index])
    high.hide_render=True;high.hide_set(True);high['purpose']='Author high only; micro height field source. Runtime export selects GAME only.'
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.file.pack_all();blend=R/'Models'/f'TS01_CombatShirt_{rig}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.export_scene.fbx(filepath=str(R/'Exports'/f'TS01_CombatShirt_{rig}.fbx'),use_selection=True,add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z')
    bpy.ops.export_scene.gltf(filepath=str(R/'Exports'/f'TS01_CombatShirt_{rig}.glb'),export_format='GLB',use_selection=True,export_all_influences=True)
    source_rows.append(dict(rig=rig,blend=str(blend),game_triangles=len(d['triangles']),high_polygons=len(high.data.polygons)));print('TS01_R3_HIGH_GAME_SOURCE',rig,flush=True)
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
d=read(R/'Authored/shirt_detail_Jason.json');vest=read(S/'Integration/Delivery/vest_Jason_Wear.json');vest['materials']=['/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/Materials/M_'+m.removeprefix('TS01_') for m in vest['material_slots']]
for i,m in enumerate(vest['material_slots']):
    if m in ['TS01_RangerRipstop','TS01_RangerNylon','TS01_OliveWebbing','TS01_CharcoalStretch','TS01_StitchThread']:vest['materials'][i]='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3/Materials/M_'+({'TS01_RangerRipstop':'CombatRipstop','TS01_CharcoalStretch':'CombatStretch','TS01_StitchThread':'CombatThread'}.get(m,'CombatCarrier'))
merge(d,vest);write(R/'Authored/outfit_display_Jason.json',d);ob=ns['mesh'](d,'GAME_CarrierAndCombatShirt');bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'Models/TS01_CarrierAndCombatShirt.blend'))
tree=ast.parse((P/'Tools/ModernTacticalSet/prepare_delivery.py').read_text());icon_ns=dict(bpy=bpy,np=np,Vector=Vector,Matrix=Matrix,OUT=OUT,P=P,read=read,write=write)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='icon'],type_ignores=[]),'combat_inventory_art','exec'),icon_ns)
art=icon_ns['icon'](ob,'ue_modern_kevlar_vest',3,3,'vest');display=read(art['display']);display['materials']=[next(path for path in d['materials'] if material(path).name==name) for name in display['material_slots']];write(art['display'],display)
center=(np.array(d['positions']).min(0)+np.array(d['positions']).max(0))*.5;d['positions']=(np.array(d['positions'])-center).tolist();write(R/'Authored/pickup.json',d)
write(R/'artwork.json',dict(completed=True,icon=art,pickup=str(R/'Authored/pickup.json'),sources=source_rows,pickup_origin_offset=center.tolist()))
