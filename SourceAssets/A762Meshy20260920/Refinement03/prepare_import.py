"""Adapt the established importer to this revision's two changed mesh assets."""
from pathlib import Path
O=Path(__file__).parent
text=(O.parent/'Refinement02/import_reconstruction.py').read_text(encoding='utf-8')
text=text.replace("P='/Game/Weapons/A762/Refinement02'","P='/Game/Weapons/A762/Refinement03'")
text=text.replace("['SK_A762_Manny','SM_A762_RearSight','SM_A762_FrontSight']","['SK_A762_Manny','SM_A762_RearSight']")
text=text.replace("[('SK_A762_Manny',True),('SM_A762_RearSight',False),('SM_A762_FrontSight',False)]","[('SK_A762_Manny',True),('SM_A762_RearSight',False)]")
text=text.replace('A762_RECONSTRUCTION02_IMPORTED_AND_SAVED','A762_REFINEMENT03_IMPORTED_AND_SAVED')
(O/'import_surfaces.py').write_text(text,encoding='utf-8')
print('Prepared Refinement03 import batch')
