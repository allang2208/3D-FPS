#include "RSH12ForegripAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"

UStaticMeshComponent* RSH12ForegripAssets::Configure(AActor* Owner, USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing, const TCHAR* Family, bool bEnabled)
{
    // Destroy disabled components so whole-weapon visibility propagation cannot
    // restore a grip that the player removed or replaced.
    if(!bEnabled || !Host || !Host->GetSkeletalMeshAsset())
    {
        if(Existing)Existing->DestroyComponent();
        return nullptr;
    }
    const FString Path=TEXT("/Game/Weapons/RSH12/Foregrips20261004/Meshes/SM_RSH12_")+FString(Family);
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Path);
    if(!Mesh){if(Existing)Existing->DestroyComponent();return nullptr;}
    if(!Existing)
    {
        Existing=NewObject<UStaticMeshComponent>(Owner);
        Owner->AddInstanceComponent(Existing);
        Existing->SetupAttachment(Host,TEXT("WPN_root"));
        Existing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Existing->SetCastShadow(false);Existing->bReceivesDecals=false;
        Existing->SetOnlyOwnerSee(Host->bOnlyOwnerSee);
        Existing->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);
        Existing->RegisterComponent();
    }
    Existing->AttachToComponent(Host,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_root"));
    Existing->EmptyOverrideMaterials();Existing->SetStaticMesh(Mesh);
    // Same canonical->715 WPN_root frame for single and both dual meshes.
    // Native root is scaled 100; mesh centimeters therefore use relative .01.
    const FVector Forward(0.f,.9980492592f,-.0624317825f);
    const FVector Up(0.f,.0624317825f,.9980492592f);
    const FVector Origin(-.0001100056f,.1150264516f,-.0183265284f);
    const FVector Contact=Origin+Forward*.094f+Up*.0194712f;
    Existing->SetRelativeTransform(FTransform(FRotationMatrix::MakeFromXZ(Forward,Up).ToQuat(),Contact,FVector(.01f)));
    Existing->SetVisibility(true);
    return Existing;
}
