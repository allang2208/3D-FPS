"""Install the rear finish and extend existing weather mappings for both new guns."""
import unreal as u,json,hashlib,ast
from pathlib import Path
O=Path(__file__).parent;ROOT=O.parent.parent;E=u.EditorAssetLibrary;LIB=u.MaterialEditingLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
FINISH='/Game/Weapons/M1911/RearFinish20260913';DEST='/Game/Weather/WeaponExpansion20260913';SHADERS=ROOT/'SourceAssets/WeatherNatural20260912'
sources=json.loads((O/'sources.json').read_text());author=json.loads((O/'rear_finish.json').read_text());receipt={'rear_finish':{},'rain_mapping':{},'skipped':[]}
# Use the established weather-node construction API without regenerating sky/rain systems.
unreal=u;REPORT={'materials':[]}
tree=ast.parse((ROOT/'Tools/Weather/build_natural_weather.py').read_text(encoding='utf-8'))
functions={'node','wire','prop','scalar','constant','vector','custom','save','duplicate'}
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in functions],type_ignores=[]),'<existing weather graph helpers>','exec'))
textures={}
for kind,file in author['textures'].items():
    t=u.AssetImportTask();t.filename=file;t.destination_path=FINISH+'/Textures';t.destination_name=Path(file).stem;t.automated=True;t.replace_existing=True;t.save=False
    TOOLS.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+t.destination_name)
    tex.srgb=kind=='BaseColor';tex.compression_settings=u.TextureCompressionSettings.TC_DEFAULT if kind=='BaseColor' else u.TextureCompressionSettings.TC_MASKS;tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    save(tex);textures[kind]=tex
old_mat='/Game/Weapons/M1911/Hero20260913/Materials/M_M1911_Hero_Steel'
matpath=FINISH+'/Materials/M_M1911_RearUnified_Steel'
mat=u.load_asset(matpath) if E.does_asset_exist(matpath) else E.duplicate_asset(old_mat,matpath)
for kind,propname in [('BaseColor','BASE_COLOR'),('ORM','ROUGHNESS')]:
    input=LIB.get_material_property_input_node(mat,getattr(u.MaterialProperty,'MP_'+propname));input.set_editor_property('texture',textures[kind])
save(mat)
old_mesh='/Game/Weapons/M1911/Hero20260913/SK_M1911_Manny';meshpath=FINISH+'/SK_M1911_Manny'
mesh=u.load_asset(meshpath) if E.does_asset_exist(meshpath) else E.duplicate_asset(old_mesh,meshpath)
slots=mesh.materials
for i,slot in enumerate(slots):
    if str(slot.material_slot_name)=='M_M1911_Hero_Steel':slot.material_interface=mat;slots[i]=slot
mesh.set_editor_property('materials',slots);save(mesh)
E.set_metadata_tag(mesh,'RearFinishSource',old_mesh);E.set_metadata_tag(mat,'RearFinishParts',','.join(author['targets']));save(mesh);save(mat)
receipt['rear_finish']={'mesh':mesh.get_path_name(),'material':mat.get_path_name(),'parts':author['targets'],'normal_ao':'Retained from original Hero atlas'}
# Replace just the dry rear material in the source list before building rain variants.
for m,slots in sources['weapons']['M1911'].items():
    for slot in slots:
        if slot['material']==old_mat+'.M_M1911_Hero_Steel':slot['material']=mat.get_path_name()
materials={}
for family,meshes in sources['weapons'].items():
    for meshname,slots in meshes.items():
        for slot in slots:
            p=slot['material'];label=(p+' '+slot['slot']).lower() if p else ''
            if not p or any(x in label for x in ['manny','reticle','lens','glass','recess','ammo','emissive']):
                if p:receipt['skipped'].append(p)
                continue
            materials[p]=u.load_asset(p)
masters={}
def wet_master(source):
    key=hashlib.sha1(source.get_path_name().encode()).hexdigest()[:10];m,fresh=duplicate(source,'M_Wet_'+source.get_name()+'_'+key)
    if not fresh:return m
    original={}
    for name,default in [('BASE_COLOR',(.5,.5,.5)),('ROUGHNESS',.5),('NORMAL',(0,0,1))]:
        property=getattr(u.MaterialProperty,'MP_'+name);src=LIB.get_material_property_input_node(m,property)
        original[name]=(src,LIB.get_material_property_input_node_output_name(m,property)) if src else (vector(m,default) if isinstance(default,tuple) else constant(m,default))
    wet=scalar(m,'WeaponWetness',0)
    if source.get_path_name()==mat.get_path_name():
        # The same Steel atlas contains dark bore occluders. Keep those cavities
        # dry instead of adding bright water highlights inside the muzzle.
        wet=custom(m,'return Wet*smoothstep(.006,.014,dot(Base,float3(.2126,.7152,.0722)));',dict(Wet=wet,Base=original['BASE_COLOR']),1,'M1911 cavity exclusion')
    data=custom(m,(SHADERS/'WeaponBeads.hlsl').read_text(),dict(UV=node(m,u.MaterialExpressionTextureCoordinate),Wet=wet),4,'WeatherBeads')
    prop(custom(m,'return Base*(1-Data.a*.07);',dict(Base=original['BASE_COLOR'],Data=data),3),'BASE_COLOR')
    prop(custom(m,'return lerp(lerp(Base,max(.085,Base*.70),Data.a),.065,Data.b*.8);',dict(Base=original['ROUGHNESS'],Data=data),1),'ROUGHNESS')
    prop(custom(m,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',dict(Base=original['NORMAL'],Data=data),3),'NORMAL')
    LIB.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);E.set_metadata_tag(m,'DryWeaponMaterial',source.get_path_name());return save(m)
for path,source in materials.items():
    if not source:raise RuntimeError('Missing weapon material '+path)
    base=source
    while isinstance(base,u.MaterialInstance):base=base.get_editor_property('parent')
    if base.blend_mode not in [u.BlendMode.BLEND_OPAQUE,u.BlendMode.BLEND_MASKED]:receipt['skipped'].append(path);continue
    if LIB.get_material_property_input_node(base,u.MaterialProperty.MP_MATERIAL_ATTRIBUTES) or LIB.get_material_property_input_node(base,u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Needs attribute wet-layer integration: '+path)
    master=masters.get(base.get_path_name())
    if not master:master=wet_master(base);masters[base.get_path_name()]=master
    result=master
    if isinstance(source,u.MaterialInstanceConstant):
        values={kind:{str(n):getattr(LIB,'get_material_instance_'+kind+'_parameter_value')(source,n) for n in getattr(LIB,'get_'+kind+'_parameter_names')(base)} for kind in ['scalar','vector','texture','static_switch']}
        key=hashlib.sha1(path.encode()).hexdigest()[:10];result,_=duplicate(source,'MI_Wet_'+source.get_name()+'_'+key);LIB.set_material_instance_parent(result,master)
        for kind,params in values.items():
            for name,value in params.items():
                if value is not None:getattr(LIB,'set_material_instance_'+kind+'_parameter_value')(result,name,value)
        LIB.update_material_instance(result);save(result)
    receipt['rain_mapping'][path]=result.get_path_name()
    u.log('NEW_WEAPON_WET_MATERIAL '+path)
receipt['libraries']={}
for path in sources['weather_libraries']:
    da=u.load_asset(path);mapping=dict(da.get_editor_property('wet_materials'));before=len(mapping)
    mapping.update({p:u.load_asset(w) for p,w in receipt['rain_mapping'].items()})
    da.set_editor_property('wet_materials',mapping);save(da);receipt['libraries'][path]={'before':before,'after':len(mapping)}
receipt['skipped']=sorted(set(receipt['skipped']))
(O/'installed.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('M1911_REAR_QBZ191_RAIN_INSTALLED '+str(len(receipt['rain_mapping'])))
