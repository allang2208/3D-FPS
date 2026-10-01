"""Export only revised seat timber; preserve the original structure package."""
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT.parent/'Scripts/author_theatre.py'),run_name='__main__',init_globals={
    'EXPORT_KINDS':('SeatWood','WritingLedges'),
    'EXPORT_SUFFIX':'_V2',
    'EXPORT_OUT':ROOT/'Authored',
    'EXPORT_BLEND_NAME':'AnatomyTheatre_Seats_RoundedWood_V2.blend',
})
