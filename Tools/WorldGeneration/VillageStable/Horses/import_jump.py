"""Import just the jumping animation on the existing stable residents' skeleton."""
from pathlib import Path
import sys
import unreal as ue

here = Path(__file__).resolve().parent
sys.path[:0] = [str(here), str(here.parent)]
from import_horses import DEST, fbx_options, import_file, match_root_units, save

mesh = ue.load_asset(DEST+'/SK_StableWarhorse')
name = 'A_Warhorse_HurdleJump'
fbx = here.parents[3]/'SourceAssets/HillsVillageStable/JumpR13'/ (name+'.fbx')
clip = import_file(fbx,name,DEST+'/Animations',fbx_options(mesh.skeleton))
if not isinstance(clip,ue.AnimSequence) or clip.get_editor_property('skeleton') != mesh.skeleton or clip.get_play_length() <= 0:
    raise RuntimeError('Jump import did not yield a Warhorse animation')
match_root_units(clip,mesh)
save(clip)
