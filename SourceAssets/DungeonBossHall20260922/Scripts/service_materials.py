"""Deterministic sheath and layered weathering PBR, unique to the Boss room."""
import numpy as np

def extend(specs,noise,write,n):
    def normal(height,scale=.8):
        gy,gx=np.gradient(height,scale/n);v=np.stack((-gx,gy,np.ones_like(gx)),axis=-1)
        v/=np.linalg.norm(v,axis=-1,keepdims=True);return v*.5+.5
    coarse,medium,grain,fine=noise(6),noise(32),noise(124),noise(350)
    # Rubber is nonmetallic; very fine moulding grain and broad handling scuffs.
    rubber=np.array([26,29,27])[None,None,:]/255*(.91+.13*coarse[:,:,None]+.05*grain[:,:,None])
    specs['BossCableJacket']=dict(maps={
        'BaseColor':write('BossCableJacket','BaseColor',rubber),
        'Roughness':write('BossCableJacket','Roughness',.64+.16*medium+.05*(fine-.5)),
        'Metallic':write('BossCableJacket','Metallic',np.zeros((n,n))),
        'Normal':write('BossCableJacket','Normal',normal((fine-.5)*.000010+(grain-.5)*.000014,.8))},
        metallic=0,normal_strength=.40,provenance='Project-authored fine moulded rubber sheath; no metal response')
    # Three scales break corrosion into crust patches, dark pits and sparse orange edges.
    cluster=np.clip((coarse*.55+medium*.45-.42)*4,0,1)
    jagged=np.clip((grain-.35)*2,0,1)
    weather=np.clip(.12+cluster*.60+jagged*.28,0,1)
    rust=(np.array([59,31,16])[None,None,:]*(1-cluster[:,:,None])+
          np.array([137,73,31])[None,None,:]*cluster[:,:,None])/255
    rust*=.80+.26*grain[:,:,None]+.12*fine[:,:,None]
    rust_normal=normal((medium-.5)*.00035+(grain-.5)*.00060+(fine-.5)*.00015)
    rust_maps=dict(Weather=write('BossPipeWeather','Weather',weather),RustColor=write('BossPipeWeather','RustColor',rust),
        RustNormal=write('BossPipeWeather','RustNormal',rust_normal))
    for key,base,rough,metal in [('BossPipeCoat',[67,79,70],.58,.035),('BossPipeHardware',[83,88,83],.48,.76)]:
        # Old coating fades in broad zones; corrosion placement comes from authored flange/underside masks.
        chalk=.82+.24*coarse+.05*grain
        color=np.array(base)[None,None,:]/255*chalk[:,:,None]
        pores=np.clip((grain-.81)*5,0,1)
        color*=1-.18*pores[:,:,None]
        maps=dict(BaseColor=write(key,'BaseColor',color),Roughness=write(key,'Roughness',rough+(medium-.5)*.14+pores*.12),
            Metallic=write(key,'Metallic',np.full((n,n),metal)),Normal=write(key,'Normal',normal((fine-.5)*.000035-pores*.00010)),**rust_maps)
        specs[key]=dict(maps=maps,metallic=metal,normal_strength=.65,vertex_pipe_weather=True,rust_roughness=.91,
            provenance='Project-authored faded coating / nonmetallic iron oxide, placed by flange and gravity masks')
