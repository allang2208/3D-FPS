"""Install fitted pistol devices with the accepted M1911 finish and rain layer."""
import unreal as u, json, ast
from pathlib import Path

O=Path(__file__).parent
ROOT=O.parent.parent
D='/Game/Weapons/M1911/Tactical20260913'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
tree=ast.parse((O.parent/'WeaponAttachmentFinish20260913/import_finish.py').read_text(encoding='utf-8'))
helpers={'save','node','link','output','constant','mul','clone'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),'<existing material helpers>','exec'))
auth=json.loads((O/'authoring.json').read_text())
reference='/Game/Weapons/M1911/RearFinish20260913/Materials/M_M1911_RearUnified_Steel'
textures={kind:u.load_asset('/Game/Weapons/M1911/Attachments20260913/Textures/T_M1911_Attachment_'+kind) for kind in ['BaseColor','ORM']}
for kind,tex in textures.items():
    if tex is None:raise RuntimeError('Missing existing M1911 coating '+kind)
originals={
    'laser':'/Game/Weapons/TacticalDevices20260913/M4/laser/M_M4_laser_Body_OpticalV2',
    'flashlight':'/Game/Weapons/TacticalDevices20260913/HunyuanV3/M4/flashlight/M_M4_flashlight_Body_MetalTail',
}
report={'parts':{},'dry_to_wet':{},'weather_libraries':{}}
dry_materials=[]

def coat(material):
    uv=node(material,u.MaterialExpressionTextureCoordinate,coordinate_index=1)
    samples={}
    for kind,tex in textures.items():
        sample=node(material,u.MaterialExpressionTextureSample,texture=tex,
                    sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        link(uv,'',sample,'UVs');samples[kind]=sample
    return [(u.MaterialProperty.MP_BASE_COLOR,samples['BaseColor'],'RGB'),
            (u.MaterialProperty.MP_ROUGHNESS,samples['ORM'],'G'),
            (u.MaterialProperty.MP_METALLIC,samples['ORM'],'B')]

def body_material(kind):
    m=clone(originals[kind],D+'/Materials/M_M1911_'+kind+'_Body')
    if E.get_metadata_tag(m,'M1911TacticalFinish')!='20260913':
        region=node(m,u.MaterialExpressionVertexColor)
        for prop,sample,out in coat(m):
            blend=L.get_material_property_input_node(m,prop)
            if not isinstance(blend,u.MaterialExpressionLinearInterpolate):raise RuntimeError('Source coating graph changed: '+kind)
            # Keep each original optical/rubber input A and all normal/AO wiring.
            link(sample,out,blend,'B');link(region,'R',blend,'Alpha')
        output(constant(m,.5),'',u.MaterialProperty.MP_SPECULAR)
        if kind=='laser':
            uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
            base=node(m,u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/Weapons/TacticalDevices20260913/Textures/T_laser_BaseColor'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            link(uv,'',base,'UVs')
            gb=node(m,u.MaterialExpressionMax);link(base,'G',gb,'A');link(base,'B',gb,'B')
            red=node(m,u.MaterialExpressionSubtract);link(base,'R',red,'A');link(gb,'',red,'B')
            gain=node(m,u.MaterialExpressionMultiply,const_b=12.);link(red,'',gain,'A')
            clamp=node(m,u.MaterialExpressionClamp,min_default=0.,max_default=1.);link(gain,'',clamp,'Input')
            aperture=node(m,u.MaterialExpressionMultiply);link(clamp,'',aperture,'A');link(region,'G',aperture,'B')
            color=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(16.,.001,.0005,1.))
            emission=node(m,u.MaterialExpressionMultiply);link(aperture,'',emission,'A');link(color,'',emission,'B')
            output(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        E.set_metadata_tag(m,'M1911TacticalFinish','20260913')
        E.set_metadata_tag(m,'WeaponFinishReference',reference)
        E.set_metadata_tag(m,'WeaponFinishRegion','UV1 M1911 metal; UV0 optics and laser rubber retained; flashlight metal tail retained')
        L.recompile_material(m)
    save(m);dry_materials.append(m);return m

collar_path=D+'/Materials/M_M1911_Tactical_Collar'
collar=u.load_asset(collar_path) if E.does_asset_exist(collar_path) else A.create_asset('M_M1911_Tactical_Collar',D+'/Materials',u.Material,u.MaterialFactoryNew())
if E.get_metadata_tag(collar,'M1911TacticalFinish')!='20260913':
    for prop,sample,out in coat(collar):output(sample,out,prop)
    output(constant(collar,.5),'',u.MaterialProperty.MP_SPECULAR)
    E.set_metadata_tag(collar,'WeaponFinishReference',reference)
    E.set_metadata_tag(collar,'M1911TacticalFinish','20260913');L.recompile_material(collar)
save(collar);dry_materials.append(collar)

for kind,info in auth.items():
    body=body_material(kind)
    task=u.AssetImportTask();task.filename=info['fbx'];task.destination_path=D+'/'+kind;task.destination_name='SM_TacticalDevice'
    task.automated=True;task.replace_existing=True;task.save=False
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_materials=False;options.import_textures=False;options.import_animations=False
    data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=options;A.import_asset_tasks([task])
    mesh=u.load_asset(task.destination_path+'/SM_TacticalDevice')
    if mesh is None:raise RuntimeError('No imported device '+kind)
    slots=mesh.static_materials
    for i,slot in enumerate(slots):
        is_collar='Collar' in str(slot.material_slot_name)
        slot.material_interface=collar if is_collar else body
        slot.material_slot_name=u.Name('M_Tactical_Collar' if is_collar else 'M_Tactical_'+kind)
        slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    E.set_metadata_tag(mesh,'WeaponFinishReference',reference)
    E.set_metadata_tag(mesh,'M1911TacticalSource',info['source']);save(mesh)
    report['parts'][kind]={'mesh':mesh.get_path_name(),'body_material':body.get_path_name(),'collar_material':collar.get_path_name(),
                           'coating_uv':1,'physical_tile_m':.1,'reference_material':reference,'emitter_author_ue_cm':info['emitter_ue_cm']}
    u.log('M1911_TACTICAL_PART_IMPORTED '+kind)

# Keep newly added metal surfaces on the existing per-weapon wetness system.
weather_tree=ast.parse((ROOT/'Tools/Weather/build_natural_weather.py').read_text(encoding='utf-8'))
weather_names={'node','wire','prop','scalar','constant','vector','custom','save','duplicate'}
weather={'unreal':u,'LIB':L,'TOOLS':A,'DEST':D+'/Wet','REPORT':{'materials':[]}}
exec(compile(ast.Module(body=[x for x in weather_tree.body if isinstance(x,ast.FunctionDef) and x.name in weather_names],type_ignores=[]),'<existing wet-material helpers>','exec'),weather)
for source in dry_materials:
    wet,fresh=weather['duplicate'](source,'M_Wet_'+source.get_name())
    if fresh:
        original={}
        for name,default in [('BASE_COLOR',(.5,.5,.5)),('ROUGHNESS',.5),('NORMAL',(0,0,1))]:
            prop=getattr(u.MaterialProperty,'MP_'+name);node_in=L.get_material_property_input_node(wet,prop)
            original[name]=(node_in,L.get_material_property_input_node_output_name(wet,prop)) if node_in else (weather['vector'](wet,default) if isinstance(default,tuple) else weather['constant'](wet,default))
        wetness=weather['scalar'](wet,'WeaponWetness',0)
        region=weather['node'](wet,u.MaterialExpressionVertexColor)
        mask=weather['custom'](wet,'return Wet*Metal;',{'Wet':wetness,'Metal':(region,'R')},1,'M1911 optical/rubber exclusion')
        beads=weather['custom'](wet,(ROOT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(),
            {'UV':weather['node'](wet,u.MaterialExpressionTextureCoordinate),'Wet':mask},4,'WeatherBeads')
        weather['prop'](weather['custom'](wet,'return Base*(1-Data.a*.07);',{'Base':original['BASE_COLOR'],'Data':beads},3),'BASE_COLOR')
        weather['prop'](weather['custom'](wet,'return lerp(lerp(Base,max(.085,Base*.70),Data.a),.065,Data.b*.8);',{'Base':original['ROUGHNESS'],'Data':beads},1),'ROUGHNESS')
        weather['prop'](weather['custom'](wet,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',{'Base':original['NORMAL'],'Data':beads},3),'NORMAL')
        E.set_metadata_tag(wet,'DryWeaponMaterial',source.get_path_name());weather['save'](wet)
    report['dry_to_wet'][source.get_path_name()]=wet.get_path_name()
for path in ['/Game/Weather/RainVisibility/DA_WeatherPresentation','/Game/Weather/NaturalV2/DA_WeatherPresentation']:
    library=u.load_asset(path);mapping=dict(library.get_editor_property('wet_materials'))
    mapping.update({dry:u.load_asset(wet) for dry,wet in report['dry_to_wet'].items()})
    library.set_editor_property('wet_materials',mapping);save(library)
    report['weather_libraries'][path]='Merged three M1911 tactical material mappings'
(O/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('M1911_TACTICAL_IMPORT_COMPLETE')
