#include "HK416Attachments.h"
#include "HK416WeaponAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"

FTransform HK416Attachments::ReferenceMount(const USkeletalMeshComponent* Host)
{
    const auto& Ref = Host->GetSkeletalMeshAsset()->GetRefSkeleton();
    FTransform Bind = FTransform::Identity;
    for (int32 I = Ref.FindBoneIndex(TEXT("WPN_root")); I != INDEX_NONE; I = Ref.GetParentIndex(I))
        Bind = Bind * Ref.GetRefBonePose()[I];
    return FTransform::Identity.GetRelativeTransform(Bind);
}

UStaticMeshComponent* HK416Attachments::Configure(AActor* Owner, USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing, const FString& Part, bool Enabled)
{
    if (Existing) Existing->SetVisibility(false);
    if (!Enabled || !HK416WeaponAssets::Matches(Host)) return Existing;
    auto* Mesh = LoadObject<UStaticMesh>(nullptr, *HK416WeaponAssets::AttachmentPath(Part));
    if (!Mesh) return Existing;
    if (!Existing)
    {
        Existing = NewObject<UStaticMeshComponent>(Owner);
        Existing->SetupAttachment(Host, TEXT("WPN_root"));
        Existing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Existing->SetCastShadow(false);
        Existing->bReceivesDecals = false;
        Existing->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);
        Existing->SetOnlyOwnerSee(Host->bOnlyOwnerSee);
        Existing->RegisterComponent();
    }
    else Existing->AttachToComponent(Host, FAttachmentTransformRules::KeepRelativeTransform, TEXT("WPN_root"));
    Existing->EmptyOverrideMaterials();
    Existing->SetStaticMesh(Mesh);
    Existing->SetRelativeTransform(ReferenceMount(Host));
    Existing->SetVisibility(true);
    return Existing;
}
