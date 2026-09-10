from pathlib import Path
for name in ['verify_assets.py','verify_mat_saved.py']:
 p=Path(__file__).parent/name
 exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p)})
