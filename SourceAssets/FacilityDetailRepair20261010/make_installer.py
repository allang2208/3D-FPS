"""Adapt the project's existing mesh/map save pipeline to these owned repairs."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
s=(PROJECT/'SourceAssets/HallStairCorner20261010/install.py').read_text('utf-8-sig')
s=s.replace('Import the stair/corner assets and save only their four existing dungeon maps.','Import detailed facility fittings and save the production and two transit maps.')
s=s.replace('HallStairCorner.Source','FacilityDetailRepair.Source').replace("R['REVISION']","R['REVISION']")
s=s.replace("if mesh and E.get_metadata_tag(mesh,'FacilityDetailRepair.Source')!=item['sha256']:raise RuntimeError('Preserve differing asset '+path)\n    if not mesh:","source=E.get_metadata_tag(mesh,'FacilityDetailRepair.Source') if mesh else None\n    if mesh and source not in (item['sha256'],item.get('previous_sha256','')):raise RuntimeError('Preserve differing asset '+path)\n    if not mesh or source!=item['sha256']:")
s=s.replace('t.replace_existing=False','t.replace_existing=bool(mesh)')
s=s.replace("if not mesh or source!=item['sha256']:","if not mesh or source!=item['sha256'] or item.get('force_reimport'):")
s=s.replace("        t=u.AssetImportTask();", "        if mesh and item.get('authored_tangents'):\n            previous_import=mesh.get_editor_property('asset_import_data')\n            if isinstance(previous_import,u.FbxStaticMeshImportData):previous_import.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)\n        t=u.AssetImportTask();")
s=s.replace('d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;',"d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS if item.get('authored_tangents') else u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS\n        ")
s=s.replace('build.recompute_tangents=True',"build.recompute_tangents=not item.get('authored_tangents',False)")
s=s.replace('    SM.set_lod_build_settings(mesh,0,build)',"    if item.get('tangent_basis')=='ue_legacy':build.use_mikk_t_space=False;build.recompute_tangents=True\n    SM.set_lod_build_settings(mesh,0,build)")
s=s.replace("for item in R['manifest']():report['saved_assets'].append(import_mesh(item));record()", "report['saved_assets'].extend(runpy.run_path(str(ROOT/'materials.py'))['install']());record()\n        for item in R['manifest']():report['saved_assets'].append(import_mesh(item));record()")
a=s.index('        changes={}\n');b=s.index("        bank['contract_sha1']=contract(catalog)",a)
s=s[:a]+'''        changes=R['apply_catalog'](catalog)
'''+s[b:]
s=s.replace("superseded=set(R['replacements']())","superseded=R['superseded']()")
s=s.replace("if module['id'] not in R['MODULES']:continue","if module['id']!='FacilityTransit':continue")
s=s.replace("report.update(stage='production_saved',replacements=changes,original_lights_preserved=True,added_corner_lights=R['lamps']())","report.update(stage='production_saved',replacements=changes,original_lights_preserved=True)")
s=s.replace('HALL_STAIR_CORNER_SAVED','FACILITY_DETAIL_REPAIR_SAVED')
(ROOT/'install.py').write_text(s,encoding='utf-8-sig')
