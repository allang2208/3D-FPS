import subprocess,sys
from pathlib import Path
P=Path(__file__).parent
B='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
for key in ['ballast_hardened','ballast_rune','ballast_magic_orb']:
    for script in (['author_pommel.py']+(['refine_details.py'] if key!='ballast_hardened' else [])+['finish_collar.py','make_icon.py']):
        print('START',key,script,flush=True)
        with (P/(key+'_'+script+'.log')).open('w',encoding='utf-8') as log:
            subprocess.run([B,'--background','--factory-startup','--python-exit-code','1','--python',str(P/script),'--',key],stdout=log,stderr=subprocess.STDOUT,check=True)
        print('DONE',key,script,flush=True)
