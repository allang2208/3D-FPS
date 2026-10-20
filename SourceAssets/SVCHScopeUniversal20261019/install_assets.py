"""Import/save only new KV optic assets. No game/editor preview or acceptance."""
import unreal as u,json,re
from pathlib import Path
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();ROOT='/Game/Weapons/KVScope20261019'
S=P/'SourceAssets/SVCHReplacement20261018/Download/Extracted/Original/Native/KVInhibitor'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'complete':False,'saved':[],'runtime_tested':False}
if (O/'assets_receipt.json').exists():receipt=json.loads((O/'assets_receipt.json').read_text())
dirty={a.get_path_name() for a in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def record():(O/'assets_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    if a.get_path_name() not in receipt['saved']:receipt['saved'].append(a.get_path_name())
    record()
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing asset '+p)
    return a
def owned(p):
    if p in dirty:raise RuntimeError('Preserve dirty package '+p)
    if E.does_asset_exist(p) and not any(x.split('.')[0]==p for x in receipt['saved']):raise RuntimeError('Preserve pre-existing asset '+p)
def imported(file,name,options=None,root=ROOT):
    p=root+'/'+name;owned(p)
    if E.does_asset_exist(p):return load(p)
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=root;task.destination_name=name;task.automated=True;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task]);return load(p)
textures={}
for kind in ('BC','N'):
    tex=imported(S/('KVInhibitor_sight_scope'+('' if kind=='BC' else '_n')+'.png'),'T_KVScope_'+kind)
    tex.set_editor_property('srgb',kind=='BC');tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT if kind=='BC' else u.TextureCompressionSettings.TC_NORMALMAP)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON if kind=='BC' else u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP)
    if kind=='N':tex.set_editor_property('flip_green_channel',False)
    save(tex);textures[kind]=tex
materials={}
for name,rough,metal in [('Body',.42,.45),('Cable',.68,0.),('Glass',.08,.25),('Adapter',.38,.8)]:
    p=ROOT+'/M_KVScope_'+name;owned(p)
    mat=load(p) if E.does_asset_exist(p) else A.create_asset('M_KVScope_'+name,ROOT,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    if name in ('Body','Cable'):
        for kind,prop in [('BC',u.MaterialProperty.MP_BASE_COLOR),('N',u.MaterialProperty.MP_NORMAL)]:
            n=L.create_material_expression(mat,u.MaterialExpressionTextureSample);n.texture=textures[kind];n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BC' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL;L.connect_material_property(n,'RGB',prop)
    else:
        n=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector);n.constant=u.LinearColor(.015,.06,.09,1) if name=='Glass' else u.LinearColor(.028,.032,.036,1);L.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
    for value,prop in [(rough,u.MaterialProperty.MP_ROUGHNESS),(metal,u.MaterialProperty.MP_METALLIC)]:
        n=L.create_material_expression(mat,u.MaterialExpressionConstant);n.r=value;L.connect_material_property(n,'',prop)
    L.recompile_material(mat);save(mat);materials[name]=mat
mapping={'KVInhibitor_sight_scope':'Body','KVInhibitor_sight_scope_cables':'Cable','att_lens_scope':'Glass','KV_AdapterSteel':'Adapter'}
for key,part in json.loads((O/'authoring.json').read_text())['meshes'].items():
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opts.import_as_skeletal=False;opts.import_mesh=True;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False
    opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.auto_generate_collision=False;opts.static_mesh_import_data.generate_lightmap_u_vs=False;opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;opts.static_mesh_import_data.normal_generation_method=u.FBXNormalGenerationMethod.BUILT_IN
    mesh=imported(part['fbx'],part['name'],opts);slots=list(mesh.static_materials)
    for i,slot in enumerate(slots):
        name=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name));slot.material_interface=materials[mapping[name]];slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    # Commandlets do not instantiate StaticMeshEditorSubsystem. Their FBX
    # import options above already retain normals and select built-in tangents.
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    if editor:
        settings=editor.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=False;editor.set_lod_build_settings(mesh,0,settings)
    for name,p in part['sockets'].items():
        socket=mesh.find_socket(name)
        if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
        socket.set_editor_property('relative_location',u.Vector(*p))
    E.set_metadata_tag(mesh,'Source','Selected SVCH package: KV Inhibitor / other\\sight_scope.smd. Real model number unconfirmed. Magnification is configured by the gameplay optic variant.')
    save(mesh)
icon=imported(O/'optic_kv_scope_4x.png','optic_kv_scope_4x',root='/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms')
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);icon.set_editor_property('srgb',True);icon.set_editor_property('never_stream',True)
E.set_metadata_tag(icon,'Icon.SourceRecipe',str(O/'icon_generation.json'));E.set_metadata_tag(icon,'Icon.Revision','KVScopeUniversal20261019');save(icon)
receipt['complete']=True;record();print('KV_SCOPE_ASSETS_SAVED',len(receipt['saved']),flush=True)
