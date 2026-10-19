"""Save Chixiao PBR, rune surfaces, mesh LODs and standard icon in an isolated host."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D='/Game/Weapons/Zhanmadao20261018/ChixiaoBladeV1'
E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=P/'AssetHost':raise RuntimeError('Wrong asset host')
ex=json.loads((P/'exports.json').read_text(encoding='utf-8'))
source=next(iter(json.loads((P/'source_bindings.json').read_text(encoding='utf-8'))['factory'].values())).split('.')[0]
receipt={'assets':[],'assets_saved':False,'staged_assets_saved':False,'complete':False,'game_tested':False,'effects_applied':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    if isinstance(obj,u.Material):
        errors=E.recompile_material(obj)
        if errors:raise RuntimeError('Shader build: '+str(errors))
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed '+obj.get_path_name())
    receipt['assets'].append(obj.get_path_name());record()
def texture(file,path,channel):
    folder,name=path.rsplit('/',1);task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory()
    A.import_asset_tasks([task]);obj=load(path);icon=channel=='Icon';normal=channel=='Normal'
    props=dict(srgb=channel in ['BaseColor','Icon'],max_texture_size=1024 if icon else 4096,
        compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON if icon else u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_BC7 if channel=='BaseColor' else u.TextureCompressionSettings.TC_MASKS,
        lod_group=u.TextureGroup.TEXTUREGROUP_UI if icon else u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_WEAPON,never_stream=icon)
    if icon:props['mip_gen_settings']=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    if normal:props['flip_green_channel']=True
    obj.set_editor_properties(props);save(obj);return obj
textures={key:texture(P/'Textures'/('Chixiao_'+key+'.png'),D+'/Textures/T_Chixiao_'+key+'_V1',key) for key in ['BaseColor','ORM','Normal']}
name='M_TangDaoBladeRuneSurface_Zhanmadao_chixiao_V1';target=D+'/Materials/'+name
surface=u.load_asset(target) or L.duplicate_asset(source,target)
if not surface:raise RuntimeError('Missing native rune donor')
replacement=(P/'rune_placement.hlsl').read_text(encoding='utf-8')
replaced=set();rune=False
for n in E.get_material_expressions(surface):
    if isinstance(n,u.MaterialExpressionTextureSample):
        tex=n.get_editor_property('texture')
        if tex:
            old=tex.get_name()
            key='BaseColor' if 'BaseColor' in old else 'ORM' if 'MetallicRoughness' in old or 'ORM' in old else 'Normal' if 'Normal' in old else None
            if key:n.set_editor_property('texture',textures[key]);replaced.add(key)
    if isinstance(n,u.MaterialExpressionCustom):
        code=n.get_editor_property('code');marker='// END_ZHANMADAO_BLADE_CONTOUR_V1'
        if marker not in code:continue
        rest=code.split(marker,1)[1]
        # Replace only this blade's contour and its owned Beiwei branch.
        if '// BEIWEI_RUNE_V1' in rest:
            begin=rest.index('// BEIWEI_RUNE_V1');opening=rest.index('{',begin);depth=1;i=opening+1
            while depth:
                depth+=(rest[i]=='{')-(rest[i]=='}');i+=1
            rest=rest[:begin]+rest[i:]
        n.set_editor_property('code',replacement+'\n'+rest);rune=True
if replaced!={'BaseColor','ORM','Normal'} or not rune:raise RuntimeError('Incomplete surface authoring')
surface.set_editor_properties(dict(two_sided=False,used_with_skeletal_mesh=False))
save(surface)
gold_name='M_Chixiao_Brass_V1';gold_path=D+'/Materials/'+gold_name
gold=u.load_asset(gold_path) or A.create_asset(gold_name,D+'/Materials',u.Material,u.MaterialFactoryNew())
for n in list(E.get_material_expressions(gold)):E.delete_material_expression(gold,n)
front=E.create_material_expression(gold,u.MaterialExpressionSubstrateShadingModels)
front.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
for kind,value,pin,prop in [('color',None,'BaseColor',u.MaterialProperty.MP_BASE_COLOR),('scalar',.92,'Metallic',u.MaterialProperty.MP_METALLIC),('scalar',.34,'Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
    n=E.create_material_expression(gold,u.MaterialExpressionConstant3Vector if kind=='color' else u.MaterialExpressionConstant)
    n.set_editor_property('constant' if kind=='color' else 'r',u.LinearColor(.35,.19,.052,1) if kind=='color' else value)
    E.connect_material_expressions(n,'',front,pin);E.connect_material_property(n,'',prop)
E.connect_material_property(front,'',u.MaterialProperty.MP_FRONT_MATERIAL);save(gold)
receipt['temporal_bindings']={}
for material in [surface,gold]:
    target=material.get_path_name().split('.')[0]+'_Whirlwind'
    temporal=u.load_asset(target) or L.duplicate_asset(material.get_path_name(),target)
    if not any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in E.get_material_expressions(temporal)):
        output=E.create_material_expression(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
        one=E.create_material_expression(temporal,u.MaterialExpressionConstant);one.set_editor_property('r',1.)
        E.connect_material_expressions(one,'',output,'')
    save(temporal);receipt['temporal_bindings'][material.get_path_name()]=temporal.get_path_name()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
name=ex['mesh_name'];path=D+'/Meshes/'+name
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
opt.lod_number=3;opt.auto_compute_lod_distances=True
cfg=opt.static_mesh_import_data;cfg.combine_meshes=False;cfg.import_mesh_lods=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False;cfg.build_nanite=False
cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;cfg.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'));task.destination_name=name;task.destination_path=D+'/Meshes';task.options=opt;task.automated=True;task.save=False;task.replace_existing=False
if not L.does_asset_exist(path):A.import_asset_tasks([task])
mesh=load(path);materials={'M_Chixiao_BladeSurface':surface,'M_Chixiao_Brass':gold}
for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,materials[str(slot.material_slot_name)])
nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;nanite.explicit_tangents=True;mesh.set_editor_property('nanite_settings',nanite)
save(mesh)
icon_key='ue_zhanmadao_blade_1_chixiao'
texture(P/'Export/Chixiao_Icon_Framed.png','/Game/ColdSteelData/AttachmentIcons20260913/'+icon_key,'Icon')
receipt.update(staged_assets_saved=True,mesh=mesh.get_path_name(),materials={k:v.get_path_name() for k,v in materials.items()},icon_key=icon_key)
record();print('CHIXIAO_ASSETS_STAGED',len(receipt['assets']),flush=True)
