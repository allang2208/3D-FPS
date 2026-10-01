records=[]
for kind,g in G.items():
 if not g['f']:continue
 name='SM_DataArchive_'+kind+globals().get('EXPORT_SUFFIX','');mesh=bpy.data.meshes.new(name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
 obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
 names=list(dict.fromkeys(g['m']))
 for key in names:mesh.materials.append(MATS[key])
 uv=mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
 for face,mat,coords,smooth in zip(mesh.polygons,g['m'],g['uv'],g['smooth']):
  face.material_index=names.index(mat);face.use_smooth=smooth
  dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
  scale=.8 if mat=='ServicePaint' else .075 if mat=='V2_CeramicFractureCore' else 1.28 if 'WallRelief' in mat else 2
  for ci,li in enumerate(face.loop_indices):
   p=mesh.vertices[mesh.loops[li].vertex_index].co
   uv.data[li].uv=coords[ci] if coords is not None else (p[dims[0]]/scale,p[dims[1]]/scale)
   age.data[li].color=(.13+.13*max(0,math.sin(p.x*1.2+p.y*.8+p.z*3)),0,0,1)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 if kind!='Tiles':
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 if kind in ('Walls','Floors','FurnaceMasonry','FurnaceDoors','LoadingTroughs','ObservationDeck','Stairs','AshPit','SamplePortCaps'):
  bevel=obj.modifiers.new('Manufactured arris','BEVEL');bevel.width=.003 if kind in ('Stairs','Coping') else .005;bevel.segments=2;bevel.limit_method='ANGLE'
  bpy.ops.object.modifier_apply(modifier=bevel.name)
 tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
 mesh=obj.data;uv=mesh.uv_layers.active.data
 for face in mesh.polygons:
  ids=list(face.loop_indices);a,b,c=(uv[i].uv.copy() for i in ids)
  if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1.e-12:continue
  dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
  for li in ids:
   p=mesh.vertices[mesh.loops[li].vertex_index].co;uv[li].uv=(p[dims[0]]/2,p[dims[1]]/2)
 fbx=OUT/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
 records.append({'name':name,'kind':kind,'fbx':str(fbx),'materials':{'RS_'+key:MAPPING[key] for key in names},
                 'triangles':len(mesh.polygons),'collision':kind not in ('Tiles','Frames','Nosing','CableTrays','CableHangers','Conduits','DisplayScreens','DisplayMounts','LampHangers'),
                 'sample_only':kind=='SamplePortCaps'})
 print('INCINERATOR_AUTHORED',kind,len(mesh.polygons),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/globals().get('EXPORT_BLEND_NAME','AbandonedIncineratorHall_Subject.blend')))
(OUT/'manifest.json').write_text(json.dumps({'objects':records,'tests_run':False,'rendered':False,'revision':CFG['revision'],
 'ceramic_source':'DungeonTileFracture20260922 through CorridorSurfaces','source_units':'metres; UE centimetres'},indent=2),encoding='utf-8')
print('INCINERATOR_SUBJECT_AUTHORED',len(records),flush=True)
