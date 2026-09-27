#include "ColdSteelStaffIcon.h"
#include "Engine/Texture2D.h"

void ColdSteelStaffIcon::FrameVisiblePixels(FSlateBrush& Brush,const FColor* Pixels,int32 Width,int32 Height)
{
    int32 MinX=Width,MinY=Height,MaxX=-1,MaxY=-1;
    for(int32 Y=0;Y<Height;++Y)for(int32 X=0;X<Width;++X)
    {
        if(Pixels[Y*Width+X].A==0)continue;
        MinX=FMath::Min(MinX,X);MinY=FMath::Min(MinY,Y);
        MaxX=FMath::Max(MaxX,X);MaxY=FMath::Max(MaxY,Y);
    }
    if(MaxX<MinX||MaxY<MinY)return;
    // Keep two transparent texels for bilinear filtering; retain the crystal's
    // translucent edges. Only the brush UVs change, not the underlying PNG/model.
    MinX=FMath::Max(0,MinX-2);MinY=FMath::Max(0,MinY-2);
    MaxX=FMath::Min(Width,MaxX+3);MaxY=FMath::Min(Height,MaxY+3);
    Brush.SetUVRegion(FBox2d(FVector2D(double(MinX)/Width,double(MinY)/Height),
                             FVector2D(double(MaxX)/Width,double(MaxY)/Height)));
    Brush.ImageSize=FVector2D(MaxX-MinX,MaxY-MinY);
}

void ColdSteelStaffIcon::FrameImportedTexture(FSlateBrush& Brush,UTexture2D* Texture)
{
    // ImportFileAsTexture2D creates an uncompressed transient platform mip.
    auto* Platform=Texture?Texture->GetPlatformData():nullptr;
    if(!Platform||Platform->PixelFormat!=PF_B8G8R8A8||Platform->Mips.IsEmpty())return;
    auto& Mip=Platform->Mips[0];
    const auto* Pixels=static_cast<const FColor*>(Mip.BulkData.LockReadOnly());
    if(Pixels)FrameVisiblePixels(Brush,Pixels,Mip.SizeX,Mip.SizeY);
    Mip.BulkData.Unlock();
}
