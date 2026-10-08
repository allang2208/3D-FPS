"""Assemble this task's real-skin motion renders for visual review."""
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/MeleeV17/Review/V17')
groups={'Bite':[0,12,15,17,21,35], 'Flurry':[0,12,16,22,28,48]}
sheet=Image.new('RGB',(480*6,430*2),(24,26,30))
for row,(role,indices) in enumerate(groups.items()):
    for col,index in enumerate(indices):
        frame=Image.open(ROOT/role/f'{index:03}.png').convert('RGB')
        sheet.paste(frame,(480*col,430*row))
        ImageDraw.Draw(sheet).text((480*col+12,430*row+408),f'{role}  {index/30:.3f}s',fill='white')
    frames=[Image.open(p).convert('RGB') for p in sorted((ROOT/role).glob('*.png'))]
    durations=[33 if i%3 else 34 for i in range(len(frames))]
    frames[0].save(ROOT/(role+'_V17.gif'),save_all=True,append_images=frames[1:],duration=durations,loop=0)
sheet.save(ROOT/'melee_v17_review_sheet.png')
print('MELEE_REVIEW_MEDIA_SAVED')
