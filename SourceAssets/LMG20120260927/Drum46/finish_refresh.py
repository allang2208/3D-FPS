"""Refresh only the three new drum materials from the active J44 polymer."""
from pathlib import Path
O=Path(__file__).parent
source=(O/'install.py').read_text()
exec(compile(source.split("path=D+'/SM_LMG201_LargeDrum';task=")[0],str(O/'install.py'),'exec'))
receipt['finish']={'polymer_roughness':rough_poly,'coating_roughness':rough_coat,'polymer_reference':poly.get_path_name(),'coating_reference':coat.get_path_name()}
record();print('DRUM46_FINISH_SAVED',flush=True)
