"""Produce the editable blade, FBX, PBR maps and monochrome catalog icon."""
from pathlib import Path
import subprocess
import sys
from PIL import Image,ImageOps

P=Path(__file__).resolve().parent
subprocess.run([sys.executable,str(P/'paint_finish.py')],check=True)
subprocess.run(['E:/Program Files/Blender Foundation/Blender 5.1/blender.exe',
                '--background','--factory-startup','--python-exit-code','1',
                '--python',str(P/'author_blade.py')],check=True)
path=P/'Icons/ue_highland_claymore_blade_1_highland_ridge_piercer.png'
with Image.open(path) as src:
    rgba=src.convert('RGBA')
gray=ImageOps.grayscale(rgba)
Image.merge('RGBA',(gray,gray,gray,rgba.getchannel('A'))).save(path)
