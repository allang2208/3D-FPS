import unreal as u
print('OBJECT_APIS',[(n,hasattr(u,n)) for n in ['ObjectIterator','get_objects_of_class','get_all_objects','NiagaraSimCache']])
print('NIAGARA_COMPONENT',[n for n in dir(u.NiagaraComponent) if any(x in n for x in ['particle','variable','advance','complete','bounds','asset'])])
if hasattr(u,'NiagaraSimCache'):
    print('CACHE',[n for n in dir(u.NiagaraSimCache) if any(x in n for x in ['read','write','capture','particle','frame'])])
print('NIAGARA_LIB',[n for n in dir(u.NiagaraFunctionLibrary) if any(x in n for x in ['particle','debug','cache'])])
print('ITERATORS',[n for n in dir(u) if 'Iterator' in n or 'SimCache' in n])
