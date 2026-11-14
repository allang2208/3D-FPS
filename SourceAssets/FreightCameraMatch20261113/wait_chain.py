import ctypes as c,sys
from ctypes import wintypes as w
a=c.WinDLL('advapi32',use_last_error=True)
class Obj(c.Structure):
    _fields_=[('name',w.WCHAR*128),('timeout',c.c_longlong),('alert',w.BOOL)]
class Thread(c.Structure):
    _fields_=[('pid',w.DWORD),('tid',w.DWORD),('wait',w.DWORD),('switch',w.DWORD)]
class Both(c.Union):_fields_=[('obj',Obj),('t',Thread)]
class Node(c.Structure):_fields_=[('kind',c.c_int),('status',c.c_int),('info',Both)]
a.OpenThreadWaitChainSession.restype=w.HANDLE
s=a.OpenThreadWaitChainSession(0,None)
for t in sys.argv[1:]:
    n=w.DWORD(16);cy=w.BOOL();arr=(Node*16)()
    ok=a.GetThreadWaitChain(w.HANDLE(s),None,0,int(t),c.byref(n),arr,c.byref(cy))
    print(t,ok,[(i.kind,i.status,i.info.t.pid if i.kind==8 else i.info.obj.name[:100],i.info.t.tid if i.kind==8 else '') for i in arr[:n.value]] if ok else c.get_last_error())
