"""Prepare the certified hill grid's rock exposure, real relief, and deterministic ledge sites."""
from pathlib import Path
import json, shutil, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates, maximum_filter
from scipy.spatial import cKDTree
from continuous_meadow import surface
from generate_slope_grass import WEST,SOUTH,CELL,TILES,ROWS,COLS,site_hash,grid_at
from prepare_gate_road_surface import smooth

LAYER='e67bff01-9454-4b85-b895-192974f44bce'
GRANITE='6896fe23-db5a-427b-acd1-c826b38d43d3'
LEDGE='ffa5ac16-348a-4c1f-8404-6c031ebfcfce'
SHELF='2854ca12-58fc-4b5e-80c7-33c73823f8bd'

def read_scan(folder,ch,mode,size=2048):
    with Image.open(next(folder.glob('*_'+ch+'.jpg'))) as tex:
        return np.asarray(tex.convert(mode).resize((size,size),Image.Resampling.LANCZOS),dtype='f4')/255.

def save_image(path,values):
    Image.fromarray(np.rint(255*np.clip(values,0.,1.)).astype('u1')).save(path)

def textures(out):
    a,b=[out/'Fab'/key for key in (LAYER,GRANITE)]
    # Preserve the layered face's bedding and fissures. Granite mineral detail fills the raised portions.
    rock=read_scan(a,'BaseColor','RGB');granite=read_scan(b,'BaseColor','RGB')
    height=read_scan(a,'Displacement','L');fine=read_scan(b,'Displacement','L')
    weight=.08+.24*smooth(.24,.78,height)
    c=rock*(1.-weight[...,None])+granite*weight[...,None]
    save_image(out/'T_CliffColor.png',c)
    save_image(out/'T_CliffNormal.png',read_scan(a,'Normal','RGB',1024))
    ao=read_scan(a,'AO','L',1024);rough=read_scan(a,'Roughness','L',1024)
    h=.88*height+.12*fine
    hp=np.asarray(Image.fromarray(h).resize((1024,1024),Image.Resampling.LANCZOS))
    save_image(out/'T_CliffARH.png',np.stack((ao,rough,hp),-1))
    return height

def prepare_ledge(out,uid,name):
    import trimesh
    raw=next((out/'Fab'/uid).rglob('*.gltf'));model=json.loads(raw.read_text())
    # Fit the measured open rim to y=0 (glTF up). Seat the original scanned front outward.
    mesh=trimesh.load(raw,force='mesh',process=True);mesh.merge_vertices(merge_tex=True,merge_norm=True)
    rim=mesh.vertices[np.unique(mesh.edges_unique[np.bincount(mesh.edges_unique_inverse)==1])]
    normal=np.linalg.svd(rim-rim.mean(0))[2][-1]
    if normal@np.sum(mesh.face_normals*mesh.area_faces[:,None],axis=0)<0:normal=-normal
    tangent=np.linalg.svd(rim-rim.mean(0))[2][0] if uid==SHELF else np.array([1.,0.,0.]);tangent-=normal*(tangent@normal);tangent/=np.linalg.norm(tangent)
    basis=np.stack((tangent,normal,np.cross(tangent,normal)),axis=1)
    pivot=rim.mean(0);pivot+=normal*np.percentile((rim-pivot)@normal,93)
    node=model['nodes'][0];T=trimesh.transformations.quaternion_matrix(np.roll(node['rotation'],1))[:3,:3];scale=node['scale'][0]
    data=bytearray((raw.parent/model['buffers'][0]['uri']).read_bytes())
    for key,index in model['meshes'][0]['primitives'][0]['attributes'].items():
        if key not in ('POSITION','NORMAL','TANGENT'):continue
        acc=model['accessors'][index];v=model['bufferViews'][acc['bufferView']]
        ar=np.frombuffer(data,'<f4',count=acc['count']*(4 if key=='TANGENT' else 3),offset=v.get('byteOffset',0)+acc.get('byteOffset',0)).reshape(acc['count'],-1)
        transformed=ar[:,:3]@T.T
        ar[:,:3]=((transformed*scale-pivot) if key=='POSITION' else transformed)@basis
        if key=='POSITION':acc['min']=ar.min(0).tolist();acc['max']=ar.max(0).tolist()
    if uid==SHELF:
        prim=model['meshes'][0]['primitives'][0]
        def attribute(i,dtype):
            acc=model['accessors'][i];view=model['bufferViews'][acc['bufferView']]
            count=acc['count']*(2 if acc['type']=='VEC2' else 1)
            return np.frombuffer(data,dtype,count=count,offset=view.get('byteOffset',0)+acc.get('byteOffset',0))
        uv=attribute(prim['attributes']['TEXCOORD_0'],'<f4').reshape(-1,2)
        indices=model['accessors'][prim['indices']]
        tri=attribute(prim['indices'],{5123:'<u2',5125:'<u4'}[indices['componentType']]).reshape(-1,3)
        mask=Image.new('L',(256,256));painter=ImageDraw.Draw(mask)
        for face in (uv[tri]*255.).astype(int):painter.polygon([tuple(pt) for pt in face],fill=255)
        tex=Image.open(next(raw.parent.rglob('*_B.png'))).convert('RGB')
        mid=np.median(np.asarray(tex.resize(mask.size))[np.asarray(mask)>0],axis=0)
        rock_mid=np.median(np.asarray(Image.open(out/'T_CliffColor.png').resize(mask.size)),axis=(0,1))
        # Retain the shelf's own fractures but integrate the open-cut stone colour and dry finish.
        tint=np.asarray(tex.resize((1024,1024),Image.Resampling.LANCZOS),dtype='f4')
        tint=rock_mid*.91+.71*(tint-mid)
        Image.fromarray(np.rint(tint).clip(0,255).astype('u1')).save(out/'T_BareShelf_B.png')
    model['nodes']=[{'mesh':0,'name':name}];model['buffers'][0]['uri']=name+'.bin'
    for part in model['meshes'][0]['primitives']:part.pop('material',None)
    for k in ('materials','textures','images','samplers'):model.pop(k,None)
    folder=out/'Geometry';folder.mkdir(exist_ok=True)
    (folder/(name+'.bin')).write_bytes(data);(folder/(name+'.gltf')).write_text(json.dumps(model),encoding='utf-8')

def field_noise(rng,shape,radius):
    a=gaussian_filter(rng.standard_normal(shape).astype('f4'),radius)
    return np.clip((a-a.mean())/max(a.std(),1.e-5),-2.,2.)

def thin_near_grass(base_file,out_file,rock):
    a=np.fromfile(base_file,'u1').reshape(TILES,TILES,ROWS,COLS)
    count=0;jj,ii=np.indices((ROWS,COLS),dtype='u4')
    for j in range(TILES):
        for i in range(TILES):
            if rock[j*16:(j+1)*16+1,i*16:(i+1)*16+1].max()<.30:continue
            ids=((j*TILES+i)*ROWS+jj)*COLS+ii;h=site_hash(ids)
            x=WEST+CELL*(i+(ii+.25+.5*(jj%2)+((h&255)/255.-.5)*.20)/COLS)
            y=SOUTH+CELL*(j+(jj+.5+(((h>>8)&255)/255.-.5)*.20)/ROWS)
            remove=(a[j,i]!=0)&((site_hash(ids+np.uint32(541))&65535)/65536.<smooth(.3,.88,grid_at(rock,x,y)))
            count+=int(remove.sum());a[j,i][remove]=0
    a.tofile(out_file);return count

def prepare(base,out):
    out.mkdir(exist_ok=True,parents=True)
    for f in ('paint.rg8','quarry-clear.u8','gate-road.csv','quarry-road.csv','hill.json','settlement.i16'):
        shutil.copy2(base/f,out/f)
    for name in ('T_ContinuousMeadowField.png','T_ContinuousMeadowBlades.png','T_ContinuousMeadowNormal.png'):
        shutil.copy2(base/name,out/name)
    shutil.copytree(base.parent/'HillReliefPools-R28/Turf',out/'Turf',dirs_exist_ok=True)
    grass=out/'Grass';shutil.copytree(base/'Grass',grass,dirs_exist_ok=True)
    scan=textures(out);prepare_ledge(out,LEDGE,"NordicLedge");prepare_ledge(out,SHELF,"BareShelf")
    z=np.fromfile(base/'region.i16','<i2').reshape(1025,1025).astype(float)*.01
    y,x=np.mgrid[-320:705,-624:401];rng=np.random.default_rng(237890)
    roads=np.vstack([np.loadtxt(base/(k+'-road.csv'),delimiter=',',skiprows=1)[:,:2] for k in ('gate','quarry')])
    distances,nearest=cKDTree(roads).query(np.c_[x.ravel(),y.ravel()]);rd=distances.reshape(z.shape)
    paint=np.fromfile(base/'paint.rg8','u1').reshape(1025,1025,2)[...,0]/255.
    donor=np.fromfile(grass/'study_dirt_2m.u8','u1').reshape(253,253)/255.
    xy=np.arange(-252,253);paint[68:573,372:877]=grid_at(donor,*np.meshgrid(xy,xy),-252,-252,2)
    pond=maximum_filter(np.fromfile(grass/'pond_wet.u8','u1').reshape(4097,4097),5)[::4,::4]>0
    quarry=np.fromfile(base/'quarry-clear.u8','u1').reshape(z.shape)>11
    hill=json.loads((base/'hill.json').read_text());vx,vy=hill['site_min_m']
    town=np.hypot(np.maximum(np.maximum(vx-x,x-vx-118),0),np.maximum(np.maximum(vy-y,y-vy-145),0))
    safe=smooth(3.25,5.,rd)*(1.-smooth(.12,.53,paint))*smooth(2.,5.,distance_transform_edt(~pond))*smooth(1.,4.,distance_transform_edt(~quarry))*smooth(2.,8.,town)
    # Cull very small isolated rises. Lower the threshold on the uphill side of maintained cuts.
    sy,sx=np.gradient(gaussian_filter(z,1.05));grade=np.degrees(np.arctan(np.hypot(sx,sy)))
    foot=grid_at(z,roads[nearest,0].reshape(z.shape),roads[nearest,1].reshape(z.shape))
    cut=(1.-smooth(9.,16.,rd))*smooth(.22,1.30,z-foot)
    broad=field_noise(rng,z.shape,9.);grain=field_noise(rng,z.shape,2.3)
    start=36.-8.*cut+1.65*broad+1.15*grain
    cover=smooth(start,start+11.,grade)*safe
    # Soil survives in sheltered pockets around actual standing roots, elongated down the slope.
    stand=np.fromfile(grass/'planting.bin',dtype=[('xy','<f4',2),('yaw','<f4'),('s','<f4'),('slot','<i4')])
    trunks=np.vstack((stand['xy'][stand['slot']<2]*.01,np.fromfile(grass/'study_trees.f32','<f4').reshape(-1,3)[:,:2],
                      np.fromfile(grass/'harvest-trees.f32','<f4').reshape(-1,3)[:,:2]*.01))
    slope_len=np.maximum(.02,np.hypot(sx,sy))
    seed_xy=np.c_[(x+.70*sx/slope_len+.28*grain).ravel(),(y+.70*sy/slope_len+.32*broad).ravel()]
    root_gap=cKDTree(trunks).query(seed_xy)[0].reshape(x.shape)
    shelter=(1.-smooth(.62,2.85+.40*grain,root_gap))*(1.-.73*cut)
    debris=smooth(.58,1.60,grain+.42*broad)*(1.-smooth(42.,60.,grade))*(1.-.64*cut)
    cover*=1.-np.maximum(.83*shelter,.58*debris)

    # Deposit and canopy footprints in the original, hand-placed forest keep their ground contact.
    solid=Image.new('L',(1025,1025));draw=ImageDraw.Draw(solid)
    for name in ('study_trees','study_obstacles','study_pond_props'):
        for cx,cy,rad in np.fromfile(grass/(name+'.f32'),'<f4').reshape(-1,3):
            i,j=cx-WEST,cy-SOUTH;r=float(rad)+.7;draw.ellipse((i-r,j-r,i+r,j+r),fill=255)
    contacts=smooth(.4,2.5,distance_transform_edt(np.asarray(solid)==0))
    # Scan-derived metre-scale shelves with smoothly changing phase. Sample multiple non-collinear
    # coordinates so neither radial sine ripples nor a rectangular tiling signature can dominate.
    low=gaussian_filter(scan[::4,::4],20.,mode='wrap');low=(low-np.median(low))/max(low.std(),.02)
    band1=map_coordinates(low,[((.71*y+.39*x+.69*z+3.2*broad)/13.)*512,((.76*x-.35*y+2.*grain)/16.)*512],order=1,mode='grid-wrap')
    band2=map_coordinates(low,[((.49*x-.71*y+.83*z)/8.1)*512,((.34*x+.77*y)/9.3)*512],order=1,mode='grid-wrap')
    relief=.30*gaussian_filter(np.tanh(.69*band1+.40*band2),.65)*cover*contacts
    delta=np.rint(relief*100).astype('<i2');cm=np.rint(z*100).astype('<i2')+delta
    cm.tofile(out/'region.i16');sub=delta[68:573,372:877].copy();sub.tofile(out/'cliff-landscape-delta.i16')
    ref=np.fromfile(base/'reference.f32','<f4');ref[:505**2]+=sub.ravel();ref.tofile(out/'reference.f32')
    Image.fromarray((cm.astype('i4')+32768).astype('u2')).save(out/'H_HillsCliffs.png')
    rock=np.rint(255*cover).astype('u1');rock.tofile(out/'cliff-mask.u8')
    gy,gx=np.gradient(gaussian_filter(cm.astype(float)*.01,1.3));norm=np.sqrt(1+gx*gx+gy*gy)
    field=np.stack((cover,.5-.5*gx/norm,.5-.5*gy/norm),axis=-1)
    save_image(out/'T_CliffField.png',.25*(field[:-1,:-1]+field[1:,:-1]+field[:-1,1:]+field[1:,1:]))
    near=thin_near_grass(base.parent/'VillageLoessReview-R33/Grass/near_grass.u8',grass/'near_grass.u8',cover)
    fine=np.fromfile(base/'meadow-fine.f32','<f4').reshape(-1,8);px,py=fine[:,0]*.01,fine[:,1]*.01
    keep=rng.random(len(px))>=smooth(.3,.88,grid_at(cover,px,py))
    shifts=surface(cm,px,py)-surface(z*100.,px,py)
    fine[:,2]+=shifts;fine[keep].tofile(out/'meadow-fine.f32')
    # A jittered lattice limits instances in long faces. Screen the complete ledge footprint near roads/water.
    iy,ix=np.indices((147,147));px=WEST+(ix+rng.uniform(.10,.90,ix.shape))*7.;py=SOUTH+(iy+rng.uniform(.10,.90,ix.shape))*7.
    coverage=grid_at(cover,px,py);size=rng.uniform(.73,1.62,px.shape);road=grid_at(rd,px,py)<13.3
    permit=(px<398)&(py<702)&(coverage>.42)&(rng.random(px.shape)<coverage*np.where(road,.76,.48))&(grid_at(contacts,px,py)>.8)
    for ox,oy in [(1,0),(-1,0),(0,1),(0,-1)]:
        permit&=(grid_at(safe,px+1.5*size*ox,py+1.5*size*oy)>.50)
    ang=rng.uniform(-19,19,px.shape)+180*rng.integers(0,2,px.shape)
    dtype=np.dtype([('x','<f4'),('y','<f4'),('yaw','<f4'),('scale','<f4'),('road','<i4')])
    rows=np.empty(int(permit.sum()),dtype)
    # Bare shelves predominate on open cuts; forest ledges retain moss. The larger
    # shelf is scaled to fit the footprint already cleared against the road and shore.
    bare=rng.random(road.shape)<np.where(road,.86,.41)
    size=np.where(bare,size*.70,size)
    for col,val in [('x',px*100),('y',py*100),('yaw',ang),('scale',size),('road',road.astype('i4')+2*bare.astype('i4'))]:rows[col]=val[permit]
    rows.tofile(out/'ledge-sites.bin')
    report=dict(onset_degrees={'road_cut':28,'hillside':36},transition_degrees=11,full_rock_m2=int((rock>=240).sum()),exposed_m2=int((rock>=127).sum()),
        changed_height_knots=int((delta!=0).sum()),reference_changed=int((sub!=0).sum()),delta_cm=[int(delta.min()),int(delta.max())],
        road_centre_max_cm=int(np.abs(delta[rd<=3.25]).max()),settlement_max_cm=int(np.abs(delta[town==0]).max()),
        water_max_cm=int(np.abs(delta[pond]).max()),quarry_max_cm=int(np.abs(delta[quarry]).max()),
        hill_ledges=int(np.sum((rows['road']&1)==0)),road_ledges=int(np.sum(rows['road']&1)),bare_shelves=int(np.sum(rows['road']>=2)),near_grass_removed=near,fine_grass_remaining=int(keep.sum()))
    hill.update(relief_recipe='CliffExposure-R35',parent_relief=base.name)
    (out/'hill.json').write_text(json.dumps(hill,indent=2))
    (out/'cliff-exposure.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':print(prepare(Path(sys.argv[1]),Path(sys.argv[2])))
