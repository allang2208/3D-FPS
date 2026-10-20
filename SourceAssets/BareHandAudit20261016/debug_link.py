import bpy, sys
path = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.open_mainfile(filepath=path)
for name in ('SK_Manny_Simple', 'SK_Manny_Arms', 'SK_Manny_Arms_Export'):
    o = bpy.data.objects.get(name)
    if o: print('LINK', name, 'obj.library', o.library, 'override', bool(o.override_library), 'data', o.data.name, 'data.library', o.data.library,
                'data.override', bool(o.data.override_library), 'verts', len(o.data.vertices), 'mats', [m.name for m in o.data.materials if m],
                'users_scene', [s.name for s in o.users_scene])
