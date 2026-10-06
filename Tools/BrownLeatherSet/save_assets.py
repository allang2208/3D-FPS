"""Save the two leather items and their native shoe-fit variants in new packages."""
import importlib.util,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BrownLeatherSet20261004'
DEST='/Game/Characters/ModularOutfit20260924/BrownLeatherSet20261004'
spec=importlib.util.spec_from_file_location('brown_leather_mesh_io',str(P/'Tools/ChainmailPants/save_assets.py'))
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared);shared.DEST=DEST
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils;T=u.GeometryScript_MeshTransforms
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
SLOTS=['AgedSteel','BrownLeather','LayeredSole','WaxedThread','ReinforcedLeather']
def load(path):
    result=u.load_asset(path)
    if not result:raise RuntimeError('Missing production dependency '+path)
    return result
def read(name):return json.loads((R/(name+'.json')).read_text())
def copy(mesh):
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy source '+mesh.get_path_name())
    return dm
def mat(name):
    folder=DEST+'/Materials'
    material=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    if not material:raise RuntimeError('Cannot create '+name)
    if L.get_material_expressions(material):return material,False
    L.set_material_usage(material,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.set_material_usage(material,u.MaterialUsage.MATUSAGE_STATIC_MESH)
    return material,True
def compile_save(material):
    errors=L.recompile_material(material)
    if errors:raise RuntimeError('Material compilation failed '+str(errors))
    shared.save(material)
def constant(name,color,roughness,metal):
    m,create=mat(name)
    if create:
        n=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*color,1));shared.output(n,u.MaterialProperty.MP_BASE_COLOR)
        for value,prop in [(roughness,u.MaterialProperty.MP_ROUGHNESS),(metal,u.MaterialProperty.MP_METALLIC)]:
            n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',value);shared.output(n,prop)
    compile_save(m);return m
def materials():
    folder=DEST+'/Materials';E.make_directory(folder);textures={}
    for channel in ['BaseColor','Normal','ORM']:
        name='T_BrownLeather_'+channel;task=u.AssetImportTask();task.filename=str(R/'Textures'/(name+'.png'));task.destination_path=folder;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=load(folder+'/'+name)
        tex.set_editor_property('srgb',channel=='BaseColor');tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property('flip_green_channel',channel=='Normal');tex.set_editor_property('never_stream',False);tex.set_editor_property('max_texture_size',1024);tex.set_editor_property('compression_no_alpha',True)
        tex.set_editor_property('address_x',u.TextureAddress.TA_WRAP);tex.set_editor_property('address_y',u.TextureAddress.TA_WRAP);shared.save(tex);textures[channel]=tex
    leather=[]
    for suffix,tint in [('Main',(1.,1.,1.)),('Reinforced',(.83,.80,.77))]:
        m,create=mat('M_BrownLeather_'+suffix)
        if create:
            uv=L.create_material_expression(m,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',4.);uv.set_editor_property('v_tiling',4.)
            for channel,tex in textures.items():
                n=L.create_material_expression(m,u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',channel);n.set_editor_property('texture',tex)
                n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);shared.wire(uv,n,'UVs')
                if channel=='BaseColor':
                    color=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);color.set_editor_property('constant',u.LinearColor(*tint,1))
                    multiply=L.create_material_expression(m,u.MaterialExpressionMultiply);shared.wire(n,multiply,'A','RGB');shared.wire(color,multiply,'B');shared.output(multiply,u.MaterialProperty.MP_BASE_COLOR)
                elif channel=='Normal':shared.output(n,u.MaterialProperty.MP_NORMAL,'RGB')
                else:
                    for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:shared.output(n,prop,pin)
        compile_save(m);leather.append(m)
    return [constant('M_BrownLeather_AgedSteel',(.105,.113,.12),.55,1.),leather[0],
        load('/Game/Characters/ModularOutfit20260924/ArmoredBoots20261004/Materials/M_ArmoredBoots_Sole'),
        constant('M_BrownLeather_WaxedThread',(.14,.11,.073),.8,0.),leather[1]]
def save_skeletal(data,name,mats):
    source=load(data['source']);native=copy(source);dm=shared.dynamic(data,native)
    mesh=u.load_asset(DEST+'/'+name) or A.duplicate_asset(name,DEST,source)
    if not mesh:raise RuntimeError('Cannot create '+name)
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=SLOTS,enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+name)
    build=S.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(mesh,0,build)
    if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):raise RuntimeError('Cannot configure LODs '+name)
    if not S.regenerate_lod(mesh,3,True,False):raise RuntimeError('Cannot generate LODs '+name)
    mesh.set_editor_property('physics_asset',None);E.set_metadata_tag(mesh,'SourceContract',data['contract']);shared.save(mesh)
    print('BROWN_LEATHER_SKELETAL_SAVED',name,flush=True);return mesh
def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():raise RuntimeError('Cannot author during play')
    mats=materials();saved={'materials':[m.get_path_name() for m in mats]}
    for key,source in [('boots','Jason_LeatherBoots'),('pants','Jason_LeatherPants'),('pants_short','Jason_LeatherPants_ShortBootsFit'),('pants_high','Jason_LeatherPants_HighBootsFit')]:
        data=read(source);mesh=save_skeletal(data,'SK_'+source,mats);saved[key]=mesh.get_path_name()
        if key not in ['boots','pants']:continue
        for kind in ['icon','pickup']:
            dm=copy(mesh)
            if kind=='icon':
                if key=='boots':
                    remove=[]
                    for ti in range(dm.get_triangle_count()):
                        valid,a,b,c=u.GeometryScript_MeshQueries.get_triangle_positions(dm,ti)
                        if valid and a.x+b.x+c.x<0:remove.append(ti)
                    u.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,u.GeometryScript_List.convert_array_to_index_list(remove),False)
                    T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=150,roll=0));T.rotate_mesh(dm,u.Rotator(pitch=30,yaw=0,roll=0))
                else:T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=180,roll=0))
                path=DEST+'/Icons/SM_Leather'+key.title()+'_Display'
            else:
                points=data['positions'];center=[(min(p[i] for p in points)+max(p[i] for p in points))*.5 for i in range(3)];T.translate_mesh(dm,u.Vector(*[-x for x in center]))
                if key=='pants':T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=0,roll=-90))
                path=DEST+'/Pickups/SM_Leather'+key.title()
            saved[key+'_'+kind]=shared.static(dm,path,mats)
    (R/'saved_assets.json').write_text(json.dumps(saved,indent=2),encoding='utf-8');print('BROWN_LEATHER_ASSETS_SAVED',flush=True)
if __name__=='__main__':main()
