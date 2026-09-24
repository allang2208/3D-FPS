import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Receipts'
dxc='C:/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64/dxc.exe'
rows=[]
for name,typ,textures,inputs,outputs,call in [
    ('mortar_projected','float4',['HeightTex','ReliefColor','ReliefNormal','ReliefSurface'],
     'float3 Position,SurfaceNormal,ViewLocal; float DistanceCm,SurfaceTileCm,DepthCm,FadeStart,FadeEnd,Steps,RefineSteps,ReliefStrength;',
     'out float3 NormalLocal,out float AO', 'float3 n;float ao;float4 s=Surface(n,ao);return s+float4(n,ao)*.1;'),
    ('concrete_parallax','float2',['HeightTex'],
     'float2 UV;float3 View,WorldNormal;float DistanceCm,DepthCm;', '', 'return float4(Surface(),0,1);')]:
    source=(ROOT/'Scripts'/(name+'.ush')).read_text()
    wrapper='#define Texture2DSampleGrad(T,S,U,X,Y) T.SampleGrad(S,U,X,Y)\n'
    wrapper+='\n'.join('Texture2D<float4> '+t+';SamplerState '+t+'Sampler;' for t in textures)
    wrapper+='\ncbuffer Inputs{'+inputs+'};\n'+typ+' Surface('+outputs+'){\n'+source+'\n}\n'
    wrapper+='float4 main():SV_Target0{'+call+'}\n'
    file=OUT/(name+'.sm6.hlsl');file.write_text(wrapper)
    p=subprocess.run([dxc,'-T','ps_6_0','-E','main','-Fo',str(OUT/(name+'.dxil')),str(file)],capture_output=True,text=True)
    rows.append(dict(source=name,sha256=hashlib.sha256(source.encode()).hexdigest(),exit_code=p.returncode,output=p.stdout+p.stderr))
(OUT/'shader-compile-v2.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
raise SystemExit(int(any(x['exit_code'] for x in rows)))
