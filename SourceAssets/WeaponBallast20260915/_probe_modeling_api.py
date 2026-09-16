import unreal
names = [n for n in dir(unreal.ModelingService) if not n.startswith('_')]
print('COUNT', len(names))
print('SAMPLE', ', '.join(names[:40]))
for fn in ['create_mesh','append_box','append_cylinder','append_torus','append_cone','append_disc','boolean','auto_uv','get_uv_stats','get_mesh_info','save_mesh_to_static_mesh','generate_collision','cut_groove_along_polyline','set_asset_materials','remesh','transform_mesh']:
    d = getattr(unreal.ModelingService, fn, None)
    print('---', fn, '---')
    print((d.__doc__ or '')[:600] if d else 'MISSING')