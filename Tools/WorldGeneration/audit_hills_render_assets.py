"""Read the active hills palette, graphs and material inputs without saving assets."""
import json
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME/Saved/HillsDisappearanceAudit20261114')
root.mkdir(parents=True, exist_ok=True)
out = {'meshes': {}, 'graphs': [], 'materials': {}, 'functions': {}, 'textures': {}, 'missing': [], 'dirty_packages': []}
lib = u.MaterialEditingLibrary

def value(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, u.Object):
        return v.get_path_name()
    return str(v)

def props(obj, names):
    row = {}
    for name in names:
        try:
            row[name] = value(obj.get_editor_property(name))
        except Exception:
            pass
    return row

def texture(tex):
    if not tex or tex.get_path_name() in out['textures']:
        return
    out['textures'][tex.get_path_name()] = props(tex,[
        'virtual_texture_streaming','never_stream','lod_bias','max_texture_size',
        'mip_gen_settings','mip_load_options','do_scale_mips_for_alpha_coverage',
        'alpha_coverage_thresholds','compression_settings','compression_no_alpha','srgb'])

def function(fn):
    if not fn or fn.get_path_name() in out['functions']:
        return
    row = out['functions'][fn.get_path_name()] = {'class':fn.get_class().get_name(),'nodes':[]}
    if not isinstance(fn,u.MaterialFunction):
        row['inspection'] = 'not a MaterialFunction; no expression traversal'
        return
    for node in lib.get_material_function_expressions(fn):
        info = {'path':node.get_path_name(),'class':node.get_class().get_name()}
        info.update(props(node,['desc','code','parameter_name','default_value','material_function','texture']))
        row['nodes'].append(info)
        if isinstance(node,u.MaterialExpressionMaterialFunctionCall):
            function(node.get_editor_property('material_function'))
        try:
            texture(node.get_editor_property('texture'))
        except Exception:
            pass

def material(mat):
    if not mat or mat.get_path_name() in out['materials']:
        return
    path = mat.get_path_name()
    row = out['materials'][path] = {'class':mat.get_class().get_name()}
    # This includes texture dependencies hidden inside material functions, not
    # only exposed parameters or top-level texture expressions.
    used = lib.get_material_used_textures(mat)
    row['used_textures'] = [value(tex) for tex in used]
    for tex in used:
        texture(tex)
    if isinstance(mat, u.MaterialInstance):
        row.update(props(mat, ['parent', 'base_property_overrides']))
        row['scalars'] = {str(key):lib.get_material_instance_scalar_parameter_value(mat, key)
                          for key in lib.get_scalar_parameter_names(mat)}
        row['textures'] = {}
        for key in lib.get_texture_parameter_names(mat):
            tex = lib.get_material_instance_texture_parameter_value(mat,key)
            row['textures'][str(key)] = value(tex)
            texture(tex)
        material(mat.get_editor_property('parent'))
    elif isinstance(mat, u.Material):
        row.update(props(mat, ['blend_mode','opacity_mask_clip_value','use_material_attributes',
            'max_world_position_offset_displacement','two_sided','dithered_lod_transition',
            'used_with_instanced_static_meshes','used_with_skeletal_mesh','used_with_nanite']))
        row['roots'] = {}
        for name in ('OPACITY_MASK','WORLD_POSITION_OFFSET','MATERIAL_ATTRIBUTES','FRONT_MATERIAL'):
            try:
                row['roots'][name] = value(lib.get_material_property_input_node(mat,getattr(u.MaterialProperty,'MP_'+name)))
            except Exception:
                pass
        row['nodes'] = []
        for node in lib.get_material_expressions(mat):
            info = {'path':node.get_path_name(), 'class':node.get_class().get_name()}
            info.update(props(node,['desc','code','parameter_name','default_value','material_function',
                                    'transform_source_type','transform_type','world_position_shader_offset']))
            info['inputs'] = [value(n) for n in lib.get_inputs_for_material_expression(mat,node)]
            if isinstance(node,u.MaterialExpressionMaterialFunctionCall):
                function(node.get_editor_property('material_function'))
            try:
                tex = node.get_editor_property('texture')
                info['texture'] = value(tex)
                texture(tex)
            except Exception:
                pass
            row['nodes'].append(info)

da = u.load_asset('/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming')
roles = ['trees','rocks','shrubs','grass','grass_accents','forest_saplings','forest_shrubs','forest_ferns',
         'rainforest_grass','rainforest_carpet_grass','rainforest_twigs','rainforest_herbs','forest_fungi',
         'forest_moss','river_rocks','river_ground_cover','river_pebbles','river_reeds','river_bank_grasses',
         'river_understory','meadow_flowers','fallen_logs','forest_roots','cliffs','backdrop_trees']
palette = {role:list(da.get_editor_property(role)) for role in roles}
for role in ('rainforest_bank_boulder','trunk_collision_mesh'):
    ref = da.get_editor_property(role)
    palette[role] = [ref] if ref else []
for i, family in enumerate(da.get_editor_property('clearing_flowers')):
    palette['clearing_flowers_'+str(i)] = list(family.get_editor_property('variants'))
for role, refs in palette.items():
    for ref in refs:
        path = ref.get_path_name()
        if path in out['meshes']:
            out['meshes'][path]['roles'].append(role)
            continue
        mesh = u.load_asset(path)
        if not mesh:
            out['missing'].append(path)
            continue
        row = out['meshes'][path] = {'roles':[role], 'class':mesh.get_class().get_name()}
        row.update(props(mesh,['nanite_settings','positive_bounds_extension','negative_bounds_extension',
                               'min_lod','lod_for_collision','support_ray_tracing']))
        slots = mesh.get_editor_property('materials' if isinstance(mesh,u.SkeletalMesh) else 'static_materials')
        row['materials'] = []
        for slot in slots:
            mat = slot.get_editor_property('material_interface')
            row['materials'].append(value(mat))
            material(mat)
for ref in da.get_editor_property('graphs'):
    graph = u.load_asset(ref.get_path_name())
    row = {'path':graph.get_path_name(), 'nodes':[]}
    row.update(props(graph,['hi_gen_grid_size','use_2d_grid','generation_radii','use_actor_componentless_generation']))
    for node in graph.get_editor_property('nodes'):
        settings = node.get_settings()
        info = {'class':settings.get_class().get_name()}
        info.update(props(settings,['layer','synchronous_load','allow_descriptor_changes','apply_mesh_bounds_to_points',
                                    'mesh_selector_type','mesh_selector_parameters','transform_provider']))
        try:
            selector = settings.get_editor_property('mesh_selector_parameters')
            d = selector.get_editor_property('template_descriptor')
            info['descriptor'] = props(d,['component_class','static_mesh','skinned_asset','transform_provider',
                'instance_start_cull_distance','instance_end_cull_distance','instance_min_draw_distance',
                'bounds_scale','cast_shadow','evaluate_world_position_offset','world_position_offset_disable_distance',
                'override_materials','collision_profile_name','allow_density_scaling','enable_density_scaling'])
        except Exception:
            pass
        row['nodes'].append(info)
    out['graphs'].append(row)
out['dirty_packages'] = [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                         if '/WorldGeneration/TemperateHills/' in p.get_path_name()]
(root/'render-assets.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
u.log('HILLS_RENDER_ASSET_AUDIT meshes=%d materials=%d graphs=%d missing=%d' %
      (len(out['meshes']),len(out['materials']),len(out['graphs']),len(out['missing'])))
