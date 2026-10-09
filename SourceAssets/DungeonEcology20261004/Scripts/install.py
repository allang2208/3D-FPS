"""Import this batch and save three subject maps and the full ecology line.
No PIE, screenshots, layout generation or production pool registration.
"""
from pathlib import Path
import json,re,hashlib,math,runpy
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
CFG=json.loads((ROOT/'Config/room.json').read_text('utf8'));MAN=json.loads((ROOT/'Authored/manifest.json').read_text('utf8'));BASE=CFG['ue_base']
if CFG.get('phase')=='production' and not globals().get('ECOLOGY_ASSETS_ONLY',False):
    raise RuntimeError('Subject map installation retired. Use Production20261005/Scripts/install_production.py; mesh-only authoring may explicitly set ECOLOGY_ASSETS_ONLY.')
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ML=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not globals().get('ECOLOGY_EDITOR_BATCH',False):raise RuntimeError('Use the background or guarded existing-editor entry')
RP=ROOT/'Receipts/install-v7.json'
report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},materials=[],maps={},saved_assets=[])
report.update(stage='importing',revision=CFG['revision'],tests_run=False,rendered=False,game_run=False,editor_opened=False,random_pool_registered=False)
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def asset(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Required asset unavailable: '+path)
    return a
def save(a):
    if not a.get_path_name().startswith(BASE+'/'):raise RuntimeError('Save outside ecology namespace')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed: '+a.get_path_name())
    if a.get_path_name() not in report['saved_assets']:report['saved_assets'].append(a.get_path_name())
    record()
def node(m,kind,**props):
    n=ML.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def const(m,value):return node(m,'Constant',r=value)
def color(m,rgb):return node(m,'Constant3Vector',constant=u.LinearColor(*rgb,1))
def wire(a,b,pin,out=''):
    if not ML.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection failed '+pin)
def custom(m,code,inputs,size=1):
    n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    pins=[]
    for k in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',k);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for k,v in inputs.items():wire(v,n,k)
    return n
def tex(m,path,kind):
    return node(m,'TextureSampleParameter2D',parameter_name=kind,texture=asset(path),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='Packed' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
def surface(m,values):
    slab=node(m,'SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    names={str(s).replace(' ','').lower():str(s) for s in ML.get_material_expression_input_names(slab)}
    for prop,(n,out,pin) in values.items():
        if not ML.connect_material_property(n,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material property '+prop)
        wire(n,slab,names.get(pin.replace(' ','').lower(),pin),out)
    if not ML.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Front material')
def finish(m):
    errors=ML.recompile_material(m)
    if errors:raise RuntimeError('Material build failed '+str(errors))
    ML.layout_material_expressions(m);save(m)
def make(key):
    material_base=CFG.get('soil_material_base',CFG.get('mesh_base',BASE)) if key in ('SoilPot','SoilBed') else BASE+'/RefineV3' if key in ('JarGlass','JarGel','Leaf') else BASE
    name='M_Eco_'+key;path=material_base+'/Materials/'+name
    if E.does_asset_exist(path):return None
    m=AT.create_asset(name,material_base+'/Materials',u.Material,u.MaterialFactoryNew())
    m.set_editor_property('used_with_instanced_static_meshes',True)
    m.set_editor_property('used_with_nanite',key not in ('Glass','Water','JarGlass','JarGel','Leaf'))
    return m
texture_path=BASE+'/Textures/T_Eco_Labels_BaseColor'
if not E.does_asset_exist(texture_path):
    task=u.AssetImportTask();task.filename=str(ROOT/'Authored/T_Eco_Labels_BaseColor.png');task.destination_path=BASE+'/Textures';task.automated=True;task.save=False;task.replace_existing=False
    AT.import_asset_tasks([task]);t=asset(texture_path);t.set_editor_property('srgb',True);t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7);save(t)
normandy='/Game/UnrealNormandy/Textures/'
for key,prefix,albedo in [('Bark','T_LS_BlackAlderBark_00A','BaseColor'),('Soil','T_LC_GroundGrassSoil_00A','Albedo'),('Algae','T_LC_GroundMossy_00A','Albedo')]:
    m=make(key)
    if not m:continue
    bc=tex(m,normandy+prefix+'_'+albedo,'BaseColor');nm=tex(m,normandy+prefix+'_Normal','Normal');packed=tex(m,normandy+prefix+'_RHAOM','Packed')
    surface(m,{'BASE_COLOR':(bc,'RGB','BaseColor'),'NORMAL':(nm,'RGB','Normal'),'ROUGHNESS':(packed,'R','Roughness'),'METALLIC':(const(m,0),'','Metallic')})
    ML.connect_material_property(packed,'B',u.MaterialProperty.MP_AMBIENT_OCCLUSION);finish(m)
for key,rgb,rough,metal in [('Ceramic',(.54,.59,.51),.3,0),('Paper',(.52,.45,.29),.85,0),('DarkPlastic',(.016,.027,.024),.49,0),('Diffuser',(.45,.48,.4),.35,0),('Labels',None,.66,.05)]:
    m=make(key)
    if not m:continue
    bc=tex(m,texture_path,'BaseColor') if key=='Labels' else color(m,rgb)
    values={'BASE_COLOR':(bc,'RGB' if key=='Labels' else '','BaseColor'),'ROUGHNESS':(const(m,rough),'','Roughness'),'METALLIC':(const(m,metal),'','Metallic')}
    if key=='Diffuser':values['EMISSIVE_COLOR']=(color(m,(2.1,2.0,1.55)),'','EmissiveColor')
    surface(m,values);finish(m)
m=make('Glass')
if m:
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    f=node(m,'Fresnel');uv=node(m,'TextureCoordinate')
    rough=custom(m,'return .08+.06*pow(saturate(.5+.5*sin(UV.y*8+sin(UV.x*17))),6);',{'UV':uv})
    opacity=custom(m,'return .045+F*.22;',{'F':f})
    surface(m,{'BASE_COLOR':(color(m,(.57,.68,.61)),'','BaseColor'),'ROUGHNESS':(rough,'','Roughness'),'OPACITY':(opacity,'','Opacity'),'SPECULAR':(const(m,.5),'','Specular')});finish(m)
m=make('Water')
if m:
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    m.set_editor_property('two_sided',True);m.set_editor_property('screen_space_reflections',True)
    wp=node(m,'WorldPosition');time=node(m,'Time');f=node(m,'Fresnel')
    normal=custom(m,'float2 p=P.xy*.01; float a=dot(p,float2(2.3,1.4))-T*.9; float b=dot(p,float2(-5.1,3.7))+T*1.35; return normalize(float3(.034*cos(a)+.012*cos(b),.028*sin(a)+.018*sin(b),1));',{'P':wp,'T':time},3)
    opacity=custom(m,'return .32+F*.48;',{'F':f})
    surface(m,{'BASE_COLOR':(color(m,(.055,.105,.064)),'','BaseColor'),'NORMAL':(normal,'','Normal'),'ROUGHNESS':(const(m,.11),'','Roughness'),'SPECULAR':(const(m,.5),'','Specular'),'OPACITY':(opacity,'','Opacity')});finish(m)
for key,rgb,rough,opacity in [('JarGlass',(.69,.78,.67),.075,.13),('JarGel',(.30,.38,.16),.19,.27)]:
    m=make(key)
    if not m:continue
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    f=node(m,'Fresnel');op=custom(m,f'return {opacity}+F*.44;',{'F':f})
    surface(m,{'BASE_COLOR':(color(m,rgb),'','BaseColor'),'ROUGHNESS':(const(m,rough),'','Roughness'),'SPECULAR':(const(m,.5),'','Specular'),'OPACITY':(op,'','Opacity')});finish(m)
m=make('Leaf')
if m:
    m.set_editor_property('two_sided',True)
    surface(m,{'BASE_COLOR':(color(m,(.045,.125,.024)),'','BaseColor'),'ROUGHNESS':(const(m,.53),'','Roughness')});finish(m)
report['stage']='materials_saved';record()

# The existing excavated-soil scan supplies matching colour, normal, height and roughness.
# UV relief is bounded to millimetres; broad relief is authored in the mesh itself.
for key,ratio in [('SoilPot',.012),('SoilBed',.010)]:
    m=make(key)
    if not m:continue
    prefix=normandy+'T_LC_GroundSoilExcavated_00A_'
    uv=node(m,'TextureCoordinate');height=tex(m,prefix+'Height','Height')
    # This installed height texture uses TC_Masks. Linear Grayscale caused
    # both soil materials to fail SM6 compilation and render checkerboards.
    height.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    wire(uv,height,'UVs')
    offset=node(m,'BumpOffset',height_ratio=ratio,reference_plane=.5)
    wire(uv,offset,'Coordinate');wire(height,offset,'Height','R')
    bc=tex(m,prefix+'Albedo','BaseColor');nm=tex(m,prefix+'Normal','Normal');packed=tex(m,prefix+'RHAOM','Packed')
    for t in (bc,nm,packed):wire(offset,t,'UVs')
    wet=custom(m,'return C*float3(.53,.47,.39);',{'C':bc},3)
    rough=custom(m,'return clamp(R*.25+.66,.7,.95);',{'R':packed})
    surface(m,{'BASE_COLOR':(wet,'','BaseColor'),'NORMAL':(nm,'RGB','Normal'),'ROUGHNESS':(rough,'','Roughness'),'SPECULAR':(const(m,.23),'','Specular'),'METALLIC':(const(m,0),'','Metallic')})
    ML.connect_material_property(packed,'B',u.MaterialProperty.MP_AMBIENT_OCCLUSION);finish(m)

sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
meshitems={};roomitems={}
for item in MAN['objects']:
    path=item['asset'];name=item['name'];digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
    previous=report['meshes'].get(name);mesh=u.load_asset(path) if E.does_asset_exist(path) else None
    if mesh and not item.get('reused') and (not previous or previous.get('source_sha256')!=digest):raise RuntimeError('Preserve existing differing asset '+path)
    if item.get('reused') and not mesh:raise RuntimeError('Required retained asset unavailable '+path)
    if not mesh:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=name;task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=opts.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
        d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.one_convex_hull_per_ucx=True
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=opts;task.factory=u.FbxFactory();AT.import_asset_tasks([task]);mesh=asset(path)
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            k=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mesh.set_material(i,asset(item['materials'][k]))
        bs=sub.get_lod_build_settings(mesh,0);bs.set_editor_property('use_full_precision_u_vs',True);bs.set_editor_property('use_high_precision_tangent_basis',True);bs.set_editor_property('recompute_tangents',True);sub.set_lod_build_settings(mesh,0,bs)
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX if item['simple_collision_hulls'] else u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        n=mesh.get_editor_property('nanite_settings').copy();n.enabled=item['nanite'];n.explicit_tangents=True;n.generate_fallback=u.NaniteGenerateFallback.ENABLED
        n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;n.fallback_percent_triangles=1.;n.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',n)
        if item['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+name)
        report['meshes'][name]=dict(path=path,source_sha256=digest,source_triangles=item['triangles'],nanite=item['nanite'],collision=item['collision']);save(mesh)
    meshitems[name]=(mesh,item);roomitems.setdefault(item['room_id'],[]).append((mesh,item))
    u.log('ECOLOGY_ASSET_SAVED '+name)
report['stage']='assets_saved';record()

AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
def pos(p,off=(0,0,0)):return u.Vector((p[0]+off[0])*100,-(p[1]+off[1])*100,(p[2]+off[2])*100)
def tag(a,name,room='Environment'):
    a.set_actor_label('EcoSubject_'+name);a.set_editor_property('tags',[u.Name('Ecology.Subject'),u.Name(room)])
    a.set_folder_path('Ecology/'+room);return a
def static(mesh,p,off,name,room,collision=True,yaw=0,scale=None):
    a=AA.spawn_actor_from_class(u.StaticMeshActor,pos(p,off),u.Rotator(pitch=0,yaw=-yaw,roll=0));tag(a,name,room)
    c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(u.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    if scale is not None:a.set_actor_scale3d(u.Vector(scale,scale,scale))
    return a
def cap(x,name):
    a=static(asset('/Engine/BasicShapes/Cube'),[x,0,1.4],[0,0,0],name,'PreviewCaps')
    a.set_actor_scale3d(u.Vector(.14,3,2.8));a.static_mesh_component.set_material(0,asset('/Game/Dungeons/SeamMetal20260923/Materials/MI_PaintedSteel'))
def wall_position(mesh,p,yaw,mount):
    if not mount:return list(p)
    bounds=mesh.get_bounds();axis=mount['axis'];side=mount['side'];ang=math.radians(yaw);co,si=math.cos(ang),math.sin(ang);projected=[]
    for sx in (-1,1):
        for sy in (-1,1):
            x=(bounds.origin.x+sx*bounds.box_extent.x)/100;y=-(bounds.origin.y+sy*bounds.box_extent.y)/100
            projected.append((x*co-y*si,x*si+y*co)[axis])
    result=list(p);result[axis]=mount['plane']-side*mount['gap_m']-(max(projected) if side>0 else min(projected))
    return result
def spawn_container(c,r,off):
    reference=c['body']
    if c['body'].endswith('RecordsFrame'):reference=BASE+'/Meshes/SM_Eco_RecordsCarcass'
    if 'Tools' in c['container_id'] and c['container_id'].endswith('.Drawer'):
        reference=next(p['body'] for p in r['containers'] if p['container_id']==c['container_id'].rsplit('.',1)[0]+'.Cabinet')
    c['position_m']=wall_position(asset(reference),c['position_m'],c['yaw_blender'],c.get('wall_mount'))
    a=AA.spawn_actor_from_class(u.ColdSteelSceneContainer,pos(c['position_m'],off),u.Rotator(pitch=0,yaw=-c['yaw_blender'],roll=0));tag(a,c['container_id'],r['id'])
    a.set_editor_property('container_id','EcologySubject.'+c['container_id']);a.set_editor_property('caption',c['caption']);a.set_editor_property('storage_pages',c.get('storage_pages',1))
    a.set_editor_property('opened_yaw',c.get('opened_yaw',100));a.set_editor_property('opened_roll',c.get('opened_roll',108));a.set_editor_property('initial_open_fraction',0.)
    a.set_editor_property('opening_motion',getattr(u.ColdSteelContainerMotion,c['opening_motion'].upper()))
    if 'drawer_travel' in c:a.set_editor_property('drawer_travel',u.Vector(*c['drawer_travel']))
    a.body.set_mobility(u.ComponentMobility.MOVABLE);a.body.set_static_mesh(asset(c['body']));a.door.set_static_mesh(asset(c['door']))
    a.body.set_collision_profile_name('BlockAll');a.door.set_collision_profile_name('NoCollision');a.door_hinge.set_relative_location(u.Vector(*c['hinge']),False,False)
    return a
def projected_box(mesh,p,yaw):
    b=mesh.get_bounds();co,si=math.cos(math.radians(yaw)),math.sin(math.radians(yaw));points=[]
    for sx in (-1,1):
        for sy in (-1,1):
            x=(b.origin.x+sx*b.box_extent.x)/100;y=-(b.origin.y+sy*b.box_extent.y)/100
            for sz in (-1,1):points.append([p[0]+x*co-y*si,p[1]+x*si+y*co,p[2]+(b.origin.z+sz*b.box_extent.z)/100])
    return [min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]
def overlaps(a,b,gap=.10):return all(a[0][i]<b[1][i]+gap and a[1][i]>b[0][i]-gap for i in range(3))
def place_wall_groups(r):
    occupied=[]
    for c in r.get('wall_column_keepout_m',[]):occupied.append(([c['center'][i]-c['extent'][i] for i in range(3)],[c['center'][i]+c['extent'][i] for i in range(3)]))
    for c in r.get('furniture_keepout_m',[]):occupied.append(([c['center'][i]-c['extent'][i] for i in range(3)],[c['center'][i]+c['extent'][i] for i in range(3)]))
    for group in r['container_groups']:
        prefix=r['id']+'.'+group['id'];children=[c for c in r['containers'] if c['container_id']==prefix or c['container_id'].startswith(prefix+'.')]
        if not children:continue
        first=children[0];mount=first.get('wall_mount')
        if not mount:continue
        ref=BASE+'/Meshes/SM_Eco_RecordsCarcass' if first['body'].endswith('RecordsFrame') else first['body'];mesh=asset(ref)
        anchor=wall_position(mesh,first['position_m'],first['yaw_blender'],mount);tangent=1-mount['axis'];chosen=None
        for delta in [0]+[sign*i*.2 for i in range(1,9) for sign in (-1,1)]:
            candidate=anchor[:];candidate[tangent]+=delta;bounds=projected_box(mesh,candidate,first['yaw_blender'])
            if bounds[0][tangent]<-r['size'][tangent]/2+.35 or bounds[1][tangent]>r['size'][tangent]/2-.35:continue
            if any(overlaps(bounds,other,.12) for other in occupied):continue
            chosen=candidate;occupied.append(bounds);break
        if chosen is None:raise RuntimeError('No column-free wall bay for '+prefix)
        shift=[chosen[i]-first['position_m'][i] for i in range(3)];old=first['position_m'][:]
        for c in children:c['position_m']=[c['position_m'][i]+shift[i] for i in range(3)]
        for part in r['parts']:
            if part['mesh'].endswith('RecordsCarcass') and abs(part['position'][0]-old[0])<.05 and abs(part['position'][1]-old[1])<.6:part['position']=[part['position'][i]+shift[i] for i in range(3)]
        group['position_m']=chosen;group['column_clearance_m']=.12

def botanical_transform(p):
    scale=p['height_m']/p['source_height_m'];root=p['root_anchor_blender_m'];co,si=math.cos(math.radians(p['yaw'])),math.sin(math.radians(p['yaw']))
    return [p['position'][0]-(root[0]*co-root[1]*si)*scale,p['position'][1]-(root[0]*si+root[1]*co)*scale,p['position'][2]-root[2]*scale-p.get('bury_m',0)],scale

def botanical_tree(p,r,off,label):
    mesh=asset(p['mesh']);pp,scale=botanical_transform(p)
    a=static(mesh,pp,off,r['id']+'_'+label,r['id'],True,p['yaw'],scale)
    # Ecology-only instances retain the stock textures and LODs; indoor wind is disabled.
    for i,slot in enumerate(mesh.static_materials):
        source=slot.material_interface;name='MI_EcoTree_'+hashlib.sha1(source.get_path_name().encode()).hexdigest()[:10];tree_base=CFG.get('tree_material_base',CFG['mesh_base']);path=tree_base+'/Materials/'+name
        mi=u.load_asset(path) if E.does_asset_exist(path) else None
        if not mi:
            mi=AT.create_asset(name,tree_base+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());ML.set_material_instance_parent(mi,source)
            for parameter in ML.get_scalar_parameter_names(source):
                if ('Wind' in str(parameter) and 'Strength' in str(parameter)) or str(parameter)=='ShadowLength':ML.set_material_instance_scalar_parameter_value(mi,parameter,0.)
            ML.update_material_instance(mi);save(mi)
        a.static_mesh_component.set_material(i,mi)

def interactive(spec,r,off):
    loc=pos(spec['position_m'],off);rot=u.Rotator(pitch=0,yaw=spec['yaw_ue'],roll=0)
    if spec['type']=='glass_window':
        actor=tag(AA.spawn_actor_from_class(u.WardGlassWindow,loc,rot),r['id']+'_'+spec['id'],r['id'])
        pane=actor.get_editor_property('glass_pane');pane.set_static_mesh(asset(spec['pane']))
        pane.set_cast_shadow(False)
        pane.set_editor_property('receives_decals',False)
        for prop,key in [('fracture_mesh','fracture'),('fracture_material','fracture_material'),('impact_particles','impact_particles'),('break_sound','sound')]:
            pane.set_editor_property(prop,asset(spec[key]))
        pane.set_editor_property('pane_dimensions',u.Vector(*spec['dimensions_cm']))
    elif spec['type']=='solid_door':
        # Same native door and sprint-push path as the station office.
        actor=tag(AA.spawn_actor_from_class(u.ColdSteelDoor,loc,rot),r['id']+'_'+spec['id'],r['id'])
        components={c.get_name():c for c in actor.get_components_by_class(u.SceneComponent)}
        frame,leaf,hinge=[components[name] for name in ('DoorFrame','DoorLeaf','DoorHinge')]
        frame.set_static_mesh(None);frame.set_collision_profile_name('NoCollision');frame.set_visibility(False)
        mesh=asset(spec['leaf']);leaf.set_static_mesh(mesh)
        positive=spec['positive_hinge'];sign=1 if positive else -1
        leaf.set_relative_rotation(u.Rotator(pitch=0,yaw=180 if positive else 0,roll=0),False,True)
        bounds=mesh.get_bounding_box();center=(bounds.min+bounds.max)*.5;extent=(bounds.max-bounds.min)*.5
        hinge.set_relative_location(u.Vector(0,sign*extent.y,0),False,True)
        leaf.set_relative_location(u.Vector(-center.x,-sign*extent.y-center.y,extent.z-center.z),False,True)
        for key,value in dict(hinge_on_positive_y=positive,open_angle_degrees=85,
            open_seconds=spec['open_seconds'],auto_close_seconds=spec['auto_close_seconds']).items():actor.set_editor_property(key,value)
    else:raise RuntimeError('Unsupported ecology interaction '+spec['type'])

def populate(r,off,map_name):
    place_wall_groups(r)
    for prop in r.get('props',[]):
        if prop.get('identity')=='ecology_upper_platform':
            runpy.run_path(str(ROOT/'Scripts/ecology_treasure.py'))['spawn'](AA,asset,prop,off,map_name)
    for mesh,item in roomitems[r['id']]:
        a=static(mesh,[0,0,0],off,item['name'],r['id'],item['collision'])
        if item['kind'] in ('Rails','VaultPipes'):
            a.set_editor_property('tags',[*a.tags,u.Name('Traversal.GuardrailDrop')]);a.static_mesh_component.set_editor_property('component_tags',[u.Name('Traversal.GuardrailDrop')])
        if item['kind'] in ('Water','Glass','LampDiffusers','LampHousings','Algae','Signs','FloorJoints','SpecimenGlass','SpecimenGel','SpecimenLabels','StairApproachMarkings'):a.static_mesh_component.set_cast_shadow(False)
    for i,p in enumerate(r['parts']):
        mesh=asset(p['mesh']);p['position']=wall_position(mesh,p['position'],p['yaw'],p.get('wall_mount'))
        static(mesh,p['position'],off,r['id']+'_Fixed'+str(i),r['id'],p['collision'],p['yaw'])
    plant_groups={}
    for i,p in enumerate(r['plants']):
        mesh=asset(p['mesh']);pp,scale=botanical_transform(p)
        a=static(mesh,pp,off,r['id']+'_Plant'+str(i),r['id'],False,p['yaw'],scale)
        a.static_mesh_component.set_editor_property('min_draw_distance',0.);a.static_mesh_component.set_editor_property('ld_max_draw_distance',2600.)
        plant_groups.setdefault(p['mesh'],[]).append(a)
    for key,actors in plant_groups.items():
        if len(actors)<2:continue
        cluster=u.PlazaInstanceTools.create_plaza_cluster(actors,'EcoSubject_'+r['id']+'_Plants_'+key.rsplit('/',1)[-1])
        if cluster:
            tag(cluster,r['id']+'_Plants_'+key.rsplit('/',1)[-1],r['id'])
            for a in actors:AA.destroy_actor(a)
    if r.get('hero_tree'):botanical_tree(r['hero_tree'],r,off,'ScannedTree')
    for index,tree in enumerate(r.get('trees',[])):botanical_tree(tree,r,off,'GardenTree'+str(index))
    for spec in r.get('runtime_actors',[]):interactive(spec,r,off)
    for l in r['lights']:
        fill=l.get('fill_only',False)
        cls=u.PointLight if fill else u.RectLight;component=u.PointLightComponent if fill else u.RectLightComponent
        a=tag(AA.spawn_actor_from_class(cls,pos(l['position'],off),u.Rotator(pitch=-90 if not fill else 0,yaw=90 if not fill else 0,roll=0)),r['id']+'_'+l['id'],r['id']);c=a.get_component_by_class(component)
        c.set_mobility(u.ComponentMobility.MOVABLE);c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(l['lumens']);c.set_light_color(u.LinearColor(*l['tint'],1))
        if not fill:
            c.set_editor_property('source_width',255. if l.get('grow_fixture') else float(l.get('source_width_cm',100)))
            c.set_editor_property('source_height',23. if l.get('grow_fixture') else float(l.get('source_height_cm',28)))
        for key in ('attenuation_radius','cast_shadows','max_draw_distance','max_distance_fade_range'):
            c.set_editor_property(key,l[{'attenuation_radius':'radius_cm','cast_shadows':'cast_shadows','max_draw_distance':'max_draw_distance_cm','max_distance_fade_range':'fade_range_cm'}[key]])
        c.set_editor_property('indirect_lighting_intensity',0. if fill else .85);a.set_editor_property('tags',[*a.tags,u.Name('Dungeon.Light.'+l['role'])])
    for c in r['containers']:spawn_container(c,r,off)
    if r['id']=='EcoHydroponics':
        a=tag(AA.spawn_actor_from_class(u.AmbientSound,pos([11.5,5.5,0],off)),'WaterReturnAudio',r['id']);c=a.get_component_by_class(u.AudioComponent)
        c.set_sound(asset('/Game/Props/RomanFountain20260917/PolishV9/Audio/S_FountainBed_LoopV9'));c.set_editor_property('volume_multiplier',.10)
        c.set_editor_property('override_attenuation',True);s=c.get_editor_property('attenuation_overrides');s.set_editor_property('attenuate',True);s.set_editor_property('spatialize',True)
        s.set_editor_property('attenuation_shape_extents',u.Vector(150,0,0));s.set_editor_property('falloff_distance',900.);c.set_editor_property('attenuation_overrides',s)
def postprocess():
    p=tag(AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector()),'Exposure');p.set_editor_property('unbound',True);s=p.get_editor_property('settings');c=CFG['postprocess']
    for k,v in [('override_auto_exposure_min_brightness',True),('auto_exposure_min_brightness',c['exposure_ev']),('override_auto_exposure_max_brightness',True),('auto_exposure_max_brightness',c['exposure_ev']),('override_auto_exposure_bias',True),('auto_exposure_bias',c['exposure_bias']),('override_bloom_intensity',True),('bloom_intensity',c['bloom']),('override_vignette_intensity',True),('vignette_intensity',c['vignette'])]:s.set_editor_property(k,v)
    blend=u.WeightedBlendable();blend.set_editor_property('weight',1.);blend.set_editor_property('object',asset(CFG['container_outline']));blends=u.WeightedBlendables();blends.set_editor_property('array',[blend]);s.set_editor_property('weighted_blendables',blends);p.set_editor_property('settings',s)
def make_map(target,rooms,combined=False):
    previous=report['maps'].get(target,{})
    if previous.get('stage')=='map_saved' and previous.get('geometry_revision',0)>=CFG['geometry_revision']:return
    if E.does_asset_exist(target):
        world=u.EditorLoadingAndSavingUtils.load_map(target)
        if not world:raise RuntimeError('Cannot load ecology subject '+target)
        # These four maps are owned by this subject. Other actors remain untouched.
        for a in list(AA.get_all_level_actors()):
            if 'Ecology.Subject' in [str(t) for t in a.tags]:AA.destroy_actor(a)
    else:
        world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
    if not world:raise RuntimeError('Map creation failed')
    world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/FPSGAME.FPSGAMEGameMode'))
    for r in rooms:populate(r,r['offset'] if combined else [0,0,0],target.rsplit('/',1)[-1])
    if combined:
        for start,end in CFG['links']:
            for mesh,item in roomitems['Link']:static(mesh,[0,0,0],[start,0,0],'Link'+str(start)+item['name'],'Links',item['collision'])
        cap(CFG['rooms'][0]['offset'][0]+CFG['rooms'][0]['ports'][0]['position'][0],'ThemeEntryCap');cap(CFG['rooms'][-1]['offset'][0]+CFG['rooms'][-1]['ports'][1]['position'][0],'ThemeExitCap')
    else:
        cap(rooms[0]['ports'][0]['position'][0],'EntryCap');cap(rooms[0]['ports'][1]['position'][0],'ExitCap')
    tag(AA.spawn_actor_from_class(u.PlayerStart,pos(rooms[0]['player_start']),u.Rotator(pitch=0,yaw=0,roll=0)),'PlayerStart');postprocess()
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed '+target)
    report['maps'][target]=dict(stage='map_saved',rooms=[r['id'] for r in rooms],containers=sum(len(r['containers']) for r in rooms),combined=combined,geometry_revision=CFG.get('geometry_revision',1))
    record();u.log('ECOLOGY_MAP_SAVED '+target)

# Drafts are source-only and carry complete hard-asset references for later integration.
modules=[]
for r in CFG['rooms']:
    a,b,h=r['size'];parts=[]
    for mesh,item in roomitems[r['id']]:parts.append(dict(mesh=item['asset'],position=[0,0,0],yaw=0,collision=item['collision'],guardrail_drop=item['kind'] in ('Rails','VaultPipes')))
    modules.append(dict(id=r['id'],name=r['name'],family_id=r['id'],role='room',phase='subject',parts=parts,
        cells=[dict(min=[-a*50-14,-b*50-14,-160 if r['id']=='EcoHydroponics' else -30],max=[a*50+14,b*50+14,h*100+40]),dict(min=[-a*50-214,-214,-30],max=[-a*50,214,370]),dict(min=[a*50,-214,-30],max=[a*50+214,214,370])],
        ports=[dict(id=p['id'],position=[p['position'][0]*100,-p['position'][1]*100,p['position'][2]*100],normal=[p['normal'][0],-p['normal'][1],p['normal'][2]],width=300,height=280) for p in r['ports']],port_pairs=[[0,1]],
        author_lights=r['lights'],author_plants=r['plants'],author_tree=r.get('hero_tree'),author_trees=r.get('trees',[]),author_containers=r['containers'],author_fixed_parts=r['parts'],
        runtime_actors=[dict(s,position=[s['position_m'][0]*100,-s['position_m'][1]*100,s['position_m'][2]*100],yaw=s['yaw_ue']) for s in r.get('runtime_actors',[])],
        props=r.get('props',[]),encounter_anchors_m=r['encounter_anchors_m'],random_pool_registered=False))
for r in CFG['rooms']:make_map(r['map'],[r])
make_map(CFG['sample_map'],CFG['rooms'],True)
(ROOT/'Config/modules-draft.json').write_text(json.dumps(dict(modules=modules,sequence=CFG['sequence'],registered=False),ensure_ascii=False,indent=2),encoding='utf8')
report.update(stage='samples_saved',container_physical_groups=24,unique_search_entries=32,mesh_entries=len(MAN['objects']),new_meshes=sum(1 for i in MAN['objects'] if not i.get('reused')),source_triangles=sum(i['triangles'] for i in MAN['objects']),console_commands=['open '+CFG['sample_map']]+['open '+r['map'] for r in CFG['rooms']],return_command='open '+CFG['return_map'])
(ROOT/'Config/room.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf8')
report['saved_revision']=CFG['revision'];record();u.log('ECOLOGY_SUBJECTS_DELIVERED')
