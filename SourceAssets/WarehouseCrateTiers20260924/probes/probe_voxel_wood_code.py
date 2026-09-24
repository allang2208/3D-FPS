import unreal as u
mat = u.load_asset('/Game/Building/Voxels/Rounded/M_Voxel_Wood')
prop = u.MaterialEditingLibrary.get_material_property_input_node(mat, u.MaterialProperty.MP_BASE_COLOR)
print('CODE_BEGIN'); print(prop.get_editor_property('code')); print('CODE_END', flush=True)
try:
    print('INPUT_NAMES', prop.get_editor_property('input_names'), flush=True)
    for i, link in enumerate(prop.get_editor_property('inputs')):
        src = link.get_editor_property('expression')
        print('INPUT', i, src.get_class().get_name() if src else None,
              (src.get_editor_property('texture').get_path_name() if src and 'TextureSample' in src.get_class().get_name() and src.get_editor_property('texture') else ''),
              (getattr(src, 'output_0', None) and getattr(src, 'output_0').get_editor_property('output_name') if src and 'Parameter' in src.get_class().get_name() else src.get_editor_property('name') if src and 'Parameter' in src.get_class().get_name() else ''), flush=True)
except Exception as e:
    print('INPUTS_ERR', e, flush=True)
for tp in ('/Game/UnrealNormandy/Textures/T_WoodSurface_00A_BaseColor',
           '/Game/UnrealNormandy/Textures/T_WoodSurface_00A_RHAOM',
           '/Game/UnrealNormandy/Textures/T_WoodSurface_00A_Normal'):
    t = u.load_asset(tp)
    print('TEX', tp.split('/')[-1], t.get_editor_property('compression_settings'), 'srgb', t.get_editor_property('srgb'),
          'lod', t.get_editor_property('lod_group'), flush=True)
