from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'fit_grip_position.py').read_text().split('\nbest=')[0],'surface_fit','exec'))
idle,_=pose('idle',0);nativehand=rest['WPN_root']@idle['WPN_root'].inverted()@idle['hand_r'];currenthand=inv@row['hand_r'];localpoints=[currenthand.inverted()@p for p in points]
axis=Vector((0,.4,.916515)).normalized();pivot=Vector((0,-.018,.04));best=None
for degrees in (-90,-75,-60,-45,-30,-15):
 for down in (0,.01,.02,.03,.04):
  for outside in (0,.005,.01,.015,.02):
   q=Quaternion(axis,math.radians(degrees));delta=-axis*down+(q@Vector((1,0,0)))*outside;D=Matrix.LocRotScale(pivot+delta-q@pivot,q,Vector((1,1,1)));H=D@nativehand;points=[H@p for p in localpoints]
   detail=evaluate((0,0,0),True);cost=detail['cost']+.08*(degrees+55)**2+.02*(down*1000)**2+.02*(outside*1000)**2
   if best is None or cost<best['fit_cost']:best={'degrees':degrees,'down':down,'outside':outside,'fit_cost':cost,**detail,'matrix':[list(v) for v in H]};print('FIT',json.dumps(best),flush=True)
(O/'registered_club_grip.json').write_text(json.dumps(best,indent=2));print('REGISTERED_CLUB_GRIP',json.dumps(best),flush=True)
