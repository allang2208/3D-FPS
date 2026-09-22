#pragma once
#include "GunsmithSystem.h"
class UMeshComponent;
namespace ColdSteelMeleeRune
{
    FString Selected(const FColdSteelItem& Item);
    // Definition：物品定义 id，金色符文强化据此选择剑身原装刃面纹样遮罩。
    void Apply(UMeshComponent* Mesh,const FString& Rune,const FString& Definition=FString());
    bool UpdatePose(UMeshComponent* Mesh,double PreviewTime=-1);
}
