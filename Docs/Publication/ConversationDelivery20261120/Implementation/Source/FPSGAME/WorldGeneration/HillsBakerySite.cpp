#include "HillsBakerySite.h"
#include "../Building/ColdSteelWindow.h"
#include "Engine/Level.h"
#include "VillageShopTorches.h"
#include "VillageChimneySmoke.h"
#include "AI/NavigationSystemBase.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

namespace HillsBakerySite
{
    static const FName Ruin(TEXT("VillageBakery.Ruin"));
    static const FName Restored(TEXT("VillageBakery.Restored"));
    static const FName Solid(TEXT("VillageBakery.Solid"));

    void Apply(AActor& Site, bool bRepaired)
    {
        TInlineComponentArray<UStaticMeshComponent*> Parts(&Site);
        for (UStaticMeshComponent* Part : Parts)
        {
            const bool bRuin = Part->ComponentHasTag(Ruin);
            if (!bRuin && !Part->ComponentHasTag(Restored)) continue;
            const bool bShow = bRuin != bRepaired;
            Part->SetVisibility(bShow);
            Part->SetHiddenInGame(!bShow);
            const auto Collision = bShow && Part->ComponentHasTag(Solid)
                ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision;
            if (Part->GetCollisionEnabled() != Collision)
            {
                Part->SetCollisionEnabled(Collision);
                if (Site.HasAuthority() && Part->CanEverAffectNavigation())
                    FNavigationSystem::UpdateComponentData(*Part);
            }
        }
        if (const ULevel* Village = Site.GetLevel())
            for (AActor* Actor : Village->Actors)
                if (IsValid(Actor) && Actor->ActorHasTag(TEXT("VillageBakery.Window")))
                    if (auto* Window = Cast<AColdSteelWindow>(Actor)) Window->SetRepairAvailable(bRepaired);
        if (Site.GetNetMode() != NM_DedicatedServer)
        {
            TInlineComponentArray<UPointLightComponent*> Lamps(&Site);
            for (UPointLightComponent* Lamp : Lamps)
                if (Lamp->ComponentHasTag(Restored))
                {
                    Lamp->SetVisibility(bRepaired);
                    Lamp->SetHiddenInGame(!bRepaired);
                }
            VillageChimneySmoke::Apply(Site,bRepaired);
            VillageShopTorches::Apply(Site, VillageShopTorches::EShop::Bakery, bRepaired);
        }
    }

    bool IsOccupied(const AActor& Site)
    {
        const FTransform& Frame = Site.GetActorTransform();
        FBox Bounds(ForceInit);
        TInlineComponentArray<UStaticMeshComponent*> Parts(&Site);
        for (const UStaticMeshComponent* Part : Parts)
        {
            if (Part->ComponentHasTag(Solid))
                Bounds += Part->CalcBounds(Part->GetComponentTransform().GetRelativeTransform(Frame)).GetBox();
        }
        if (!Bounds.IsValid) return true;
        Bounds.Max.Z += 4.;
        return Site.GetWorld()->OverlapAnyTestByObjectType(Frame.TransformPosition(Bounds.GetCenter()),
            Frame.GetRotation(), FCollisionObjectQueryParams(ECC_Pawn),
            FCollisionShape::MakeBox(Bounds.GetExtent()*Frame.GetScale3D().GetAbs()),
            FCollisionQueryParams(SCENE_QUERY_STAT(VillageBakeryRepair), false, &Site));
    }
}
