#pragma once
#include "CoreMinimal.h"
class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;

namespace Saiga12KMagazineAssets
{
inline constexpr auto Part=TEXT("saiga12k_ext12");
inline constexpr auto MeshPath=TEXT("/Game/Weapons/Saiga12K/Detail20261018/SM_Saiga12K_Ext12");
inline constexpr auto DrumPart=TEXT("saiga12k_drum20");
inline constexpr auto DrumMeshPath=TEXT("/Game/Weapons/Saiga12K/Drum20261018/SM_Saiga12K_Drum20");
UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Host,UStaticMeshComponent* Existing,const FString& Variant,bool Enabled);
}
