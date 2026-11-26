"""Current trouser GAME sources, empty drop, and the required 2x3 inventory icon."""
import bpy,ast,sys,copy,math
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write,subset
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR3';OUT=R/'Icons';OUT.mkdir(exist_ok=True);DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3'
bpy.ops.wm.open_mainfile(filepath=str(S/'Models/04_TacticalTrousers.blend'))
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
for name in ['CombatRipstop','CombatCarrier','CombatStretch','CombatThread']:
    mat=bpy.data.materials.new('M_'+name);mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF');bs.inputs['Specular IOR Level'].default_value=.26;bs.inputs['Sheen Weight'].default_value=.38
    for channel in ['BaseColor','NormalGL','ORM']:
        image=bpy.data.images.load(str(R/'Textures'/(name+'_'+channel+'.png')),check_existing=True)
        if channel!='BaseColor':image.colorspace_settings.name='Non-Color'
        tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT';coords=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=8/28.8;links.new(coords.outputs['UV'],scale.inputs[0]);links.new(scale.outputs['Vector'],tex.inputs['Vector'])
        if channel=='BaseColor':links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif channel=='NormalGL':n=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bs.inputs['Normal'])
        else:n=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Green'],bs.inputs['Roughness']);links.new(n.outputs['Blue'],bs.inputs['Metallic'])
def material(path):
    name=path.split('/')[-1].split('.')[0];return bpy.data.materials.get(name) or bpy.data.materials.get('TS01_'+name.removeprefix('M_'))
tree=ast.parse((P/'Tools/ModernTacticalSet/shirt_sources.py').read_text());ns=dict(bpy=bpy,np=np,Vector=Vector,Matrix=Matrix,material=material)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','rig']],type_ignores=[]),'trouser_native_sources','exec'),ns)
for rig in ['Jason','Kaitlin']:
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    d=read(R/'Authored'/f'pants_{rig}.json');d=subset(d,[not d['material_slots'][i].startswith('NATIVE:') for i in d['triangle_materials']]);used=sorted(set(d['triangle_materials']));mapping={old:i for i,old in enumerate(used)};d['material_slots']=[d['material_slots'][i] for i in used];d['materials']=[d['materials'][i] for i in used];d['triangle_materials']=[mapping[i] for i in d['triangle_materials']]
    for i,slot in enumerate(d['material_slots']):
        textile={'TS01_RangerRipstop':'CombatRipstop','TS01_RangerNylon':'CombatCarrier','TS01_OliveWebbing':'CombatCarrier','TS01_CharcoalStretch':'CombatStretch','TS01_StitchThread':'CombatThread'}
        if slot in textile:d['materials'][i]=DEST+'/Materials/M_'+textile[slot]
    ob=ns['mesh'](d,'GAME_CombatTrousers_'+rig);arm=ns['rig'](d);ob.parent=arm;ob.modifiers.new('NativeBind','ARMATURE').object=arm;bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'Models'/f'TS01_CombatTrousers_{rig}.blend'))
    bpy.ops.export_scene.fbx(filepath=str(R/'Exports'/f'TS01_CombatTrousers_{rig}.fbx'),use_selection=True,add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z')
    if rig=='Jason':male=copy.deepcopy(d)
    print('TS01_R3_TROUSER_SOURCE',rig,flush=True)
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
ob=ns['mesh'](male,'GAME_CombatTrousers_Display');tree=ast.parse((P/'Tools/ModernTacticalSet/prepare_delivery.py').read_text());icon_ns=dict(bpy=bpy,np=np,Vector=Vector,Matrix=Matrix,OUT=OUT,P=P,read=read,write=write)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='icon'],type_ignores=[]),'trouser_inventory_art','exec'),icon_ns);art=icon_ns['icon'](ob,'ue_modern_tactical_pants',2,3,'pants')
display=read(art['display']);display['materials']=[next(path for path in male['materials'] if material(path).name==name) for name in display['material_slots']];write(art['display'],display)
center=(np.array(male['positions']).min(0)+np.array(male['positions']).max(0))*.5;male['positions']=(np.array(male['positions'])-center).tolist();write(R/'Authored/pants_pickup.json',male);write(R/'lower-artwork.json',dict(completed=True,icon=art,pickup=str(R/'Authored/pants_pickup.json')))
