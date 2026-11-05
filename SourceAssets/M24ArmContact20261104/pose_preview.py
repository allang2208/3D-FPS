from pathlib import Path
__file__=str(Path(__file__).parent/'common.py')
exec(compile(Path(__file__).read_text(),'contact studio','exec'))
exec(compile((TASKOUT/'arm.py').read_text(),'native hinge','exec'))
import sys
fr=ContactFrame('mag10',18,'old');x=fr.initial()
if '--latest' in sys.argv:
    history=json.loads((TASKOUT/'mag10_old_iterations.json').read_text());x=np.array(history[-1]['x'])
if '--solved' in sys.argv:x=np.array(json.loads((TASKOUT/'grip_anchors.json').read_text())['mag10']['old']['parameters'])
row=fr.pose(x)
label='solved' if '--solved' in sys.argv else ('latest' if '--latest' in sys.argv else 'initial')
for view in ('back','bottom'):picture(row,'mag10',str(TASKOUT/label),view)
(TASKOUT/'preview_parameters.json').write_text(json.dumps({'x':x.tolist()}))
print('POSE_PREVIEW_SAVED',flush=True)
