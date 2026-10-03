"""Install the five authored clips through the project bridge."""
from pathlib import Path
O=Path(__file__).parent
exec(compile((O.parent/'RifleMagazineGrip20260922/import_animations.py').read_text(),str(O/'import_animations.py'),'exec'))
