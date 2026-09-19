import json,time,subprocess,sys
from pathlib import Path
P=Path(__file__).parent
while True:
    subprocess.run([sys.executable,str(P/'generate.py'),'fetch'],check=True)
    finished=True
    for seed in [91703,91727]:
        h=P/f'seed_{seed}'/'history.json'
        if not h.exists():finished=False;continue
        status=json.loads(h.read_text())['status']['status_str']
        if status=='error':raise RuntimeError('Generation failed: '+str(seed))
        if status!='success':finished=False
    if finished:break
    time.sleep(45)
print('BALANCED_CANDIDATES_DOWNLOADED',flush=True)
