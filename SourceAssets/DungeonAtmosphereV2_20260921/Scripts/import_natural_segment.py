"""Install the scoped natural-history segment through the project UE bridge."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
SOURCE=ROOT/'Authored/NaturalPass';BASE='/Game/Dungeons/AtmosphereV2';OUT=BASE+'/NaturalPass'
TARGET='/Game/GameMaps/L_Dungeon_Prototype'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay is active; current session preserved')
if UE.get_editor_world().get_path_name().split('.')[0]!=TARGET:raise RuntimeError('Dungeon target is not loaded; current editor preserved')
manifest=json.loads((SOURCE/'geometry-manifest.json').read_text());recipes=json.loads((SOURCE/'material-manifest.json').read_text())
RESUME_DECALS=globals().get('NATURAL_RESUME_DECALS',False)
receipt={'map':TARGET,'history':manifest['history'],'geometry':manifest['stats'],'materials':{},'meshes':{},'saved':False,'tests_run':False,'visual_acceptance':'pending user review'}
if RESUME_DECALS:receipt=json.loads((ROOT/'Receipts/natural-segment-import.json').read_text())
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Unable to save '+obj.get_path_name())
def write():
    (ROOT/'Receipts/natural-segment-import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def texture(name,file,channel):
    if globals().get('NATURAL_SKIP_TEXTURE_IMPORT',False):
        existing=u.load_asset(OUT+'/Textures/T_'+name)
        if existing:return existing
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=OUT+'/Textures';task.destination_name='T_'+name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;A.import_asset_tasks([task])
    tex=u.load_asset(OUT+'/Textures/T_'+name)
    if not tex:raise RuntimeError('Texture import failed: '+name)
    tex.set_editor_property('srgb',channel=='BaseColor')
    if channel=='Normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    elif channel!='BaseColor':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(tex);return tex
def expr(mat,cls):return L.create_material_expression(mat,cls)
def wire(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,'' if pin=='Input' else pin):raise RuntimeError('Material wire failed: '+pin)
def output(mat,n,prop,pin=''):
    if not L.connect_material_property(n,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output failed: '+prop)
for name,maps in ([] if RESUME_DECALS else recipes.items()):
    tex={channel:texture(name+'_'+channel,file,channel) for channel,file in maps.items()}
    path=OUT+'/Materials/M_'+name;mat=u.load_asset(path)
    if not mat:
        mat=A.create_asset('M_'+name,OUT+'/Materials',u.Material,u.MaterialFactoryNew())
        for channel,prop in [('BaseColor','BASE_COLOR'),('Roughness','ROUGHNESS'),('Normal','NORMAL')]:
            n=expr(mat,u.MaterialExpressionTextureSample);n.texture=tex[channel]
            n.sampler_type={'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'Roughness':u.MaterialSamplerType.SAMPLERTYPE_MASKS,'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL}[channel]
            output(mat,n,prop,'R' if channel=='Roughness' else '')
        L.layout_material_expressions(mat);L.recompile_material(mat);save(mat)
    receipt['materials'][name]=path
write()

actors={actor.get_actor_label():actor for actor in AA.get_all_level_actors()}
previous={}
for entry in ([] if RESUME_DECALS else manifest['objects']):
    name=entry['name'];path=OUT+'/Structure/'+name
    task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=OUT+'/Structure';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
    options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Mesh import failed: '+name)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=str(slot.get_editor_property('material_slot_name')).removeprefix('V2_')
        material_path=receipt['materials'].get(key)
        if not material_path:
            material_path=BASE+('/TilePolish' if key in ('TileGlazeAtlas','TileMortar','TileCeramicCore') else '')+'/Materials/M_'+key
        mat=u.load_asset(material_path)
        if not mat:raise RuntimeError('Unknown material slot '+key)
        mesh.set_material(i,mat)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=True;mesh.set_editor_property('nanite_settings',settings);save(mesh)
    label=entry['actor_label'];actor=actors.get(label)
    if not actor and entry['replace_actor_mesh']:raise RuntimeError('Expected owned actor missing: '+label)
    if not actor:
        actor=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector());actor.set_actor_label(label)
        actor.set_folder_path('DungeonAtmosphereV2/SurfaceHistory')
    c=actor.get_component_by_class(u.StaticMeshComponent)
    previous[label]=c.static_mesh.get_path_name() if c.static_mesh else None
    c.set_static_mesh(mesh);c.set_editor_property('override_materials',[])
    c.set_collision_profile_name('BlockAll' if entry['collision'] else 'NoCollision')
    c.set_editor_property('cast_shadow',True)
    receipt['meshes'][name]={'path':path,'source':entry['fbx'],'actor':label,'collision':entry['collision'],'previous_mesh':previous[label]};write()

def decal_material(name,mask,color,roughness):
    tex=texture(mask,SOURCE/'Textures'/(mask+'.png'),'Opacity')
    path=OUT+'/Materials/M_'+name;mat=u.load_asset(path)
    if mat:return mat
    mat=A.create_asset('M_'+name,OUT+'/Materials',u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL);mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    # UE 5.8 DeferredDecal.usf uses local Z/Y for default UV. Remap to image
    # horizontal/vertical coordinates so gravity streaks run DOWN the wall.
    uv=expr(mat,u.MaterialExpressionTextureCoordinate)
    x=expr(mat,u.MaterialExpressionComponentMask);y=expr(mat,u.MaterialExpressionComponentMask)
    for mask,axis in [(x,'r'),(y,'g')]:
        for channel in ('r','g','b','a'):mask.set_editor_property(channel,channel==axis)
        wire(uv,mask,'Input')
    invert=expr(mat,u.MaterialExpressionOneMinus);wire(x,invert,'Input')
    append=expr(mat,u.MaterialExpressionAppendVector);wire(y,append,'A');wire(invert,append,'B')
    sample=expr(mat,u.MaterialExpressionTextureSample);sample.texture=tex;sample.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS;wire(append,sample,'UVs')
    output(mat,sample,'OPACITY','R')
    n=expr(mat,u.MaterialExpressionConstant3Vector);n.constant=u.LinearColor(*color,1);output(mat,n,'BASE_COLOR')
    n=expr(mat,u.MaterialExpressionConstant);n.r=roughness;output(mat,n,'ROUGHNESS')
    L.layout_material_expressions(mat);L.recompile_material(mat);save(mat);return mat

decals={
    'Leak':decal_material('NaturalLeakVertical','NaturalLeak_Opacity',(.042,.034,.022),.27),
    'Wet':decal_material('NaturalWet','NaturalWet_Opacity',(.032,.038,.031),.15),
    'Dust':decal_material('NaturalDust','NaturalDust_Opacity',(.24,.22,.17),.96),
    'Silt':decal_material('NaturalSilt','NaturalDust_Opacity',(.074,.067,.045),.72)}
disabled=[]
for actor in AA.get_all_level_actors():
    label=actor.get_actor_label()
    if label in ('DGN_AV2_Damp_0','DGN_AV2_TilePolish_Leak_0','DGN_AV2_TilePolish_Leak_1','DGN_AV2_TilePolish_Leak_2'):
        actor.get_component_by_class(u.DecalComponent).set_visibility(False);disabled.append(label)
    if label.startswith('DGN_AV2_Natural_Decal_'):AA.destroy_actor(actor)
placements=[('Leak',[380,-385,192],u.Rotator(pitch=0,yaw=-90,roll=0),[5,85,188]),
    ('Wet',[380,-364,1.5],u.Rotator(pitch=-90,yaw=0,roll=0),[5,32,73]),
    ('Silt',[380,-376,1.5],u.Rotator(pitch=-90,yaw=0,roll=0),[5,22,77]),
    ('Dust',[150,-43,1.5],u.Rotator(pitch=-90,yaw=0,roll=0),[5,30,60])]
for name,pos,rot,size in placements:
    actor=AA.spawn_actor_from_class(u.DecalActor,u.Vector(*pos),rot);actor.set_actor_label('DGN_AV2_Natural_Decal_'+name)
    actor.set_folder_path('DungeonAtmosphereV2/SurfaceHistory');c=actor.get_component_by_class(u.DecalComponent)
    c.set_decal_material(decals[name]);c.set_editor_property('decal_size',u.Vector(*size));c.set_editor_property('sort_order',4 if name=='Leak' else 3)
restore_file=SOURCE/'previous-ue-references.json'
if RESUME_DECALS:
    previous={entry['actor_label']:BASE+'/Structure/'+entry['actor_label'].replace('DGN_AV2_','SM_V2_') for entry in manifest['objects'] if entry['replace_actor_mesh']}
if not restore_file.exists():restore_file.write_text(json.dumps({'meshes':previous,'hidden_decals':disabled},indent=2),encoding='utf-8')
if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():raise RuntimeError('Natural segment map save failed')
receipt.update({'saved':True,'disabled_previous_decals':disabled,'localized_decals':[p[0] for p in placements]});write()
print('NATURAL_SEGMENT_SAVED: entrance north/south tile spans, fracture-derived floor fragments, repair skim, gravity-oriented leaks')
