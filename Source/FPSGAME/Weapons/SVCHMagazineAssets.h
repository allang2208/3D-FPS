#pragma once
#include "SVCHWeaponAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

// Both shells are fitted to this SVCh's installed magazine socket, not the
// M4/SVD bind pose. See SourceAssets/SVCHReplacement20261018/MagazineSeat20261019.
namespace SVCHMagazineAssets
{
    inline constexpr const TCHAR* Standard = TEXT("/Game/Weapons/SVCH/Replacement20261018/MagazineSeat20261019/SM_SVCH_Magazine10.SM_SVCH_Magazine10");
    inline constexpr const TCHAR* Extended = TEXT("/Game/Weapons/SVCH/Replacement20261018/MagazineSeat20261019/SM_SVCH_Magazine20.SM_SVCH_Magazine20");

    inline bool IsFitted(const UStaticMeshComponent* Part)
    {
        return Part && Part->GetStaticMesh() &&
            (Part->GetStaticMesh()->GetPathName() == Standard || Part->GetStaticMesh()->GetPathName() == Extended);
    }

    inline void FactoryMagazine(USkeletalMeshComponent* Rifle, bool Visible)
    {
        const auto* Mesh = Rifle->GetSkeletalMeshAsset();
        const auto* Render = Mesh->GetResourceForRendering();
        if (!Render) return;
        for (int32 L = 0; L < Render->LODRenderData.Num(); ++L)
            for (int32 S = 0; S < Render->LODRenderData[L].RenderSections.Num(); ++S)
            {
                const int32 M = Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if (!Mesh->GetMaterials().IsValidIndex(M)) continue;
                const FName Slot = Mesh->GetMaterials()[M].MaterialSlotName;
                if (Slot == TEXT("KVInhibitor_mag") || Slot == TEXT("bullet_338lp"))
                    Rifle->ShowMaterialSection(M, S, Visible, L);
            }
    }

    inline UStaticMeshComponent* Configure(AActor* Owner, USkeletalMeshComponent* Rifle,
        UStaticMeshComponent* Part, bool UseExtended, bool Enabled)
    {
        auto* Asset = Enabled ? LoadObject<UStaticMesh>(nullptr, UseExtended ? Extended : Standard) : nullptr;
        if (Asset)
        {
            if (!Part)
            {
                Part = NewObject<UStaticMeshComponent>(Owner, TEXT("SVCHMagazine"));
                Part->SetupAttachment(Rifle, TEXT("WPN_SOCKET_Magazine"));
                Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                Part->SetCastShadow(false);
                Part->bReceivesDecals = false;
                Part->RegisterComponent();
            }
            else Part->AttachToComponent(Rifle, FAttachmentTransformRules::KeepRelativeTransform, TEXT("WPN_SOCKET_Magazine"));
            if (Part->GetStaticMesh() != Asset) Part->EmptyOverrideMaterials();
            Part->SetStaticMesh(Asset);
            // Exported in actual socket centimetres; cancel its inherited x100
            // skeleton units once. No extra bind inverse or hand-tuned offset.
            Part->SetRelativeTransform(FTransform(FQuat::Identity, FVector::ZeroVector, FVector(.01f)));
        }
        if (Part) Part->SetVisibility(Asset != nullptr && Rifle->IsVisible());
        FactoryMagazine(Rifle, Asset == nullptr);
        if (Enabled && !Asset) UE_LOG(LogTemp, Error, TEXT("SVCH_MAGAZINE: missing fitted magazine asset"));
        return Part;
    }
}
