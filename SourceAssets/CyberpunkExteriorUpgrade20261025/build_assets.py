"""Save proportion-preserving building assemblies, full inherited PBR and night adaptation."""
from pathlib import Path
import unreal as u,json,hashlib,runpy,gc
R=Path(__file__).resolve().parent;PROJECT=R.parents[1];BASE='/Game/Props/CyberpunkExteriorUpgrade20261025'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();S=u.get_engine_subsystem(u.SubobjectDataSubsystem);F=u.SubobjectDataBlueprintFunctionLibrary
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
sources=json.loads((R/'sources.json').read_text());layout=json.loads((R/'layout.json').read_text())
report=dict(stage='authoring',blueprints={},materials={},meshes={},windows={},tests_run=False)
H=runpy.run_path(str(PROJECT/'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV10/build_assets.py'));node=H['node'];wire=H['wire'];custom=H['custom']
window_cache={};root_window='/Game/CitySampleBuildings/Material/Window/M_Window.M_Window'
wet_cache={}

def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing production dependency '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def duplicate(source,prefix):
    name=prefix+'_'+source.get_name()+'_'+hashlib.sha1(source.get_path_name().encode()).hexdigest()[:8];path=BASE+'/Materials/'+name
    return load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Materials',source)

def window_material(path):
    if path in window_cache:return window_cache[path]
    src=load(path)
    if isinstance(src,u.Material):
        if src.get_path_name()!=root_window:return src
        dst=duplicate(src,'M_Exterior')
        if E.get_metadata_tag(dst,'ExteriorNightVersion')!='1':
            emission=L.get_material_property_input_node(dst,u.MaterialProperty.MP_EMISSIVE_COLOR)
            output=L.get_material_property_input_node_output_name(dst,u.MaterialProperty.MP_EMISSIVE_COLOR)
            if not emission:raise RuntimeError('Source interior window emission is not available')
            gain=custom(dst,'return lerp(.035,1.0,Night);',dict(Night=H['night'](dst)),1,description='Exterior sky-driven occupied-room intensity')
            multiply=node(dst,'Multiply');L.connect_material_expressions(emission,output,multiply,'A');wire(gain,multiply,'B');L.connect_material_property(multiply,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
            errors=L.recompile_material(dst)
            if errors:raise RuntimeError('Window material compilation '+str(errors))
            E.set_metadata_tag(dst,'ExteriorNightVersion','1')
        save(dst)
    else:
        parent=src.get_editor_property('parent');newparent=window_material(parent.get_path_name())
        if newparent==parent:return src
        dst=duplicate(src,'MI_Exterior');L.set_material_instance_parent(dst,newparent)
        # These source parameters control stable room occupancy, not a per-frame flicker.
        for k,v in dict(AmountOff=.60,Exposure=1.0).items():L.set_material_instance_scalar_parameter_value(dst,k,v)
        L.update_material_instance(dst);save(dst)
    window_cache[path]=dst;report['windows'][path]=dst.get_path_name();return dst

def material(path):
    row=sources['materials'].get(path,{})
    if 'AmountOff' in row.get('scalars',{}):return window_material(path)
    return load(path)

def wet_material(path):
    if path in wet_cache:return wet_cache[path]
    src=load(path);dst=duplicate(src,'MI_ExteriorWet' if isinstance(src,u.MaterialInstanceConstant) else 'M_ExteriorWet')
    if isinstance(src,u.MaterialInstanceConstant):
        L.set_material_instance_parent(dst,wet_material(src.get_editor_property('parent').get_path_name()));L.update_material_instance(dst)
    elif E.get_metadata_tag(dst,'ExteriorWeatherVersion')!='1':
        rough=L.get_material_property_input_node(dst,u.MaterialProperty.MP_ROUGHNESS)
        if rough:
            output=L.get_material_property_input_node_output_name(dst,u.MaterialProperty.MP_ROUGHNESS)
            weather=node(dst,'CollectionParameter',collection=load('/Game/Weather/Materials/MPC_FPS_Weather'),parameter_name='WeatherWetness')
            value=custom(dst,'return lerp(Rough,max(.18,Rough*.48),saturate(Wet)*(.25+.55*saturate(N.z)));',dict(Rough=rough,Wet=weather,N=node(dst,'VertexNormalWS')),1,description='Exterior weather roughness, original normals retained')
            L.connect_material_expressions(rough,output,value,'Rough');L.connect_material_property(value,'',u.MaterialProperty.MP_ROUGHNESS)
            errors=L.recompile_material(dst)
            if errors:raise RuntimeError('Soul wet material compilation '+str(errors))
        E.set_metadata_tag(dst,'ExteriorWeatherVersion','1')
    save(dst);wet_cache[path]=dst;report['materials'][path]=dst.get_path_name();return dst

def make_blueprint(name):
    path=BASE+'/Blueprints/'+name;bp=u.load_asset(path)
    if not bp:
        factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.Actor);bp=A.create_asset(name,BASE+'/Blueprints',u.Blueprint,factory)
    handles=S.k2_gather_subobject_data_for_blueprint(bp);byname={str(F.get_variable_name(F.get_data(h))):h for h in handles}
    def obj(h):return F.get_object(F.get_data(h))
    def component(name,cls,parent):
        h=byname.get(name)
        if not h:
            h,reason=S.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=cls,blueprint_context=bp))
            if not F.is_handle_valid(h):raise RuntimeError(str(reason))
            S.rename_subobject(h,u.Text(name));byname[name]=h
        c=obj(h);c.modify();return h,c
    roots=[h for h in handles if F.is_root_component(F.get_data(h))]
    if roots:root=roots[0]
    else:
        root,c=component('BuildingRoot',u.SceneComponent,handles[0]);S.make_new_scene_root(handles[0],root,bp)
    obj(root).set_mobility(u.ComponentMobility.STATIC)
    return bp,root,component

def finish_blueprint(bp):
    if not u.BlueprintEditorLibrary.compile_blueprint(bp):raise RuntimeError('Building assembly compilation '+bp.get_name())
    cdo=u.get_default_object(bp.generated_class());tick=cdo.get_editor_property('primary_actor_tick');tick.set_editor_property('start_with_tick_enabled',False);cdo.set_editor_property('primary_actor_tick',tick);save(bp)

def buildings():
    for key,definition in layout['prototypes'].items():
        name='BP_Exterior_'+key.removeprefix('BPP_');bp,root,component=make_blueprint(name);count=0
        for pi,part in enumerate(definition['parts']):
            for ci,row in enumerate(sources['assemblies'][part]['components']):
                h,c=component(f'Part{pi}_Module{ci:03d}',u.InstancedStaticMeshComponent,root);c.set_mobility(u.ComponentMobility.STATIC);c.set_static_mesh(load(row['mesh']));c.set_collision_profile_name('NoCollision')
                c.set_editor_property('cast_shadow',True);c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('visible_in_ray_tracing',False)
                c.set_editor_property('instancing_random_seed',int(hashlib.sha1((part+row['component']).encode()).hexdigest()[:7],16)+1)
                c.clear_instances();transforms=[]
                for t in row['instances']:
                    v=u.Transform();v.translation=u.Vector(*t['p']);v.rotation=u.Quat(*t['q']);v.scale3d=u.Vector(*t['s']);transforms.append(v)
                c.add_instances(transforms,False,False,False);count+=len(transforms)
                if row.get('num_custom_data_floats',0):
                    n=row['num_custom_data_floats'];c.set_num_custom_data_floats(n)
                    for i,v in enumerate(row['per_instance_sm_custom_data']):c.set_custom_data_value(i//n,i%n,v,False)
                if row.get('custom_primitive_data'):
                    cp=c.get_editor_property('custom_primitive_data');cp.set_editor_property('data',row['custom_primitive_data']);c.set_editor_property('custom_primitive_data',cp)
                for mi,path in enumerate(row['materials']):c.set_material(mi,material(path))
                c.set_editor_property('component_tags',[u.Name('ExteriorFab'),u.Name(part),u.Name(row['component'])])
        finish_blueprint(bp);report['blueprints'][key]=dict(path=bp.get_path_name(),instances=count,parts=definition['parts']);record();print('EXTERIOR_BUILDING_SAVED',key,count,flush=True)

def import_mesh(row,roles):
    t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
    o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;o.import_mesh=True;o.import_materials=False;o.import_textures=False;o.import_animations=False;d=o.static_mesh_import_data
    for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():d.set_editor_property(k,v)
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=o;A.import_asset_tasks([t]);m=load(BASE+'/Meshes/'+row['name'])
    for i,s in enumerate(m.static_materials):m.set_material(i,load(roles[str(s.material_slot_name)]))
    settings=SM.get_lod_build_settings(m,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;SM.set_lod_build_settings(m,0,settings)
    ns=m.get_editor_property('nanite_settings').copy();ns.enabled=True;ns.explicit_tangents=True;m.set_editor_property('nanite_settings',ns)
    save(m);return m

def remainder(only=None):
    for row in json.loads((R/'remainder.json').read_text())['meshes']:
        if only=='landmarks' and not row['key'].startswith('Landmark_'):continue
        label='AP7_Bay'+row['key'] if row['key'].startswith('Landmark_') else 'BAY_'+row['key']
        original=sources['map'][label]['components'][0];mesh=sources['meshes'][original['mesh']];roles=dict(zip(mesh['slots'],original['materials']))
        m=import_mesh(row,roles);report['meshes'][row['key']]=m.get_path_name();record()
    if only:return
    old='/Game/Props/CyberpunkApartmentRebuild20261022/'
    roles=dict(Machined=old+'RefinementV7/Materials/M_AP7_Machined',Rubber=old+'RefinementV7/Materials/M_AP7_Roof',Copper=old+'RefinementV18/Materials/M_AP18_Copper')
    # Use the actual saved V18 surface bindings, including their normal maps.
    v18=json.loads((PROJECT/'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV18/assets_saved.json').read_text())
    for k in ('Rubber','Copper'):
        if k in v18['materials']:roles[k]=v18['materials'][k]
    row=json.loads((R/'service_platform.json').read_text());m=import_mesh(row,roles);report['meshes']['ServicePlatform']=m.get_path_name();record()

def service_cluster():
    bp,root,component=make_blueprint('BP_Exterior_RoofService')
    parts=[dict(name='Deck',mesh=report['meshes']['ServicePlatform'],p=[0,0,0])]
    soul='/Game/SoulCity/Environment/Meshes/Building_Slum/'
    # The original mesh pivots are compensated from their source bounds; bottoms
    # sit on the 22 cm deck, with gaps between separate manufactured housings.
    for name,key,xy in [('VentA','SM_Slums_Vent_02c',[-65,-55]),('VentB','SM_Slums_Vent_02d',[65,-55]),('Exhaust','SM_Slums_Pipe_05a',[-75,65]),('Duct','SM_Slums_Pipe_03a',[65,55])]:
        path=soul+key+'.'+key;b=sources['meshes'][path];center=[(b['min'][j]+b['max'][j])*.5 for j in range(2)]
        parts.append(dict(name=name,mesh=path,p=[xy[0]-center[0],xy[1]-center[1],22-b['min'][2]]))
    for part in parts:
        h,c=component(part['name'],u.StaticMeshComponent,root);mesh=load(part['mesh']);c.set_mobility(u.ComponentMobility.STATIC);c.set_static_mesh(mesh);c.set_editor_property('relative_location',u.Vector(*part['p']));c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',True);c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('affect_distance_field_lighting',False)
        if part['name']!='Deck':
            for i,m in enumerate(mesh.static_materials):c.set_material(i,wet_material(m.material_interface.get_path_name()))
    finish_blueprint(bp);report['blueprints']['RoofService']=dict(path=bp.get_path_name(),components=len(parts));record()

def main():
    if hasattr(u,'PlazaInstanceTools'):print('EXTERIOR_AUTHORING_HELPERS',[x for x in dir(u.PlazaInstanceTools) if any(k in x for k in ('capture','render','compil','flush','nanite','texture'))],flush=True)
    u.EditorLoadingAndSavingUtils.new_blank_map(False)
    buildings();remainder();service_cluster();report['stage']='assets_saved';record();print('EXTERIOR_ASSETS_SAVED',len(report['blueprints']),len(report['windows']),flush=True)
if __name__=='__main__':main()
