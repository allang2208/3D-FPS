"""Author the quarter-second, depth-tested hit glint and interrupted gold rings."""
import unreal as u

folder = "/Game/Weapons/SniperZhiming"
name = "M_Zhiming_Critical"
lib = u.EditorAssetLibrary
edit = u.MaterialEditingLibrary
asset = (u.load_asset(folder+"/"+name) if lib.does_asset_exist(folder+"/"+name)
         else u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.Material,u.MaterialFactoryNew()))
edit.delete_all_material_expressions(asset)
asset.set_editor_property("blend_mode", u.BlendMode.BLEND_ADDITIVE)
asset.set_editor_property("shading_model", u.MaterialShadingModel.MSM_UNLIT)
asset.set_editor_property("two_sided", True)
uv = edit.create_material_expression(asset,u.MaterialExpressionTextureCoordinate)
clock = edit.create_material_expression(asset,u.MaterialExpressionTime)


def scalar(name, value):
    node=edit.create_material_expression(asset,u.MaterialExpressionScalarParameter)
    node.set_editor_property("parameter_name",name)
    node.set_editor_property("default_value",value)
    return node


inputs={"UV":uv,"Clock":clock,"T0":scalar("Start",0.),"Rate":scalar("InvDuration",4.),
        "Spark":scalar("Spark",0.)}
effect=edit.create_material_expression(asset,u.MaterialExpressionCustom)
pins=[]
for name in inputs:
    pin=u.CustomInput()
    pin.set_editor_property("input_name",name)
    pins.append(pin)
effect.set_editor_property("inputs",pins)
effect.set_editor_property("output_type",u.CustomMaterialOutputType.CMOT_FLOAT3)
effect.set_editor_property("description","Zhiming critical echo")
effect.set_editor_property("code", """
float age=saturate((Clock-T0)*Rate);
float2 p=UV*2-1;
if(Spark>.5){
    float2 q=abs(p);
    float diamond=1-smoothstep(.12,.23,q.x+q.y*.7);
    float rays=exp(-55*min(q.x,q.y))*exp(-4.8*max(q.x,q.y));
    return (diamond*float3(1.1,.38,2.2)+rays*float3(2.4,1.45,.57))*(1-smoothstep(.04,.42,age));
}
float light=0;
for(int i=0;i<2;i++){
    float2 q=(p-float2(0,(i-.5)*.54))/float2(.83-i*.09,.26);
    float d=length(q);
    float width=clamp(fwidth(d),.013,.095);
    float arc=1-smoothstep(.012,.012+width,abs(d-1));
    float gap=smoothstep(.07,.34,abs(q.y-.35)+max(0.,-q.x));
    light+=arc*gap;
}
return light*float3(2.1,1.25,.39)*smoothstep(0,.16,age)*(1-smoothstep(.68,1,age));
""")
for pin,node in inputs.items():
    if not edit.connect_material_expressions(node,"",effect,pin):
        raise RuntimeError("Could not bind " + pin)
edit.connect_material_property(effect,"",u.MaterialProperty.MP_EMISSIVE_COLOR)
opacity=edit.create_material_expression(asset,u.MaterialExpressionConstant)
opacity.set_editor_property("r",1.)
edit.connect_material_property(opacity,"",u.MaterialProperty.MP_OPACITY)
edit.recompile_material(asset)
if not lib.save_loaded_asset(asset,False):
    raise RuntimeError("Could not save critical presentation material")
u.log("ZHIMING_CRITICAL_FX_SAVED " + asset.get_path_name())
