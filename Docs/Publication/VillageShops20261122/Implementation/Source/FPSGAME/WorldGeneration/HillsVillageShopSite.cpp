#include "HillsVillageShopSite.h"
#include "VillageInteriorLighting.h"
#include "../Building/ColdSteelWindow.h"
#include "Engine/Level.h"
#include "VillageChimneySmoke.h"
#include "AI/NavigationSystemBase.h"
#include "Components/StaticMeshComponent.h"
#include "Components/LightComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

namespace HillsVillageShopSite
{
    const FShop Bakery = {
        TEXT("VillageBakery.Ruin"), TEXT("VillageBakery.Restored"), TEXT("VillageBakery.Solid"),
        TEXT("VillageBakery.Window"), NAME_None, VillageShopTorches::EShop::Bakery
    };
    const FShop Gunshop = {
        TEXT("VillageGunshop.Ruin"), TEXT("VillageGunshop.Restored"), TEXT("VillageGunshop.Solid"),
        TEXT("VillageGunshop.Window"), TEXT("VillageGunshop.Service"), VillageShopTorches::EShop::Gunshop
    };

    void Apply(AActor& Site, const FShop& Shop, bool bRepaired)
    {
        TInlineComponentArray<UStaticMeshComponent*> Parts(&Site);
        for (UStaticMeshComponent* Part : Parts)
        {
            const bool bRuin = Part->ComponentHasTag(Shop.Ruin);
            if (!bRuin && !Part->ComponentHasTag(Shop.Restored)) continue;
            const bool bShow = bRuin != bRepaired;
            Part->SetVisibility(bShow);
            Part->SetHiddenInGame(!bShow);
            const auto Collision = bShow && Part->ComponentHasTag(Shop.Solid)
                ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision;
            if (Part->GetCollisionEnabled() != Collision)
            {
                Part->SetCollisionEnabled(Collision);
                if (Site.HasAuthority() && Part->CanEverAffectNavigation())
                    FNavigationSystem::UpdateComponentData(*Part);
            }
        }
        if (const ULevel* Village = Site.GetLevel())
        {
            for (AActor* Actor : Village->Actors)
            {
                if (!IsValid(Actor)) continue;
                if (Actor->ActorHasTag(Shop.Window))
                {
                    if (auto* Window = Cast<AColdSteelWindow>(Actor)) Window->SetRepairAvailable(bRepaired);
                }
                else if (!Shop.Service.IsNone() && Actor->ActorHasTag(Shop.Service))
                {
                    Actor->SetActorHiddenInGame(!bRepaired);
                    Actor->SetActorEnableCollision(bRepaired);
                }
            }
        }
        if (Site.GetNetMode() != NM_DedicatedServer)
        {
            TInlineComponentArray<ULightComponent*> Lamps(&Site);
            for (ULightComponent* Lamp : Lamps)
                if (Lamp->ComponentHasTag(Shop.Restored))
                {
                    if (bRepaired) UVillageInteriorLighting::ApplyAppearance(Cast<UPointLightComponent>(Lamp));
                    Lamp->SetVisibility(bRepaired);
                    Lamp->SetHiddenInGame(!bRepaired);
                }
            if (Shop.Lighting == VillageShopTorches::EShop::Bakery) VillageChimneySmoke::Apply(Site,bRepaired);
            VillageShopTorches::Apply(Site, Shop.Lighting, bRepaired);
        }
    }

    bool IsOccupied(const AActor& Site, const FShop& Shop)
    {
        const FTransform& Frame = Site.GetActorTransform();
        FBox Bounds(ForceInit);
        TInlineComponentArray<UStaticMeshComponent*> Parts(&Site);
        for (const UStaticMeshComponent* Part : Parts)
        {
            if (Part->ComponentHasTag(Shop.Solid))
                Bounds += Part->CalcBounds(Part->GetComponentTransform().GetRelativeTransform(Frame)).GetBox();
        }
        if (!Bounds.IsValid) return true;
        Bounds.Max.Z += 4.;
        return Site.GetWorld()->OverlapAnyTestByObjectType(Frame.TransformPosition(Bounds.GetCenter()),
            Frame.GetRotation(), FCollisionObjectQueryParams(ECC_Pawn),
            FCollisionShape::MakeBox(Bounds.GetExtent()*Frame.GetScale3D().GetAbs()),
            FCollisionQueryParams(SCENE_QUERY_STAT(VillageShopRepair), false, &Site));
    }
}
