#include "M1911MagazineVisual.h"
#include "G18WeaponAssets.h"
#include "M1911WeaponAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace M1911MagazineVisual
{
void ShowFactoryMagazine(USkeletalMeshComponent* Host, bool bVisible)
{
    const auto* Asset = Host ? Host->GetSkeletalMeshAsset() : nullptr;
    const auto* Render = Asset ? Asset->GetResourceForRendering() : nullptr;
    if (!Render) return;
    for (int32 L = 0; L < Render->LODRenderData.Num(); ++L)
        for (int32 S = 0; S < Render->LODRenderData[L].RenderSections.Num(); ++S)
        {
            const int32 M = Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            // Shell, floorplate and follower share this factory atlas. Cartridges
            // retain their separate material and animated bullet bone.
            if (Asset->GetMaterials().IsValidIndex(M)
                && (Asset->GetMaterials()[M].MaterialSlotName == TEXT("M_M1911_Hero_Magazine") || Asset->GetMaterials()[M].MaterialSlotName == TEXT("M_G18_Magazine")))
                Host->ShowMaterialSection(M, S, bVisible, L);
        }
}

UStaticMeshComponent* Configure(AActor* Owner, USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing, bool bEnabled)
{
    auto* Asset = Host ? Host->GetSkeletalMeshAsset() : nullptr;
    const FName Socket(TEXT("WPN_SOCKET_Magazine"));
    bEnabled = bEnabled && Asset && Host->DoesSocketExist(Socket);
    if (bEnabled)
    {
        auto* Mesh = LoadObject<UStaticMesh>(nullptr, *(G18WeaponAssets::Matches(Host)?G18WeaponAssets::AttachmentPath(TEXT("ext_mag")):M1911WeaponAssets::AttachmentPath(TEXT("ext_mag"))));
        if (Mesh)
        {
            if (!Existing)
            {
                Existing = NewObject<UStaticMeshComponent>(Owner);
                Existing->SetupAttachment(Host, Socket);
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
            FTransform Bind = FTransform::Identity;
            for (int32 I = Ref.FindBoneIndex(Socket); I != INDEX_NONE; I = Ref.GetParentIndex(I))
                Bind = Bind * Ref.GetRefBonePose()[I];
            // Exported in this pistol's unchanged skeletal mesh frame, matching
            // the original magazine through both reload tracks.
            Existing->SetRelativeTransform(FTransform::Identity.GetRelativeTransform(Bind));
        }
        else
        {
            UE_LOG(LogTemp, Error, TEXT("M1911 missing extended magazine mesh"));
            bEnabled = false;
        }
    }
    if (Existing) Existing->SetVisibility(bEnabled);
    ShowFactoryMagazine(Host, !bEnabled);
    return Existing;
}
}
