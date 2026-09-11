import sys
from pathlib import Path
ROOT=Path(__file__).parent;sys.path.insert(0,str(ROOT));variant=sys.argv[sys.argv.index('--')+1];sys.argv.remove(variant)
source=(ROOT/'ReferenceWorkflow/build_m4.py').read_text().replace('O=Path(__file__).parent',"O=ROOT/'m4'/variant").replace('BASE=O.parents[1]','BASE=ROOT.parent').replace('from fit_pose import solve_arm','from front_pose import solve_arm')
if sys.argv[-1]=='--':sys.argv.pop()
exec(compile(source,str(ROOT/'ReferenceWorkflow/build_m4.py'),'exec'))
