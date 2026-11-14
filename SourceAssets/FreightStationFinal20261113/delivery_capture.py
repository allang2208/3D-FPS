from pathlib import Path
R=Path(__file__).resolve().parent
code=(R/'host.py').read_text('utf8').replace('range(1,21)','range(15,21)')
exec(compile(code,str(R/'host.py'),'exec'),{'__file__':str(R/'host.py')})
