"""Recompute only the right-hand contact; reuse the finished left-arm candidate."""
from pathlib import Path
task=Path(__file__).resolve().parent
source=(task/'author.py').read_text().split('right=pickle.load')[0]
exec(compile(source,str(task/'author.py'),'exec'))
right={p:apply_right(p) for p in right36}
pickle.dump(right,open(HERE/'right.pkl','wb'))
print('Stable case-axis contact authored',flush=True)
