"""Contact sheets of unretouched new UE screenshots and skin diagnostics."""
from pathlib import Path
import json,sys
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
capture=HERE.parent/'Wrist34/geometry_wrist_thirty_eight_clearance'
out=HERE/'sheets_clearance';out.mkdir(exist_ok=True)

def sheet(rows,folder,path,cols=4,width=400):
    sample=Image.open(folder/rows[0]['file']);height=round(width*sample.height/sample.width)
    result=Image.new('RGB',(cols*width,((len(rows)+cols-1)//cols)*(height+24)),'#202020')
    draw=ImageDraw.Draw(result)
    for i,row in enumerate(rows):
        image=Image.open(folder/row['file']).convert('RGB');image.thumbnail((width,height))
        x=(i%cols)*width;y=(i//cols)*(height+24);result.paste(image,(x,y+24))
        draw.text((x+4,y+5),f"{path.stem} source={row['source']:.3f}",fill='white')
    result.save(path,quality=94)

if '--contact' in sys.argv:
    rows=json.loads((HERE/'contact_clearance_inventory.json').read_text())
    for case in sorted({r['case'] for r in rows}):
        for view in ['palm','outside']:
            part=[dict(file=r['image'],source=r['source']) for r in rows if r['case']==case and r['view']==view]
            for start in range(0,len(part),12):
                sheet(part[start:start+12],HERE/'contact_clearance',out/f'{case}_{view}_{start//12:02d}.jpg')
else:
    for folder in sorted(capture.iterdir()):
        if not folder.is_dir():continue
        rows=json.loads((folder/'review.json').read_text())['frames']
        if 'wrist_' in folder.name:
            sheet(rows,folder,out/(folder.name+'.jpg'),cols=4,width=400)
        else:
            # All supplied player-view intermediate contact and regrip samples.
            for start in range(0,len(rows),16):
                sheet(rows[start:start+16],folder,out/f'{folder.name}_player_{start//16:02d}.jpg')
    receipt=json.loads((capture/'receipt.json').read_text())
    assert receipt['complete'] and not receipt['asset_writes']
    print('New UE capture cases',len(receipt['cases']))
