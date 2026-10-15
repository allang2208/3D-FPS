"""Check MSVC CodeView source checksums before testing a shared build snapshot."""
import hashlib,json,struct
from pathlib import Path
project=Path('D:/FPS3D/FPSGAME')
names=['M66RecoveryGroundNode','M66RecoveryAuditScene','M66RecoveryAuditGameMode','M66AnimInstance','M66CorpseSurface','MonsterCorpseRagdollComponent','MonsterSurfaceGroundingNode']
out=[]
for name in names:
    src=project/'Source/FPSGAME/Monsters'/f'{name}.cpp'
    obj=project/'Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME'/f'{name}.cpp.obj'
    data=obj.read_bytes();u32=lambda p:struct.unpack_from('<I',data,p)[0]
    big=data[:4]==b'\0\0\xff\xff'
    count=u32(44) if big else struct.unpack_from('<H',data,2)[0]
    start=56 if big else 20+struct.unpack_from('<H',data,16)[0]
    found={}
    for i in range(count):
        p=start+i*40
        if data[p:p+8].rstrip(b'\0')!=b'.debug$S':continue
        size,offset=u32(p+16),u32(p+20);b=data[offset:offset+size]
        if b[:4]!=b'\x04\0\0\0':continue
        records={};q=4
        while q+8<=len(b):
            kind,n=struct.unpack_from('<II',b,q);records.setdefault(kind,[]).append(b[q+8:q+8+n]);q=(q+8+n+3)&~3
        strings=b''.join(records.get(0xf3,[]))
        for checks in records.get(0xf4,[]):
            q=0
            while q+6<=len(checks):
                index,n,kind=struct.unpack_from('<IBB',checks,q)
                filename=strings[index:].split(b'\0',1)[0].decode('utf8',errors='replace').replace('\\','/').lower()
                found[filename]=(kind,checks[q+6:q+6+n].hex());q=(q+6+n+3)&~3
    entry=found.get(src.as_posix().lower());algorithm={1:'md5',2:'sha1',3:'sha256'}.get(entry[0] if entry else None,'sha256')
    expected=hashlib.new(algorithm,src.read_bytes()).hexdigest();match=bool(entry and entry[1]==expected)
    out.append({'source':str(src),'object':str(obj),'algorithm':algorithm,'source_checksum':expected,'embedded_checksum':entry,'match':match,'source_mtime':src.stat().st_mtime,'object_mtime':obj.stat().st_mtime})
result={'all_match':all(r['match'] for r in out),'sources':out}
(Path(__file__).parent/'Records/compiled_sources.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2));raise SystemExit(0 if result['all_match'] else 2)
