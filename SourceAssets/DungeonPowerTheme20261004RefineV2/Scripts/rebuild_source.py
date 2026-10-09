"""Rebuild this editable source package without touching Unreal or shared assets.

Usage: python Scripts/rebuild_source.py --blender /path/to/blender
Requires Pillow and fontTools for native Chinese label artwork.
"""
import argparse,subprocess,sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--blender',default='blender')
    args=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    scripts=root/'Scripts'
    for name in ('prepare_design.py','layout_reuse.py','prepare_revision.py',
                 'prepare_chinese_container_labels.py','prepare_chinese_cabinet_overlay.py','prepare_chinese_server_overlay.py','prepare_chinese_workshop_overlay.py',
                 'place_revision_supplement.py'):
        subprocess.run([sys.executable,str(scripts/name)],cwd=root,check=True)
    subprocess.run([sys.executable,str(root/'UpperControlRoom20261005/layout.py')],cwd=root,check=True)
    # The original source library is a preserved editable master, not a set of
    # stand-in assets. Rebuild it if it is absent from a complete source copy.
    if not (root/'Authored/Reused_Original_Assets.blend').exists():
        subprocess.run([args.blender,'--background','--threads','4','--python',str(scripts/'prepare_reuse.py')],cwd=root,check=True)
    for name in ('author_scene.py','assemble_reused_assets.py','apply_source_surfaces.py','assemble_revision_supplement.py'):
        subprocess.run([args.blender,'--background','--threads','4','--python',str(scripts/name)],cwd=root,check=True)
    for name in ('prepare_modules.py','write_layout_drawing.py','finalize_source_receipts.py'):
        subprocess.run([sys.executable,str(scripts/name)],cwd=root,check=True)
    print('POWER_REFINE_V2_SOURCE_REBUILT_NO_UE_NO_RENDER_NO_TESTS')

if __name__=='__main__':main()
