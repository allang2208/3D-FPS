"""Create the new revision's authoring entry from the accepted V2 source."""
from pathlib import Path
root=Path(__file__).resolve().parent
previous=root.parent/'RefinementV2'
for name in ('refinement_design.py','refinement_parts.py','author.py','import_assets.py','install_level.py','publish.py'):
 text=(previous/name).read_text(encoding='utf8')
 text=text.replace('CyberpunkApartment.RefinementV2','CyberpunkApartment.RefinementV3')
 text=text.replace("/RefinementV2'","/RefinementV3'")
 if name=='refinement_design.py':
  text += "\nSCENE_SCALE=1.20\n"
 if name=='refinement_parts.py':
  text=text.replace(" return dict(containers=containers,revision=", " e['cubby']=cubby;e['container_instance']=instance;e['retire_mesh']=retire\n return dict(containers=containers,revision=")
 if name=='author.py':
  text=text.replace("refinement=apply_refinement(globals())", "refinement=apply_refinement(globals())\nfrom refinement_v3_parts import apply_v3\napply_v3(globals(),refinement)")
  text=text.replace("records=[]\n", "records=[]\nprevious_rows={r['key']:r for r in json.loads((ROOT.parent/'RefinementV2/assembly.json').read_text('utf8'))['meshes']}\n")
  text=text.replace("for face in (mesh.polygons if kind!='WindowDrapes' else []):", "for face in (mesh.polygons if kind!='WindowDrapes' else []):\n  if order[face.material_index] in ('OfficeUI','WorkoutUI'):continue")
  text=text.replace(" bpy.ops.export_scene.fbx(filepath=str(fbx)", " reuse_old=kind in previous_rows and kind not in v3_changed\n if not reuse_old:bpy.ops.export_scene.fbx(filepath=str(fbx)")
  text=text.replace(" for co in hulls:bpy.data.objects.remove(co,do_unlink=True)", " if reuse_old:\n  records[-1]=dict(previous_rows[kind],reused_revision='RefinementV2')\n for co in hulls:bpy.data.objects.remove(co,do_unlink=True)")
  text=text.replace("source_layout_scale=1.25", "source_layout_scale=1.50,instance_scale=SCENE_SCALE")
 if name=='import_assets.py':
  text=text.replace(" for key in FINISHES:finish(key)", " for key in FINISHES:finish(key)\n from import_screens import install_screens\n install_screens()")
  text=text.replace("  digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest()", "  if row.get('reused_revision'):\n   report['meshes'][row['key']]=dict(path=asset(row['asset']).get_path_name(),reused_revision=row['reused_revision']);continue\n  digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest()")
  text=text.replace("wire(rgb([v*emission for v in color]),'EmissiveColor'", "wire(rgb([v*emission for v in color]),'Emissive Color'")
 if name=='install_level.py':
  text=text.replace("tag(a,['ColdSteel.SceneContainer'])", "tag(a,['ColdSteel.SceneContainer','ColdSteel.SceneContainer.Reclosable'])")
  text=text.replace(" report['spawn']=sp", " from install_v3_details import finish_layout\n report['v3']=finish_layout(world,OWNER,SCENE_SCALE)\n report['spawn']=sp")
 if name=='publish.py':
  text += "\nrunpy.run_path(str(root/'install_sky.py'),run_name='__main__')\n"
 (root/name).write_text(text,encoding='utf8')
print('APARTMENT_V3_SOURCE_ENTRIES_CREATED')
