"""Pack the Project Nature grass albedo and its matching blade opacity into one distant mip chain."""
from pathlib import Path
import sys
from PIL import Image

def pack(source, destination):
    with Image.open(source/'color.png') as paint, Image.open(source/'mask.png') as coverage:
        if paint.size != coverage.size:
            raise ValueError('Grass albedo and opacity have different atlas layouts')
        # Preserve colour outside the cutout so BC filtering does not create dark outlines.
        image = paint.convert('RGB').resize((512,512),Image.Resampling.LANCZOS)
        image.putalpha(coverage.getchannel('R').resize(image.size,Image.Resampling.LANCZOS))
        image.save(destination/'T_HillsFarGrass.png')

if __name__=='__main__':
    pack(Path(sys.argv[1]),Path(sys.argv[2]))
