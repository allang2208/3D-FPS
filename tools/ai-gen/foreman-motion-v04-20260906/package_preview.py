from pathlib import Path
from PIL import Image,ImageDraw
import math,json
R=Path(__file__).resolve().parent
report={}
for clip,duration in [('Idle',1.),('Walk',1.5),('Attack',1.5),('Death',1.4),('WalkGameSpeed',1.5*(.40/(1.5*.62))/.65)]:
 paths=sorted((R/'runtime'/clip).glob('*.png'));assert len(paths)==math.ceil(duration*24)+1,(clip,len(paths))
 frames=[]
 for path in paths:
  im=Image.open(path).convert('RGB').crop((400,45,1490,1030));im.thumbnail((640,640));frames.append(im)
 if clip!='Death':frames=frames[:-1]
 n=len(frames)-1 if clip=='Death' else len(frames)
 delays=[round((i+1)*duration*100/n)*10-round(i*duration*100/n)*10 for i in range(n)]
 if clip=='Death':delays.append(1000)
 frames[0].save(R/(clip+'.gif'),save_all=True,append_images=frames[1:],duration=delays,loop=0,disposal=2)
 check=Image.open(R/(clip+'.gif'));total=0
 for i in range(check.n_frames):check.seek(i);total+=check.info.get('duration',0)
 assert total==sum(delays)
 report[clip]={'frames':check.n_frames,'duration_ms':total,'source':'Godot default D3D12 actual GLB render'}
 if clip in ['Attack','Death','Walk']:
  selected=[frames[round(i*(len(frames)-1)/11)] for i in range(12)]
  sheet=Image.new('RGB',(1200,900))
  for i,im in enumerate(selected):im=im.copy();im.thumbnail((300,300));sheet.paste(im,((i%4)*300,(i//4)*300))
  sheet.save(R/(clip+'-contact.jpg'),quality=90)
(R/'preview-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
