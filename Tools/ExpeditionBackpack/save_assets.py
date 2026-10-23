"""Save the supplied pack, PBR material and six native wearable variants.

No second decimation pass, runtime launch or acceptance renders. Resume each
saved mesh by its authored source digest so interrupted imports do not repeat.
"""
import json,hashlib,importlib.util,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ExpeditionBackpack20261022'
DEST='/Game/Characters/ExpeditionBackpack20261022'
OLD='/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/EquipmentFit20261003'
E,G,L=u.EditorAssetLibrary,u.GeometryScript_AssetUtils,u.MaterialEditingLibrary
A=u.AssetToolsHelpers.get_asset_tools()
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
manifest=json.loads((R/'manifest.json').read_text())
receipts=json.loads((R/'saved_assets.json').read_text()) if (R/'saved_assets.json').exists() else {'variants':{}}
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
io=load_module('expedition_dynamic_io',P/'Tools/ChainmailPants/save_assets.py')
winding=load_module('expedition_winding',P/'Tools/BackpackHarness/winding.py')

def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside expedition asset scope')
    asset.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):
        raise RuntimeError('Failed saving '+asset.get_path_name())

def receipt():
    receipts.update(revision=manifest['revision'],runtime_tested=False,accepted_by_user=False)
    (R/'saved_assets.json').write_text(json.dumps(receipts,indent=2))

def material(name):
    result=u.load_asset(DEST+'/'+name) or A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(result)
    L.set_material_usage(result,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    result.set_editor_property('two_sided',False)
    return result

def sample(mat,texture,kind):
    node=L.create_material_expression(mat,u.MaterialExpressionTextureSample)
    node.set_editor_property('texture',texture);node.set_editor_property('sampler_type',kind);return node

def connect(node,pin,prop):
    if not L.connect_material_property(node,pin,prop):raise RuntimeError('Cannot connect material channel')

def materials():
    E.make_directory(DEST+'/Textures');textures={}
    for channel,filename in [('BaseColor','T_Expedition_BaseColor'),('Normal','T_Expedition_Normal_GL'),('MR','T_Expedition_MetallicRoughness')]:
        task=u.AssetImportTask();task.filename=str(R/'Textures'/(filename+'.png'))
        task.destination_path=DEST+'/Textures';task.destination_name=filename
        task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
        texture=u.load_asset(task.destination_path+'/'+filename)
        if not texture:raise RuntimeError('Texture import failed '+filename)
        texture.set_editor_property('srgb',channel=='BaseColor')
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='MR' else u.TextureCompressionSettings.TC_DEFAULT)
        texture.set_editor_property('never_stream',False)
        if channel=='Normal':texture.set_editor_property('flip_green_channel',True)
        save(texture);textures[channel]=texture
    mat=material('M_ExpeditionBackpack');mat.set_editor_property('two_sided',True)
    for channel,texture in textures.items():
        node=sample(mat,texture,u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='MR' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        if channel=='BaseColor':connect(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        elif channel=='Normal':connect(node,'RGB',u.MaterialProperty.MP_NORMAL)
        else:
            # Meshy's map is metallic-roughness; its R channel is not occlusion.
            connect(node,'G',u.MaterialProperty.MP_ROUGHNESS);connect(node,'B',u.MaterialProperty.MP_METALLIC)
    L.recompile_material(mat);save(mat)
    fabric=material('M_ExpeditionHarness_Fabric')
    for channel in ['BaseColor','ORM','Normal']:
        texture=u.load_asset(OLD+'/Textures/T_HarnessFabricR1_'+channel)
        if not texture:raise RuntimeError('Missing retained harness fabric texture '+channel)
        node=sample(fabric,texture,u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        if channel=='BaseColor':
            gray=L.create_material_expression(fabric,u.MaterialExpressionDesaturation)
            fraction=L.create_material_expression(fabric,u.MaterialExpressionConstant);fraction.set_editor_property('r',1.)
            # UE shortens the first Desaturation pin to an unnamed input.
            # An explicit empty pin name selects input zero; "Input" fails.
            if not L.connect_material_expressions(node,'RGB',gray,''):
                raise RuntimeError('Cannot connect fabric color to Desaturation input zero')
            if not L.connect_material_expressions(fraction,'',gray,'Fraction'):
                raise RuntimeError('Cannot connect fabric desaturation fraction')
            tint=L.create_material_expression(fabric,u.MaterialExpressionConstant3Vector);tint.set_editor_property('constant',u.LinearColor(.92,.87,.71,1))
            mul=L.create_material_expression(fabric,u.MaterialExpressionMultiply)
            if not L.connect_material_expressions(gray,'',mul,'A') or not L.connect_material_expressions(tint,'',mul,'B'):
                raise RuntimeError('Cannot connect the fabric tint')
            connect(mul,'',u.MaterialProperty.MP_BASE_COLOR)
        elif channel=='Normal':connect(node,'RGB',u.MaterialProperty.MP_NORMAL)
        else:
            for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:connect(node,pin,prop)
    errors=L.recompile_material(fabric)
    if errors:raise RuntimeError('Fabric material compile errors: '+str(errors))
    save(fabric)
    hardware=u.load_asset(DEST+'/M_ExpeditionHarness_Hardware') or E.duplicate_asset(OLD+'/M_BackpackHarness_Hardware',DEST+'/M_ExpeditionHarness_Hardware')
    if not hardware:raise RuntimeError('Cannot duplicate harness hardware material')
    save(hardware)
    receipts['materials']=[mat.get_path_name(),hardware.get_path_name(),fabric.get_path_name()];receipt()

def static_dynamic(data):
    data=winding.to_unreal(data);vertices=[];normals=[];uv=[];triangles=[];lookup={}
    for fi,face in enumerate(data['triangles']):
        row=[]
        for ci,vi in enumerate(face):
            n=data['normals'][fi][ci];tex=data['uv'][fi][ci];key=(vi,*n,*tex)
            if key not in lookup:
                lookup[key]=len(vertices);vertices.append(u.Vector(*data['positions'][vi]));normals.append(u.Vector(*n));uv.append(u.Vector2D(*tex))
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    dm=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv,triangles=triangles),0,True)
    return dm

def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('Finish PIE before creating wearable assets')
        if any(pkg.get_path_name().startswith(DEST+'/') for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError('Expedition assets have unsaved editor edits')
    E.make_directory(DEST);materials()
    src=R/'Authored/static_source.json';digest=hashlib.sha256(src.read_bytes()).hexdigest()
    static_path=DEST+'/SM_ExpeditionBackpack'
    if receipts.get('static',{}).get('sha256')!=digest or not E.does_asset_exist(static_path):
        data=json.loads(src.read_text());dm=static_dynamic(data)
        mesh=u.load_asset(static_path)
        if mesh:
            _,status=G.copy_mesh_to_static_mesh(dm,mesh,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
        else:
            mesh,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,static_path,
                u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,enable_collision=False,enable_nanite=True))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot create complete display pack')
        mesh.set_material(0,u.load_asset(DEST+'/M_ExpeditionBackpack'))
        E.set_metadata_tag(mesh,'BackpackFrontFaceConvention',winding.UE_CONVENTION)
        E.set_metadata_tag(mesh,'SourceSHA256',digest);save(mesh)
        receipts['static']={'asset':mesh.get_path_name(),'sha256':digest,'saved':True,'triangles':len(data['triangles']),'nanite':True};receipt()
        del dm,data;gc.collect();u.SystemLibrary.collect_garbage()
        print('EXPEDITION_STATIC_SAVED',flush=True)
    for row in manifest['variants']:
        profile=row['profile'];src=Path(row['source']);digest=hashlib.sha256(src.read_bytes()).hexdigest();path=row['asset'].split('.')[0]
        if receipts['variants'].get(profile,{}).get('sha256')==digest and E.does_asset_exist(path):
            print('EXPEDITION_RESUMED',profile,flush=True);continue
        data=json.loads(src.read_text());mesh=u.load_asset(path) or E.duplicate_asset(OLD+'/SK_Jason_Backpack',path)
        if not mesh:raise RuntimeError('Cannot create native wearable '+profile)
        native,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native reference skeleton')
        # Never retain a different backpack's reduced LOD on this new mesh.
        count=S.get_lod_count(mesh)
        if count>1 and not S.remove_lods(mesh,list(range(1,count))):raise RuntimeError('Cannot remove inherited backpack LODs')
        dm=io.dynamic(winding.to_unreal(data),native)
        mats=[u.load_asset(m['asset']) for m in data['materials']]
        options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,
            new_material_slot_names=[m['slot'] for m in data['materials']],enable_recompute_normals=False,enable_recompute_tangents=True,
            bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD(lod_index=0))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save wearable '+profile)
        setting=S.get_lod_build_settings(mesh,0);setting.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(mesh,0,setting)
        mesh.set_editor_property('physics_asset',None)
        E.set_metadata_tag(mesh,'EquipmentDefinition','ue_expedition_backpack')
        E.set_metadata_tag(mesh,'BackpackFrontFaceConvention',winding.UE_CONVENTION)
        E.set_metadata_tag(mesh,'BackpackHarnessRevision',manifest['revision'])
        E.set_metadata_tag(mesh,'SourceSHA256',digest);save(mesh)
        receipts['variants'][profile]={'asset':mesh.get_path_name(),'sha256':digest,'saved':True,'triangles':len(data['triangles']),'lod_count':1,'no_additional_decimation':True};receipt()
        print('EXPEDITION_WEARABLE_SAVED',profile,flush=True)
        del dm,native,data,mesh;gc.collect();u.SystemLibrary.collect_garbage()
    receipts['completed']=True;receipt();print('EXPEDITION_ALL_ASSETS_SAVED',flush=True)

if __name__=='__main__':main()
