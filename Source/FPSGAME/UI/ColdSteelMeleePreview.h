#pragma once
#include "CoreMinimal.h"
#include "ColdSteelInventoryTypes.h"
#include "Engine/StaticMesh.h"

namespace ColdSteelMeleePreview
{
inline bool Supports(const FColdSteelItem& Item){return Item.Definition==TEXT("ue_rune_sword");}
inline FString MeshPath(const FColdSteelItem& Item){return ColdSteelInventory::Text(Item,TEXT("world_mesh"));}

// Use the blade's long and thin axes, independent of the asset's import orientation.
inline FQuat Rotation(const UStaticMesh& Mesh,bool Portrait=false)
{
    const FVector Size=Mesh.GetBoundingBox().GetSize();
    int32 Long=0,Thin=0;
    for(int32 Axis=1;Axis<3;++Axis){if(Size[Axis]>Size[Long])Long=Axis;if(Size[Axis]<Size[Thin])Thin=Axis;}
    if(Long==Thin)Thin=(Long+1)%3;
    FVector Blade=FVector::ZeroVector,Normal=FVector::ZeroVector;Blade[Long]=1;Normal[Thin]=1;
    const FQuat Source=FRotationMatrix::MakeFromXZ(Blade,Normal).ToQuat();
    const FQuat Target=FRotationMatrix::MakeFromXZ(Portrait?FVector::UpVector:-FVector::RightVector,-FVector::ForwardVector).ToQuat();
    return Target*Source.Inverse();
}
inline FTransform Pose(const UStaticMesh& Mesh,const FQuat& Rotation)
{
    return FTransform(Rotation,FVector(500,0,0)-Rotation.RotateVector(Mesh.GetBoundingBox().GetCenter()));
}
}
