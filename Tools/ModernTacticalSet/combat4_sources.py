"""Native GAME authoring sources and standard transparent inventory artwork from actual R4 meshes."""
import bpy,bmesh,ast,sys,math,copy,gc
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write,merge,subset
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR4';B=S/'CombatShirtR3';OUT=R/'Icons'

def material(path):
    name=path.split('/')[-1].split('.')[0];mat=bpy.data.materials.get(name) or bpy.data.materials.get('TS01_'+name.removeprefix('M_'))
    if mat is None:raise RuntimeError('Missing source PBR material '+path)
    return mat

def setup(master):
    bpy.ops.wm.open_mainfile(filepath=str(S/'Models'/master))
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
    for name in ['CombatRipstop','CombatCarrier','CombatStretch','CombatCuff','CombatLining','CombatThread']:
        mat=bpy.data.materials.new('M_'+name);mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.8;bs.inputs['Specular IOR Level'].default_value=.26;bs.inputs['Sheen Weight'].default_value=.38
        for channel in ['BaseColor','NormalGL','ORM']:
            image=bpy.data.images.load(str(B/'Textures'/(name+'_'+channel+'.png')),check_existing=True)
            if channel!='BaseColor':image.colorspace_settings.name='Non-Color'
            tex=nodes.new('ShaderNodeTexImage');tex.image=image;coords=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=8/28.8;links.new(coords.outputs['UV'],scale.inputs[0]);links.new(scale.outputs['Vector'],tex.inputs['Vector'])
            if channel=='BaseColor':links.new(tex.outputs['Color'],bs.inputs['Base Color'])
            elif channel=='NormalGL':n=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bs.inputs['Normal'])
            else:n=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Green'],bs.inputs['Roughness']);links.new(n.outputs['Blue'],bs.inputs['Metallic'])

tree=ast.parse((P/'Tools/ModernTacticalSet/shirt_sources.py').read_text());ns=dict(bpy=bpy,np=np,Vector=Vector,Matrix=Matrix,material=material)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','rig']],type_ignores=[]),'r4_native_sources','exec'),ns)
tree=ast.parse((P/'Tools/ModernTacticalSet/prepare_delivery.py').read_text());iconns=dict(bpy=bpy,bmesh=bmesh,np=np,Vector=Vector,Matrix=Matrix,OUT=OUT,P=P,read=read,write=write)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='icon'],type_ignores=[]),'r4_inventory','exec'),iconns)

def empty(d):
    d=subset(d,[not d['material_slots'][i].startswith('NATIVE:') for i in d['triangle_materials']]);used=sorted(set(d['triangle_materials']));mapping={old:i for i,old in enumerate(used)};d['material_slots']=[d['material_slots'][i] for i in used];d['materials']=[d['materials'][i] for i in used];d['triangle_materials']=[mapping[i] for i in d['triangle_materials']];return d

def author(d,label,high=False):
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    ob=ns['mesh'](d,'GAME_'+label);arm=ns['rig'](d);ob.parent=arm;ob.modifiers.new('NativeBind','ARMATURE').object=arm
    if high:
        hi=ob.copy();hi.data=ob.data.copy();hi.name='HIGH_'+label;bpy.context.collection.objects.link(hi)
        for mod in list(hi.modifiers):hi.modifiers.remove(mod)
        bpy.context.view_layer.objects.active=hi;sub=hi.modifiers.new('AuthorMicroSubdivision','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name);me=hi.data;me.update();fields={}
        for i,mat in enumerate(me.materials):
            file=B/'Bakes'/(mat.name.removeprefix('M_')+'_height_field.npz')
            if file.exists():fields[i]=np.load(file)['height_cm']
        offsets=np.zeros(len(me.vertices));counts=np.zeros(len(me.vertices));uv=me.uv_layers.active;nn=np.array([v.normal[:] for v in me.vertices])
        for face in me.polygons:
            field=fields.get(face.material_index)
            if field is None:continue
            size=field.shape[0]
            for li in face.loop_indices:
                vi=me.loops[li].vertex_index;u,v=uv.data[li].uv;u*=8/28.8;v=1-(1-v)*8/28.8;offsets[vi]+=float(field[int((1-v)%1*size)%size,int(u%1*size)%size])*.01;counts[vi]+=1
        for v in me.vertices:
            if counts[v.index]:v.co+=Vector(nn[v.index])*(offsets[v.index]/counts[v.index])
        hi.hide_render=True;hi.hide_set(True)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.file.pack_all();blend=R/'Models'/(label+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.export_scene.fbx(filepath=str(R/'Exports'/(label+'.fbx')),use_selection=True,add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z')
    if high:bpy.ops.export_scene.gltf(filepath=str(R/'Exports'/(label+'.glb')),export_format='GLB',use_selection=True,export_all_influences=True)
    print('R4_NATIVE_SOURCE',label,flush=True);return str(blend)

def main():
    vest_only='--vest-only' in sys.argv
    previous=read(R/'artwork.json') if vest_only else {}
    art=previous.get('items',{});sources=previous.get('sources',[])
    for kind,master,item,w,h in [('vest','01_KevlarVest.blend','ue_modern_kevlar_vest',3,3),('pants','04_TacticalTrousers.blend','ue_modern_tactical_pants',2,3),('boots','05_TacticalBoots.blend','ue_modern_tactical_boots',2,3),('gloves','03_TacticalGloves.blend','ue_modern_tactical_gloves',2,2)]:
        if vest_only and kind!='vest':continue
        setup(master)
        for rig in ['Jason','Kaitlin']:
            if kind=='vest':
                d=read(R/'Authored'/f'shirt_detail_{rig}.json');sources.append(author(d,'TS01_CombatShirt_'+rig,True));merge(d,read(R/'Authored'/f'vest_{rig}.json'))
            else:d=empty(read(R/'Authored'/((f'wear_pants_{rig}.json') if kind=='pants' else f'{kind}_{rig}.json')))
            sources.append(author(d,'TS01_'+kind+'_'+rig))
            if rig=='Jason':male=copy.deepcopy(d)
        for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
        ob=ns['mesh'](male,'GAME_'+kind+'_Inventory');iconns['bones']=male['bones'];icon=iconns['icon'](ob,item,w,h,kind);display=read(icon['display']);display['materials']=[next(path for path in male['materials'] if material(path).name.split('.')[0]==name) for name in display['material_slots']];write(icon['display'],display)
        center=(np.array(male['positions']).min(0)+np.array(male['positions']).max(0))*.5;male['positions']=(np.array(male['positions'])-center).tolist();pickup=R/'Authored'/(kind+'_pickup.json');write(pickup,male);art[item]=dict(kind=kind,icon=icon,pickup=str(pickup));write(R/'artwork.json',dict(completed=False,items=art,sources=sources));gc.collect();print('R4_STANDARD_ICON',kind,flush=True)
    write(R/'artwork.json',dict(completed=True,items=art,sources=sources))
    if vest_only:write(R/'collar-artwork.json',dict(completed=True,native_neck_fit=read(R/'collar-fitted.json'),source='Actual final R4 shirt and refitted carrier'))
if __name__=='__main__':main()
