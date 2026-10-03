"""Prepare the ordinary background Editor build with this batch's receipt."""
from pathlib import Path
O=Path(__file__).parent
text=(O.parent/'RSH12Integration20261003/build_editor.ps1').read_text(encoding='utf-8-sig')
text=text.replace('RSH12Integration20261003','RSH12SingleAction20261003').replace('rsh12-20261003.log','rsh12-single-action-20261003.log')
(O/'build_editor.ps1').write_text(text,encoding='utf-8-sig')
