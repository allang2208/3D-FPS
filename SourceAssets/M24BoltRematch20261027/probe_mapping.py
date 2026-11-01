from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'author_candidate.py').read_text().split("roles=('fire'")[0],'candidate_setup','exec'))
row={n:Matrix(m) for n,m in source['clips']['fire']['poses'][29].items()}
for native_name,current_name in [('sniper','WPN_root'),('bolt','WPN_BoltHandle'),('boltrear','WPN_BoltCarrier')]:
 m=Matrix(raw['parts']['30'][native_name]);p,q,sc=m.decompose();m=Matrix.LocRotScale(p,q,Vector((1,1,1)))
 d=row[current_name]@m.inverted()
 print(native_name,'map',[list(x) for x in d],flush=True)
 print('mapped_wrist',list(d@Matrix(raw['poses']['30']['R_wrist']).translation),flush=True)
print('REJECTED',list(row['hand_r'].translation),flush=True)
print('CANDIDATE',list(raw_hand(row,30)['hand_r'].translation),flush=True)
