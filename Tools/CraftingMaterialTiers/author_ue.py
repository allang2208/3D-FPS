"""Author only this task's new packages in an isolated headless UE project."""
from pathlib import Path
import json
import unreal as u

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/CraftingMaterialTiers20261026'
if Path(u.Paths.project_dir()).resolve()!=(OUT/'AssetHost').resolve():raise RuntimeError('Isolated AssetHost required')
ROWS=json.loads((OUT/'materials.json').read_text(encoding='utf-8'))
BASE='/Game/Items/CraftingMaterialTiers20261026';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
E.make_directory(BASE)
def node(m,cls):return L.create_material_expression(m,cls)
def link(a,o,b,i):
    if not L.connect_material_expressions(a,o,b,i):raise RuntimeError('Cannot connect material input '+i)
def prop(a,o,p):
    if not L.connect_material_property(a,o,p):raise RuntimeError('Cannot connect material property '+str(p))
def scalar(m,name,value):
    n=node(m,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def vector(m,name,value):
    n=node(m,u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*value,1));return n

wood=(ROOT/'SourceAssets/WoodworkingSurfaceV2_20261026/stock_surface.hlsl').read_text(encoding='utf-8')
wood=wood.replace('radius * 2.85','radius * 2.85 * GrainScale').replace('(warp - .5) * .7','(warp - .5) * .7 * WarpScale')
wood=wood.replace('(wander - .5) * 1.15','(wander - .5) * 1.15 * WarpScale')
wood=wood.replace('float3(.24,.122,.052), float3(.40,.243,.113)','TintDark, TintLight').replace('clamp(.77 + fibers','clamp(BaseRoughness + fibers')
wood=wood.replace('float2(-24.0, 7.0)','float2(-7.0, 1.0)').replace('float2(31.0, -11.0)','float2(9.0, -2.0)')
wood=wood.replace('latewood * lerp(.20, .28, endGrain)','latewood * lerp(.32, .40, endGrain)')
metal=r'''struct MetalSurface {
 float hash(float2 p) { p=frac(p*float2(123.34,456.21));p+=dot(p,p+45.32);return frac(p.x*p.y); }
 float noise(float2 p) {float2 i=floor(p),f=frac(p);f=f*f*(3.-2.*f);return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);}
};
MetalSurface s;float3 p=LocalPosition;
float2 uv=float2(p.x*.32,p.y*155.+p.z*95.);
float aa=1.-smoothstep(.4,1.6,length(fwidth(uv)));
float brushed=(s.noise(uv)-.5)*aa;
float crystal=s.noise(p.xy*24.+p.z*7.)-.5;
float broad=s.noise(p.xy*.6+p.z*.2);
float3 base=lerp(TintDark,TintLight,saturate(.32+broad*.36+crystal*.09));
base*=1.+brushed*.10;
Roughness=clamp(BaseRoughness+brushed*.10+crystal*.065,.28,.62);
float h=brushed*.0012+crystal*.00035;
float3 n=normalize(GeometricNormal),dx=ddx(WorldPosition),dy=ddy(WorldPosition);
float3 sx=cross(dy,n),sy=cross(n,dx);float det=dot(dx,sx);
SurfaceNormal=normalize(n-(ddx(h)*sx+ddy(h)*sy)*sign(det)/max(abs(det),.00001));
return saturate(base);'''

masters={};saved=[]
for family,shader in [('metal',metal),('wood',wood)]:
    name='M_MetalTier' if family=='metal' else 'M_WoodTier'
    if E.does_asset_exist(BASE+'/'+name):m=E.load_asset(BASE+'/'+name)
    else:
        m=A.create_asset(name,BASE,u.Material,u.MaterialFactoryNew());m.set_editor_property('tangent_space_normal',False)
        world=node(m,u.MaterialExpressionWorldPosition);local=node(m,u.MaterialExpressionTransformPosition)
        local.set_editor_property('transform_source_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
        local.set_editor_property('transform_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL);link(world,'',local,'')
        first=next(c for c in ROWS if c['family']==family)
        inputs={'LocalPosition':local,'WorldPosition':world,'GeometricNormal':node(m,u.MaterialExpressionVertexNormalWS),
            'TintDark':vector(m,'TintDark',first['low']),'TintLight':vector(m,'TintLight',first['high']),
            'BaseRoughness':scalar(m,'BaseRoughness',first['roughness'])}
        if family=='wood':inputs.update({'SurfaceData':node(m,u.MaterialExpressionVertexColor),'GrainScale':scalar(m,'GrainScale',1),'WarpScale':scalar(m,'WarpScale',1)})
        custom=node(m,u.MaterialExpressionCustom);custom.set_editor_property('code',shader);custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        pins=[]
        for key in inputs:
            p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
        custom.set_editor_property('inputs',pins);outputs=[]
        for key,kind in [('Roughness',u.CustomMaterialOutputType.CMOT_FLOAT1),('SurfaceNormal',u.CustomMaterialOutputType.CMOT_FLOAT3)]:
            p=u.CustomOutput();p.set_editor_property('output_name',key);p.set_editor_property('output_type',kind);outputs.append(p)
        custom.set_editor_property('additional_outputs',outputs)
        for key,n in inputs.items():link(n,'RGB' if key in ('TintDark','TintLight') else '',custom,key)
        for o,p in [('',u.MaterialProperty.MP_BASE_COLOR),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('SurfaceNormal',u.MaterialProperty.MP_NORMAL)]:prop(custom,o,p)
        prop(scalar(m,'Metallic',1 if family=='metal' else 0),'',u.MaterialProperty.MP_METALLIC)
        prop(scalar(m,'Specular',.5 if family=='metal' else .23),'',u.MaterialProperty.MP_SPECULAR)
        L.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);L.recompile_material(m)
        if not E.save_loaded_asset(m,False):raise RuntimeError('Material save failed '+name)
    masters[family]=m;saved.append(m.get_path_name());(OUT/(family+'_surface.hlsl')).write_text(shader,encoding='utf-8')

for c in ROWS:
    suffix=('Ingot_' if c['family']=='metal' else 'WoodCore_')+c['key'];mi_name='MI_'+suffix
    mi=E.load_asset(BASE+'/'+mi_name) if E.does_asset_exist(BASE+'/'+mi_name) else A.create_asset(mi_name,BASE,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,masters[c['family']])
    for k,v in [('TintDark',c['low']),('TintLight',c['high'])]:L.set_material_instance_vector_parameter_value(mi,k,u.LinearColor(*v,1))
    L.set_material_instance_scalar_parameter_value(mi,'BaseRoughness',c['roughness'])
    if c['family']=='wood':
        L.set_material_instance_scalar_parameter_value(mi,'GrainScale',c['grain']);L.set_material_instance_scalar_parameter_value(mi,'WarpScale',c['warp'])
    L.update_material_instance(mi)
    if not E.save_loaded_asset(mi,False):raise RuntimeError('Instance save failed '+mi_name)
    name='SM_'+suffix;task=u.AssetImportTask()
    for k,v in [('filename',str(OUT/'Export'/f'{name}.fbx')),('destination_path',BASE),('destination_name',name),('automated',True),('replace_existing',True),('save',True)]:task.set_editor_property(k,v)
    opts=u.FbxImportUI();opts.set_editor_property('import_as_skeletal',False);opts.set_editor_property('import_materials',False);opts.set_editor_property('import_textures',False);opts.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
    data=opts.get_editor_property('static_mesh_import_data');data.set_editor_property('auto_generate_collision',True)
    data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE);data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task.set_editor_property('options',opts);A.import_asset_tasks([task]);mesh=E.load_asset(BASE+'/'+name)
    if not isinstance(mesh,u.StaticMesh):raise RuntimeError('Mesh import failed '+name)
    mesh.set_material(0,mi)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed '+name)
    saved.extend([mi.get_path_name(),mesh.get_path_name()])
(OUT/'ue-authoring.json').write_text(json.dumps({'saved_assets':saved,'host':u.Paths.project_dir(),'gameplay_test':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('CRAFTING_MATERIAL_ASSETS_SAVED',len(saved))
