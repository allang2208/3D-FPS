"""Adapt the two painted Landscape layers to exterior mesh UVs without replacing their shading."""
import json
import os
from pathlib import Path
import unreal as u

ed = u.MaterialEditingLibrary
lib = u.EditorAssetLibrary
folder = '/Game/ForestPathStudy/VillageRegion/Reference/'
donor = u.load_asset('/Game/ForestPathStudy/Materials/MI_ForestPathForest')
lib.make_directory(folder)
def build():
    if lib.does_asset_exist(folder+'MI_ForestReference'):
        saved = u.load_asset(folder+'MI_ForestReference')
        if saved.get_base_material().get_path_name().split('.')[0] != folder+'M_ForestReferenceMesh':
            raise RuntimeError('Unexpected existing mesh material parent')
        return
    master = u.load_asset(folder+'M_ForestReferenceMesh') if lib.does_asset_exist(folder+'M_ForestReferenceMesh') else lib.duplicate_asset(donor.get_base_material().get_path_name(), folder+'M_ForestReferenceMesh')
    if not master:
        raise RuntimeError('Reference master destination must be empty')

    def node(kind, x, y):
        return ed.create_material_expression(master, kind, x, y)

    def inputs(expr):
        return dict(zip(map(str, ed.get_material_expression_input_names(expr)), ed.get_inputs_for_material_expression(master, expr)))

    def wire(src, output, dst, pin):
        if not ed.connect_material_expressions(src, output, dst, pin):
            raise RuntimeError(f'{src.get_name()}.{output} -> {dst.get_name()}.{pin}')

    original = list(ed.get_material_expressions(master))
    call = next(n for n in original if str(n.get_editor_property('desc')) == 'R4 wild grass surface')
    uv = node(u.MaterialExpressionTextureCoordinate, -3100, 2000)
    uv.set_editor_property('coordinate_index', 4)
    def channel(green):
        n = node(u.MaterialExpressionComponentMask,-2850,2000+green*220)
        for key in ('r','g','b','a'):
            n.set_editor_property(key,key == ('g' if green else 'r'))
        wire(uv,'',n,'')
        return n
    road, verge = channel(False), channel(True)
    combined = node(u.MaterialExpressionMax,-2400,2200)
    wire(call,'Verge',combined,'A')
    wire(verge,'',combined,'B')
    for n in original:
        pins = inputs(n)
        if isinstance(n,u.MaterialExpressionBlendMaterialAttributes) and pins.get('Alpha') == call:
            wire(combined,'',n,'Alpha')
        if isinstance(n,u.MaterialExpressionMultiply) and pins.get('A') == call and pins.get('B') == call:
            wire(combined,'',n,'A')

    for layer in [n for n in original if isinstance(n,u.MaterialExpressionLandscapeLayerBlend)]:
        pins = inputs(layer)
        scalar = str(layer.get_editor_property('desc')) == 'Forest floor painted relief'
        height = pins.get('Height C')
        u.log('REFERENCE_INPUTS '+str([(k,v.get_name() if v else None,ed.get_input_node_output_name_for_material_expression(layer,v) if v else None) for k,v in pins.items()]))
        alpha = node(u.MaterialExpressionCustom,-1200,2400 if scalar else 1800)
        custom_inputs=[]
        for name in ('C','H'):
            inp=u.CustomInput()
            inp.set_editor_property('input_name',name)
            custom_inputs.append(inp)
        alpha.set_editor_property('inputs',custom_inputs)
        alpha.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
        alpha.set_editor_property('code','float w=saturate(C); float h=clamp(2*w-1+H,0.0001,1.0); return w>0 ? h/(1-w+h) : 0;')
        wire(road,'',alpha,'C')
        def source_pin(n):
            return str(ed.get_input_node_output_name_for_material_expression(layer,n) or '')
        # The material function used twice by Layer C exposes material attributes and its height separately.
        if height:
            out=source_pin(height)
            if height == pins.get('Layer C'):
                out='Height'
            wire(height,out,alpha,'H')
        else:
            zero=node(u.MaterialExpressionConstant,-1500,2400)
            entry=next(e for e in layer.get_editor_property('layers') if str(e.get_editor_property('layer_name'))=='C')
            zero.set_editor_property('r',float(entry.get_editor_property('const_height_input')))
            wire(zero,'',alpha,'H')
        mix=node(u.MaterialExpressionLinearInterpolate if scalar else u.MaterialExpressionBlendMaterialAttributes,-800,2400 if scalar else 1800)
        for k,d in [('Layer AutoMaterial','A'),('Layer C','B')]:
            wire(pins[k],source_pin(pins[k]),mix,d)
        wire(alpha,'',mix,'Alpha')
        for n in original:
            for pin,feed in inputs(n).items():
                if feed==layer:
                    wire(mix,'',n,pin)
        ed.delete_material_expression(master,layer)
        original.remove(layer)
    for n in original:
        if isinstance(n,u.MaterialExpressionLandscapeGrassOutput):
            ed.delete_material_expression(master,n)
    errors=ed.recompile_material(master)
    if errors: raise RuntimeError(str(errors))
    if not lib.save_loaded_asset(master,False): raise RuntimeError('Cannot save mesh parent')
    inst=lib.duplicate_asset(donor.get_path_name(),folder+'MI_ForestReference')
    if not inst: raise RuntimeError('Cannot duplicate forest instance')
    ed.set_material_instance_parent(inst,master)
    ed.update_material_instance(inst)
    if not lib.save_loaded_asset(inst,False): raise RuntimeError('Cannot save forest instance')
    (Path(os.environ['FPS_FOREST_REFERENCE_BATCH'])/'material.json').write_text(json.dumps({'source':donor.get_path_name(),'parent':master.get_path_name(),'instance':inst.get_path_name()}))

build()
