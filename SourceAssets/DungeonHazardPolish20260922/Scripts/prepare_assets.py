from pathlib import Path
for filename in ('import_materials.py','read_inputs.py','complete_scene.py'):
    p=Path(__file__).with_name(filename)
    exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
