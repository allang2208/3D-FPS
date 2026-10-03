"""Staff-area finish: complete glazed tiles, without the shared loss generator."""
import math
import random
import zlib
import numpy as np
from mathutils import Vector
from corridor_surfaces import clip
from natural_wall_damage import TW,TH,Build,inset

class IntactStaffTiles:
    def __init__(self,accepted):
        self.source=accepted.source
        self.panels=accepted.panels
        self.donors=accepted.donors
        self.placements=[]

    def wall(self,host,start,direction,normal,length,openings,breach,depth):
        # Preserve original wall axes, door cropping and glaze atlas coordinates.
        rid=host['ROOM']['id'];seed=zlib.crc32((rid+str(tuple(start))+':intact-staff').encode())
        rng=random.Random(seed);records=[]
        bed='V2_WallReliefBed';core='V2_CeramicFractureCore';finish='V2_WallReliefFinish'
        records.append(([(t,.134,z,t/1.28,z/1.28) for t,z in ((0,.155),(0,1.59),(length,1.59),(length,.155))],bed,False))
        tile_count=0
        for col in range(math.ceil(length/TW)):
            for row in range(9):
                donor,coeff,glaze=rng.choice(self.donors)
                a=col*TW+.003;b=min(length,(col+1)*TW-.003)
                if b<=a:continue
                z0=.164+row*TH;z1=.316+row*TH
                outline=[(a,z0),(b,z0),(b,z1),(a,z1)];top=inset(outline,.0007)
                # Whole straight edges and a manufactured glaze bevel. No
                # missing cells, exposed patches or bonded fracture remnants.
                uv=lambda t,z:tuple(np.array([t-col*TW,z-row*TH,1])@coeff)
                back_uv=lambda t,z:(t/.075,z/.075)
                builder=Build(('x',0,length,0,1))
                front=lambda t,z:.163
                lip=lambda t,z:.1615
                back=lambda t,z:.141
                substrate=lambda t,z:.132
                builder.cap(top,front,glaze,uv)
                builder.sides(top,outline,front,lip,glaze,uv)
                builder.sides(outline,outline,lip,back,core)
                builder.cap(outline,back,core,back_uv,back=True)
                builder.sides(outline,outline,back,substrate,finish)
                for face,mat,uvs in zip(builder.f,builder.mi,builder.uv):
                    records.append(([(builder.v[i][0],builder.v[i][1],builder.v[i][2],*p) for i,p in zip(face,uvs)],mat,False))
                tile_count+=1
        cuts=list(openings)
        if breach:cuts.append(dict(center=(breach['left']+breach['right'])/2,width=breach['right']-breach['left']+.46,height=breach['height']+.22))
        g=host['group']('Tiles');cache={}
        for points,material,smooth in records:
            points=clip(clip(points,0,0,True),0,length,False)
            pieces=[points] if len(points)>=3 else []
            for opening in cuts:
                left=opening['center']-opening['width']/2;right=opening['center']+opening['width']/2
                bottom=opening.get('bottom',0);next_pieces=[]
                for piece in pieces:
                    if max(p[0] for p in piece)<=left or min(p[0] for p in piece)>=right or min(p[2] for p in piece)>=opening['height'] or max(p[2] for p in piece)<=bottom:
                        next_pieces.append(piece);continue
                    middle=clip(clip(piece,0,left,True),0,right,False)
                    next_pieces.extend([clip(piece,0,left,False),clip(piece,0,right,True),
                        clip(middle,2,opening['height'],True),clip(middle,2,bottom,False)])
                pieces=[p for p in next_pieces if len(p)>=3]
            for piece in pieces:
                face=[]
                for t,d,z,u,v in piece:
                    p=Vector(start)+Vector(direction)*t+Vector(normal)*(d+depth/2-.12)
                    key=(round(p.x,7),round(p.y,7),round(z,7))
                    if key not in cache:cache[key]=len(g['v']);g['v'].append((p.x,p.y,z))
                    face.append(cache[key])
                if len(set(face))<3:continue
                g['f'].append(tuple(face));g['m'].append(material)
                g['uv'].append([(p[3],p[4]) for p in piece]);g['smooth'].append(smooth)
        self.placements.append(dict(room=rid,wall_start=list(start),length=length,
            finish='intact',tile_cells=tile_count,missing=0,bonded_remnants=0))
