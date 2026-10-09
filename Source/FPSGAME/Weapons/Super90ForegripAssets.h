#pragma once
#include "CoreMinimal.h"

class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;

namespace Super90ForegripAssets
{
inline FString Family(const FString& Variant)
{
    if(Variant==TEXT("vertical_foregrip"))return TEXT("vertical");
    if(Variant==TEXT("tactical_vertical_foregrip"))return TEXT("tactical_vertical");
    if(Variant==TEXT("canted_foregrip"))return TEXT("canted");
    if(Variant==TEXT("prism_handstop"))return TEXT("prism");
    if(Variant==TEXT("angled_foregrip"))return TEXT("angled");
    return FString();
}
inline FString MeshPath(const FString& GripFamily)
{
    return TEXT("/Game/Weapons/Super90/Foregrips20261007/Meshes/SM_Super90_")+GripFamily;
}
inline FString ProfilePath(FName GripFamily)
{
    return TEXT("/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_")+GripFamily.ToString();
}
UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing,const TCHAR* GripFamily,bool bEnabled);
}
