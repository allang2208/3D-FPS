m=mat_create('M_WW_ClearSawHood')
m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property('two_sided',True)
m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
for value,prop in [([.55,.73,.76],u.MaterialProperty.MP_BASE_COLOR),(.08,u.MaterialProperty.MP_ROUGHNESS),(.12,u.MaterialProperty.MP_OPACITY),(.5,u.MaterialProperty.MP_SPECULAR),(0,u.MaterialProperty.MP_METALLIC)]:connect(constant(m,value),prop)
assert not L.recompile_material(m);save(m);materials['WW_ClearSawHood']=m
assert m.get_editor_property('blend_mode')==u.BlendMode.BLEND_TRANSLUCENT
assert L.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY)
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
def import_mesh(name,file):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False;task.factory=u.FbxFactory()
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
    d.generate_lightmap_u_vs=False;d.auto_generate_collision=False;d.one_convex_hull_per_ucx=True;d.remove_degenerates=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=opt;A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert isinstance(mesh,u.StaticMesh),task.imported_object_paths
    return mesh
probe=import_mesh('AxisProbe',S/'AxisProbe.fbx');origin=probe.get_bounds().origin
# FBX converts Blender X/Y/Z to UE X/-Y/Z; verify using an asymmetric positive-space cube.
assert abs(origin.x-87)<.01 and abs(origin.y+1)<.01 and abs(origin.z-90.3)<.01,('Unexpected axis conversion',str(origin))
report['axis_probe_origin_cm']=[origin.x,origin.y,origin.z]
report['source_to_ue_axes']=['X','-Y','Z'];report['blade_pivot_cm']=[86.5,0,88.8]
report['meshes']=[]
canon=lambda s:re.sub('[^a-z0-9]','',str(s).lower())
lookup={canon(k):v for k,v in materials.items()}
source=R/'Source/WoodworkingBench/v4_manifest.json';source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
for record in man['meshes']:
    name=record['name'];mesh=import_mesh(name,S/(name+'_LOD0.fbx'))
    for lod in [1,2]:assert sub.import_lod(mesh,lod,str(S/f'{name}_LOD{lod}.fbx'))==lod
    assert sub.get_lod_count(mesh)==3
    for lod in range(3):
        b=sub.get_lod_build_settings(mesh,lod)
        for k,v in {'remove_degenerates':False,'recompute_normals':False,'recompute_tangents':True,'use_mikk_t_space':True,'use_full_precision_u_vs':True,'use_high_precision_tangent_basis':True,'generate_lightmap_u_vs':False}.items():b.set_editor_property(k,v)
        sub.set_lod_build_settings(mesh,lod,b)
    nan=mesh.get_editor_property('nanite_settings');nan.enabled=False;sub.set_nanite_settings(mesh,nan,True)
    slots=list(mesh.static_materials);unique=[];indices={};remap={}
    for i,slot in enumerate(slots):
        key=canon(slot.material_slot_name);assert key in lookup,('Unknown slot',str(slot.material_slot_name))
        if key not in indices:indices[key]=len(unique);unique.append(slot)
        remap[i]=indices[key]
    for lod in range(3):
        for section in range(mesh.get_num_sections(lod)):sub.set_lod_material_slot(mesh,remap[sub.get_lod_material_slot(mesh,lod,section)],lod,section)
    mesh.set_editor_property('static_materials',unique)
    for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,lookup[canon(slot.material_slot_name)])
    assert len(unique)==(1 if 'Blade' in name else 7)
    convex=sub.get_convex_collision_count(mesh);assert convex==record['collision_boxes'],(name,convex,record['collision_boxes'])
    body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    b=mesh.get_bounds();dims=[2*b.box_extent.x,2*b.box_extent.y,2*b.box_extent.z]
    expected=[(hi-lo)*100 for hi,lo in zip(record['bounds_m']['max'],record['bounds_m']['min'])]
    assert all(abs(a-e)<.05 for a,e in zip(dims,expected)),('Wrong import scale',dims,expected)
    if 'Blade' not in name:
        socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name','WoodworkingSawPivot');socket.set_editor_property('relative_location',u.Vector(86.5,0,88.8));mesh.add_socket(socket)
        assert mesh.find_socket('WoodworkingSawPivot')
    else:assert abs(b.origin.x)<.01 and abs(b.origin.y)<.01 and abs(b.origin.z)<.01
    triangles=[mesh.get_num_triangles(i) for i in range(3)]
    assert all(a>0 and a<=e for a,e in zip(triangles,record['lod_triangles']))
    E.set_metadata_tag(mesh,'WoodworkingBenchSourceManifestSHA256',source_sha);E.set_metadata_tag(mesh,'WoodworkingBenchRevision','V4')
    E.set_metadata_tag(mesh,'WoodworkingBladeAxis','X');E.set_metadata_tag(mesh,'WoodworkingBladePivotCm','86.5,0,88.8')
    mesh.modify();assert sub.set_lod_screen_sizes(mesh,[1,.45,.18]);save(mesh)
    report['meshes'].append({'mesh':mesh.get_path_name(),'triangles':triangles,'source_triangles':record['lod_triangles'],'dimensions_cm':dims,'bounds_origin_cm':[b.origin.x,b.origin.y,b.origin.z],'lod_screen_sizes':list(sub.get_lod_screen_sizes(mesh)),'convex_collision_count':convex,'materials':[{'slot':str(x.material_slot_name),'path':x.material_interface.get_path_name()} for x in mesh.static_materials]})
report.update(source_manifest_sha256=source_sha,textures=[t.get_path_name() for t in textures.values()],glass_opacity=.12,glass_blend=str(materials['WW_ClearSawHood'].get_editor_property('blend_mode')))
(W/'ue_import_receipt.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('WOODWORKING_V4_IMPORTED '+json.dumps(report,ensure_ascii=False))
