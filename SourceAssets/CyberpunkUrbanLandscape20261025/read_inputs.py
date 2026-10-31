from pathlib import Path
import unreal as u, json
R=Path(__file__).resolve().parent;P=R.parents[1]
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
out=dict(meshes={},materials={},actors={},stage='reading')
def tr(t):return dict(p=list(t.translation.to_tuple()),q=list(t.rotation.to_tuple()),s=list(t.scale3d.to_tuple()))
def material(m):
    if not m:return None
    path=m.get_path_name()
    if path in out['materials']:return path
    r=dict(type=m.get_class().get_name());out['materials'][path]=r
    if isinstance(m,u.MaterialInstanceConstant):
        r['parent']=material(m.get_editor_property('parent'))
        r['scalars']={str(k):L.get_material_instance_scalar_parameter_value(m,k) for k in L.get_scalar_parameter_names(m)}
        r['textures']={str(k):(L.get_material_instance_texture_parameter_value(m,k).get_path_name() if L.get_material_instance_texture_parameter_value(m,k) else None) for k in L.get_texture_parameter_names(m)}
    elif isinstance(m,u.Material):
        r['blend']=str(m.get_editor_property('blend_mode'));r['two_sided']=m.get_editor_property('two_sided')
        r['normal_connected']=bool(L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL))
        r['front_material']=bool(L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL))
        r['textures']={}
        for n in L.get_material_expressions(m):
            if isinstance(n,u.MaterialExpressionTextureBase):
                t=n.get_editor_property('texture')
                if t:r['textures'][n.get_name()]=t.get_path_name()
    return path
def mesh(path):
    m=u.load_asset(path)
    if not isinstance(m,u.StaticMesh):raise RuntimeError('Expected static vegetation or fixture '+path)
    b=m.get_bounding_box();r=dict(path=m.get_path_name(),min=list(b.min.to_tuple()),max=list(b.max.to_tuple()),slots=[str(s.material_slot_name) for s in m.static_materials],materials=[material(s.material_interface) for s in m.static_materials],nanite=m.get_editor_property('nanite_settings').enabled)
    out['meshes'][path]=r;return r
fol='/Game/SoulCity/Environment/Meshes/Foliage/'
for key,name in [('TreeA','SM_Aspen_Tree_01'),('TreeB','SM_LV_Soul_Tree01_B'),('TreeC','SM_S_Soul_Tree2'),('Shrub','SM_S_Soul_bush')]:
    row=mesh(fol+name);row['key']=key
for key,path in [('GroundA','/Game/PN_FoliageCollection/Meshes/groundPlantMesh/ground_01_01'),('GroundB','/Game/PN_FoliageCollection/Meshes/groundPlantMesh/ground_03_01'),('Flower','/Game/PN_FoliageCollection/Meshes/flowerMesh/flower_03_01'),('Grass','/Game/PN_GrassLibrary/Meshes/grassMesh/grass_01_01_mesh')]:
    row=mesh(path);row['key']=key
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=editor.get_editor_world()
out['editor_world']=world.get_path_name() if world else None;out['game_running']=bool(editor.get_game_world());out['dirty_maps']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if not world or world.get_path_name().split('.')[0]!='/Game/GameMaps/L_CyberpunkApartment':
    world=u.load_asset('/Game/GameMaps/L_CyberpunkApartment');out['read_saved_map_asset']=True
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    label=actor.get_actor_label()
    if not (label.startswith(('AP16_','AP18_','AP7_BayLandmark_','EX25_','BAY_City_','BAY_Quay_')) or label in ('BAY_FarTerrain','BAY_Water')):continue
    row=dict(transform=tr(actor.get_actor_transform()),components=[])
    for c in actor.get_components_by_class(u.StaticMeshComponent):
        if not c.static_mesh:continue
        path=c.static_mesh.get_path_name();b=c.static_mesh.get_bounding_box()
        component=dict(mesh=path,min=list(b.min.to_tuple()),max=list(b.max.to_tuple()),transform=tr(c.get_world_transform()),materials=[material(m) for m in c.get_materials()],slots=[str(s.material_slot_name) for s in c.static_mesh.static_materials])
        if label=='AP16_Trees' or label.startswith(('AP18_Frontage_','AP18_Lookouts_')):mesh(path)
        row['components'].append(component)
    out['actors'][label]=row
for path in ['/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV18/Materials/M_AP18_Paving','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7/Materials/M_AP7_Machined','/Game/Props/RomanFountain20260917/Materials/M_FountainWaveWaterV3']:
    material(u.load_asset(path))
out['stage']='inputs_read';(R/'inputs.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print('URBAN_INPUTS_READ',len(out['meshes']),len(out['actors']),out['editor_world'],out['game_running'])
