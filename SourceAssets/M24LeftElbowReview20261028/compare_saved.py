from pathlib import Path
exec(compile((Path(__file__).parent/'compare_mesh.py').read_text().split('samples={}')[0],'extract_mesh','exec'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'m24_after.fbx'),use_anim=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');mesh=next(o for o in bpy.data.objects if o.type=='MESH');saved=extract(mesh,rig)
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_ElbowCorrected_Editable.blend'),use_scripts=False)
author=extract(bpy.data.objects['M24_V9_BareArms'],bpy.data.objects['M24_V9_Rig']);mapping={}
if set(saved['tri'])!=set(author['tri']):raise RuntimeError('Saved skin topology differs')
for key in saved['tri']:
 for uv,vi in saved['tri'][key].items():mapping[vi]=author['tri'][key][uv]
missing=set(author['shapes'])-set(saved['shapes'])
if missing:raise RuntimeError('Saved shapes missing '+str(missing))
errors={n:max(float(np.linalg.norm(saved['shapes'][n][v]-author['shapes'][n][w])*1000) for v,w in mapping.items()) for n in author['shapes']}
weight_error=max(abs(saved['weights'][v].get(n,0)-author['weights'][w].get(n,0)) for v,w in mapping.items() for n in set(saved['weights'][v])|set(author['weights'][w]))
report={'actual_saved_asset_readback':True,'skin_triangles_matched':len(saved['tri']),'skin_vertices_matched':len(mapping),'morphs_matched':len(errors)-1,'max_morph_coordinate_error_mm':max(errors.values()),'weight_max_delta':weight_error,'missing_shapes':list(missing),'shape_errors_mm':errors}
(O/'saved_mesh_comparison.json').write_text(json.dumps(report,indent=2))
if report['max_morph_coordinate_error_mm']>.02 or weight_error>1e-6:raise RuntimeError('Saved geometry differs from checked candidate')
print('M24_SAVED_MESH_COMPARE',json.dumps({k:v for k,v in report.items() if k!='shape_errors_mm'}),flush=True)
