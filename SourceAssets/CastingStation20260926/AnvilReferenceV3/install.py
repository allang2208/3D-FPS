"""Save the reference-shaped anvil and its assembled station at the existing runtime paths."""
from pathlib import Path
import datetime,json,sys
import unreal as u

ROOT=Path(u.Paths.project_dir());HERE=ROOT/'SourceAssets/CastingStation20260926/AnvilReferenceV3'
DEST='/Game/Props/CastingStation20260926';SURF=DEST+'/AnvilReferenceV3'
MAN=json.loads((HERE/'Authored/manifest.json').read_text(encoding='utf8'))
sys.path.insert(0,str(ROOT/'Tools/Fluids'))
from furnace_material_graph import node,wire,prop,custom,scalar
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
saved=[]

def save(asset):
    if isinstance(asset,u.Material):
        errors=L.recompile_material(asset)
        if errors:raise RuntimeError('Material compilation failed: '+str(errors))
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    saved.append(asset.get_path_name())

def texture(kind):
    name='T_Anvil_Worked_'+kind
    task=u.AssetImportTask();task.filename=str(HERE/'Textures'/(name+'.png'))
    task.destination_path=SURF+'/Textures';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);tex=u.load_asset(task.destination_path+'/'+name)
    if not tex:raise RuntimeError('Texture import failed '+name)
    tex.set_editor_property('srgb',kind=='BaseColor')
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal'
        else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_BC7)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD)
    if kind=='Normal':tex.set_editor_property('flip_green_channel',False)
    save(tex);return tex

def material(worked):
    name='M_AnvilReferenceSteel';path=SURF+'/Materials/'+name
    mat=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,SURF+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('used_with_nanite',True)
    def sample(tex,kind):
        if not tex:raise RuntimeError('Missing source metal map '+kind)
        n=node(mat,u.MaterialExpressionTextureSample);n.set_editor_property('texture',tex)
        n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal'
            else u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        return n
    body={kind:sample(u.load_asset('/Game/Props/BlastFurnace20260923/Textures/T_BlastFurnace_WroughtIron_'+kind),kind)
        for kind in ['BaseColor','Roughness','Metallic','Normal','AO']}
    work={kind:sample(tex,kind) for kind,tex in worked.items()}
    work['ORM'].set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    wear=node(mat,u.MaterialExpressionVertexColor)
    # The vertex mask identifies the working zones, not a solid sheet of fresh silver steel.
    # The existing scanned metal mask breaks these zones into irregular rubbed/oxidized patches.
    body_value=scalar(mat,'AgedBodyBrightness',.42)
    work_value=scalar(mat,'AgedWorkfaceBrightness',.34)
    coverage=scalar(mat,'MaximumRubbedSteel',.70)
    rubbed=custom(mat,'return saturate(Wear)*(0.12+max(MaxRubbed-0.12,0.0)*smoothstep(0.15,0.8,Clean));',
        {'Wear':(wear,'R'),'Clean':(body['Metallic'],'R'),'MaxRubbed':coverage})
    base=custom(mat,'float l=dot(Iron,float3(0.2126,0.7152,0.0722)); float3 oxide=(Iron*0.75+l*0.25)*BodyValue; '
        'float3 oldsteel=Worked*float3(0.97,0.95,0.91)*WorkValue; return lerp(oxide,oldsteel,saturate(Rubbed));',
        {'Iron':(body['BaseColor'],'RGB'),'Worked':(work['BaseColor'],'RGB'),'Rubbed':rubbed,
         'BodyValue':body_value,'WorkValue':work_value},3)
    rough=custom(mat,'return lerp(clamp(0.72+Iron*0.2,0.72,0.93),clamp(0.60+Worked*0.2,0.60,0.8),saturate(Rubbed));',
        {'Iron':(body['Roughness'],'R'),'Worked':(work['ORM'],'G'),'Rubbed':rubbed})
    metallic=custom(mat,'return lerp(0.04+Iron*0.62,Worked*0.88,saturate(Rubbed));',
        {'Iron':(body['Metallic'],'R'),'Worked':(work['ORM'],'B'),'Rubbed':rubbed})
    normal=custom(mat,'float3 n=normalize(float3(Iron.xy*0.65,Iron.z)); return normalize(lerp(n,Worked,saturate(Rubbed)));',
        {'Iron':(body['Normal'],'RGB'),'Worked':(work['Normal'],'RGB'),'Rubbed':rubbed},3)
    ao=custom(mat,'return lerp(Iron,Worked,saturate(Wear));',
        {'Iron':(body['AO'],'R'),'Worked':(work['ORM'],'R'),'Wear':rubbed})
    specular=custom(mat,'return lerp(0.28,0.5,saturate(Rubbed));',{'Rubbed':rubbed})
    slab=node(mat,u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for n,pin,property_id in [(base,'BaseColor',u.MaterialProperty.MP_BASE_COLOR),(rough,'Roughness',u.MaterialProperty.MP_ROUGHNESS),
            (metallic,'Metallic',u.MaterialProperty.MP_METALLIC),(normal,'Normal',u.MaterialProperty.MP_NORMAL),
            (specular,'Specular',u.MaterialProperty.MP_SPECULAR)]:
        wire(n,slab,pin)
        if not L.connect_material_property(n,'',property_id):raise RuntimeError('Material property '+pin)
    prop(mat,ao,'AMBIENT_OCCLUSION');prop(mat,slab,'FRONT_MATERIAL')
    E.set_metadata_tag(mat,'CastingStation.AnvilRevision','3')
    E.set_metadata_tag(mat,'CastingStation.SurfaceRevision','AgedIron4');save(mat);return mat

def run(owned_dirty=()):
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('PIE is running; asset reimport requires play to stop')
    targets={DEST+'/'+n for n in MAN['assets']}
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if targets.intersection(dirty).difference(owned_dirty) or any(p.startswith(SURF+'/') for p in dirty):
        raise RuntimeError('Unsaved target content: preserve editor changes')
    worked={kind:texture(kind) for kind in ['BaseColor','ORM','Normal']}
    mats={'Masonry':u.load_asset('/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_Masonry'),
        'DarkSteel':u.load_asset('/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_WroughtIron'),
        'PolishedSteel':u.load_asset(DEST+'/Materials/M_AnvilFace'),
        'Wood':u.load_asset('/Game/UnrealNormandy/MaterialInstances/MI_Wood_00A'),
        'Water':u.load_asset(DEST+'/Materials/M_CoolingWater'),'AnvilSteel':material(worked)}
    if any(m is None for m in mats.values()):raise RuntimeError('Missing station material')
    imported_dimensions={}
    for name,record in MAN['assets'].items():
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False
        data=options.static_mesh_import_data
        data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        data.import_uniform_scale=1.0
        # Legacy reimport can retain the prior FbxStaticMeshImportData instead of task options.
        existing=u.load_asset(DEST+'/'+name)
        if existing:
            previous=existing.get_editor_property('asset_import_data')
            if isinstance(previous,u.FbxStaticMeshImportData):
                previous.set_editor_property('convert_scene_unit',True)
                previous.set_editor_property('import_uniform_scale',1.0)
        task=u.AssetImportTask();task.filename=record['fbx'];task.destination_path=DEST;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task])
        mesh=u.load_asset(DEST+'/'+name)
        if not mesh:raise RuntimeError('Mesh import failed '+name)
        # Preserve importer's section-to-slot indices, including any retained legacy slots.
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            label=str(slot.get_editor_property('material_slot_name')).split('.')[0]
            if label in ('AnvilForge','AnvilFace','AnvilHorn'):label='AnvilSteel'
            if label not in mats:raise RuntimeError('Unknown imported slot '+label)
            mesh.set_material(i,mats[label])
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        settings=mesh.get_editor_property('nanite_settings');settings.enabled=True;mesh.set_editor_property('nanite_settings',settings)
        if name=='SM_CastingStation':
            for label,point in MAN['sockets_ue_cm'].items():
                sock=mesh.find_socket(label)
                if not sock:
                    sock=u.new_object(u.StaticMeshSocket,outer=mesh);sock.set_editor_property('socket_name',label);mesh.add_socket(sock)
                sock.set_editor_property('relative_location',u.Vector(*point))
        bounds=mesh.get_bounds()
        actual=[float(v)*2 for v in (bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z)]
        expected=record['dimensions_cm']
        if any(abs(a-b)>max(.05,b*.001) for a,b in zip(actual,expected)):
            raise RuntimeError('Imported centimetre dimensions differ from source for '+name+': '+str(actual)+' versus '+str(expected))
        imported_dimensions[name]=actual
        E.set_metadata_tag(mesh,'SourceAuthoring','SourceAssets/CastingStation20260926/AnvilReferenceV3/rebuild_anvil.py')
        E.set_metadata_tag(mesh,'CastingStation.AnvilRevision','3');save(mesh)
    receipt={'revision':'AnvilReferenceV3','saved':saved,'geometry':MAN['assets'],'construction':MAN['construction'],
        'material':'Existing Normandy-derived oxidized iron plus original worked steel, vertex blended',
        'imported_dimensions_cm':imported_dimensions,
        'runtime_tested':False,'rendered':False}
    (HERE/'Receipts').mkdir(exist_ok=True)
    (HERE/'Receipts'/('install-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')).write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    print('ANVIL_REFERENCE_SAVED '+json.dumps(receipt,ensure_ascii=False),flush=True)

if __name__=='__main__':run()
