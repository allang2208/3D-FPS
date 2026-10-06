"""Save new armored boots, body coverage and three fitted trouser variants."""
import json
import sys
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ArmoredBoots20261004'
DEST='/Game/Characters/ModularOutfit20260924/ArmoredBoots20261004'
sys.path.insert(0,str(P/'Tools/ChainmailPants'))
import save_assets as shared
# This file executes as __main__; imported shared module is the pants utility.
shared.DEST=DEST
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;T=u.GeometryScript_MeshTransforms
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)

def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing production source '+path)
    return obj
def read(name):return json.loads((R/(name+'.json')).read_text())
def copy(asset):
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy '+asset.get_path_name())
    return dm
def materials():
    folder=DEST+'/Materials';E.make_directory(folder)
    mats=[load('/Game/Characters/ModularOutfit20260924/ChainmailPants20261004/ArmorRefineV2/Materials/M_ChainmailPants_ForgedSteel')]
    for surface in ['Leather','Sole']:
        m=A.create_asset('M_ArmoredBoots_'+surface,folder,u.Material,u.MaterialFactoryNew())
        if not m:raise RuntimeError('Material already exists or cannot create '+surface)
        L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(m,u.MaterialUsage.MATUSAGE_STATIC_MESH)
        uv=L.create_material_expression(m,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',4.);uv.set_editor_property('v_tiling',4.)
        for channel in ['BaseColor','Normal','ORM']:
            name='T_ArmoredBoots_'+surface+'_'+channel;task=u.AssetImportTask()
            task.filename=str(R/'Textures'/(name+'.png'));task.destination_path=folder;task.destination_name=name;task.automated=True;task.save=False;task.replace_existing=True
            A.import_asset_tasks([task]);tex=load(folder+'/'+name)
            tex.set_editor_property('srgb',channel=='BaseColor')
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
            tex.set_editor_property('flip_green_channel',channel=='Normal');tex.set_editor_property('never_stream',False);tex.set_editor_property('max_texture_size',1024);tex.set_editor_property('compression_no_alpha',True)
            tex.set_editor_property('address_x',u.TextureAddress.TA_WRAP);tex.set_editor_property('address_y',u.TextureAddress.TA_WRAP);shared.save(tex)
            node=L.create_material_expression(m,u.MaterialExpressionTextureSampleParameter2D);node.set_editor_property('parameter_name',channel);node.set_editor_property('texture',tex)
            node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            shared.wire(uv,node,'UVs')
            if channel=='BaseColor':shared.output(node,u.MaterialProperty.MP_BASE_COLOR,'RGB')
            elif channel=='Normal':shared.output(node,u.MaterialProperty.MP_NORMAL,'RGB')
            else:
                for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:shared.output(node,prop,pin)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError('Material compilation failed '+str(errors))
        shared.save(m);mats.append(m)
    m=A.create_asset('M_ArmoredBoots_WaxedThread',folder,u.Material,u.MaterialFactoryNew())
    L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(m,u.MaterialUsage.MATUSAGE_STATIC_MESH)
    color=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);color.set_editor_property('constant',u.LinearColor(.14,.11,.073,1));shared.output(color,u.MaterialProperty.MP_BASE_COLOR)
    rough=L.create_material_expression(m,u.MaterialExpressionConstant);rough.set_editor_property('r',.8);shared.output(rough,u.MaterialProperty.MP_ROUGHNESS)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Thread compilation failed '+str(errors))
    shared.save(m);mats.append(m);return mats

def skeletal(dm,source,name,mats,slots,recompute=False,physics=False):
    mesh=A.duplicate_asset(name,DEST,source)
    if not mesh:raise RuntimeError('Destination exists or cannot duplicate '+name)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=slots,
        enable_recompute_normals=recompute,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+name)
    build=S.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(mesh,0,build)
    if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):raise RuntimeError('LOD setup failed '+name)
    if not S.regenerate_lod(mesh,3,True,False):raise RuntimeError('LOD creation failed '+name)
    if not physics:mesh.set_editor_property('physics_asset',None)
    E.set_metadata_tag(mesh,'EquipmentDefinition','ue_armored_boots');shared.save(mesh)
    print('ARMORED_BOOT_SKELETAL_SAVED',name,flush=True);return mesh

def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():raise RuntimeError('Cannot author during play')
    mats=materials();data=read('Jason_ArmoredBoots');source=load(data['source']);native=copy(source)
    dm=shared.dynamic(data,native);boots=skeletal(dm,source,'SK_Jason_ArmoredBoots',mats,['ForgedSteel','CharcoalLeather','LayeredSole','WaxedThread'])
    saved=dict(boots=boots.get_path_name(),materials=[m.get_path_name() for m in mats])
    for kind in ['icon','pickup']:
        dm=copy(boots)
        if kind=='icon':
            remove=[]
            for ti in range(dm.get_triangle_count()):
                valid,a,b,c=u.GeometryScript_MeshQueries.get_triangle_positions(dm,ti)
                if valid and a.x+b.x+c.x<0:remove.append(ti)
            u.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,u.GeometryScript_List.convert_array_to_index_list(remove),False)
            T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=150,roll=0));T.rotate_mesh(dm,u.Rotator(pitch=30,yaw=0,roll=0))
            path=DEST+'/Icons/SM_ArmoredBoots_Display'
        else:
            points=data['positions'];center=[(min(p[i] for p in points)+max(p[i] for p in points))*.5 for i in range(3)]
            T.translate_mesh(dm,u.Vector(*[-v for v in center]));path=DEST+'/Pickups/SM_ArmoredBoots'
        saved[kind]=shared.static(dm,path,mats)
    for key,label in [('base','Base'),('jeans','Jeans_ArmoredBootsFit'),('cargo','Cargo_ArmoredBootsFit')]:
        d=read(key+'_fitted');src=load(d['source']);dm=copy(src)
        if key=='base':
            for ti,slot in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,ti,slot,True)
        else:u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,u.GeometryScript_List.convert_array_to_vector_list([u.Vector(*v) for v in d['positions']]))
        model=skeletal(dm,src,'SK_Jason_'+label,[load(m['asset']) for m in d['materials']],[m['slot'] for m in d['materials']],recompute=key!='base',physics=key=='base')
        saved[key]=model.get_path_name()
    d=read('Jason_ChainmailPants_ArmoredBootsFit');src=load(d['source']);dm=shared.dynamic(d,copy(src))
    mail_saved=json.loads((P/'SourceAssets/ChainmailPants20261004/ArmorRefineV2/saved_assets.json').read_text())
    model=skeletal(dm,src,'SK_Jason_ChainmailPants_ArmoredBootsFit',[load(x) for x in mail_saved['materials']],['InterlacedMail','ForgedSteel','CharcoalLining'])
    saved['chainmail']=model.get_path_name()
    (R/'saved_assets.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
    print('ARMORED_BOOTS_ASSETS_SAVED',flush=True)

if __name__=='__main__':main()
