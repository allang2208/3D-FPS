"""Generate or resume one textured head from the three views chosen for the master artisan."""
import getpass
import os
import sys
from pathlib import Path
from PIL import Image
from pattern import SRC

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"VillageStable/Stablemaster"))
import meshy_production as jobs

def main():
    root=SRC/"HeadR4"
    jobs.ROOT=root
    inputs=root/"Inputs"
    inputs.mkdir(exist_ok=True)
    with Image.open(root/"HeadTurnaround.png") as source:
        w,h=source.size
        for i in range(3):
            view=source.crop((round(i*w/3),0,round((i+1)*w/3),h))
            view.convert("RGB").save(inputs/f"Head_{i+1}.jpg",quality=96,subsampling=0)
    key=os.environ.get("MESHY_API_KEY") or getpass.getpass("Meshy credential (hidden): ")
    jobs.task(key,"Head","multi-image-to-3d",dict(ai_model="meshy-7.1",geometry_resolution="2k",
        texture_model="meshy-7",texture_resolution="4k",enable_pbr=True,should_texture=True,
        should_remesh=True,topology="triangle",image_enhancement=False,target_polycount=90000,
        target_formats=["glb"]))

if __name__=="__main__":
    main()
