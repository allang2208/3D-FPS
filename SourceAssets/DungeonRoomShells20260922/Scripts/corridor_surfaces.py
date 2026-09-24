"""Place the APPROVED corridor's baked fracture/relief output, without a new fracture style.

Source is the final TileFracture blend, not the obsolete triangle-chip producer.
Retain per-corner atlas UVs, material identity, ceramic thickness and mortar displacement.
Placement stays rigid with boundary/door cropping. The rejected rectangular repair
is excluded from the candidate geometry and filled with adjacent intact source tiles.
"""
import bpy,json,math,re,zlib
from pathlib import Path
from mathutils import Vector

class CorridorSurfaces:
    def __init__(self,root,mapping,materials):
        self.source=root.parent/'DungeonTileFracture20260922'
        manifest=json.loads((self.source/'Authored/geometry-manifest.json').read_text())
        entries={e['name']:e for e in manifest['objects']}
        names=['SM_TileFracture_Corridor_South','SM_TileFracture_Corridor_North']
        with bpy.data.libraries.load(str(self.source/'Authored/DungeonTileFracture_Source.blend'),link=False) as (src,dst):
            dst.objects=list(names)
        objects={o.name:o for o in dst.objects}
        self.panels=[];self.placements=[]
        for name,lo,hi,fixed,inside in [(names[0],0,4.34,0,1),(names[0],9.6,14.25,0,1),(names[1],0,7.75,4,-1)]:
            ob=objects[name];mesh=ob.data;records=[]
            slots=[]
            for slot in mesh.materials:
                key=re.sub(r'[._][0-9]{3}$','',slot.name)
                path=entries[name]['materials'].get(key)
                if key=='V2_CeramicFractureCore':path='/Game/Dungeons/AtmosphereV2/TileFracture/Materials/M_CeramicFractureCore'
                if not path:
                    slots.append(None)
                    continue  # Old unused slots remain in the source blend.
                mapping[key]=path
                if key not in materials:materials[key]=bpy.data.materials.new('RS_'+key)
                slots.append(key)
            uv=mesh.uv_layers.active
            for f in mesh.polygons:
                points=[mesh.vertices[mesh.loops[li].vertex_index].co for li in f.loop_indices]
                cx=sum(v.x for v in points)/len(points);cd=sum((v.y-fixed)*inside for v in points)/len(points)
                if not lo-.002<=cx<=hi+.02 or not .095<cd<.185:continue
                # All source walls run along X; canonical coordinates are t, inward depth, z.
                data=[(v.x-lo,(v.y-fixed)*inside,v.z,*uv.data[li].uv) for v,li in zip(points,f.loop_indices)]
                if inside<0:data.reverse()
                data=clip(clip(data,0,0,True),0,hi-lo,False)
                if len(data)>=3:
                    material=slots[f.material_index]
                    if material is None:raise RuntimeError('Used corridor slot missing: '+mesh.materials[f.material_index].name)
                    records.append((data,material,f.use_smooth))
            # The accepted irregular fractures remain. The historical rectangular repair skim
            # is not an eligible room motif: restore its 3 x 4 tiles using an intact neighbour.
            if name==names[0] and lo==0:
                records=self.without_rectangular_repair(records)
            self.panels.append((hi-lo,records,name,lo))
        for ob in objects.values():bpy.data.objects.remove(ob,do_unlink=True)
        from natural_wall_damage import donor_tiles
        self.donors=donor_tiles(self.panels)

    @staticmethod
    def without_rectangular_repair(records):
        if not any('NaturalRepair' in material for points,material,smooth in records):return records
        donor=[];kept=[]
        for points,material,smooth in records:
            x=sum(p[0] for p in points)/len(points);d=sum(p[1] for p in points)/len(points);z=sum(p[2] for p in points)/len(points)
            # Original authored repair occupies South wall columns 10..12, rows 2..5.
            # Keep the continuous deep mortar bed; remove the skim and its perimeter sides.
            rejected='NaturalRepair' in material or (3.095<x<4.035 and .473<z<1.116 and d>.130)
            if not rejected:kept.append((points,material,smooth))
            row=round((z-.24)/.158)
            if 2.792<x<3.098 and 2<=row<=5 and d>=.134 and max(p[0] for p in points)<=3.1001 and min(p[0] for p in points)>=2.7899:
                donor.append((points,material,smooth))
        if not donor:raise RuntimeError('Intact source tile donor is unavailable')
        for offset in (.31,.62,.93):
            for points,material,smooth in donor:
                kept.append(([(x+offset,d,z,u,v) for x,d,z,u,v in points],material,smooth))
        return kept

    def wall(self,host,start,direction,normal,length,openings,breach,depth):
        rid=host['ROOM']['id'];seed_id=host['ROOM'].get('surface_seed_id',rid)
        variant=host['ROOM'].get('surface_variant',0)
        seed=zlib.crc32((seed_id+str(tuple(start))+':wall:'+str(variant)).encode())
        cuts=list(openings)
        if breach:cuts.append(dict(center=(breach['left']+breach['right'])/2,width=breach['right']-breach['left']+.46,height=breach['height']+.22))
        g=host['group']('Tiles');cache={};cursor=0;panel_index=seed%len(self.panels)
        def emit(points,material,smooth):
            face=[]
            for t,d,z,u,v in points:
                p=start+direction*t+normal*(d+depth/2-.12)
                key=(round(p.x,7),round(p.y,7),round(z,7))
                vi=cache.get(key)
                if vi is None:vi=len(g['v']);cache[key]=vi;g['v'].append((p.x,p.y,z))
                face.append(vi)
            if len(set(face))<3:return
            g['f'].append(tuple(face));g['m'].append(material)
            g['uv'].append([(p[3],p[4]) for p in points]);g['smooth'].append(smooth)
        from natural_wall_damage import records_for_wall
        natural,summary=records_for_wall(self.panels,length,seed,self.donors)
        while cursor<length-.001:
            width,records,name,source_start=length,natural,'clustered bonded ceramic loss',0
            span=min(width,length-cursor)
            for data,material,smooth in records:
                q=clip([(t+cursor,d,z,u,v) for t,d,z,u,v in data],0,length,False)
                if len(q)<3:continue
                pieces=[q]
                for opening in cuts:
                    left=opening['center']-opening['width']/2;right=opening['center']+opening['width']/2
                    next_pieces=[]
                    for piece in pieces:
                        if max(p[0] for p in piece)<=left or min(p[0] for p in piece)>=right or min(p[2] for p in piece)>=opening['height']:
                            next_pieces.append(piece);continue
                        next_pieces.extend([clip(piece,0,left,False),clip(piece,0,right,True),
                            clip(clip(clip(piece,0,left,True),0,right,False),2,opening['height'],True)])
                    pieces=[p for p in next_pieces if len(p)>=3]
                for piece in pieces:emit(piece,material,smooth)
            self.placements.append(dict(room=rid,source=name,source_start=source_start,length=span,wall_start=list(start),offset=cursor,variant=variant,distribution=summary))
            cursor+=width;panel_index+=1

def clip(poly,axis,threshold,greater):
    if not poly:return []
    out=[];a=poly[-1];da=(a[axis]-threshold)*(1 if greater else -1)
    for b in poly:
        db=(b[axis]-threshold)*(1 if greater else -1)
        if (da>=0)!=(db>=0):
            k=da/(da-db);out.append(tuple(x+(y-x)*k for x,y in zip(a,b)))
        if db>=0:out.append(b)
        a=b;da=db
    return out
