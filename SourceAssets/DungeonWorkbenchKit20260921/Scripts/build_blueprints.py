"""Create ordinary spawnable Blueprint assemblies. No runtime Python or per-frame rebuild."""
from pathlib import Path
import json,hashlib,unreal as u
ROOT=Path(__file__).resolve().parents[1];DEST='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit'
CFG=json.loads((ROOT/'Config/workbench.json').read_text(encoding='utf-8'));MAN=json.loads((ROOT/'Authored/manifest.json').read_text());ASSETS=json.loads((ROOT/'Receipts/asset-import.json').read_text())
if ASSETS['stage']!='assets_saved':raise RuntimeError('Import incomplete')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Gameplay active')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();S=u.get_engine_subsystem(u.SubobjectDataSubsystem);F=u.SubobjectDataBlueprintFunctionLibrary
H=CFG['table_height_cm'];H0=CFG['original_table_height_cm'];receipt=dict(stage='building',blueprints={},tests_run=False)
def write():(ROOT/'Receipts/blueprints.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def obj(handle):return F.get_object(F.get_data(handle))
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
for variant,v in CFG['variants'].items():
    path=DEST+'/Blueprints/BP_Workbench_'+variant;bp=u.load_asset(path)
    signature=hashlib.sha256(json.dumps({'components':MAN['components'],'variant':v,'height':H,'anchors':CFG['anchors'],'supports':CFG['supports'],'light':CFG['task_light']},sort_keys=True).encode()).hexdigest()
    if bp and E.get_metadata_tag(bp,'WorkbenchKitDefinition')==signature:
        receipt['blueprints'][variant]=bp.get_path_name();write();continue
    if not bp:
        factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.Actor)
        bp=A.create_asset(path.split('/')[-1],DEST+'/Blueprints',u.Blueprint,factory)
    handles=S.k2_gather_subobject_data_for_blueprint(bp)
    byname={str(F.get_variable_name(F.get_data(h))):h for h in handles}
    roots=[h for h in handles if F.is_root_component(F.get_data(h))]
    def component(name,cls,parent):
        handle=byname.get(name)
        if not handle:
            params=u.AddNewSubobjectParams(parent_handle=parent,new_class=cls,blueprint_context=bp)
            handle,reason=S.add_new_subobject(params)
            if not F.is_handle_valid(handle):raise RuntimeError('Component creation '+name+': '+str(reason))
            if not S.rename_subobject(handle,u.Text(name)):raise RuntimeError('Cannot name component '+name)
            byname[name]=handle
        c=obj(handle);c.modify();return handle,c
    if roots:root=roots[0];S.rename_subobject(root,u.Text('AssemblyRoot'))
    else:
        root,rootobj=component('AssemblyRoot',u.SceneComponent,handles[0]);S.make_new_scene_root(handles[0],root,bp)
    obj(root).set_mobility(u.ComponentMobility.STATIC)
    groups={}
    for name,loc in [('Frame',[0,0,0]),('Table',[0,0,H]),('Wall',CFG['anchors']['WallOrigin'])]:
        handle,c=component(name+'Root',u.SceneComponent,root);c.set_editor_property('relative_location',u.Vector(*loc));c.set_mobility(u.ComponentMobility.STATIC);groups[name]=handle
    handle,c=component('LampRoot',u.SceneComponent,groups['Table']);lamp=CFG['anchors']['LampBase']
    c.set_editor_property('relative_location',u.Vector(lamp[0],lamp[1],lamp[2]-H0));c.set_mobility(u.ComponentMobility.STATIC);groups['Lamp']=handle
    for e in MAN['components']:
        handle,c=component(e['id'],u.StaticMeshComponent,groups[e['group']]);c.set_mobility(u.ComponentMobility.STATIC)
        c.set_static_mesh(u.load_asset(ASSETS['meshes'][e['id']]))
        offset=v.get('tool_offsets',{}).get(e['id'],{});delta=offset.get('translation',[0,0,0]);pos=[a+b for a,b in zip(e['relative_location'],delta)]
        c.set_editor_property('relative_location',u.Vector(*pos));c.set_editor_property('relative_rotation',u.Rotator(roll=0,pitch=0,yaw=offset.get('yaw',0)))
        c.set_editor_property('relative_scale3d',u.Vector(1,1,(H-CFG['table_thickness_cm'])/(H0-CFG['table_thickness_cm']) if e['id']=='Sculpt_BenchFrame' else 1))
        visible=e['id'] not in v['omit'];c.set_visibility(visible);c.set_hidden_in_game(not visible)
        c.set_collision_profile_name('BlockAll' if e['collision'] and visible else 'NoCollision');c.set_editor_property('cast_shadow',e['cast_shadow'])
        for i,slot in enumerate(c.static_mesh.get_editor_property('static_materials')):
            import re
            key=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')));source=e['material_paths'][key]
            c.set_material(i,u.load_asset(ASSETS['materials'][variant][source]))
        c.set_editor_property('component_tags',[u.Name('WorkbenchKit'),u.Name(e['group'])]+([u.Name('Support_'+e['support'])] if e.get('support') else []))
    # Named attachment points are actual SceneComponents, visible in the Blueprint hierarchy.
    for name,p in CFG['anchors'].items():
        if name=='WallOrigin':continue
        if name=='LampEntry':p=[a+b for a,b in zip(CFG['anchors']['LampBase'],CFG['anchor_offsets_cm']['LampEntry'])]
        table_bound=name in ('LampBase','LampEntry','MainWorkArea','ReturnWorkArea')
        parent=groups['Table'] if table_bound else root;location=[p[0],p[1],p[2]-H0] if table_bound else p
        if name=='SocketExit':parent=groups['Wall'];location=CFG['anchor_offsets_cm']['SocketExit']
        handle,c=component('Anchor_'+name,u.SceneComponent,parent);c.set_editor_property('relative_location',u.Vector(*location));c.set_mobility(u.ComponentMobility.STATIC)
    for name,support in CFG['supports'].items():
        handle,c=component('SupportArea_'+name,u.BoxComponent,groups['Table'])
        x=support['x'];y=support['y'];c.set_box_extent(u.Vector((x[1]-x[0])/2,(y[1]-y[0])/2,.15))
        c.set_editor_property('relative_location',u.Vector((x[0]+x[1])/2,(y[0]+y[1])/2,0));c.set_collision_profile_name('NoCollision');c.set_hidden_in_game(True);c.set_editor_property('is_editor_only',True);c.set_mobility(u.ComponentMobility.STATIC)
    handle,c=component('OperatorClearance',u.BoxComponent,root);space=CFG['operator_clearance'];c.set_box_extent(u.Vector(*space['extent']));c.set_editor_property('relative_location',u.Vector(*space['center']));c.set_collision_profile_name('NoCollision');c.set_hidden_in_game(True);c.set_editor_property('is_editor_only',True);c.set_mobility(u.ComponentMobility.STATIC)
    handle,c=component('TaskLight',u.SpotLightComponent,groups['Lamp']);cfg=CFG['task_light'];r=[1000,148,0];base=[-27,65,H0]
    position=u.Vector(*[cfg['position'][i]-r[i]-base[i] for i in range(3)])
    target=u.Vector(*[cfg['target'][i]-r[i]-base[i] for i in range(3)])
    c.set_mobility(u.ComponentMobility.MOVABLE);c.set_editor_property('relative_location',position);c.set_editor_property('relative_rotation',u.MathLibrary.find_look_at_rotation(position,target))
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(cfg['lumens'] if v['lamp_on'] else 0);c.set_visibility(v['lamp_on'])
    c.set_editor_property('use_temperature',True);c.set_temperature(cfg['temperature']);c.set_attenuation_radius(220);c.set_inner_cone_angle(38);c.set_outer_cone_angle(64);c.set_editor_property('source_radius',1.4)
    if not u.BlueprintEditorLibrary.compile_blueprint(bp):raise RuntimeError('Blueprint compilation failed '+path)
    cdo=u.get_default_object(bp.generated_class());tick=cdo.get_editor_property('primary_actor_tick');tick.set_editor_property('start_with_tick_enabled',False);cdo.set_editor_property('primary_actor_tick',tick)
    cdo.set_editor_property('tags',[u.Name('WorkbenchKit'),u.Name('Variant_'+variant)])
    E.set_metadata_tag(bp,'WorkbenchKitDefinition',signature);E.set_metadata_tag(bp,'WorkbenchKitVariant',variant);save(bp)
    receipt['blueprints'][variant]=bp.get_path_name();write()
receipt['stage']='blueprints_saved';write();print('WORKBENCH_BLUEPRINTS_SAVED '+json.dumps(receipt['blueprints']))
