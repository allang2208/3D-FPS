from pathlib import Path
exec(compile((Path(__file__).parent/'motion.py').read_text().split("if __name__=='__main__':")[0],'motion','exec'))
result=[]
for f in (10,15,17,20,26,33,39,45,50):
 donor=compose(entry('base','fire'),f/30)[0];target=compose(entry('base','equip'),(f+3)/30)[0];idle=compose(entry('base','idle'),0)[0]
 result.append({'frame':f,'source':{n:[round(x,5) for x in donor[n].translation] for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l')},'current':{n:[round(x,5) for x in target[n].translation] for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l')}})
(O/'shoulder_source.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
