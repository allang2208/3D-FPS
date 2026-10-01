"""Export grouped meshes, preserving source UVs, round silhouettes and real collision."""
records=[]
no_collision={'Frames','RoofRibs','Hardware','RackHardware','RackBraces','Signs','SignSupports',
 'FloorMarkings','Nosing','HoistChain','HoistHook','CableTrays','LampHangers','Rollers'}
bevel_kinds={'Walls','Columns','Floors','Racks','RackDecks','RackGuards','Dock','DockEdge','RollerFrame','StairTreads','Hoist','HoistHook'}
for kind,g in G.items():
    if not g['f']:continue
    name='SM_CargoWarehouse_'+kind+globals().get('EXPORT_SUFFIX','');mesh=bpy.data.meshes.new(name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    names=list(dict.fromkeys(g['m']))
    for key in names:mesh.materials.append(MATS[key])
    uv=mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for face,mat,coords,smooth in zip(mesh.polygons,g['m'],g['uv'],g['smooth']):
        face.material_index=names.index(mat);face.use_smooth=smooth
        dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
        scale=.8 if mat=='ServicePaint' else 2.
        for ci,li in enumerate(face.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=coords[ci] if coords is not None else (p[dims[0]]/scale,p[dims[1]]/scale)
            # Existing industrial shader reads R as restrained wear rather than RGB tint.
            age.data[li].color=(.09+.12*max(0,math.sin(p.x*.83+p.y*.59+p.z*2.1)),0,0,1)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    # Retain intentional front-face winding of disconnected printed dials/signs.
    # Closed pipe walls are authored with connected outer/inner/rim topology.
    if kind not in {'Instruments','Signs','ControlHardware','FloorMarkings','WetPipework','GasDucts','Exhaust'}:
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    if kind in bevel_kinds:
        bevel=obj.modifiers.new('Fabricated edge radii','BEVEL');bevel.width=.004 if kind!='EquipmentPlinths' else .012
        bevel.segments=3;bevel.limit_method='ANGLE';bevel.harden_normals=True;bpy.ops.object.modifier_apply(modifier=bevel.name)
        normal=obj.modifiers.new('Weighted face normals','WEIGHTED_NORMAL');normal.keep_sharp=True
        bpy.ops.object.modifier_apply(modifier=normal.name)
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    mesh=obj.data;uv=mesh.uv_layers.active.data
    for face in mesh.polygons:
        ids=list(face.loop_indices);a,b,c=(uv[i].uv.copy() for i in ids)
        if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1.e-12:continue
        dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
        for li in ids:
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv[li].uv=(p[dims[0]]/2,p[dims[1]]/2)
    collision_objects=[]
    for run in [r for r in RAIL_RUNS if r['kind']==kind]:
        a,b=Vector(run['a']),Vector(run['b']);d=b-a;d.z=0;d.normalize();s=Vector((-d.y,d.x,0))
        vs=[p+s*side*.04+Vector((0,0,z)) for p in (a,b) for side,z in ((-1,0),(1,0),(1,run['height']+.04),(-1,run['height']+.04))]
        cm=bpy.data.meshes.new('UCX_'+name+'_%02d'%len(collision_objects))
        cm.from_pydata(vs,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);cm.update()
        co=bpy.data.objects.new(cm.name,cm);bpy.context.scene.collection.objects.link(co);co.select_set(True);collision_objects.append(co)
    if globals().get('EXPORT_KINDS') and kind not in EXPORT_KINDS:
        for co in collision_objects:co.hide_render=True;co.hide_viewport=True
        continue
    fbx=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    records.append(dict(name=name,kind=kind,fbx=str(fbx),materials={'RS_'+k:MAPPING[k] for k in names},
        triangles=len(mesh.polygons),collision=kind not in no_collision,sample_only=kind=='SamplePortCaps',
        nanite=kind not in {'Signs','FloorMarkings','Hardware','RackHardware','RackBraces','SignSupports','HoistChain','HoistHook','Nosing','CableTrays','LampHangers','Rollers'},
        guardrail_drop=kind in {'Railings','StairRails'},simple_collision_hulls=len(collision_objects)))
    for co in collision_objects:co.hide_render=True;co.hide_viewport=True
    print('FLUE_GAS_EXPORTED',kind,len(mesh.polygons),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'AbandonedCargoWarehouseStation_Source.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,revision=CFG['revision'],tests_run=False,rendered=False,
    source_units='metres; UE centimetres',coordinates='Blender (x,y,z) -> Unreal (100*x,-100*y,100*z)'),indent=2),encoding='utf-8')
print('FLUE_GAS_EXPORT_COMPLETE',len(records),flush=True)
