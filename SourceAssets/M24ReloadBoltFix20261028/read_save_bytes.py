"""Read the tagged saved equipment payload without loading or rewriting a profile."""
import struct,re,json
from pathlib import Path
O=Path(__file__).resolve().parent
b=(O.parents[1]/'Saved/SaveGames/ColdSteelPlayer_PIE_0_B.sav').read_bytes()
def integer(block,name):
 tag=name.encode()+b'\0\x0c\0\0\0IntProperty\0'+bytes(4)+b'\x04\0\0\0\0'
 i=block.find(tag)
 return struct.unpack_from('<i',block,i+len(tag))[0] if i>=0 else None
rows=[]
for m in re.finditer(b'Definition\0\x0c\0\0\0StrProperty\0',b):
 i=m.end()+9;n=struct.unpack_from('<i',b,i)[0]
 if n<=0 or n>200:continue
 definition=b[i+4:i+4+n-1].decode('ascii');end=b.find(b'InstanceId\0',i)
 z=b[i:end] if end>=0 else b[i:]
 if definition=='ue_m24' or integer(z,'Place')==1:rows.append({'definition':definition,'place':integer(z,'Place'),'cell':integer(z,'Cell'),'magazine':integer(z,'Magazine')})
result={'active_weapon_slot':integer(b,'ActiveWeaponSlot'),'equipment':rows,'read_only':True}
(O/'saved_equipment.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
