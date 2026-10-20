import json, struct
import numpy as np
p = r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\download\svch.glb"
src=open(p,'rb').read(); _,_,length=struct.unpack_from('<III',src,0)
off=12; chunks=[]
while off<length:
    clen,ctype=struct.unpack_from('<II',src,off); chunks.append((ctype,off+8,clen)); off+=8+clen
j=json.loads(src[chunks[0][1]:chunks[0][1]+chunks[0][2]].decode('utf-8'))
def srgb(c):
    return c
print("=== materials ===")
for i,m in enumerate(j['materials']):
    pbr=m.get('pbrMetallicRoughness',{})
    bc=pbr.get('baseColorFactor',[1,1,1,1])
    hexs=''.join(f'{int(round(max(0,min(1,c**(1/2.2)))*255)):02X}' for c in bc[:3])
    print(f"{i}: {m['name']:14s} base=({bc[0]:.4f},{bc[1]:.4f},{bc[2]:.4f}) a={bc[3]} srgb~#{hexs} metallic={pbr.get('metallicFactor','1(default)')} rough={pbr.get('roughnessFactor','1(default)')} doubleSided={m.get('doubleSided')} ext={list(m.get('extensions',{}).keys())}")
    if m.get('extensions'): print("     ",json.dumps(m['extensions']))
