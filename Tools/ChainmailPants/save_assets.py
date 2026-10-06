"""Save mail trousers, native LODs, pickup and icon source in one authoring batch."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailPants20261004'
DEST='/Game/Characters/ModularOutfit20260924/ChainmailPants20261004'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
SLOTS=['InterlacedMail','ForgedSteel','CharcoalLining']

def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing authoring input: '+path)
    return asset

def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside new trousers scope')
    asset.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):
        raise RuntimeError('Could not save '+asset.get_path_name())

def wire(a,b,pin,output=''):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect '+pin)

def output(a,prop,pin=''):
    if not L.connect_material_property(a,pin,prop):raise RuntimeError('Cannot connect output '+str(prop))

def material_assets():
    folder=DEST+'/Materials';E.make_directory(folder);textures={}
    for channel in ['BaseColor','Normal','ORM']:
        name='T_ChainmailPants_Steel_'+channel;t=u.AssetImportTask()
        t.filename=str(R/'Textures'/(name+'.png'));t.destination_path=folder;t.destination_name=name
        t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
        tex=load(folder+'/'+name);tex.set_editor_property('srgb',channel=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property('flip_green_channel',channel=='Normal');tex.set_editor_property('never_stream',False)
        tex.set_editor_property('max_texture_size',1024);tex.set_editor_property('compression_no_alpha',True)
        tex.set_editor_property('address_x',u.TextureAddress.TA_WRAP);tex.set_editor_property('address_y',u.TextureAddress.TA_WRAP)
        save(tex);textures[channel]=tex
    steel=u.load_asset(folder+'/M_ChainmailPants_ForgedSteel') or A.create_asset('M_ChainmailPants_ForgedSteel',folder,u.Material,u.MaterialFactoryNew())
    if not L.get_material_expressions(steel):
        L.set_material_usage(steel,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(steel,u.MaterialUsage.MATUSAGE_STATIC_MESH)
        uv=L.create_material_expression(steel,u.MaterialExpressionTextureCoordinate)
        uv.set_editor_property('u_tiling',4.);uv.set_editor_property('v_tiling',4.)
        for channel,tex in textures.items():
            n=L.create_material_expression(steel,u.MaterialExpressionTextureSampleParameter2D)
            n.set_editor_property('parameter_name',channel);n.set_editor_property('texture',tex)
            n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            wire(uv,n,'UVs')
            if channel=='BaseColor':output(n,u.MaterialProperty.MP_BASE_COLOR,'RGB')
            elif channel=='Normal':output(n,u.MaterialProperty.MP_NORMAL,'RGB')
            else:
                for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:output(n,prop,pin)
    errors=L.recompile_material(steel)
    if errors:raise RuntimeError('Forged material compile failed: '+str(errors))
    save(steel)
    lining=u.load_asset(folder+'/M_ChainmailPants_CharcoalLining') or A.create_asset('M_ChainmailPants_CharcoalLining',folder,u.Material,u.MaterialFactoryNew())
    if not L.get_material_expressions(lining):
        L.set_material_usage(lining,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(lining,u.MaterialUsage.MATUSAGE_STATIC_MESH)
        c=L.create_material_expression(lining,u.MaterialExpressionConstant3Vector);c.set_editor_property('constant',u.LinearColor(.028,.033,.038,1));output(c,u.MaterialProperty.MP_BASE_COLOR)
        for value,prop in [(.82,u.MaterialProperty.MP_ROUGHNESS),(0.,u.MaterialProperty.MP_METALLIC),(.35,u.MaterialProperty.MP_SPECULAR)]:
            n=L.create_material_expression(lining,u.MaterialExpressionConstant);n.set_editor_property('r',value);output(n,prop)
    errors=L.recompile_material(lining)
    if errors:raise RuntimeError('Lining material compile failed: '+str(errors))
    save(lining)
    existing=json.loads((P/'SourceAssets/ChainmailInterlace20260929/materials-saved.json').read_text())
    return [load(existing['standard']),steel,lining]

def dynamic(data,native):
    positions=[];normals=[];uvs=[];weights=[];faces=[];lookup={}
    for fi,face in enumerate(data['triangles']):
        row=[]
        for ci,vi in enumerate(face):
            normal=data['normals'][fi][ci];uv=data['uv'][fi][ci]
            key=(vi,*[round(x,7) for x in (*normal,*uv)])
            if key not in lookup:
                lookup[key]=len(positions);positions.append(u.Vector(*data['positions'][vi]));normals.append(u.Vector(*normal));uvs.append(u.Vector2D(*uv));weights.append(data['weights'][vi])
            row.append(lookup[key])
        faces.append(u.IntVector(*row))
    dm=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=positions,normals=normals,uv0=uvs,triangles=faces),0,True)
    B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
    for vi,bindings in enumerate(weights):B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=bi,weight=w) for bi,w in bindings])
    for ti,slot in enumerate(data['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,ti,slot,True)
    return dm

def static(dm,path,mats):
    mesh=u.load_asset(path)
    if mesh:
        _,status=G.copy_mesh_to_static_mesh(dm,mesh,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
    else:
        mesh,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,enable_collision=False))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot create '+path)
    for i,mat in enumerate(mats):mesh.set_material(i,mat)
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    options=u.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False;rows=[]
    for ratio,screen in [(1.,1.),(.55,.18),(.3,.07)]:
        row=u.StaticMeshReductionSettings();row.percent_triangles=ratio;row.screen_size=screen;rows.append(row)
    options.reduction_settings=rows;subsystem.set_lods(mesh,options)
    save(mesh);return mesh.get_path_name()

def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():raise RuntimeError('Cannot author assets during current play session')
    mats=material_assets();saved={'materials':[m.get_path_name() for m in mats]}
    for key,suffix in [('standard',''),('boots','_BootsFit')]:
        data=json.loads((R/('Jason_ChainmailPants'+suffix+'.json')).read_text())
        source=load(data['source']);native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native bind')
        dm=dynamic(data,native);name='SK_Jason_ChainmailPants'+suffix
        mesh=u.load_asset(DEST+'/'+name) or A.duplicate_asset(name,DEST,source)
        opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=SLOTS,enable_recompute_normals=False,enable_recompute_tangents=True,
            bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+name)
        build=S.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(mesh,0,build)
        if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):raise RuntimeError('LOD configuration failed '+name)
        if not S.regenerate_lod(mesh,3,True,False):raise RuntimeError('LOD creation failed '+name)
        mesh.set_editor_property('physics_asset',None)
        E.set_metadata_tag(mesh,'EquipmentDefinition','ue_chainmail_pants');E.set_metadata_tag(mesh,'SourceContract',data['contract'])
        save(mesh);saved[key]=mesh.get_path_name()
        if key=='standard':
            icon_dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
            u.GeometryScript_MeshTransforms.rotate_mesh(icon_dm,u.Rotator(pitch=0,yaw=180,roll=0))
            saved['icon']=static(icon_dm,DEST+'/Icons/SM_ChainmailPants_Display',mats)
            pickup_dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
            center_z=(min(p[2] for p in data['positions'])+max(p[2] for p in data['positions']))*.5
            u.GeometryScript_MeshTransforms.translate_mesh(pickup_dm,u.Vector(0,0,-center_z))
            u.GeometryScript_MeshTransforms.rotate_mesh(pickup_dm,u.Rotator(pitch=0,yaw=0,roll=-90))
            saved['pickup']=static(pickup_dm,DEST+'/Pickups/SM_ChainmailPants',mats)
        print('CHAINMAIL_PANTS_SAVED',key,flush=True)
    (R/'saved_assets.json').write_text(json.dumps(saved,indent=2))
    print('CHAINMAIL_PANTS_ASSETS_SAVED',flush=True)

if __name__=='__main__':main()
