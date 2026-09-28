"""Dedicated satin brass for floor strips; pavilion gold stays unchanged."""
import unreal as u
PATH='/Game/Props/GodSpaceLayout20260927/Materials/M_GodSpaceFloorSatinBrass'
def build():
    mat=u.load_asset(PATH)
    if mat:return mat
    tools=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
    mat=tools.create_asset(PATH.rsplit('/',1)[1],PATH.rsplit('/',1)[0],u.Material,u.MaterialFactoryNew())
    color=L.create_material_expression(mat,u.MaterialExpressionVectorParameter)
    color.set_editor_property('parameter_name','ChampagneBrassColor');color.set_editor_property('default_value',u.LinearColor(.52,.39,.23,1))
    L.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    for prop,name,value in [(u.MaterialProperty.MP_METALLIC,'Metallic',.9),(u.MaterialProperty.MP_SPECULAR,'Specular',.5)]:
        n=L.create_material_expression(mat,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value)
        L.connect_material_property(n,'',prop)
    position=L.create_material_expression(mat,u.MaterialExpressionWorldPosition)
    rough=L.create_material_expression(mat,u.MaterialExpressionScalarParameter);rough.set_editor_property('parameter_name','SatinRoughness');rough.set_editor_property('default_value',.44)
    grain=L.create_material_expression(mat,u.MaterialExpressionCustom)
    grain.set_editor_property('code','float phase=(abs(P.x+2400)>475?P.y:P.x)*30; float fade=1-smoothstep(.6,2,max(abs(ddx(phase)),abs(ddy(phase)))); return clamp(R+.025*sin(phase)*fade,.30,.65);')
    grain.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    pins=[]
    for name in ['P','R']:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    grain.set_editor_property('inputs',pins)
    L.connect_material_expressions(position,'',grain,'P');L.connect_material_expressions(rough,'',grain,'R')
    L.connect_material_property(grain,'',u.MaterialProperty.MP_ROUGHNESS)
    errors=list(L.recompile_material(mat))
    if errors:raise RuntimeError('Floor brass shader: '+str(errors))
    if not u.EditorLoadingAndSavingUtils.save_packages([mat.get_outermost()],False):raise RuntimeError('Floor brass save failed')
    return mat

if __name__=='__main__':build()
