#pragma once
#include "CoreMinimal.h"

class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;

namespace Super90RearGripAssets
{
inline bool Supports(const FString& Variant)
{
    return Variant==TEXT("phantom_reargrip")||Variant==TEXT("stable_antislip_reargrip")||Variant==TEXT("balanced_reargrip");
}
inline FString MeshPath(const FString& Variant)
{
    return Supports(Variant)?TEXT("/Game/Weapons/Super90/RearGrips20261012/Meshes/SM_Super90_")+Variant:FString();
}
UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing,const FString& Variant,bool Enabled);
}
