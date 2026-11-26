"""Shared offline/UE material specification for bounded crouch hem clearance."""
AMPLITUDE_CM=15.5
def smooth_range(x,a,b):
    import numpy as np
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def offset(d,positions,transforms):
    import numpy as np
    rest=np.array(d['positions']);normal=np.c_[rest[:,0],rest[:,1]-.8,np.zeros(len(rest))];normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
    gate=(1-smooth_range(rest[:,2],80,118))*(1-smooth_range(abs(rest[:,0]),20,25))*smooth_range(rest[:,2]-positions[:,2],12,30)
    front=smooth_range(rest[:,1],-4,10)
    delta=normal*.8;delta[:,2]=2.5+13.0*front
    return positions+delta*gate[:,None]
HLSL='''float hem = 1.0 - smoothstep(80.0, 118.0, Rest.z);
float torso = 1.0 - smoothstep(20.0, 25.0, abs(Rest.x));
float crouch = smoothstep(12.0, 30.0, Rest.z - Skinned.z);
float3 outward = normalize(float3(Rest.x, Rest.y - 0.8, 0.0));
float front = smoothstep(-4.0, 10.0, Rest.y);
return float3(outward.xy * 0.8, 2.5 + 13.0 * front) * (hem * torso * crouch);'''
