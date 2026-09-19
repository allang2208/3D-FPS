#pragma once
#include "GunsmithSystem.h"
class UMeshComponent;
namespace ColdSteelMeleeRune
{
    FString Selected(const FColdSteelItem& Item);
    void Apply(UMeshComponent* Mesh,const FString& Rune);
    bool UpdatePose(UMeshComponent* Mesh,double PreviewTime=-1);
}
