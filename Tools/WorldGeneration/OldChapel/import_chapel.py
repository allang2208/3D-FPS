"""Import the chapel kit into its exclusive package directory with no level loaded."""
import json
import os
import runpy
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))/'SourceAssets/TemperateHillsOldChapel/Concept01'
DEST='/Game/WorldGeneration/TemperateHills/OldChapel'
A=u.AssetToolsHelpers.get_asset_tools()
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Failed to save '+obj.get_path_name())
def get(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def create_mat(name):
    path=DEST+'/Materials/'+name
    mat=E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    mat.modify()
    L.delete_all_material_expressions(mat)
    return mat
def out(node,pin,matprop):
    if not L.connect_material_property(node,pin,getattr(u.MaterialProperty,'MP_'+matprop)):raise RuntimeError(matprop)
def setup_texture(source,name,channel):
    destination=DEST+'/Textures'
    path=destination+'/'+name
    if E.does_asset_exist(path):tex=get(path)
    else:
        task=u.AssetImportTask();task.filename=str(source);task.destination_path=destination;task.destination_name=name
        task.automated=True;task.save=False
        A.import_asset_tasks([task]);tex=get(path)
    tex.set_editor_property('srgb',channel=='base_color')
    if channel=='normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel',True)
    elif channel!='base_color':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('max_texture_size',2048)
    save(tex)
    return tex
materials={}
if os.environ.get('CHAPEL_RESUME')=='1':
    for folder in sorted((ROOT/'Meshy').glob('[0-9]*')):
        role=folder.name.split('_',1)[1]
        materials['Chapel'+role]=get(DEST+'/Materials/MI_Chapel'+role)
else:
    master=create_mat('M_ChapelArtifact')
    channels={'base_color':('BASE_COLOR','RGB','COLOR'),'normal':('NORMAL','RGB','NORMAL'),
              'metallic':('METALLIC','R','MASKS'),'roughness':('ROUGHNESS','R','MASKS')}
    nodes={}
    for channel in channels:
        n=L.create_material_expression(master,u.MaterialExpressionTextureSampleParameter2D)
        n.set_editor_property('parameter_name',channel)
        nodes[channel]=n
    for index,folder in enumerate(sorted((ROOT/'Meshy').glob('[0-9]*'))):
        role=folder.name.split('_',1)[1];maps={}
        for channel,(prop,pin,sampler) in channels.items():
            tex=setup_texture(folder/'downloads'/('texture_urls_0_'+channel+'.png'),'T_Chapel'+role+'_'+channel,channel)
            maps[channel]=tex
            if index==0:
                n=nodes[channel];n.texture=tex;n.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+sampler);out(n,pin,prop)
        if index==0:
            L.set_base_material_usage(master,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
            L.set_base_material_usage(master,u.MaterialUsage.MATUSAGE_NANITE,True)
            L.recompile_material(master);save(master)
        name='MI_Chapel'+role;addr=DEST+'/Materials/'+name
        mat=get(addr) if E.does_asset_exist(addr) else A.create_asset(name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(mat,master)
        for channel,tex in maps.items():L.set_material_instance_texture_parameter_value(mat,channel,tex)
        save(mat);materials['Chapel'+role]=mat

norm='/Game/UnrealNormandy/MaterialInstances/'
paths={'Coping':norm+'MI_StoneWall_Pieces_00B_Gray','Mortar':norm+'MI_Main_Mortar_00A',
       'Trail':norm+'MI_Ground_Road_00A'}
for slot,path in paths.items():materials[slot]=get(path)
surface_scope=runpy.run_path(str(Path(__file__).with_name('chapel_surfaces.py')),init_globals=globals())
materials.update(surface_scope['surface_materials']())
if os.environ.get('CHAPEL_RESUME')=='1':
    for slot in ('Glass','Lead','Iron'):materials[slot]=get(DEST+'/Materials/M_Chapel'+slot)
else:
    for slot in ('Glass','Lead','Iron'):
        mat=create_mat('M_Chapel'+slot)
        if slot=='Glass':
            mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
            mat.set_editor_property('two_sided',True)
            mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE)
        color=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
        color.constant=u.LinearColor(*({'Glass':(.53,.62,.55),'Iron':(.12,.09,.065),'Lead':(.18,.19,.16)}[slot]),1)
        out(color,'','BASE_COLOR')
        for k,v in ({'OPACITY':.16,'ROUGHNESS':.19} if slot=='Glass' else {'METALLIC':.72,'ROUGHNESS':.74}).items():
            n=L.create_material_expression(mat,u.MaterialExpressionConstant);n.r=v;out(n,'',k)
        L.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
        L.recompile_material(mat);save(mat);materials[slot]=mat

receipt=[]
for fbx in sorted((ROOT/'Authored').glob('SM_Chapel*.fbx')):
    name=fbx.stem;role=name[len('SM_Chapel'):];dest=DEST+'/Meshes'
    if os.environ.get('CHAPEL_RESUME')=='1' and role not in os.environ.get('CHAPEL_UPDATE','').split() and E.does_asset_exist(dest+'/'+name):
        receipt.append(get(dest+'/'+name).get_path_name())
        continue
    task=u.AssetImportTask();task.filename=str(fbx);task.destination_name=name;task.destination_path=dest
    task.automated=True;task.save=False;task.replace_existing=True
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
    courtyard=role in ('YardWallA','YardWallB','YardPier')
    chapel_wall=role in ('SolidBay','WindowBay','WestGable','EastGable')
    if role=='Foundation' or courtyard or chapel_wall:
        opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
    opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=get(dest+'/'+name)
    assigned=set()
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        # Reimport may preserve a display name while updating its FBX section binding.
        key=str(slot.get_editor_property('imported_material_slot_name') if role=='Foundation' or courtyard else slot.material_slot_name)
        if chapel_wall:
            # Older packages can retain the interior slot across FBX reimports.
            key='Wall'
        mesh.set_material(i,materials[key])
        assigned.add(key)
    if role=='Foundation' and not {'Footing','Mortar'}.issubset(assigned):
        raise RuntimeError('Foundation FBX material binding: '+str(assigned))
    settings=mesh.get_editor_property('nanite_settings')
    settings.set_editor_property('enabled',courtyard or role=='YardPathStone' or ('Chapel'+role) in materials)
    mesh.set_editor_property('nanite_settings',settings)
    if role in ('LancetGlass','OculusGlass'):
        editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.get_default_object(u.StaticMeshEditorSubsystem)
        for section in range(mesh.get_num_sections(0)):
            slot=editor.get_lod_material_slot(mesh,0,section)
            if slot<0:raise RuntimeError('Cannot resolve glazing section '+role)
            casts=mesh.get_material(slot)==materials['Lead']
            editor.enable_section_cast_shadow(mesh,casts,0,section)
            if editor.is_section_cast_shadow_enabled(mesh,0,section)!=casts:raise RuntimeError(role+' shadow binding')
    if courtyard:
        body=mesh.get_editor_property('body_setup')
        aggregate=body.get_editor_property('agg_geom')
        cap=104. if role=='YardPier' else 82.
        bottom=-52.
        box=u.KBoxElem()
        box.set_editor_property('center',u.Vector(0,0,(bottom+cap)*.5))
        for key,value in [('x',64. if role=='YardPier' else 180.),('y',64. if role=='YardPier' else 46.),('z',cap-bottom)]:
            box.set_editor_property(key,value)
        aggregate.set_editor_property('box_elems',[box])
        body.set_editor_property('agg_geom',aggregate)
        body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    elif role=='Door':
        body=mesh.get_editor_property('body_setup')
        aggregate=body.get_editor_property('agg_geom')
        box=u.KBoxElem()
        box.set_editor_property('center',u.Vector(0,0,132))
        for key,value in [('x',8.),('y',146.),('z',262.)]:box.set_editor_property(key,value)
        aggregate.set_editor_property('box_elems',[box])
        body.set_editor_property('agg_geom',aggregate)
    else:
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh)
    receipt.append(mesh.get_path_name())
    u.log('OLD_CHAPEL_SAVED '+name)
(ROOT/'Authored/imported.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')

