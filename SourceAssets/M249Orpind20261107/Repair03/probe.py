from pathlib import Path
import unreal as u,json
root=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
report={'slots':[],'static':[],'clips':{},'morphs':[m.get_name() for m in mesh.get_editor_property('morph_targets')]}
for s in mesh.materials:
    m=s.material_interface
    report['slots'].append(dict(slot=str(s.material_slot_name),material=m.get_path_name()))
groups=[]
for key in ('holographic','magnifier'):
    p='/Game/Weapons/M249/Assembly/SM_M249_'+key
    a=u.load_asset(p);mats=[s.material_interface.get_path_name() for s in a.static_materials]
    report['static'].append(dict(mesh=p,materials=mats,slots=[str(s.material_slot_name) for s in a.static_materials]))
    groups.append(dict(name=key,parts=[dict(mesh=p,after=mats)],camera_cm=[30,22,26],target_cm=[0,0,0]))
for role in ('idle','reload','reload_empty'):
    a=u.load_asset('/Game/Weapons/M249/Animations/A_M249_'+role)
    dm=a.get_editor_property('data_model_interface')
    report['clips'][role]=dict(seconds=a.get_play_length(),keys=dm.get_number_of_keys(),fps=str(dm.get_frame_rate()))
surface=u.load_asset('/Game/Weapons/M249/Materials/M_M249_Surface')
report['surface']=dict(two_sided=surface.get_editor_property('two_sided'),blend_mode=str(surface.get_editor_property('blend_mode')))
(root/'before_probe.json').write_text(json.dumps(report,indent=2))
(root/'optic_surface_manifest.json').write_text(json.dumps(dict(after_only=True,groups=groups),indent=2))
skin=u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/PKM/SK_PKM_BareArmsV7')
task=u.AssetExportTask();task.object=skin;task.filename=str(root/'PKM_V9_Arms.fbx')
task.automated=True;task.prompt=False;task.replace_identical=True
task.exporter=u.SkeletalMeshExporterFBX();task.options=u.FbxExportOption()
task.options.set_editor_property('export_morph_targets',True)
task.options.set_editor_property('level_of_detail',False)
if not u.Exporter.run_asset_export_task(task):raise RuntimeError('V9 native arms export failed')
report['v9_morphs']=[m.get_name() for m in skin.get_editor_property('morph_targets')]
(root/'before_probe.json').write_text(json.dumps(report,indent=2))
print('M249_REPAIR03_PROBE',json.dumps(report),flush=True)
