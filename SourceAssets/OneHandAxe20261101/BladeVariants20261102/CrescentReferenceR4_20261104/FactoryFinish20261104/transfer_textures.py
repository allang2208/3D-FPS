"""Transfer actual factory body and ground-edge PBR onto the unchanged R4 UVs."""
from pathlib import Path
import ast,json,sys
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

P=Path(sys.argv[sys.argv.index('--workdir')+1]).resolve() if '--workdir' in sys.argv else Path(__file__).resolve().parent
config=json.loads((P/'transfer_config.json').read_text('utf-8')) if (P/'transfer_config.json').exists() else {}
prefix=config.get('texture_prefix','T_TacticalHatchet_Head_SwiftCrescent_R4')
SIZE=2048;MASK_SIZE=2048
# Reuse the established same-source steel resampling, including UV rasterization.
helper=P.parents[3]/'HighlandClaymoreMeshy20260922/ClovenSurface20261002/BladeMetal20261002/author_textures.py'
tree=ast.parse(helper.read_text('utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'triangle_pixels','sample'}],type_ignores=[]),str(helper),'exec'))
source=json.loads((P/'surface_source.json').read_text('utf-8'))
maps={key:np.asarray(Image.open(path).convert('RGB'),dtype=np.float32)/255. for key,path in source['textures'].items()}
maps['BaseColor']=np.where(maps['BaseColor']<=.04045,maps['BaseColor']/12.92,((maps['BaseColor']+.055)/1.055)**2.4)
with np.load(config.get('factory_surface',P/'factory_steel.npz')) as packed:factory={key:packed[key] for key in packed.files}
with np.load(P/'target_surface.npz') as packed:target={key:packed[key] for key in packed.files}
owner=np.full((MASK_SIZE,MASK_SIZE),-1,np.int32)
for index,triangle in enumerate(factory['uv']):
    pixels=triangle_pixels(triangle,MASK_SIZE)
    if pixels is not None:
        x,y,w=pixels;owner[y,x]=index
base=np.asarray(Image.open(source['textures']['BaseColor']).convert('RGB').resize((MASK_SIZE,MASK_SIZE)),np.float32)/255.
orm=np.asarray(Image.open(source['textures']['ORM']).convert('RGB').resize((MASK_SIZE,MASK_SIZE)),np.float32)/255.
luma=base.mean(axis=2)
specs={};tiles={}
for region in ['body','edge']:
    mask=(owner>=0)&(np.ptp(base,axis=2)<.1)
    if region=='body':mask&=(luma>.10)&(luma<.42)&(orm[:,:,2]>.2)
    else:mask&=(luma>.5)&(luma<.94)&(orm[:,:,2]>.6)
    distance=distance_transform_edt(mask);cy,cx=np.unravel_index(distance.argmax(),distance.shape)
    if distance[cy,cx]<3:raise RuntimeError('No usable factory '+region+' steel patch')
    radius=max(2,int(distance[cy,cx]*.64));full=maps['BaseColor'].shape[0];scale=full/MASK_SIZE
    x0,x1=int((cx-radius)*scale),int((cx+radius+1)*scale)
    y0,y1=int((cy-radius)*scale),int((cy+radius+1)*scale)
    patch={key:value[y0:y1,x0:x1].copy() for key,value in maps.items()}
    # Periodic boundaries only; no recolouring or guessed roughness/metallic values.
    for value in patch.values():
        h,w=value.shape[:2];band=max(2,min(h,w)//8)
        for i in range(band):
            weight=.5*(1-i/band)**2
            a,b=value[:,i].copy(),value[:,w-1-i].copy()
            value[:,i]=a*(1-weight)+b*weight;value[:,w-1-i]=b*(1-weight)+a*weight
            a,b=value[i].copy(),value[h-1-i].copy()
            value[i]=a*(1-weight)+b*weight;value[h-1-i]=b*(1-weight)+a*weight
    index=owner[cy,cx];uv=factory['uv'][index];xyz=factory['points'][index]
    derivative=np.column_stack((xyz[1]-xyz[0],xyz[2]-xyz[0]))@np.linalg.inv(np.column_stack((uv[1]-uv[0],uv[2]-uv[0])))
    meters=np.maximum(np.linalg.norm(derivative,axis=0)*np.array([(x1-x0)/full,(y1-y0)/full]),.0005)
    specs[region]={'swatch_pixels':[x0,y0,x1,y1],'swatch_physical_m':meters.tolist(),
        'base_linear_mean':patch['BaseColor'].mean(axis=(0,1)).tolist(),
        'roughness_mean':float(patch['ORM'][:,:,1].mean()),'metallic_mean':float(patch['ORM'][:,:,2].mean())}
    tiles[region]=patch

def unit(a):return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-12)

# The actual R4 cutting curve supplies grain direction, keeping the grind aligned
# across the blade as the crescent turns, instead of stretching a straight stripe.
def cubic(a,b,c,d,n=144):
    t=np.linspace(0,1,n+1)[:,None]
    return (1-t)**3*np.array(a)+3*(1-t)**2*t*np.array(b)+3*(1-t)*t*t*np.array(c)+t**3*np.array(d)
curve=np.concatenate((cubic((114,46),(84,43),(52,78),(49,118)),cubic((49,118),(46,161),(69,200),(109,218))[1:]))
scale=.031743/31
edge_points=np.column_stack((.003511+(165.5-curve[:,0])*scale,.115+(240-curve[:,1])*scale))
if 'edge_points_xz_m' in config:edge_points=np.asarray(config['edge_points_xz_m'],dtype=float)
segments=edge_points[1:]-edge_points[:-1];seglen=np.linalg.norm(segments,axis=1)
starts=np.concatenate(([0.],np.cumsum(seglen)))
tree=cKDTree((edge_points[1:]+edge_points[:-1])*.5)
old=Image.open(P/'Before/Textures'/(prefix+'_BaseColor.png')).convert('RGB')
old=np.asarray(old,dtype=np.float32)/255.
out={key:np.zeros((SIZE,SIZE,3),np.float32) for key in maps};filled=np.zeros((SIZE,SIZE),bool)

def normal_to_world(encoded,n,u_axis,v_axis):
    u=unit(u_axis-n*np.sum(u_axis*n,axis=1,keepdims=True))
    v=unit(np.cross(n,u));v*=np.where(np.sum(v*v_axis,axis=1,keepdims=True)<0,-1.,1.)
    local=unit(encoded*2-1)
    return unit(u*local[:,0:1]+v*local[:,1:2]+n*local[:,2:3])

for index,triangle in enumerate(target['uv']):
    pixels=triangle_pixels(triangle,SIZE)
    if pixels is None:continue
    x,y,w=pixels
    if not len(x):continue
    pos=w@target['points'][index];n=unit(w@target['normals'][index])
    tangent=unit(w@target['tangents'][index]);tangent=unit(tangent-n*np.sum(tangent*n,axis=1,keepdims=True))
    bitangent=unit(np.cross(n,tangent))*np.sign(w@target['signs'][index])[:,None]
    # Existing region mask preserves the authored edge/body boundary exactly.
    old_color=sample(old,w@triangle)
    mask=old_color.mean(axis=1)
    lower,upper=config.get('edge_mask_thresholds',[.42,.58])
    mask=np.clip((mask-lower)/(upper-lower),0.,1.);mask=mask*mask*(3-2*mask);mask=mask[:,None]
    dominant=int(np.argmax(np.abs(n.mean(axis=0))))
    axes=(0,2) if dominant==1 else (1,2) if dominant==0 else (0,1)
    u_axis=np.eye(3)[axes[0]][None,:];v_axis=np.eye(3)[axes[1]][None,:]
    body_uv=pos[:,axes]/np.array(specs['body']['swatch_physical_m'])
    _,nearest=tree.query(pos[:,[0,2]])
    seg=segments[nearest];fraction=np.clip(np.sum((pos[:,[0,2]]-edge_points[nearest])*seg,axis=1)/seglen[nearest]**2,0.,1.)
    on_edge=edge_points[nearest]+fraction[:,None]*seg
    along=unit(seg);across=np.column_stack((along[:,1],-along[:,0]))
    # Across points toward the blade interior for this clockwise cutting curve.
    edge_uv=np.column_stack((np.sum((pos[:,[0,2]]-on_edge)*across,axis=1),starts[nearest]+fraction*seglen[nearest]))/np.array(specs['edge']['swatch_physical_m'])
    eu=np.column_stack((across[:,0],np.zeros(len(x)),across[:,1]));ev=np.column_stack((along[:,0],np.zeros(len(x)),along[:,1]))
    for key in ['BaseColor','ORM']:
        a=sample(tiles['body'][key],body_uv,True);b=sample(tiles['edge'][key],edge_uv,True)
        if key=='BaseColor' and 'body_pattern_linear_mean' in config:
            old_linear=np.where(old_color<=.04045,old_color/12.92,((old_color+.055)/1.055)**2.4)
            a*=np.clip(old_linear.mean(axis=1,keepdims=True)/config['body_pattern_linear_mean'],.94,1.06)
        out[key][y,x]=a*(1-mask)+b*mask
    a=normal_to_world(sample(tiles['body']['Normal'],body_uv,True),n,u_axis,v_axis)
    b=normal_to_world(sample(tiles['edge']['Normal'],edge_uv,True),n,eu,ev)
    world=unit(a*(1-mask)+b*mask)
    local=unit(np.column_stack((np.sum(world*tangent,axis=1),np.sum(world*bitangent,axis=1),np.sum(world*n,axis=1))))
    out['Normal'][y,x]=local*.5+.5;filled[y,x]=True
    if index%8000==0:print('FACTORY_PBR_TRANSFER triangle='+str(index),flush=True)

# Pad UV islands using their own nearest populated texels, as in the existing pipeline.
nearest=distance_transform_edt(~filled,return_distances=False,return_indices=True)
for key,pixels in out.items():
    pixels[~filled]=pixels[nearest[0][~filled],nearest[1][~filled]]
    if key=='BaseColor':pixels=np.where(pixels<=.0031308,pixels*12.92,1.055*np.maximum(pixels,0.)**(1/2.4)-.055)
    Image.fromarray(np.uint8(np.clip(pixels,0.,1.)*255+.5)).save(P/'Textures'/(prefix+'_'+key+'.png'))
(P/'texture_recipe.json').write_text(json.dumps({'source':source,'regions':specs,'size':SIZE,
    'method':'actual factory PBR swatches at measured physical scale; periodic swatch boundary; authored edge mask',
    'part_config':config,
    'normal_convention':'OpenGL, converted through authored tangent frames; flip green once in UE',
    'geometry_modified':False,'uv_modified':False,'runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('FACTORY_PBR_AUTHORED '+json.dumps(specs),flush=True)
