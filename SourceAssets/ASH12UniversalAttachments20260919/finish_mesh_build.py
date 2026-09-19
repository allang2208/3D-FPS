"""Finalize from FBX in an RHI editor so render-only bounds cannot corrupt saves."""
import unreal as u,os,runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('repair_bounds.py')),run_name='__main__')
u.log('ASH_ATTACHMENT_TANGENT_BUILD_SAVED')
if os.environ.get('ASH_ATTACHMENT_OWNED_EDITOR')=='1':u.SystemLibrary.quit_editor()
