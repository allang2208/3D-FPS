#include "HK416Attachments.h"
#include "HK416WeaponAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Rendering/SkeletalMeshRenderData.h"

FTransform HK416Attachments::ReferenceMount(const USkeletalMeshComponent* Host, FName Bone)
{
    const auto& Ref = Host->GetSkeletalMeshAsset()->GetRefSkeleton();
    FTransform Bind = FTransform::Identity;
    for (int32 I = Ref.FindBoneIndex(Bone); I != INDEX_NONE; I = Ref.GetParentIndex(I))
        Bind = Bind * Ref.GetRefBonePose()[I];
    return FTransform::Identity.GetRelativeTransform(Bind);
}

UStaticMeshComponent* HK416Attachments::Configure(AActor* Owner, USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing, const FString& Part, bool Enabled, FName Bone)
{
    if (Existing) Existing->SetVisibility(false);
    if (!Enabled || !HK416WeaponAssets::Matches(Host)) return Existing;
    auto* Mesh = LoadObject<UStaticMesh>(nullptr, *HK416WeaponAssets::AttachmentPath(Part));
    if (!Mesh) return Existing;
    if (!Existing)
    {
        Existing = NewObject<UStaticMeshComponent>(Owner);
        Existing->SetupAttachment(Host, Bone);
        Existing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Existing->SetCastShadow(false);
        Existing->bReceivesDecals = false;
        Existing->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);
        Existing->SetOnlyOwnerSee(Host->bOnlyOwnerSee);
        Existing->RegisterComponent();
    }
    else Existing->AttachToComponent(Host, FAttachmentTransformRules::KeepRelativeTransform, Bone);
    Existing->EmptyOverrideMaterials();
    Existing->SetStaticMesh(Mesh);
    Existing->SetRelativeTransform(ReferenceMount(Host, Bone));
    Existing->SetVisibility(true);
    return Existing;
}

void HK416Attachments::FactorySections(USkeletalMeshComponent* Host, const FString& Section, bool Visible)
{
    if (!HK416WeaponAssets::Matches(Host)) return;
    const auto* Asset = Host->GetSkeletalMeshAsset();
    if (const auto* Render = Asset->GetResourceForRendering())
        for (int32 L = 0; L < Render->LODRenderData.Num(); ++L)
            for (int32 S = 0; S < Render->LODRenderData[L].RenderSections.Num(); ++S)
            {
                const int32 M = Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if (Asset->GetMaterials().IsValidIndex(M) && Asset->GetMaterials()[M].MaterialSlotName.ToString().Contains(Section))
                    Host->ShowMaterialSection(M, S, Visible, L);
            }
}
