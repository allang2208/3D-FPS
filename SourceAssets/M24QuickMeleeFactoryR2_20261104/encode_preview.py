"""Package the saved R2 preview and compact inspection sheets."""
from pathlib import Path
task=Path(__file__).resolve().parent
source=(task.parent/'M24QuickMeleeGrip20261104/GIF/encode.py').read_text(encoding='utf-8')
source=source.replace("O=Path(__file__).resolve().parent", "O=Path(__file__).resolve().parent/'GIF'")
source=source.replace('M24 快速近战 | ','M24 原厂换握 R2 | ')
source=source.replace('外侧观察 | 已保存动作离线预览','右手换握近景 | 已保存动作离线预览')
source=source.replace("folder/f'{i:03d}_arms.png'", "folder/f'{i:03d}_grip.png'")
exec(compile(source,'R2 GIF encoding','exec'))

# Compact sheets for the full arm silhouette and intermediate regrip poses.
for family in families:
    sheet=Image.new('RGB',(1280,4*240),(24,28,33));d=ImageDraw.Draw(sheet)
    for j,i in enumerate((0,3,5,7,10,14,18,22)):
        x=j%2*640;y=j//2*240
        for col,view in enumerate(('fps','arms')):
            sheet.paste(Image.open(O/family/f'{i:03d}_{view}.png').resize((320,210)),(x+col*320,y+30))
        d.text((x+8,y+6),f'{family} | {i/30:.3f}s',font=small,fill='white')
    sheet.save(O/f'{family}_arms_review.jpg',quality=84)
for family in ('skeleton_base','skeleton_mag10_balanced'):
    sheet=Image.new('RGB',(1280,4*450),(24,28,33));d=ImageDraw.Draw(sheet)
    for j,t in enumerate((.05,.10,.15,.25,.46,.55,.65,.72)):
        x=j%2*640;y=j//2*450
        sheet.paste(Image.open(O/family/f'contact_{t:.3f}.png'),(x,y+30))
        d.text((x+10,y+5),f'{family} | {t:.3f}s',font=font,fill='white')
    sheet.thumbnail((1000,1400));sheet.save(O/f'{family}_regrip_review.jpg',quality=84)
print('M24_R2_REVIEW_SHEETS_READY',flush=True)
