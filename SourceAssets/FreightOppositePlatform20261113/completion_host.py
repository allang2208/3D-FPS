from pathlib import Path
r=Path(__file__).resolve().parent
code=(r/'photo_host.py').read_text('utf8').replace('range(1,25)','range(16,32)')
exec(compile(code,str(r/'photo_host.py'),'exec'),{'__file__':str(r/'photo_host.py')})
