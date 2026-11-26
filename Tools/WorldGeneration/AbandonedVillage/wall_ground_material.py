"""Wall-only RVT receivers: keep stone detail across a short, broken soil edge."""
import hashlib
import unreal as u

DEST='/Game/WorldGeneration/TemperateHills/EcologyUpgrade/Receivers/VillageWalls'
SOURCE_TAG='HillsLocalRVT20261114'
TAG='VillageWallRoot20261114'
L=u.MaterialEditingLibrary
E=u.EditorAssetLibrary

BLEND_CODE='''float d=P.z-H;
float rag=sin(P.x*.173+sin(P.y*.119)*1.7)*1.6;
float edge=6.0+rag;
float soil=.32+.10*sin(P.x*.113+P.y*.157);
return soil*(1.0-smoothstep(.5,edge,d))*smoothstep(-12.0,-2.0,d);'''


def wall_receiver(material,cache):
    key=material.get_path_name()
    if key.startswith(DEST+'/'):return material
    cache_key='wall-root:'+key
    if cache_key in cache:return cache[cache_key]
    name=('MI_' if isinstance(material,u.MaterialInstanceConstant) else 'M_')+hashlib.sha1(key.encode()).hexdigest()[:12]
    path=DEST+'/'+name
    obj=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(key,path)
    if not obj:raise RuntimeError('Cannot create wall receiver '+path)
    cache[cache_key]=obj
    if isinstance(obj,u.MaterialInstanceConstant):
        L.set_material_instance_parent(obj,wall_receiver(material.get_editor_property('parent'),cache))
        L.update_material_instance(obj)
    else:
        nodes=list(L.get_material_expressions(obj))
        if not any(n.get_editor_property('desc')==TAG for n in nodes):
            blend=[n for n in nodes if isinstance(n,u.MaterialExpressionCustom)
                   and n.get_editor_property('desc')==SOURCE_TAG
                   and 'float d=P.z-H;' in n.get_editor_property('code')]
            if len(blend)!=1:raise RuntimeError('Expected one existing ground receiver: '+key)
            blend[0].set_editor_property('code',BLEND_CODE)
            normal_mix=[]
            for n in nodes:
                if not isinstance(n,u.MaterialExpressionLinearInterpolate) or n.get_editor_property('desc')!=SOURCE_TAG:continue
                inputs=dict(zip(map(str,L.get_material_expression_input_names(n)),L.get_inputs_for_material_expression(obj,n)))
                if isinstance(inputs.get('B'),u.MaterialExpressionTransform) and isinstance(inputs.get('Alpha'),u.MaterialExpressionVirtualTextureFeatureSwitch):
                    normal_mix.append((n,inputs['Alpha']))
            if len(normal_mix)!=1:raise RuntimeError('Expected one RVT normal mix: '+key)
            mix,alpha=normal_mix[0]
            reduced=L.create_material_expression(obj,u.MaterialExpressionMultiply)
            reduced.set_editor_property('desc',TAG)
            reduced.set_editor_property('const_b',.25)
            if not L.connect_material_expressions(alpha,'',reduced,'A') or not L.connect_material_expressions(reduced,'',mix,'Alpha'):
                raise RuntimeError('Wall normal blend wiring failed')
            L.recompile_material(obj)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Wall receiver save failed: '+path)
    return obj


def dress_wall(comp,cache):
    for slot in range(comp.get_num_materials()):
        material=comp.get_material(slot)
        if material:comp.set_material(slot,wall_receiver(material,cache))
