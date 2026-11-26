#include "VillageShopTorches.h"
#include "SmithYardLamp.h"
#include "../Building/BronzeTorch.h"
#include "Components/ChildActorComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "NiagaraComponent.h"

namespace VillageShopTorches
{
    enum class ELighting { Clock, Indoor, SurvivesRuin };
    struct FMount
    {
        FName Id;
        FVector Wall;
        float Yaw;
        ELighting Lighting=ELighting::Clock;
    };

    // Wall-plate centres, above the lantern handle. Coordinates are in each house's floor frame.
    static const FMount Smith[] = {
        {TEXT("SmithWorkshopLamp"),{0,-376.5,290},90,ELighting::Indoor},
        {TEXT("SmithLoftLamp"),{-150,350,640},-90,ELighting::Indoor},
        {TEXT("SmithEntryLamp"),{365,-402,271},-90},
        {TEXT("SmithYardChainLamp"),{412,-146,276},0,ELighting::Indoor}
    };
    static const FMount Carpenter[] = {
        {TEXT("CarpenterEntryLamp"),{-365,-402,274},-90},
        {TEXT("CarpenterYardLamp"),{413,126,284},0}
    };
    static const FMount Herbalist[] = {
        {TEXT("HerbalistEntryLamp"),{-62,-373,272},-90},
        {TEXT("HerbalistSideLamp"),{368,-147,281},0},
        {TEXT("HerbalistInnerPierLamp"),{-279,-344,279},90,ELighting::SurvivesRuin},
        {TEXT("HerbalistInnerWallLamp"),{346,10,287},180,ELighting::Indoor}
    };
    static const FMount Tavern[] = {
        {TEXT("TavernEntryLamp"),{-153,-448,282},-90},
        {TEXT("TavernSideLamp"),{653,-165,275},0},
        {TEXT("TavernInnerPierLamp"),{197,-408,280},90,ELighting::SurvivesRuin},
        {TEXT("TavernInnerGableLamp"),{629,-235,280},180,ELighting::Indoor}
    };
    static const FMount Bakery[] = {
        {TEXT("BakeryDoorLamp"),{106,-15,288},-90},
        {TEXT("BakerySideLamp"),{407,613,279},0}
    };
    static const FMount Gunshop[] = {
        {TEXT("GunshopDoorLamp"),{-135,-18,283},-90},
        {TEXT("GunshopSideLamp"),{505,345,288},0}
    };

    void ConfigureWallTorch(ABronzeTorch& Torch, float Lumens, float Radius)
    {
        Torch.SetActorEnableCollision(false);
        Torch.ConfigureSceneLight(Lumens, Radius, true);
        Torch.SetSceneSpecularScale(FixtureSpecular);
        if (auto* Light = Torch.FindComponentByClass<UPointLightComponent>())
        {
            // The capsule's local Z follows the flame vertically above the cup.
            Light->SetSourceLength(14.f);
            Light->SetSourceRadius(7.f);
            Light->SetSoftSourceRadius(11.f);
            Light->SetVolumetricScatteringIntensity(.035f);
            Light->SetMaxDrawDistance(3200.f);
            Light->SetMaxDistanceFadeRange(950.f);
        }
        if (auto* Body = Torch.FindComponentByClass<UStaticMeshComponent>())
        {
            // A point-sampled shadow from the bowl otherwise cuts a rigid black
            // circle out of the doorstep. Walls, shutters and people still cast.
            Body->SetCastShadow(false);
            Body->SetCullDistance(6000.f);
            Body->SetReceivesDecals(false);
        }
        if (auto* Flame = Torch.FindComponentByClass<UNiagaraComponent>())
            Flame->SetCullDistance(4500.f);
        Torch.SetActorTickInterval(.08f);
        Torch.EnableExteriorClockSleep();
    }

    void Apply(AActor& Host, EShop Shop, bool bRepaired, AActor* FixtureHost)
    {
        AActor& Owner=FixtureHost ? *FixtureHost : Host;
        if (Host.GetNetMode()==NM_DedicatedServer || !Owner.GetRootComponent()) return;
        FTransform HostInHouse=FTransform::Identity;
        TConstArrayView<FMount> Mounts;
        switch (Shop)
        {
        case EShop::Blacksmith:
            HostInHouse=FTransform(FVector(120,40,6)); Mounts=Smith; break;
        case EShop::Carpenter:
            HostInHouse=FTransform(FRotator(0,-90,0),FVector(238,248,-1.47)); Mounts=Carpenter; break;
        case EShop::Herbalist:
            HostInHouse=FTransform(FVector(37,302,-1)); Mounts=Herbalist; break;
        case EShop::Tavern: Mounts=Tavern; break;
        case EShop::Bakery: Mounts=Bakery; break;
        case EShop::Gunshop: Mounts=Gunshop; break;
        }
        const FTransform House=HostInHouse.Inverse()*Host.GetActorTransform();
        const bool OwnsShell=Shop==EShop::Tavern || Shop==EShop::Bakery || Shop==EShop::Gunshop;
        TInlineComponentArray<UChildActorComponent*> Existing(&Owner);
        for (const FMount& Mount : Mounts)
        {
            const bool Survives=Mount.Lighting==ELighting::SurvivesRuin;
            const bool Wanted=bRepaired || Survives;
            const bool Cold=Survives && !bRepaired;
            if (auto** Found=Existing.FindByPredicate([&](const UChildActorComponent* C){return C->ComponentHasTag(Mount.Id);}))
            {
                if (Wanted && (*Found)->ComponentHasTag(AVillageShopChainLamp::Unlit)==Cold) continue;
                (*Found)->DestroyComponent();
            }
            if (!Wanted) continue;
            FVector Wall=House.TransformPosition(Mount.Wall);
            const FVector Outward=House.TransformVectorNoScale(FRotator(0,Mount.Yaw,0).Vector());
            FCollisionObjectQueryParams Solids(ECC_WorldStatic);
            Solids.AddObjectTypesToQuery(ECC_WorldDynamic);
            FHitResult Hit;
            if (Host.GetWorld()->LineTraceSingleByObjectType(Hit,Wall+Outward*45.,Wall-Outward*42.,Solids,
                    FCollisionQueryParams(SCENE_QUERY_STAT(VillageShopLampMount),true,OwnsShell ? nullptr : &Host))
                && Hit.GetActor() && Hit.GetActor()->GetLevel()==Host.GetLevel() && FVector::DotProduct(Hit.ImpactNormal,Outward)>.65)
                Wall=Hit.ImpactPoint;
            auto* Socket=NewObject<UChildActorComponent>(&Owner,NAME_None,RF_Transient);
            Socket->ComponentTags.Add(Mount.Id);
            if (Cold) Socket->ComponentTags.Add(AVillageShopChainLamp::Unlit);
            else if (Mount.Lighting!=ELighting::Clock) Socket->ComponentTags.Add(AVillageShopChainLamp::AlwaysLit);
            Socket->SetupAttachment(Owner.GetRootComponent());
            Socket->SetRelativeTransform(FTransform(Outward.Rotation(),Wall).GetRelativeTransform(Owner.GetActorTransform()));
            Socket->SetChildActorClass(AVillageShopChainLamp::StaticClass());
            Owner.AddInstanceComponent(Socket);
            Socket->RegisterComponent();
        }
    }
}
