from pathlib import Path
folder=Path(__file__).parent
for name in ('finish_publication.py','import_icons.py','compile_materials.py'):
    file=folder/name
    exec(compile(file.read_text(encoding='utf-8'),str(file),'exec'),{'__file__':str(file),'__name__':'__main__'})
print('HK416_FINAL_PUBLICATION_SAVED')
