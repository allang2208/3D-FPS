"""Integrate the rendered part into the approved neutral gunsmith frame."""
from pathlib import Path
from PIL import Image,ImageOps
import sys
root,batch=map(Path,sys.argv[1:])
src=Path(__file__).resolve().parent
plate=Image.open(root/'SourceAssets/KukriRefinement20261027/StandardEmptyFrame.png').convert('RGBA').resize((1024,1024),Image.Resampling.LANCZOS)
subject=Image.open(batch/'eclipse_subject.png').convert('RGBA')
tone=ImageOps.grayscale(subject).point(lambda v:round(255*(v/255)**.78))
combined=Image.alpha_composite(plate,Image.merge('RGBA',(tone,tone,tone,subject.getchannel('A'))))
tone=ImageOps.grayscale(combined)
Image.merge('RGBA',(tone,tone,tone,combined.getchannel('A'))).save(src/'Export/bow_frontier_compound_riser_frontier_eclipse.png')
