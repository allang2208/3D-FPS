import unreal,json
from pathlib import Path
out=Path(unreal.Paths.project_saved_dir())/'RainUpgrade'
for name in ['M_RainStreak','M_RainDroplet','M_RainMist']:
    m=unreal.load_asset('/Game/Weather/Materials/'+name)
    if name!='M_RainMist' and m.get_editor_property('shading_model')!=unreal.MaterialShadingModel.MSM_UNLIT:
        # Small translucent rain cards disappear under volumetric particle lighting.
        # Exposure-compensated neutral highlights remain readable without particle lights.
        m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
        light=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionVectorParameter)
        light.set_editor_property('parameter_name','RainHighlight')
        light.set_editor_property('default_value',unreal.LinearColor(.85,.9,1,1))
        inverse=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionEyeAdaptationInverse)
        connected=False
        for socket in ['LightValue','LightValueInput']:
            if unreal.MaterialEditingLibrary.connect_material_expressions(light,'',inverse,socket):connected=True;break
        assert connected
        assert unreal.MaterialEditingLibrary.connect_material_property(inverse,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        unreal.MaterialEditingLibrary.recompile_material(m)
        assert unreal.EditorAssetLibrary.save_loaded_asset(m,False)
    changed=False
    if name!='M_RainMist':
        for expression in unreal.MaterialEditingLibrary.get_material_expressions(m):
            if isinstance(expression,unreal.MaterialExpressionVectorParameter) and str(expression.get_editor_property('parameter_name'))=='RainHighlight':
                value=unreal.LinearColor(.85,.9,1,1)
                if expression.get_editor_property('default_value')!=value:expression.set_editor_property('default_value',value);changed=True
            if isinstance(expression,unreal.MaterialExpressionCustom):
                code=expression.get_editor_property('code')
                refined=code.replace('smoothstep(.65,1,Age)','smoothstep(.85,1,Age)').replace('*.38;','*.65;').replace('*.46;','*.6;')
                if code!=refined:expression.set_editor_property('code',refined);changed=True
    if changed:
        unreal.MaterialEditingLibrary.recompile_material(m)
        assert unreal.EditorAssetLibrary.save_loaded_asset(m,False)
    if not m.get_editor_property('used_with_niagara_sprites'):
        unreal.MaterialEditingLibrary.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
        unreal.MaterialEditingLibrary.recompile_material(m)
        assert unreal.EditorAssetLibrary.save_loaded_asset(m,False)
registry=unreal.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous(['/Game/Weather'],True)
api=unreal.get_default_object(unreal.NiagaraToolset_System)
report={}
for name in ['NS_FPS_RainFine','NS_FPS_SurfaceSplashes','NS_FPS_RainMist','NS_FPS_RoofDrips']:
    s=unreal.load_asset('/Game/Weather/VFX/'+name)
    assert s and unreal.RainAssetEditor.compile_rain(s)
    r=unreal.NiagaraExt_StackItemReference()
    r.set_editor_property('system',s);r.set_editor_property('emitter_name','RainSplashes' if name=='NS_FPS_SurfaceSplashes' else 'RainDrops');r.set_editor_property('renderer_index',0)
    radius=2600 if name=='NS_FPS_RainMist' else 2200 if name=='NS_FPS_RainFine' else 350
    bottom=-3000 if name in ['NS_FPS_RainFine','NS_FPS_RoofDrips'] else -900 if name=='NS_FPS_RainMist' else -100
    expected={'FixedBounds':{'min':{'x':-radius,'y':-radius,'z':bottom},'max':{'x':radius,'y':radius,'z':900},'isValid':True},'MaxGPUParticlesSpawnPerFrame':512 if name=='NS_FPS_RainFine' else 64}
    current=json.loads(api.call_method('GetEmitterData',(r,)).get_editor_property('property_values'))
    if any(current.get(k)!=v for k,v in expected.items()):
        data=unreal.NiagaraExt_EmitterData();data.set_editor_property('property_values',json.dumps(expected))
        api.call_method('SetEmitterData',(r,data))
        assert unreal.RainAssetEditor.compile_rain(s)
        assert unreal.EditorAssetLibrary.save_loaded_asset(s,False)
    summary=api.call_method('GetSystemSummary',(s,)).export_text()
    assert summary.count('EmitterName=')==1 and 'Fountain' not in summary,summary
    report[name]={'summary':summary,'emitter':api.call_method('GetEmitterData',(r,)).export_text(),'renderer':api.call_method('GetRendererData',(r,)).export_text()}
for name in ['NS_FPS_Rain','NS_FPS_RainSplashes']:
    report[name]={'referencers':[str(x) for x in registry.get_referencers('/Game/Weather/VFX/'+name,unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True))]}
(out/'assets-validated.json').write_text(json.dumps(report,indent=2))
unreal.log('RAIN_ASSETS_VALIDATION_PASS')
