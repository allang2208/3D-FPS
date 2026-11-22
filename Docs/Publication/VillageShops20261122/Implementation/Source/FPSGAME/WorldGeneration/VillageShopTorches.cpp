#include "VillageShopTorches.h"
#include "../Building/BronzeTorch.h"
#include "Components/ChildActorComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "NiagaraComponent.h"

namespace VillageShopTorches
{
    struct FMount
    {
        FName Id;
        FVector Wall;
        float OutwardYaw;
        float Lumens;
        float Radius;
    };

    // Centimetres above the shop floor, in the same house frame as the authored wall bays.
    // The smith already has a working exterior bracket on the front right arcade pier.
    static const FMount Smith[] = {
        {TEXT("SmithSideSconce"), {412,-146,177}, 0.f, 165.f,440.f}
    };
    // West entrance post and the solid east return behind the stock-drying rack.
    static const FMount Carpenter[] = {
        {TEXT("CarpenterEntrySconce"), {-365,-402,172}, -90.f, 270.f,535.f},
        {TEXT("CarpenterYardSconce"), {413,126,187}, 0.f, 180.f,460.f}
    };
    // Solid pier to the right of the apothecary door, beneath the sign, and the east stone bay.
    static const FMount Herbalist[] = {
        {TEXT("HerbalistEntrySconce"), {-62,-373,171}, -90.f, 225.f,490.f},
        {TEXT("HerbalistSideSconce"), {368,-147,180}, 0.f, 145.f,425.f}
    };
    // The inn sign hangs east of the entry. Its eastern gable regains this solid bay on repair.
    static const FMount Tavern[] = {
        {TEXT("TavernEntrySconce"), {-153,-448,183}, -90.f, 280.f,545.f},
        {TEXT("TavernSideSconce"), {653,-165,174}, 0.f, 170.f,465.f}
    };
    // Centre the bracket on the door pier, above the 210 cm shutter heads;
    // the second bracket seats against the actual east-wall post near the yard.
    static const FMount Bakery[] = {
        {TEXT("BakeryDoorSconce"), {106,-15,226}, -90.f, 220.f,520.f},
        {TEXT("BakerySideSconce"), {407,613,182}, 0.f, 145.f,435.f}
    };
    static const FMount Gunshop[] = {
        // Left of the doorway, between its jamb and the street casement. The sign is to the right.
        {TEXT("GunshopDoorSconce"), {-135,-18,186}, -90.f, 235.f,500.f},
        // The east ground-floor casement spans Y=48..160. Mount on the next solid stone bay.
        {TEXT("GunshopSideSconce"), {505,345,190}, 0.f, 145.f,420.f}
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

    void Apply(AActor& Host, EShop Shop, bool bRepaired)
    {
        if (Host.GetNetMode()==NM_DedicatedServer || !Host.GetRootComponent()) return;
        static const FName FixtureTag(TEXT("VillageShop.ExteriorTorch"));
        TInlineComponentArray<UChildActorComponent*> Sockets(&Host);
        if (!bRepaired)
        {
            for (UChildActorComponent* Socket : Sockets)
                if (Socket->ComponentHasTag(FixtureTag)) Socket->DestroyComponent();
            return;
        }
        // The forge owns its front-pier fixture alongside its two interior torches.
        // Give just that existing exterior lamp the same photometry as the street.
        if (Shop == EShop::Blacksmith)
        {
            static const FName Entry(TEXT("Smith_EntryTorch"));
            static const FName Tuned(TEXT("VillageShop.ExteriorPhotometry"));
            for (UChildActorComponent* Socket : Sockets)
            {
                if (Socket->GetFName() != Entry || Socket->ComponentHasTag(Tuned)) continue;
                if (auto* Torch = Cast<ABronzeTorch>(Socket->GetChildActor()))
                {
                    ConfigureWallTorch(*Torch, 260.f, 535.f);
                    Socket->ComponentTags.Add(Tuned);
                }
            }
        }

        // Workshop actors live at their workbenches. The tavern site already owns its floor frame.
        FTransform HostInHouse = FTransform::Identity;
        TConstArrayView<FMount> Mounts;
        switch (Shop)
        {
        case EShop::Blacksmith:
            HostInHouse = FTransform(FVector(120,40,6)); Mounts = Smith; break;
        case EShop::Carpenter:
            HostInHouse = FTransform(FRotator(0,-90,0), FVector(238,248,-1.47)); Mounts = Carpenter; break;
        case EShop::Herbalist:
            HostInHouse = FTransform(FVector(37,302,-1)); Mounts = Herbalist; break;
        case EShop::Tavern:
            Mounts = Tavern; break;
        case EShop::Bakery:
            Mounts = Bakery; break;
        case EShop::Gunshop:
            Mounts = Gunshop; break;
        }
        const FTransform House = HostInHouse.Inverse() * Host.GetActorTransform();
        for (const FMount& Mount : Mounts)
        {
            if (Sockets.ContainsByPredicate([&](const UChildActorComponent* C){ return C->ComponentHasTag(Mount.Id); })) continue;
            const FVector Outward = House.TransformVectorNoScale(FRotator(0,Mount.OutwardYaw,0).Vector());
            FVector Wall = House.TransformPosition(Mount.Wall);
            // Normandy's uneven masonry faces sit a few centimetres either side of their authored plane.
            // The short cast stays within the chosen bay, away from shutters, doors and signs.
            FHitResult Face;
            FCollisionObjectQueryParams Solid(ECC_WorldStatic);
            Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
            // The tavern shell is itself the host; the other hosts are separate workbenches.
            const bool bOwnsShell = Shop==EShop::Tavern || Shop==EShop::Bakery || Shop==EShop::Gunshop;
            FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageShopSconceMount),true,bOwnsShell ? nullptr : &Host);
            if (Host.GetWorld()->LineTraceSingleByObjectType(Face,Wall+Outward*45.,Wall-Outward*42.,Solid,Query)
                && Face.GetActor() && Face.GetActor()->GetLevel()==Host.GetLevel()
                && FVector::DotProduct(Face.ImpactNormal,Outward)>.65)
            {
                Wall = Face.ImpactPoint;
            }
            // The bronze shank begins 16 cm ahead of the pivot; bed it 5 cm into the support.
            const FTransform Pose(Outward.Rotation(),Wall-Outward*21.);
            auto* Socket = NewObject<UChildActorComponent>(&Host,NAME_None,RF_Transient);
            Socket->ComponentTags.Add(FixtureTag);
            Socket->ComponentTags.Add(Mount.Id);
            Socket->SetupAttachment(Host.GetRootComponent());
            Socket->SetRelativeTransform(Pose.GetRelativeTransform(Host.GetActorTransform()));
            Socket->SetChildActorClass(ABronzeTorch::StaticClass());
            Host.AddInstanceComponent(Socket);
            Socket->RegisterComponent();
            if (auto* Torch = Cast<ABronzeTorch>(Socket->GetChildActor()))
                ConfigureWallTorch(*Torch, Mount.Lumens, Mount.Radius);
        }
    }
}
