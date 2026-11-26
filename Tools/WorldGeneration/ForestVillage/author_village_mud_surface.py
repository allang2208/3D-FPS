"""Reuse the original village street shading inside the forest village's settlement mesh."""
import unreal as u

ed = u.MaterialEditingLibrary
lib = u.EditorAssetLibrary
folder = '/Game/ForestPathStudy/VillageRegion/Reference/'
switch_name = 'Use original village mud roads'


def wire(source, channel, dest, pin):
    if not ed.connect_material_expressions(source, channel, dest, pin):
        raise RuntimeError(f'{source.get_name()}.{channel} -> {dest.get_name()}.{pin}')


def save(obj):
    if not lib.save_loaded_asset(obj, False):
        raise RuntimeError(obj.get_path_name())


def author():
    forest = u.load_asset(folder+'MI_ForestReference')
    master = forest.get_base_material()
    switch = next((n for n in ed.get_material_expressions(master)
                   if isinstance(n,u.MaterialExpressionStaticSwitchParameter)
                   and str(n.get_editor_property('parameter_name')) == switch_name), None)
    if not switch:
        old = u.load_asset('/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround')
        road, = [n for n in ed.get_material_expressions(old) if isinstance(n,u.MaterialExpressionCustom)
                 and n.get_editor_property('desc') == 'VillageTerrainRoad']
        clone = ed.duplicate_material_expression(master, None, road)
        leaves = {}
        for pin, src in zip(ed.get_material_expression_input_names(road),
                            ed.get_inputs_for_material_expression(old, road)):
            if src not in leaves:
                leaves[src] = ed.duplicate_material_expression(master, None, src)
            wire(leaves[src], 'A' if str(pin)=='SinYaw' else '', clone, str(pin))

        prop = u.MaterialProperty.MP_MATERIAL_ATTRIBUTES
        original = ed.get_material_property_input_node(master, prop)
        if not isinstance(original,u.MaterialExpressionMakeMaterialAttributes):
            raise RuntimeError('Expected R18 forest surface output')
        town = ed.duplicate_material_expression(master, None, original)
        split = ed.create_material_expression(master,u.MaterialExpressionBreakMaterialAttributes)
        wire(original,'',split,str(ed.get_material_expression_input_names(split)[0]))
        rim = ed.create_material_expression(master,u.MaterialExpressionTextureCoordinate)
        rim.set_editor_property('coordinate_index',5)
        weight = ed.create_material_expression(master,u.MaterialExpressionComponentMask)
        weight.set_editor_property('r',True)
        for c in ('g','b','a'): weight.set_editor_property(c,False)
        wire(rim,'',weight,'')
        coverage = ed.create_material_expression(master,u.MaterialExpressionMultiply)
        wire(weight,'',coverage,'A')
        wire(clone,'Coverage',coverage,'B')
        for name, channel in [('BaseColor',''),('Normal','RoadNormal'),('Roughness','RoadRoughness')]:
            mix = ed.create_material_expression(master,u.MaterialExpressionLinearInterpolate)
            wire(split,name,mix,'A')
            wire(clone,channel,mix,'B')
            wire(coverage,'',mix,'Alpha')
            wire(mix,'',town,name)
        switch = ed.create_material_expression(master,u.MaterialExpressionStaticSwitchParameter)
        switch.set_editor_property('parameter_name',switch_name)
        switch.set_editor_property('default_value',False)
        wire(town,'',switch,'True')
        wire(original,'',switch,'False')
        if not ed.connect_material_property(switch,'',prop):
            raise RuntimeError('Village surface output')
        errors = ed.recompile_material(master)
        if errors: raise RuntimeError(str(errors))
        save(master)
    path = folder+'MI_ForestVillageMudRoad'
    if lib.does_asset_exist(path):
        instance = u.load_asset(path)
    else:
        instance = u.AssetToolsHelpers.get_asset_tools().create_asset(
            'MI_ForestVillageMudRoad',folder.rstrip('/'),u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    ed.set_material_instance_parent(instance,forest)
    ed.set_material_instance_static_switch_parameter_value(instance,switch_name,True)
    if not ed.get_material_instance_static_switch_parameter_value(instance,switch_name):
        raise RuntimeError(switch_name)
    save(instance)
    return instance
