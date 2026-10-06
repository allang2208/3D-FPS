"""User-requested read-only RSH attachment material audit. Never save UE assets."""
import json,datetime
from pathlib import Path
import unreal as u
O=Path(__file__).parent;O.mkdir(exist_ok=True)
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
editor_world=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor_world.get_game_world() if editor_world else None
R={'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'read_only':True,'meshes':{},'materials':{},'textures':{},'errors':[]}
def path(o):return o.get_path_name() if o else None
def prop(o,k):
    try:return o.get_editor_property(k)
    except Exception:return None
def serial(v):
    if v is None or isinstance(v,(str,bool,int,float)):return v
    if isinstance(v,u.Object):return path(v)
    if all(hasattr(v,k) for k in ('r','g','b')):return [v.r,v.g,v.b,getattr(v,'a',1.)]
    return str(v)
def texture(t):
    if not t or path(t) in R['textures']:return
    R['textures'][path(t)]={k:serial(prop(t,k)) for k in ('srgb','compression_settings','flip_green_channel','lod_group','never_stream')}
    try:R['textures'][path(t)]['size']=[t.blueprint_get_size_x(),t.blueprint_get_size_y()]
    except Exception:pass
def graph(m):
    nodes={};roots={}
    def visit(n):
        if not n:return None
        key=n.get_name()
        if key in nodes:return key
        d={'class':n.get_class().get_name()};nodes[key]=d
        for k in ('parameter_name','default_value','r','constant','const_a','const_b','const_alpha','coordinate_index','u_tiling','v_tiling','sampler_type','code','description','texture','parameter_names'):
            v=prop(n,k)
            if v is not None:d[k]=serial(v)
            if k=='texture' and v:texture(v)
        try:
            inputs=L.get_inputs_for_material_expression(m,n)
            d['inputs']=[visit(x) for x in inputs]
        except Exception as ex:d['input_error']=str(ex)
        return key
    for key in ('BASE_COLOR','ROUGHNESS','METALLIC','NORMAL','AMBIENT_OCCLUSION','EMISSIVE_COLOR','OPACITY','OPACITY_MASK'):
        try:
            p=getattr(u.MaterialProperty,'MP_'+key);n=L.get_material_property_input_node(m,p)
            roots[key]={'node':visit(n),'output':str(L.get_material_property_input_node_output_name(m,p)) if n else None}
        except Exception as ex:roots[key]={'error':str(ex)}
    return {'roots':roots,'nodes':nodes}
def material(m):
    key=path(m)
    if not m or key in R['materials']:return
    d={'class':m.get_class().get_name(),'base':path(m.get_base_material())};R['materials'][key]=d
    if isinstance(m,u.Material):
        d.update({k:serial(prop(m,k)) for k in ('blend_mode','two_sided','used_with_skeletal_mesh','used_with_clothing','automatically_set_usage_in_editor')})
        d['graph']=graph(m)
    else:
        parent=prop(m,'parent');d['parent']=path(parent);material(parent)
        for typ in ('scalar','vector','texture'):
            params={}
            try:
                for name in getattr(L,'get_'+typ+'_parameter_names')(m):
                    value=getattr(m,'get_'+typ+'_parameter_value')(name) if isinstance(m,u.MaterialInstanceDynamic) else getattr(L,'get_material_instance_'+typ+'_parameter_value')(m,name)
                    params[str(name)]=serial(value)
                    if typ=='texture':texture(value)
            except Exception as ex:d[typ+'_error']=str(ex)
            d[typ]=params
    d['metadata']={k:E.get_metadata_tag(m,k) for k in ('WeaponFinishReference','RSHOpticFinish','RSHCubeFinish') if E.get_metadata_tag(m,k)}
assets={}
def add(group,p):assets[p]=group
for v in ('holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','eoth_holographic'):
    add('optic '+v,'/Game/Weapons/RSH12/Optics20261004/Meshes/SM_RSH12_'+v)
    add('optic rail '+v,'/Game/Weapons/RSH12/Optics20261004/Meshes/SM_RSH12_Rail_'+v)
add('optic lpvo ring','/Game/Weapons/RSH12/Optics20261004/Meshes/SM_RSH12_lpvo_ring')
for p in ('PSO1','PSOReceiverShoe'):add('optic PSO','/Game/Weapons/RSH12/PSO20261004/Meshes/SM_RSH12_'+p)
for v in ('vertical','tactical_vertical','canted','prism','angled'):add('underbarrel '+v,'/Game/Weapons/RSH12/Foregrips20261004/Meshes/SM_RSH12_'+v)
for v in ('HeavyGrip','QuickDrawGrip'):
    for suffix in ('','_Surface'):add('grip body '+v,'/Game/Weapons/RSH12/'+v+'20261005/Meshes/SM_RSH12_'+v+suffix)
add('surface original','/Game/Weapons/RSH12/GripSurfaces20261004/SM_RSH12_GripSurface')
add('muzzle','/Game/Weapons/RSH12/CubeSuppressor20261004/SM_RSH12_CubeSuppressor_Long')
for side,name in [('single','SK_RSH12_Manny'),('r','SK_Dual_RSH12_r'),('l','SK_Dual_RSH12_l')]:
    add('host and speedloader '+side,'/Game/Weapons/RSH12/Native71520261003/'+side+'/'+name)
for p,group in assets.items():
    m=u.load_asset(p)
    if not m:R['errors'].append('Missing mesh '+p);continue
    static=isinstance(m,u.StaticMesh)
    slots=m.static_materials if static else m.materials
    d={'group':group,'class':m.get_class().get_name(),'slots':[]};R['meshes'][p]=d
    if static and world:
        d['uv_channels']=None;d['uv_note']='Editor UV query is disabled during PIE; no zero-UV conclusion.'
    elif static:
        try:d['uv_channels']=(u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)).get_num_uv_channels(m,0)
        except Exception as ex:d['uv_error']=str(ex)
    for i,s in enumerate(slots):
        mat=s.material_interface
        d['slots'].append({'index':i,'name':str(s.material_slot_name),'material':path(mat)})
        if not mat or '/Engine/EngineMaterials/WorldGridMaterial' in path(mat) or '/Engine/EngineMaterials/DefaultMaterial' in path(mat):R['errors'].append('Unfinished binding '+p+' slot '+str(i))
        material(mat)
for v in ('granular','diamond','quickdot'):material(u.load_asset('/Game/Weapons/PistolGripSurface20260927/Materials/M_pistol_grip_'+v))
wet=u.load_asset('/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials')
R['wet_mapping']={str(k):path(v) for k,v in dict(wet.get_editor_property('wet_materials')).items()} if wet else {}
R['dirty_packages']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith('/Game/Weapons/RSH12/')]
R['live_components']=[]
R['pie_active']=bool(world)
player=u.GameplayStatics.get_player_character(world,0) if world else None
if player:
    for c in player.get_components_by_class(u.MeshComponent):
        mesh=prop(c,'static_mesh') or prop(c,'skeletal_mesh_asset')
        if not mesh or not path(mesh).startswith('/Game/Weapons/RSH12/'):continue
        mats=[c.get_material(i) for i in range(c.get_num_materials())]
        R['live_components'].append({'component':path(c),'mesh':path(mesh),'visible':serial(prop(c,'visible')),'materials':[path(m) for m in mats]})
        for m in mats:material(m)
(O/'actual_materials.json').write_text(json.dumps(R,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'meshes':len(R['meshes']),'materials':len(R['materials']),'textures':len(R['textures']),'binding_errors':R['errors'],'pie_active':R['pie_active'],'live_components':len(R['live_components']),'report':str(O/'actual_materials.json')},ensure_ascii=False))
