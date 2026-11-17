"""Encode four real UE cloud recordings with identical playback and a labeled overview."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

p=argparse.ArgumentParser()
p.add_argument('root',type=Path)
a=p.parse_args()
versions=[('StormDomainV2','A  雷暴旧版 StormDomainV2'),('ChargedV3','B  暴风雪厚云 ChargedV3'),
          ('StormV2','C  暴风雪三层云 StormV2'),('RollingV1','D  当前版本 RollingV1')]
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
all_frames=[]
receipts=[]

def encode(frames,path):
    # Use one palette throughout each clip; no grading, generated frames or retiming.
    columns=12
    samples=Image.new('RGB',(128*columns,96*((len(frames)+columns-1)//columns)))
    for i,im in enumerate(frames):
        samples.paste(im.resize((128,96),Image.Resampling.LANCZOS),((i%columns)*128,(i//columns)*96))
    palette=samples.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    output=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    output[0].save(path,save_all=True,append_images=output[1:],duration=50,loop=0,optimize=True,disposal=1)

for version,label in versions:
    folder=a.root/version
    report=dict(line.split('=',1) for line in (folder/'capture.txt').read_text(encoding='utf-8-sig').splitlines() if '=' in line)
    assert report['cloud_version']==version,(version,report)
    process=json.loads((folder/'process.json').read_text(encoding='utf-8-sig'))
    assert process['exit_code']==0,process
    paths=sorted(folder.glob('frame-*.png'))
    assert len(paths)==int(report['saved_frames'])
    frames=[]
    for path in paths:
        with Image.open(path) as im:frames.append(im.convert('RGB'))
    if all_frames:assert len(frames)==len(all_frames[0])
    encode(frames,folder/(version+'.gif'))
    all_frames.append([im.resize((640,480),Image.Resampling.LANCZOS) for im in frames])
    receipts.append(dict(version=version,source_asset=report['cloud_asset'],frames=len(frames),fps=20,
                         duration=len(frames)/20,dimensions=list(frames[0].size),gif=str((folder/(version+'.gif')).resolve())))

# Keep the entire frame for every variant, including the much larger V3 cloud.
# Do not crop away its lower billows to fit the smaller variants.
frames=[]
for index in range(len(all_frames[0])):
    panel=Image.new('RGB',(1280,1024),(24,28,34))
    draw=ImageDraw.Draw(panel)
    for slot,((version,label),source) in enumerate(zip(versions,all_frames)):
        x,y=(slot%2)*640,(slot//2)*512
        draw.text((x+12,y+3),label,font=font,fill=(238,242,247))
        crop=source[index].resize((640,480),Image.Resampling.LANCZOS)
        panel.paste(crop,(x,y+32))
    frames.append(panel)
encode(frames,a.root/'cloud-versions-comparison.gif')
frames[min(50,len(frames)-1)].save(a.root/'comparison-keyframe.png')
full=Image.new('RGB',(1280,1024),(24,28,34))
draw=ImageDraw.Draw(full)
for slot,((version,label),source) in enumerate(zip(versions,all_frames)):
    x,y=(slot%2)*640,(slot//2)*512
    draw.text((x+12,y+3),label,font=font,fill=(238,242,247))
    full.paste(source[min(50,len(source)-1)].resize((640,480),Image.Resampling.LANCZOS),(x,y+32))
full.save(a.root/'full-scene-keyframe.png')
receipt=dict(source='UE AFPSBlizzardZone isolated comparison',clips=receipts,fps=20,
             camera_and_lighting='identical; recorded dark backdrop',cloud_height_and_footprint='current level-one Blizzard',
             gameplay_and_assets_modified=False,retouched=False,
             comparison_crop=[0,0,960,720],comparison=str((a.root/'cloud-versions-comparison.gif').resolve()))
(a.root/'comparison-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(receipt,ensure_ascii=False),flush=True)
