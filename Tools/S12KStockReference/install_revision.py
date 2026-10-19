"""Authorized final save of this task's stock mesh, two textures and UI icon."""
import unreal as u,json,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/S12KStockReference20261018';D='/Game/Weapons/Saiga12K/SpecialStock20261018'
F=json.loads((O/'Authoring/stock.json').read_text());bake=json.loads((O/'Receipts/bake.json').read_text())
if not bake['complete'] or bake['source_sha256']!=hashlib.sha256((O/'Authoring/stock.json').read_bytes()).hexdigest():raise RuntimeError('Bake source mismatch')
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;LS=u.GeometryScript_List;ED=u.GeometryScript_MeshEdits
OWNED=set(json.loads((P/'SourceAssets/Saiga12KSpecialStock20261018/Receipts/surface-install.json').read_text())['saved'])
R={'complete':False,'saved':[],'runtime_tested':False,'display_name':'S12K撞火枪托'}
def save(a):
    allowed={D+'/SM_Saiga12K_SpecialStock',D+'/Textures/T_Saiga12K_SpecialStock_N',D+'/Textures/T_Saiga12K_SpecialStock_Mask'}
    if a.get_path_name().split('.')[0] not in allowed:raise RuntimeError('Outside authorized final-save scope: '+a.get_path_name())
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    if a.get_path_name() not in R['saved']:R['saved'].append(a.get_path_name())
    (O/'Receipts/surface-install.json').write_text(json.dumps(R,indent=2),encoding='utf8');return a
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing '+p)
    return a
def fresh(p):
    if E.does_asset_exist(p):raise RuntimeError('Preserve existing package '+p)
tex={}
for suffix in ('N','Mask'):
    name='T_Saiga12K_SpecialStock_'+suffix
    if D+'/Textures/'+name+'.'+name not in OWNED:raise RuntimeError('Refresh requires owned texture receipt')
    t=u.AssetImportTask();t.filename=str(O/('Textures/'+name+'.png'));t.destination_path=D+'/Textures';t.destination_name=name;t.automated=True;t.replace_existing=True;t.replace_existing_settings=False;t.save=False;AT.import_asset_tasks([t]);a=load(D+'/Textures/'+name)
    a.srgb=False;a.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if suffix=='N' else u.TextureCompressionSettings.TC_MASKS;a.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;a.never_stream=False
    if suffix=='N':a.flip_green_channel=True
    tex[suffix]=save(a)
specs={'Polymer':('Stock',(.019,.019,.018),0.,.49),'Steel':('Body',(.034,.035,.037),1.,.38),'Rubber':('StockPad',(.009,.010,.011),0.,.66),'Inset':('Magazine',(.012,.014,.016),0.,.54),'Bronze':(None,(.16,.115,.068),1.,.38),'Letter':('Stock',(.24,.25,.26),.25,.48)}
mats=[]
for slot in F['slot_names']:
    name='MI_Saiga12K_Stock_'+slot
    if D+'/Materials/'+name+'.'+name not in OWNED:raise RuntimeError('Missing previously saved stock material '+name)
    mats.append(load(D+'/Materials/'+name))
path=D+'/SM_Saiga12K_SpecialStock'
if path+'.SM_Saiga12K_SpecialStock' not in OWNED:raise RuntimeError('Refresh requires owned mesh receipt')
dm=u.DynamicMesh();u.GeometryScript_UVs.set_num_uv_sets(dm,2)
_,ids=ED.add_vertices_to_mesh(dm,LS.convert_array_to_vector_list([u.Vector(*F['positions'][v]) for face in F['triangles'] for v in face]),True);ids=list(LS.convert_index_list_to_array(ids))
_,tids=ED.add_triangles_to_mesh(dm,LS.convert_array_to_triangle_list([u.IntVector(*ids[i:i+3]) for i in range(0,len(ids),3)]),0,True)
for fi,tid in enumerate(LS.convert_index_list_to_array(tids)):
    if tid<0:raise RuntimeError('Uncreated triangle '+str(fi))
    u.GeometryScript_Materials.set_triangle_material_id(dm,tid,F['parts'][fi],True)
    ns=[u.Vector(*v) for v in F['normals'][fi]];u.GeometryScript_Normals.set_mesh_triangle_normals(dm,tid,u.GeometryScriptTriangle(vector0=ns[0],vector1=ns[1],vector2=ns[2]),True)
    for ch in (0,1):
        uv=[u.Vector2D(*v) for v in F['uv'+str(ch)][fi]];u.GeometryScript_UVs.set_mesh_triangle_u_vs(dm,ch,tid,u.GeometryScriptUVTriangle(uv0=uv[0],uv1=uv[1],uv2=uv[2]),True)
mesh=load(path)
_,status=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,mesh,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh creation failed')
mesh.set_editor_property('static_materials',[u.StaticMaterial(material_interface=m,material_slot_name='Saiga12K_Stock_'+s) for s,m in zip(F['slot_names'],mats)])
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
opts=u.StaticMeshReductionOptions();opts.auto_compute_lod_screen_size=False;opts.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1.,1.),(.5,.18),(.25,.075))];SM.set_lods(mesh,opts)
for li in range(SM.get_lod_count(mesh)):
    bs=SM.get_lod_build_settings(mesh,li);bs.recompute_normals=False;bs.recompute_tangents=True;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True;bs.remove_degenerates=False;SM.set_lod_build_settings(mesh,li,bs)
E.set_metadata_tag(mesh,'SaigaStockOrientation','Nonfunctional tactical exterior; current virtual visible stock neck; WPN_root scale .01')
E.set_metadata_tag(mesh,'SaigaStockSource','SourceAssets/S12KStockReference20261018/Authoring/Saiga12K_SpecialStock_Editable.blend')
save(mesh);R.update(complete=True,source_sha256=bake['source_sha256'],mesh=mesh.get_path_name(),triangles=len(F['triangles']),bindings={str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials});(O/'Receipts/surface-install.json').write_text(json.dumps(R,indent=2),encoding='utf8');print('SAIGA_STOCK_SURFACE_SAVED',len(R['saved']),flush=True)

exec(compile((P/'Tools/S12KStockReference/install_icon.py').read_text(),str(P/'Tools/S12KStockReference/install_icon.py'),'exec'),{'__name__':'__main__'})
