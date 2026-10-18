"""Render the SAVED runtime family; read-only toward production assets."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parent))
import review_pose as R
out=Path(__file__).resolve().parent
saved=R.data['roasted_large_lamb'];candidate=json.loads((out/'fitted.json').read_text())
assert all(saved[k]==candidate[k] for k in ['digits','right_digits','palm_rotation','right_palm_rotation','grip_in_palm','right_grip_in_palm','times','keys'])
before=json.loads((out/'before_motion.json').read_text())
R.render(before,2.75,'before_saved')
R.render(saved,2.75,'final_present')
R.render(saved,4.65,'final_bite')
