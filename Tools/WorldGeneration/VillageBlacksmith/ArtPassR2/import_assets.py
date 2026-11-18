"""Fresh revision import: PBR, three source LODs and structural simple collision."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ArtPassR2'
DEST='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
def get(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save '+obj.get_path_name())
def node(mat,kind):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
def link(a,out,b,pin):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material pin '+pin)
def prop(a,out,mat,key):L.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+key))
def scalar(mat,value):n=node(mat,'Constant');n.r=value;return n
def vector(mat,value):n=node(mat,'Constant3Vector');n.constant=u.LinearColor(*value,1);return n
def fresh_mat(name):
    path=DEST+'/Materials/'+name
    m=get(path) if E.does_asset_exist(path) else A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    m.set_editor_property('used_with_instanced_static_meshes',True)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    return m
def sample(mat,texture,kind='COLOR',uv=None):
    n=node(mat,'TextureSample');n.texture=texture;n.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind)
    if uv:link(uv,'',n,'UVs')
    return n
def finish(m):L.recompile_material(m);save(m);return m
textures={}
for source in sorted((OUT/'Textures').glob('*.png')):
    if source.stem.endswith('review'):continue
    name='T_VillageR2_'+source.stem;path=DEST+'/Textures/'+name
    if E.does_asset_exist(path):tex=get(path)
    else:
        t=u.AssetImportTask();t.filename=str(source);t.destination_path=DEST+'/Textures';t.destination_name=name;t.automated=True;t.replace_existing=False
        A.import_asset_tasks([t]);tex=get(path)
    tex.srgb=source.stem.endswith('_Color');tex.max_texture_size=2048
    tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if 'NormalDX' in source.stem else (u.TextureCompressionSettings.TC_DEFAULT if tex.srgb else u.TextureCompressionSettings.TC_MASKS)
    if 'NormalDX' in source.stem:tex.flip_green_channel=False
    save(tex);textures[source.stem]=tex
chapel='/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelTimber_'
wood=[get(chapel+s) for s in ['Color','NormalDX','ARH']]
def woodmat(name,paint=None):
    m=fresh_mat(name);c=sample(m,wood[0]);n=sample(m,wood[1],'NORMAL');r=sample(m,wood[2],'MASKS')
    tone=node(m,'Multiply');link(c,'RGB',tone,'A');link(vector(m,(.87,.85,.81)),'',tone,'B');base=tone
    if paint:
        uv=node(m,'TextureCoordinate');uv.coordinate_index=1;mask=sample(m,textures[paint+'_Paint'],'MASKS',uv)
        blend=node(m,'LinearInterpolate');link(tone,'',blend,'A');link(vector(m,(.52,.42,.26)),'',blend,'B');link(mask,'R',blend,'Alpha');base=blend
    prop(base,'',m,'BASE_COLOR');prop(n,'RGB',m,'NORMAL');prop(r,'G',m,'ROUGHNESS');prop(r,'R',m,'AMBIENT_OCCLUSION')
    return finish(m)
def mapped(name,prefix,tint=None):
    m=fresh_mat(name);c=sample(m,textures[prefix+'_Color']);n=sample(m,textures[prefix+'_NormalDX'],'NORMAL');p=sample(m,textures[prefix+'_ORM'],'MASKS')
    if tint:
        mul=node(m,'Multiply');link(c,'RGB',mul,'A');link(vector(m,tint),'',mul,'B');prop(mul,'',m,'BASE_COLOR')
    else:prop(c,'RGB',m,'BASE_COLOR')
    prop(n,'RGB',m,'NORMAL');prop(p,'R',m,'AMBIENT_OCCLUSION');prop(p,'G',m,'ROUGHNESS');prop(p,'B',m,'METALLIC');return finish(m)
mats={'Oak':woodmat('M_VillageR2_Oak'),'Endgrain':mapped('M_VillageR2_Endgrain','Endgrain'),
 'Linen':mapped('M_VillageR2_Linen','Linen'),'Blanket':mapped('M_VillageR2_Blanket','Linen',(.48,.42,.32)),
 'Sign':woodmat('M_VillageR2_BlacksmithSign','BlacksmithSign'),'Closed':woodmat('M_VillageR2_ClosedPlaque','ClosedPlaque'),
 'Iron':get('/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron')}
# Same actual grey 01A stone used by the chapel's capstones. No RVT/ground projection.
m=fresh_mat('M_VillageR2_HearthStone');prefix='/Game/UnrealNormandy/Textures/T_StoneSurface_01A_'
c=sample(m,get(prefix+'BaseColor'));n=sample(m,get(prefix+'Normal'),'NORMAL');p=sample(m,get(prefix+'RHAOM'),'MASKS')
prop(c,'RGB',m,'BASE_COLOR');prop(n,'RGB',m,'NORMAL');prop(p,'R',m,'ROUGHNESS');prop(p,'B',m,'AMBIENT_OCCLUSION');mats['Stone']=finish(m)
report={'materials':{k:v.get_path_name() for k,v in mats.items()},'meshes':[],'gameplay_started':False}
for row in json.loads((OUT/'model-manifest.json').read_text())['assets']:
    name=row['name'];path=DEST+'/Meshes/'+name
    existing=E.does_asset_exist(path)
    if existing and name!='SM_VillageOakTable' and E.get_metadata_tag(get(path),'VillageArtOwner')!='VillageBlacksmithArtR2_20261117':
        raise RuntimeError('Unexpected pre-existing revision '+path)
    t=u.AssetImportTask();t.filename=row['lods'][0]['file'];t.destination_path=DEST+'/Meshes';t.destination_name=name;t.automated=True;t.replace_existing=False;t.save=False
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;t.options=opt;t.factory=u.FbxFactory()
    # The first table import reached collision setup before failing on the UE 5.8 struct setter.
    # Resume its in-memory geometry; never replace-import the mesh (which can rescale it).
    if not existing:A.import_asset_tasks([t])
    mesh=get(path)
    for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,mats[str(slot.material_slot_name)])
    for lod in row['lods'][1:]:
        if S.get_lod_count(mesh)<=lod['level'] and S.import_lod(mesh,lod['level'],lod['file'])!=lod['level']:raise RuntimeError('LOD import '+name)
    S.set_lod_screen_sizes(mesh,[1.,.25,.08])
    # Retain dynamic-lighting raster LODs; no hidden Nanite fallback reduction.
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=False;mesh.set_editor_property('nanite_settings',settings)
    body=mesh.get_editor_property('body_setup');agg=body.get_editor_property('agg_geom');boxes=[]
    for center,size,yaw in row['colliders']:
        b=u.KBoxElem();b.set_editor_property('center',u.Vector(*center));b.set_editor_property('rotation',u.Rotator(yaw=yaw))
        for axis,value in zip(('x','y','z'),size):b.set_editor_property(axis,value)
        boxes.append(b)
    if not boxes and name.endswith('AbandonedTimber'):
        # Low loose debris gets a shallow bound, not complex-per-triangle character collision.
        bounds=mesh.get_bounding_box();b=u.KBoxElem();b.set_editor_property('center',(bounds.min+bounds.max)*.5);span=bounds.max-bounds.min
        for axis,value in zip(('x','y','z'),(span.x,span.y,span.z)):b.set_editor_property(axis,value)
        boxes.append(b)
    agg.set_editor_property('box_elems',boxes);agg.set_editor_property('convex_elems',[]);body.set_editor_property('agg_geom',agg);body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    slots=list(mesh.get_editor_property('static_materials'))
    for slot in slots:
        info=slot.get_editor_property('uv_channel_data');info.set_editor_property('bOverrideDensities',True);info.set_editor_property('LocalUVDensities',[100.,100.,0.,0.])
    mesh.set_editor_property('static_materials',slots)
    E.set_metadata_tag(mesh,'VillageArtOwner','VillageBlacksmithArtR2_20261117');save(mesh)
    report['meshes'].append({'path':path,'lods':S.get_lod_count(mesh),'simple_boxes':len(boxes),'source_triangles':row['lods'][0]['triangles']})
    (OUT/'assets-saved.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('VILLAGE_ART_R2_ASSETS_SAVED '+str(len(report['meshes'])))
