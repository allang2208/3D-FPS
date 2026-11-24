"""Use the approved ImageGen empty plate for every factory slot, without rescaling the model by eye."""
from pathlib import Path
import sys
from PIL import Image, ImageOps

root, batch = map(Path, sys.argv[1:])
export = Path(__file__).resolve().parent / 'Export'
plate = Image.open(root / 'SourceAssets/KukriRefinement20261027/StandardEmptyFrame.png').convert('RGBA')
plate = plate.resize((1024, 1024), Image.Resampling.LANCZOS)
for slot in ('riser', 'grip', 'string', 'arrow_rest', 'stabilizer', 'sight_category'):
    part = Image.open(batch / 'Subjects' / (slot + '.png')).convert('RGBA')
    # Lift the dark cord, carbon limbs and grip enough to separate their edges
    # from the graphite plate at card size. Leave the plate's levels intact.
    tone = ImageOps.grayscale(part).point(lambda v: round(255*(v/255)**.72))
    subject = Image.merge('RGBA', (tone, tone, tone, part.getchannel('A')))
    combined = Image.alpha_composite(plate, subject)
    gray = ImageOps.grayscale(combined)
    result = Image.merge('RGBA', (gray, gray, gray, combined.getchannel('A')))
    key = 'category_sight' if slot == 'sight_category' else slot + '_false'
    result.save(export / ('bow_frontier_compound_' + key + '_r3.png'))
