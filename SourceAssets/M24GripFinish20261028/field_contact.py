field=np.load(OUT/'stock_field.npz');field_lo=field['lo'];field_step=float(field['step']);field_shape=field['shape'];field_values=field['values']
def body_field(Q):
 p=(Q-field_lo)/field_step;i=np.floor(p).astype(int);i=np.clip(i,0,field_shape-2);w=np.clip(p-i,0,1);result=np.zeros(len(Q))
 for x in (0,1):
  for y in (0,1):
   for z in (0,1):
    weight=(w[:,0] if x else 1-w[:,0])*(w[:,1] if y else 1-w[:,1])*(w[:,2] if z else 1-w[:,2])
    result+=field_values[i[:,0]+x,i[:,1]+y,i[:,2]+z]*weight
 return result
previous_actual=actual
def actual(row,P,full_winding=False,subset=None):
 other=None if subset is None else subset-{'M24_base'}
 if subset is not None and not other:ds={}
 else:ds=previous_actual(row,P,full_winding,other)
 if subset is None or 'M24_base' in subset:
  if full_winding:ds['M24_base']=previous_actual(row,P,True,{'M24_base'})['M24_base']
  else:
   inv=np.array(rest['WPN_root']@row['WPN_root'].inverted());Q=P@inv[:3,:3].T+inv[:3,3];ds['M24_base']=body_field(Q)
 return ds
