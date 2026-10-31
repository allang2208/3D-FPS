from pathlib import Path
import runpy
R=Path(__file__).resolve().parent
runpy.run_path(str(R/'author_roads.py'),run_name='__main__')
runpy.run_path(str(R/'publish.py'),run_name='__main__')
runpy.run_path(str(R/'inventory.py'),run_name='__main__',init_globals={'OUTPUT_NAME':'after.json'})
