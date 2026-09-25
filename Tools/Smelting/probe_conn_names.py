import unreal
AT=unreal.AssetToolsHelpers.get_asset_tools(); MEL=unreal.MaterialEditingLibrary; EAL=unreal.EditorAssetLibrary
STONE='/Game/Items/EnhancementMaterials/enhancement_stone'
if EAL.does_asset_exist('/Game/TempProbe6'): EAL.delete_asset('/Game/TempProbe6')
EAL.make_directory('/Game/TempProbe6')

def fresh(n):
    m=AT.create_asset(n,'/Game/TempProbe6',unreal.Material,unreal.MaterialFactoryNew())
    return m

def ts(m,styp):
    e=MEL.create_material_expression(m,unreal.MaterialExpressionTextureSample,-600,0)
    e.set_editor_property('texture',EAL.load_asset(STONE+'/T_enhancement_stone_0_Base_Color'))
    e.set_editor_property('sampler_type',styp); return e

print('--- 1) TextureSample(Color) -> Multiply.A 各种输出名 ---')
m=fresh('P_A')
sb=ts(m,unreal.MaterialSamplerType.SAMPLERTYPE_COLOR); mul=MEL.create_material_expression(m,unreal.MaterialExpressionMultiply,-200,0)
for nm in ('','color','Color','RGBA','rgb'):
    print('  OUT',repr(nm),'->',MEL.connect_material_expressions(sb,nm,mul,'A'))
print('--- 2) Multiply.A 输入名 ---')
m2=fresh('P_B'); sb2=ts(m2,unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
for nm in ('A','a','','InputA'):
    mul2=MEL.create_material_expression(m2,unreal.MaterialExpressionMultiply,-200,100)
    print('  IN',repr(nm),'->',MEL.connect_material_expressions(sb2,'color',mul2,nm))
print('--- 3) VectorParameter -> Multiply.B ---')
m3=fresh('P_C'); v=MEL.create_material_expression(m3,unreal.MaterialExpressionVectorParameter,-600,300)
v.set_editor_property('parameter_name',unreal.Name('Tint'))
for nm in ('B','b',''):
    mul3=MEL.create_material_expression(m3,unreal.MaterialExpressionMultiply,-200,200)
    print('  IN',repr(nm),'->',MEL.connect_material_expressions(v,nm,mul3,'B'))
print('--- 4) connect_material_property 的输出名（Multiply 与 TextureSample） ---')
m4=fresh('P_D'); sb4=ts(m4,unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
mul4=MEL.create_material_expression(m4,unreal.MaterialExpressionMultiply,-200,0)
print('  mul->BASE  ',[ (nm,MEL.connect_material_property(mul4,nm,unreal.MaterialProperty.MP_BASE_COLOR)) for nm in ('','color') ])
sn4=ts(m4,unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
print('  tex->NORMAL',[ (nm,MEL.connect_material_property(sn4,nm,unreal.MaterialProperty.MP_NORMAL)) for nm in ('color','') ])
print('  readback BASE ->',type(MEL.get_material_property_input_node(m4,unreal.MaterialProperty.MP_BASE_COLOR)).__name__)
print('  readback NORMAL ->',type(MEL.get_material_property_input_node(m4,unreal.MaterialProperty.MP_NORMAL)).__name__)
EAL.delete_asset('/Game/TempProbe6')
print('NAME_PROBE_DONE')
