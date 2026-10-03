import unreal as u
L = u.MaterialEditingLibrary
m = u.Material
import unreal
factory = unreal.MaterialFactoryNew()
A = unreal.AssetToolsHelpers.get_asset_tools()
mat = A.create_asset('ProbeMat', '/Game/Transient', unreal.Material, factory)
for cls in (unreal.MaterialExpressionVertexColor, unreal.MaterialExpressionMultiply):
    e = L.create_material_expression(mat, cls)
    try:
        outs = [str(x) for x in L.get_material_expression_output_names(e)]
    except Exception as ex:
        outs = ['ERR:' + str(ex)]
    try:
        ins = [str(x) for x in L.get_material_expression_input_names(e)]
    except Exception as ex:
        ins = ['ERR:' + str(ex)]
    print('PINS', cls.__name__, 'OUT=', outs, 'IN=', ins)
