"""Rebuild only the failed lid from its pre-thickness source, retaining Detail35 features."""
from pathlib import Path
O=Path(__file__).parent
source=(O.parent/'Detail35/model.py').read_text()
source=source.split('# Precision topology replaces')[0]
source=source.replace("path=O/'Textures'/", "path=O.parent/'Detail35/Textures'/")
source=source.replace("np.load(O/'Work'/", "np.load(O.parent/'Detail35/Work'/")
source=source.replace('sol.use_even_offset=True','sol.use_even_offset=False;sol.thickness_clamp=.5')
source=source.replace("'Continuous formed inner wall'","'Bounded normal-offset inner wall'")
exec(compile(source,str(O/'rebuild_lid.py'),'exec'),globals())
sample=json.loads((O/'coating_sample.json').read_text());color=sample['base_linear_median'];metal=sample['metallic_median'];rough=sample['roughness_median']
for mat,rgb,met,r in [(coat,color,metal,rough),(inner,[x*.78 for x in color],metal,.68),(satin,[x*1.65 for x in color],.65,.50)]:
 bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(*rgb,1);bs.inputs['Metallic'].default_value=met;bs.inputs['Roughness'].default_value=r
# Even-offset compensation on the generated needle/concave corners created
# metre-long spikes. Rebuild from the outer shell, using a bounded unit-normal
# displacement; do not clamp already exploded vertices or leave damaged faces.
for ob in list(bpy.context.scene.objects):
 if ob not in [cover,rig]:bpy.data.objects.remove(ob,do_unlink=True)
select([cover,rig]);path=O/'Exports/SK_LMG201_R36_Cover.fbx'
bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_R36_Lid.blend'))
# The user requested a final scoped check: record the actual new cover geometry.
inv=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted();v=np.array([inv@cover.matrix_world@x.co for x in cover.data.vertices]);edges=np.array([list(e.vertices) for e in cover.data.edges]);lengths=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)
outside=(abs(v[:,0]-.0008)>.045)|(v[:,1]<-.25)|(v[:,1]>-.08)|(v[:,2]<.05)|(v[:,2]>.095)
report={'export':str(path),'source':'Detail35 lid with original Surface32 exterior before Solidify','repair':'Disable unbounded even-thickness compensation; bounded normal offset and edge clamp','bounds_m':np.stack([v.min(0),v.max(0)]).tolist(),'max_edge_m':float(lengths.max()),'outlier_vertices':int(outside.sum()),'vertex_count':len(v),'faces':len(cover.data.polygons),'material_slots':[m.name for m in cover.data.materials],'bind_bone':'LMG201_Cover'}
(O/'lid.json').write_text(json.dumps(report,indent=2))
if outside.any():raise RuntimeError('Rebuilt lid exceeds its own original local envelope')
print('REPAIR36_LID',json.dumps(report),flush=True)
