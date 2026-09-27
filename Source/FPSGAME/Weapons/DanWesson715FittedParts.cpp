#include "DanWesson715FittedParts.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace DanWesson715FittedParts
{
void ShowFactoryGrip(USkeletalMeshComponent* Host, bool bVisible)
{
    const auto* Asset = Host ? Host->GetSkeletalMeshAsset() : nullptr;
    const auto* Render = Asset ? Asset->GetResourceForRendering() : nullptr;
    if (!Render) return;
    for (int32 L = 0; L < Render->LODRenderData.Num(); ++L)
        for (int32 S = 0; S < Render->LODRenderData[L].RenderSections.Num(); ++S)
        {
            const int32 M = Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            if (Asset->GetMaterials().IsValidIndex(M)
                && Asset->GetMaterials()[M].MaterialSlotName == TEXT("M_DW715_Hero_Grip"))
                Host->ShowMaterialSection(M, S, bVisible, L);
        }
}

UStaticMeshComponent* Configure(AActor* Owner, USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing, const FString& Part, bool bEnabled, bool bMuzzle)
{
    bEnabled = bEnabled && (bMuzzle ? IsMuzzle(Part) : IsGrip(Part));
    auto* Asset = Host ? Host->GetSkeletalMeshAsset() : nullptr;
    if (bEnabled && Asset)
    {
        auto* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath(Part));
        if (Mesh)
        {
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
            if (Existing->GetStaticMesh() != Mesh) Existing->EmptyOverrideMaterials();
            Existing->SetStaticMesh(Mesh);
            const auto& Ref = Asset->GetRefSkeleton();
            auto Bone = [&Ref](const TCHAR* Name)
            {
                FTransform Result = FTransform::Identity;
                for (int32 I = Ref.FindBoneIndex(Name); I != INDEX_NONE; I = Ref.GetParentIndex(I))
                    Result = Result * Ref.GetRefBonePose()[I];
                return Result;
            };
            const FTransform Root = Bone(TEXT("WPN_root"));
            const FVector Up = Root.GetRotation().GetAxisZ();
            const FVector Forward = FVector::VectorPlaneProject(
                Bone(TEXT("WPN_FrontSight")).GetLocation() - Bone(TEXT("WPN_RearSight")).GetLocation(), Up).GetSafeNormal();
            const FVector Origin = bMuzzle ? Bone(TEXT("WPN_SOCKET_Muzzle")).GetLocation() : Root.GetLocation();
            // +X-forward FBX in centimetres, using the same reference frame as the 715 optics.
            // Relative transform also cancels the skeleton's imported root scale.
            Existing->SetRelativeTransform(FTransform(FRotationMatrix::MakeFromXZ(Forward, Up).ToQuat(), Origin).GetRelativeTransform(Root));
        }
        else
        {
            UE_LOG(LogTemp, Error, TEXT("DW715 missing fitted part %s"), *Part);
            bEnabled = false;
        }
    }
    else bEnabled = false;
    if (Existing) Existing->SetVisibility(bEnabled);
    if (!bMuzzle) ShowFactoryGrip(Host, !bEnabled);
    return Existing;
}
}
