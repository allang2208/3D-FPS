"""Save only the two fitted magazine meshes and their extended-shell material."""
import unreal as u,json,gzip,hashlib
from pathlib import Path
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve()
ROOT='/Game/Weapons/SVCH/Replacement20261018/MagazineSeat20261019'
SOURCE=O.parent/'Download/Extracted/Original/Native/KVInhibitor'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'complete':False,'saved':[],'skeletal_mesh_modified':False,'V9_modified':False}
if (O/'assets_receipt.json').exists():receipt=json.loads((O/'assets_receipt.json').read_text())
dirty={x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    if a.get_path_name() not in receipt['saved']:receipt['saved'].append(a.get_path_name())
    (O/'assets_receipt.json').write_text(json.dumps(receipt,indent=2))
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing '+p)
    return a
def ensure_new(p):
    if p in dirty:raise RuntimeError('Preserve unsaved asset '+p)
    if E.does_asset_exist(p) and p not in receipt.get('created_in_failed_pie_attempt',[]) and not any(n.split('.')[0]==p for n in receipt['saved']):raise RuntimeError('Preserve unowned asset '+p)
matpath=ROOT+'/M_SVCH_ExtendedMagazine';ensure_new(matpath)
if any(n.split('.')[0]==matpath for n in receipt['saved']):mat=load(matpath)
else:
    mat=load(matpath) if E.does_asset_exist(matpath) else A.create_asset('M_SVCH_ExtendedMagazine',ROOT,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    for kind in ('color','normal'):
        name='T_SVCH_ExtendedMagazine_'+('BC' if kind=='color' else 'N');p=ROOT+'/'+name;ensure_new(p)
        if not E.does_asset_exist(p):
            task=u.AssetImportTask();task.filename=str(SOURCE/('KVInhibitor_mag_extended'+('' if kind=='color' else '_n')+'.png'));task.destination_path=ROOT;task.destination_name=name;task.automated=True;task.save=False;A.import_asset_tasks([task])
        tex=load(p);tex.set_editor_property('srgb',kind=='color');tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT if kind=='color' else u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON if kind=='color' else u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP)
        if kind=='normal':tex.set_editor_property('flip_green_channel',False)
        save(tex);n=L.create_material_expression(mat,u.MaterialExpressionTextureSample);n.texture=tex;n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='color' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL
        L.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR if kind=='color' else u.MaterialProperty.MP_NORMAL)
    for value,prop in [(.45,u.MaterialProperty.MP_ROUGHNESS),(0.,u.MaterialProperty.MP_METALLIC)]:
        n=L.create_material_expression(mat,u.MaterialExpressionConstant);n.r=value;L.connect_material_property(n,'',prop)
    L.recompile_material(mat);save(mat)
donor=load('/Game/Weapons/SVCH/Replacement20261018/RealSights20261019/SK_SVCH_RealFoldingSights')
materials={str(s.material_slot_name):s.material_interface for s in donor.materials};materials['KVInhibitor_mag_extended']=mat
readback={}
for kind in ('Magazine10','Magazine20'):
    name='SM_SVCH_'+kind;p=ROOT+'/'+name;ensure_new(p)
    if not E.does_asset_exist(p):
        opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opts.import_as_skeletal=False;opts.import_mesh=True;opts.import_animations=False;opts.import_materials=False;opts.import_textures=False
        opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.auto_generate_collision=False;opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=u.AssetImportTask();task.filename=str(O/(name+'.fbx'));task.destination_path=ROOT;task.destination_name=name;task.automated=True;task.save=False;task.options=opts;task.factory=u.FbxFactory();A.import_asset_tasks([task])
    mesh=load(p);slots=list(mesh.static_materials)
    for i,s in enumerate(slots):
        key=str(s.material_slot_name).removesuffix('.001');s.material_interface=materials[key];slots[i]=s
    mesh.set_editor_property('static_materials',slots);save(mesh)
    dm=u.DynamicMesh();result=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if u.GeometryScriptOutcomePins.SUCCESS not in result:raise RuntimeError('Saved static mesh unavailable '+p)
    _,vs,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False);vs=u.GeometryScript_List.convert_vector_list_to_array(vs)
    readback[kind]={'path':mesh.get_path_name(),'positions':[[v.x,v.y,v.z] for v in vs],'materials':[str(s.material_slot_name) for s in slots]}
with gzip.open(O/'installed_geometry.json.gz','wt') as f:json.dump(readback,f,separators=(',',':'))
receipt['complete']=True;(O/'assets_receipt.json').write_text(json.dumps(receipt,indent=2));print('SVCH_MAGAZINE_ASSETS_SAVED',flush=True)
