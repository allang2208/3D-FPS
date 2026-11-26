"""Build the formal landscape and its compatible rigid shadow casters in an authoring host."""
import json
from pathlib import Path
import unreal as u

REF='/Game/ForestPathStudy/VillageRegion/Reference/'
PACKED=REF+'Terrain/MI_ForestTilePacked'
SWITCH='UsePackedForestTileUV'
ed=u.MaterialEditingLibrary
assets=u.EditorAssetLibrary

def save(obj):
    if not assets.save_loaded_asset(obj,False):raise RuntimeError('Failed to save '+obj.get_path_name())

def packed_ground_material():
    master=u.load_asset(REF+'M_ForestReferenceMesh')
    parent=u.load_asset(REF+'MI_ForestReference')
    nodes=list(ed.get_material_expressions(master))
    changed=False
    # Keep every legacy consumer on its own UV layout; only the tile child selects the compact layout.
    for coord in (n for n in nodes if isinstance(n,u.MaterialExpressionTextureCoordinate) and n.get_editor_property('coordinate_index')>=4):
        index=coord.get_editor_property('coordinate_index')
        if index not in (4,5):raise RuntimeError('Unmapped forest UV '+str(index))
        consumers=[]
        for node in nodes:
            if isinstance(node,u.MaterialExpressionStaticSwitchParameter) and str(node.get_editor_property('parameter_name'))==SWITCH:continue
            inputs=ed.get_inputs_for_material_expression(master,node)
            for pin,source in zip(ed.get_material_expression_input_names(node),inputs):
                if source==coord:consumers.append((node,str(pin)))
        if not consumers:continue
        select=ed.create_material_expression(master,u.MaterialExpressionStaticSwitchParameter)
        select.set_editor_property('parameter_name',SWITCH)
        select.set_editor_property('default_value',False)
        if index==4:
            compact=ed.create_material_expression(master,u.MaterialExpressionTextureCoordinate)
            compact.set_editor_property('coordinate_index',3)
            for prop in ('u_tiling','v_tiling','un_mirror_u','un_mirror_v'):
                compact.set_editor_property(prop,coord.get_editor_property(prop))
        else:
            # UV5 belongs to the village foundation. It reads zero on exterior tiles.
            compact=ed.create_material_expression(master,u.MaterialExpressionConstant2Vector)
        if not ed.connect_material_expressions(coord,'',select,'False') or not ed.connect_material_expressions(compact,'',select,'True'):raise RuntimeError(SWITCH)
        for node,pin in consumers:
            if not ed.connect_material_expressions(select,'',node,pin):raise RuntimeError(node.get_name()+' '+pin)
        changed=True
    if changed:
        errors=ed.recompile_material(master)
        if errors:raise RuntimeError(str(errors))
        save(master)
    child=u.load_asset(PACKED) if assets.does_asset_exist(PACKED) else u.AssetToolsHelpers.get_asset_tools().create_asset('MI_ForestTilePacked',REF+'Terrain',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    if child.get_editor_property('parent')!=parent or not ed.get_material_instance_static_switch_parameter_value(child,SWITCH):
        ed.set_material_instance_parent(child,parent)
        ed.set_material_instance_static_switch_parameter_value(child,SWITCH,True)
        ed.update_material_instance(child)
        save(child)
    if not ed.get_material_instance_static_switch_parameter_value(child,SWITCH):raise RuntimeError('Packed forest switch not applied')
    return child

def install_landscape(native):
    name=REF+'TrailLandscape/L_ForestPathForest'
    world=u.EditorLoadingAndSavingUtils.load_map(name)
    land,=[a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.Landscape) and a.get_outermost().get_name()==name]
    land.modify()
    land.set_editor_property('enable_nanite',True)
    if not native.build_reference_landscape_nanite(land):raise RuntimeError(name+' Nanite build incomplete')
    count=sum(c.get_class().get_name()=='LandscapeNaniteComponent' for c in land.get_components_by_class(u.StaticMeshComponent))
    if not count or not u.EditorLoadingAndSavingUtils.save_map(world,name):raise RuntimeError(name+' not saved')
    return count

def install():
    """Reapply the saved hills selection after a mesh reimport, respecting the original material/UV contracts."""
    recipe=json.loads(Path(__file__).with_name('shadow_geometry.json').read_text(encoding='utf-8'))
    native=u.ForestVillageRegion
    packed=packed_ground_material()
    for path in recipe['base_materials']:
        mat=u.load_asset(path)
        if not isinstance(mat,u.Material):raise RuntimeError(path)
        if not mat.get_editor_property('used_with_nanite'):
            mat.modify()
            mat.set_editor_property('used_with_nanite',True)
            errors=ed.recompile_material(mat)
            if errors:raise RuntimeError(str(errors))
            save(mat)
    for path in recipe['meshes']:
        mesh=u.load_asset(path)
        if not isinstance(mesh,u.StaticMesh):raise RuntimeError(path)
        ground=path.startswith(REF+'Terrain/SM_ForestGround_')
        if not native.build_scenery_nanite_mesh(mesh,packed if ground else None):raise RuntimeError('Nanite build failed: '+path)
        save(mesh)
    return install_landscape(native)

if __name__=='__main__':install()
