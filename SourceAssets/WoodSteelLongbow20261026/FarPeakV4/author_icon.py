"""Render only the actual-part input; framed output is authored with imagegen."""
from pathlib import Path
import runpy

source = Path(__file__).parent.parent / 'FarPeakIconV6'
runpy.run_path(str(source / 'author_part_reference.py'), run_name='__main__')
print('Far Peak part reference saved. Regenerate the framed icon using '
      'FarPeakIconV6/imagegen-prompt.txt and the approved metal-frame master '
      'after model changes. The current saved framed PNG is preserved.', flush=True)
