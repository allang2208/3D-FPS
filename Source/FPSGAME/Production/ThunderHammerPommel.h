#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;
struct FLightningCast;
class AActor;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;

namespace ThunderHammerPommel
{
    inline constexpr const TCHAR* LeiXi=TEXT("lei_xi_pommel");
    void Configure(FLightningCast& Spell,const FColdSteelItem* Item);
    void ConfirmElectricDamage(AActor* Source,const FLightningCast& Spell,float AppliedDamage);
    UMaterialInstanceDynamic* BindVisual(UStaticMeshComponent* Root);
    void UpdateVisual(AActor* Holder,UMaterialInstanceDynamic* Core,bool& WasActive);
    void RefreshWorldCore(AActor* Holder,UStaticMeshComponent* Part);
}
