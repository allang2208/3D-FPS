"""Chunked PyTorch neighborhood attention for the NAF inference path on Windows.

Uses dilation residue classes and shifted edge windows (no zero padding).
This replaces the native NATTEN operator, not the learned NAF weights.
"""
import torch
import torch.nn.functional as F

def na2d(q, k, v, kernel_size, dilation=(1, 1), stride=1, backend=None):
    if stride != 1:
        raise ValueError('NAF fallback supports stride=1 only')
    if isinstance(kernel_size, int): kernel_size=(kernel_size,kernel_size)
    if isinstance(dilation, int): dilation=(dilation,dilation)
    b,h,w,n,d=q.shape
    kh,kw=kernel_size;dh,dw=dilation
    if h < kh*dh or w < kw*dw:
        raise ValueError('Neighborhood larger than NAF feature map')
    out=torch.empty((b,h*w,n,v.shape[-1]),device=q.device,dtype=v.dtype)
    qflat=q.reshape(b,h*w,n,d)
    kflat=k.reshape(b,h*w,n,k.shape[-1]);vflat=v.reshape(b,h*w,n,v.shape[-1])
    oy=torch.arange(kh,device=q.device)*dh
    ox=torch.arange(kw,device=q.device)*dw
    for start in range(0,h*w,256):
        ids=torch.arange(start,min(start+256,h*w),device=q.device)
        y=ids//w;x=ids%w
        # Clamp in each dilated lattice; preserve the query's residue class.
        sy=torch.minimum(torch.clamp(y//dh-kh//2,min=0),(h-1-y%dh)//dh-kh+1)*dh+y%dh
        sx=torch.minimum(torch.clamp(x//dw-kw//2,min=0),(w-1-x%dw)//dw-kw+1)*dw+x%dw
        idx=((sy[:,None,None]+oy[None,:,None])*w+sx[:,None,None]+ox[None,None,:]).flatten(1)
        keys=kflat[:,idx].permute(0,1,3,2,4)
        values=vflat[:,idx].permute(0,1,3,2,4)
        query=qflat[:,ids].unsqueeze(-2)
        result=F.scaled_dot_product_attention(query,keys,values,scale=d**-0.5)
        out[:,ids]=result.squeeze(-2)
    return out.reshape(b,h,w,n,v.shape[-1])
