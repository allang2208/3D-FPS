import unreal
AT=unreal.AssetToolsHelpers.get_asset_tools()
MEL=unreal.MaterialEditingLibrary
EAL=unreal.EditorAssetLibrary
for old in ('/Game/TempProbe/PROBE_M','/Game/TempProbe/PROBE_MI'):
    if EAL.does_asset_exist(old): EAL.delete_asset(old)
m=AT.create_asset('PROBE_M','/Game/TempProbe',unreal.Material,unreal.MaterialFactoryNew())
assert m, 'material create failed'
e=MEL.create_material_expression(m,unreal.MaterialExpressionVectorParameter,0,0)
e.set_editor_property('parameter_name',unreal.Name('Tint'))
e.set_editor_property('default_value',unreal.LinearColor(0.5,0.5,0.6,1))
MEL.connect_material_property(e,'',unreal.MaterialProperty.MP_BASE_COLOR)
print('INSTANCE_FNS',[x for x in dir(MEL) if 'instance' in x.lower() and not x.startswith('get') and not x.startswith('is')])
print('PARAM_NAMES',MEL.get_vector_parameter_names(m))
mi=AT.create_asset('PROBE_MI','/Game/TempProbe',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
mi.set_editor_property('parent',m)
for fn in ('update_material_instance','update_material_instance_editor_values'):
    if hasattr(MEL,fn):
        try: getattr(MEL,fn)(mi); print('called',fn)
        except Exception as ex: print('call',fn,'err',str(ex)[:120])
print('after-parent setter:',MEL.set_material_instance_vector_parameter_value(mi,'Tint',unreal.LinearColor(1,0.6,0.2,1)))
try:
    print('readback:',MEL.get_material_instance_vector_parameter_value(mi,'Tint'))
except Exception as ex: print('readback err',str(ex)[:120])
arr=mi.get_editor_property('vector_parameter_values')
print('ARR_LEN',len(arr))
EAL.delete_asset('/Game/TempProbe')
print('PROBE7_DONE')
