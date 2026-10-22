"""Resolve recorded crash addresses against local DLL exports without downloading symbols."""
import bisect,json,re,struct,sys
from pathlib import Path
root=Path(sys.argv[1]);modules=json.loads((root/'host-modules.json').read_text(encoding='utf-8-sig'));log=(root/'host.log').read_text(encoding='utf-8-sig',errors='replace')
for module in modules:
    data=Path(module['file']).read_bytes();u16=lambda at:struct.unpack_from('<H',data,at)[0];u32=lambda at:struct.unpack_from('<I',data,at)[0]
    pe=u32(0x3c);count=u16(pe+6);opt=pe+24;sections=opt+u16(pe+20)
    table=[(u32(sections+i*40+12),u32(sections+i*40+8),u32(sections+i*40+20),u32(sections+i*40+16)) for i in range(count)]
    def offset(rva):
        for start,virtual,raw,size in table:
            if start<=rva<start+max(virtual,size):return raw+rva-start
        return rva
    export=offset(u32(opt+(112 if u16(opt)==0x20b else 96)));n=u32(export+24);functions=offset(u32(export+28));names=offset(u32(export+32));ordinals=offset(u32(export+36));symbols=[]
    for i in range(n):
        name_at=offset(u32(names+i*4));end=data.index(b'\0',name_at);symbols.append((u32(functions+u16(ordinals+i*2)*4),data[name_at:end].decode(errors='replace')))
    symbols.sort();addresses=[a for a,_ in symbols]
    for address in re.findall(r'\[Callstack\] 0x([0-9a-f]+) '+re.escape(module['name'])+r'!',log,re.I):
        rva=int(address,16)-module['base'];idx=bisect.bisect_right(addresses,rva)-1
        print(module['name'],hex(rva),'nearest_export',symbols[idx][1],'+',hex(rva-symbols[idx][0]),flush=True)
