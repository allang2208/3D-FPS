"""Pack the approved generated cloud alpha as a linear material mask."""
from pathlib import Path
import shutil
from PIL import Image

P = Path(__file__).resolve().parent
icon = Path('C:/Users/allan/.codex/generated_images/01a0fac7-5db8-7c71-9676-89462fa1c1fa/exec-3253230a-d239-49b9-a43f-71762a465115.png')
shutil.copy2(icon, P/'Icons/ue_tang_dao_blade_2_auspicious_cloud_rune.png')
image = Image.open(P/'Artwork/CloudRune_Alpha.png').convert('RGBA')
image.getchannel('A').save(P/'Artwork/TangDao_CloudRune_Mask.png')
print('CLOUD_RUNE_ARTWORK_PACKED', image.size)
