#pragma once
#include "CoreMinimal.h"

class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;

namespace Super90StockAssets
{
inline bool Supports(const FString& Variant)
{
    return Variant==TEXT("skeleton")||Variant==TEXT("core_stock")||Variant==TEXT("qr_performance")
        ||Variant==TEXT("tactical_telescopic")||Variant==TEXT("legendary_adjustable_tactical_stock");
}
inline FString MeshPath(const FString& Variant)
{
    return Supports(Variant)?TEXT("/Game/Weapons/Super90/CommonStocks20261013/Meshes/SM_Super90_")+Variant:FString();
}
UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing,const FString& Variant,bool Enabled);
}
