from pathlib import Path
O=Path(__file__).parent
for name in ('install_assets.py','install_profile.py'):
    script=O/name
    exec(compile(script.read_text(),str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
