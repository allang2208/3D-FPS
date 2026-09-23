from pathlib import Path
root=Path(__file__).parent
for source in [root/'reimport_mesh.py',root.parent/'Integration04/import_motion.py',root/'check_imported_pose.py']:
 exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),{'__file__':str(source),'__name__':'__main__'})
