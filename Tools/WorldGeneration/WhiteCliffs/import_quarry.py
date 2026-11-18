"""Import licensed Quixel scans and the authored quarry kit, then save owned assets."""
import json, shutil
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME')
TASK=ROOT/'SourceAssets/HillsRiverLake20261117'
DEST='/Game/WorldGeneration/TemperateHills/WhiteCliffs'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
report={'saved':[],'sources':[],'runtime_tested':False,'gameplay_started':False}
E.make_directory(DEST)
def get(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())
    report['saved'].append(obj.get_path_name())
    (TASK/'Receipts/assets.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def texture(file,name,kind):
    path=DEST+'/Textures/'+name
    if E.does_asset_exist(path):return get(path)
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=DEST+'/Textures';t.destination_name=name
    t.automated=True;t.replace_existing=False;t.save=False;A.import_asset_tasks([t])
    tex=get(path);tex.max_texture_size=2048
    tex.srgb=kind=='BaseColor'
    if kind=='Normal':tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP
    elif kind!='BaseColor':tex.compression_settings=u.TextureCompressionSettings.TC_MASKS
    save(tex);return tex
def scan_material(folder,name):
    path=DEST+'/Materials/M_'+name
    if E.does_asset_exist(path):return get(path)
    mat=A.create_asset('M_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    for kind,prop,output in [('BaseColor','MP_BASE_COLOR','RGB'),('Normal','MP_NORMAL','RGB'),('Roughness','MP_ROUGHNESS','R'),('AO','MP_AMBIENT_OCCLUSION','R'),('Metalness','MP_METALLIC','R')]:
        file=next(folder.glob('*_'+kind+'.jpg'),None)
        if file is None:
            if kind=='Metalness':continue
            raise RuntimeError('Missing '+kind+' in '+str(folder))
        tex=texture(file,'T_'+name+'_'+kind,kind)
        n=L.create_material_expression(mat,u.MaterialExpressionTextureSample);n.texture=tex
        n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else (
            u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        if kind=='BaseColor' and name in ('CliffA','CliffB','LimestoneSpoil'):
            mat.set_editor_property('two_sided',True)
            # The quarry scans carry iron-brown staining. Regrade their albedo
            # to pale limestone while retaining scan grain, AO and normal relief.
            mono=L.create_material_expression(mat,u.MaterialExpressionDesaturation)
            fraction=L.create_material_expression(mat,u.MaterialExpressionConstant);fraction.r=1.
            if not L.connect_material_expressions(n,'RGB',mono,''):
                raise RuntimeError('Could not connect limestone desaturation input')
            L.connect_material_expressions(fraction,'',mono,'Fraction')
            power=L.create_material_expression(mat,u.MaterialExpressionPower)
            exponent=L.create_material_expression(mat,u.MaterialExpressionConstant);exponent.r=.65
            L.connect_material_expressions(mono,'',power,'Base')
            L.connect_material_expressions(exponent,'',power,'Exp')
            tint=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
            tint.constant=u.LinearColor(1.05,1.035,.98,1.)
            multiply=L.create_material_expression(mat,u.MaterialExpressionMultiply)
            L.connect_material_expressions(power,'',multiply,'A');L.connect_material_expressions(tint,'',multiply,'B')
            limit=L.create_material_expression(mat,u.MaterialExpressionClamp)
            limit.set_editor_property('min_default',0.);limit.set_editor_property('max_default',.58)
            if not L.connect_material_expressions(multiply,'',limit,''):
                raise RuntimeError('Could not connect limestone clamp input')
            L.connect_material_property(limit,'',u.MaterialProperty.MP_BASE_COLOR)
        else:
            L.connect_material_property(n,output,getattr(u.MaterialProperty,prop))
    L.recompile_material(mat);save(mat);return mat
def import_mesh(file,name,materials):
    path=DEST+'/Meshes/'+name
    if E.does_asset_exist(path):return get(path)
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=DEST+'/Meshes';t.destination_name=name
    t.automated=True;t.replace_existing=False;t.save=False
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False
    opts.import_as_skeletal=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.auto_generate_collision=False
    opts.static_mesh_import_data.generate_lightmap_u_vs=False
    opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    t.options=opts;A.import_asset_tasks([t]);mesh=get(path)
    for i,slot in enumerate(mesh.static_materials):
        key=str(slot.material_slot_name)
        mesh.set_material(i,materials if not isinstance(materials,dict) else materials[key])
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=True
    authored=isinstance(materials,dict)
    ns.fallback_percent_triangles=1. if authored else .35
    ns.fallback_relative_error=0. if authored else .25
    mesh.set_editor_property('nanite_settings',ns)
    # The shed retains a real door and broken roof; a single convex hull would seal them.
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh)
    bounds=mesh.get_bounding_box()
    report.setdefault('meshes',[]).append({'path':path,'min':[bounds.min.x,bounds.min.y,bounds.min.z],
        'max':[bounds.max.x,bounds.max.y,bounds.max.z],'nanite':True,'collision':'complex static'})
    return mesh
cache=ROOT.parent/'VaultCache/FabLibrary'
scans=[
 ('Quarry_Cliff-5c019f10','CliffA','5c019f10-e69f-4945-8b45-c6e2d8c16f8a'),
 ('Quarry_Cliff-9caa4be4','CliffB','9caa4be4-3b5b-4d55-a3de-2fdc9e4e5bd6'),
 ('Small_Limestone_Rocks_Pack-09676e2a','LimestoneSpoil','09676e2a-5131-4474-9095-8b31e99192f9')]
meshes=[]
for folder,name,uid in scans:
    src=cache/folder/'Extracted'
    mat=scan_material(src,name)
    solid_r9=DEST+'/Meshes/SM_White'+name+'_SolidR9'
    solid=ROOT/'SourceAssets/HillsLandscapeRepair20261117/SolidScans'/('SM_White'+name+'_Solid.fbx')
    if name in ('CliffA','CliffB') and E.does_asset_exist(solid_r9):
        meshes.append(get(solid_r9))
    elif name in ('CliffA','CliffB') and solid.exists():
        mat.set_editor_property('two_sided',False);L.recompile_material(mat);save(mat)
        meshes.append(import_mesh(solid,'SM_White'+name+'_Solid',mat))
    else:
        meshes.append(import_mesh(next(src.glob('*.fbx')),'SM_White'+name,mat))
    report['sources'].append({'seller':'Quixel Megascans','url':'https://www.fab.com/listings/'+uid,
        'source':str(src),'format':'High FBX and PBR','acquisition':'free, saved in library'})
# Owned copies preserve instancing support without altering shared forge or village materials.
cloned={}
def copy_material(path):
    if path in cloned:return cloned[path]
    original=get(path);name=original.get_name();target=DEST+'/Materials/Quarry_'+name
    mat=get(target) if E.does_asset_exist(target) else E.duplicate_asset(path,target)
    if isinstance(mat,u.MaterialInstanceConstant):
        parent=copy_material(original.get_editor_property('parent').get_path_name())
        L.set_material_instance_parent(mat,parent)
    else:
        mat.set_editor_property('used_with_instanced_static_meshes',True);L.recompile_material(mat)
    save(mat);cloned[path]=mat;return mat
oak=copy_material('/Game/Props/CastingStation20260926/RealismV5/M_OakDry')
iron=copy_material('/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron')
stone=copy_material('/Game/UnrealNormandy/MaterialInstances/MI_StoneWall_Pieces_00B_Gray')
mats={'Oak':oak,'Iron':iron,'Stone':stone,'Rope':oak}
props=[]
for row in json.loads((TASK/'Authored/manifest.json').read_text(encoding='utf8')):
    props.append(import_mesh(TASK/'Authored'/(row['name']+'.fbx'),row['name'],mats))
winch=cache/'Historic_Medieval_Castle_Winch_Wood_Old-d6d814b3'/'Extracted'
winch_mat=scan_material(winch,'OldWinch')
props.append(import_mesh(next(winch.glob('*.fbx')),'SM_QuarryOldWinch',winch_mat))
report['sources'].append({'seller':'Quixel Megascans','url':'https://www.fab.com/listings/d6d814b3-b1b0-4e83-9d20-418ac005dd19',
    'source':str(winch),'acquisition':'free, saved in library'})
data=get('/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming')
source=ROOT/'Content/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming.uasset'
backup=TASK/'Before/DA_TemperateHillsStreaming.uasset'
if not backup.exists():shutil.copy2(source,backup)
data.set_editor_property('white_cliff_meshes',meshes)
data.set_editor_property('quarry_props',props)
save(data)
# Mesh save may mark owned material usage dirty after the initial material save.
if not E.save_directory(DEST,True,True):raise RuntimeError('Owned quarry dependency save failed')
report['complete']=True
(TASK/'Receipts/assets.json').write_text(json.dumps(report,indent=2),encoding='utf8')
u.log('HILLS_RIVER_LAKE_ASSETS_SAVED')
