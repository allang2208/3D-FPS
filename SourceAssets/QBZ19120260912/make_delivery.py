"""Encode actual runtime captures at their recorded game-clock timestamps."""
from pathlib import Path
import re,json,subprocess,imageio_ffmpeg,sys
O=Path(__file__).parent;label=sys.argv[1] if len(sys.argv)>1 else 'complete';root=O.parents[1]
log=(O/f'runtime-{label}.log').read_text(encoding='utf-8-sig');frames=root/'Saved/QBZ191IntegrationAudit'/label
rows=[(int(n),float(t)) for n,t in re.findall(r'QBZ191_FRAME stage=\d+ index=(\d+) elapsed=([\d.]+)',log)]
rows=[(n,t) for n,t in rows if (frames/f'frame_{n:04}.png').exists()]
assert rows
concat=O/'gameplay.ffconcat';lines=['ffconcat version 1.0']
for i,(n,t) in enumerate(rows):
 lines += ["file '"+(frames/f'frame_{n:04}.png').as_posix()+"'",f'duration {rows[i+1][1]-t if i+1<len(rows) else .1:.6f}']
concat.write_text('\n'.join(lines)+'\n')
ff=imageio_ffmpeg.get_ffmpeg_exe();subprocess.run([ff,'-y','-loglevel','error','-safe','0','-i',str(concat),'-vf','fps=20,scale=800:-2','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(O/'QBZ191-gameplay.mp4')],check=True)
subprocess.run([ff,'-y','-loglevel','error','-i',str(O/'QBZ191-gameplay.mp4'),'-filter_complex','fps=12,scale=640:-1,split[a][b];[a]palettegen[p];[b][p]paletteuse','-loop','0',str(O/'QBZ191-gameplay.gif')],check=True)
result={'label':label,'passes':len(re.findall('QBZ191_INTEGRATION: PASS',log)),'failures':len(re.findall('QBZ191_INTEGRATION: FAIL',log)),'complete':'QBZ191_INTEGRATION: COMPLETE failures=0' in log,'frames':len(rows),'runtime_log':str(O/f'runtime-{label}.log'),'mesh':'/Game/Weapons/QBZ191/Calibrated/SK_QBZ191_Manny','video':str(O/'QBZ191-gameplay.mp4')}
(O/'acceptance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
