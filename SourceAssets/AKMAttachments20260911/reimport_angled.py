from pathlib import Path
p=Path(__file__).with_name('import_assets.py')
s=p.read_text().split('opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH')[0]
s=s.replace('for key,spec in sources.items():',"for key,spec in sources.items():\n if key not in ['angled','optic']:continue")
exec(compile(s,str(p),'exec'))
u.log('AKM_ANGLED_REIMPORT_PASS')
