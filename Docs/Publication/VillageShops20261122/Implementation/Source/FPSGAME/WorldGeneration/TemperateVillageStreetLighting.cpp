#include "TemperateHillsWorld.h"
#include "VillageRoadLamp.h"
#include "Components/ChildActorComponent.h"

namespace VillageStreetLighting
{
    struct FStreetStation
    {
        int32 RoadSegment;
        double Fraction;
        double Side;
    };

    // Stations on the through-road in TemperateVillageLayout. Leave the smith and
    // carpenter approaches, chapel fork, bakery entrance and east bend open.
    // The existing inn lamp occupies the opposite verge between stations 2 and 3.
    constexpr FStreetStation Interior[] = {
        {1, .056, -1.}, {2, .30, 1.}, {4, .714, 1.}, {6, .091, -1.},
        {6, .909, 1.}, {7, .831, -1.}, {8, .864, 1.}
    };
}

void ATemperateHillsWorld::RefreshVillageStreetLighting()
{
    AActor* Host = StreamedTavern.Get();
    if (!Host || !Host->GetRootComponent() || GetNetMode() == NM_DedicatedServer) return;

    const bool bStreet = VillageSite.bPlaced && VillageSite.bHilltop && IsVillageWallRepaired();
    const bool bJunction = bStreet || IsTavernRepaired();
    static const FName StreetTag(TEXT("VillageStreet.MainRoad"));
    static const FName InnTag(TEXT("VillageShop.TavernRoadLamp"));
    TInlineComponentArray<UChildActorComponent*> Sockets(Host);
    for (UChildActorComponent* Socket : Sockets)
    {
        if ((!bStreet && Socket->ComponentHasTag(StreetTag)) || (!bJunction && Socket->ComponentHasTag(InnTag)))
            Socket->DestroyComponent();
    }

    auto Exists = [&](FName Id)
    {
        return Sockets.ContainsByPredicate([Id](const UChildActorComponent* Socket)
            { return IsValid(Socket) && Socket->ComponentHasTag(Id); });
    };
    auto Install = [&](FName Id, const FTransform& LocalPose)
    {
        auto* Socket = NewObject<UChildActorComponent>(Host, NAME_None, RF_Transient);
        Socket->ComponentTags.Add(Id);
        if (Id != InnTag) Socket->ComponentTags.Add(StreetTag);
        Socket->SetMobility(Host->GetRootComponent()->Mobility);
        Socket->SetupAttachment(Host->GetRootComponent());
        Socket->SetRelativeTransform(LocalPose);
        Socket->SetChildActorClass(AVillageRoadLamp::StaticClass());
        Host->AddInstanceComponent(Socket);
        Socket->RegisterComponent();
        return Socket;
    };

    // Preserve the original inn fixture when the tavern is repaired first.
    // It uses the inn floor frame and is also a station in the municipal row.
    if (bJunction && !Exists(InnTag))
        Install(InnTag, FTransform(FRotator(0.,149.,0.), FVector(586.,-1125.,-4.)));
    if (!bStreet) return;

    int32 PostIndex = 0;
    const double VillageYaw = FMath::RadiansToDegrees(FMath::Atan2(VillageSite.Axis.Y, VillageSite.Axis.X));
    static const FName KeepVerge(TEXT("VillageStreet.HighGateVerge"));
    auto AddPost = [&](FVector2D Foot, FVector2D TowardRoad, bool bKeepVerge=false)
    {
        const FName Id(TEXT("VillageStreet.Post"), ++PostIndex);
        for (UChildActorComponent* Socket : Sockets)
        {
            if (!IsValid(Socket) || !Socket->ComponentHasTag(Id)) continue;
            if (Socket->ComponentHasTag(KeepVerge)==bKeepVerge) return;
            // The wall has changed tier since this station was installed.
            Socket->DestroyComponent();
            break;
        }
        const FVector2D XY = VillageSite.World(Foot.X, Foot.Y);
        const double Yaw = VillageYaw + FMath::RadiansToDegrees(FMath::Atan2(TowardRoad.Y, TowardRoad.X));
        const FTransform WorldPose(FRotator(0.,Yaw,0.), FVector(XY,Height(XY.X,XY.Y)));
        auto* Post=Install(Id, WorldPose.GetRelativeTransform(Host->GetActorTransform()));
        if (bKeepVerge) Post->ComponentTags.Add(KeepVerge);
    };

    for (const auto& Station : VillageStreetLighting::Interior)
    {
        const auto& Road = TemperateVillageLayout::Roads[Station.RoadSegment];
        const FVector2D Segment(Road.DX,Road.DY);
        const FVector2D Out = FVector2D(-Road.DY,Road.DX).GetSafeNormal() * Station.Side;
        const FVector2D Center = FVector2D(Road.X,Road.Y) + Segment * Station.Fraction;
        AddPost(Center + Out * (Road.HalfWidth + 45.), -Out);
    }

    // Keep the inner pair along the road verge. The western vault projects
    // 8.04 m from its grille and the eastern vault 6.04 m.
    for (const int32 GateSide : {-1,1})
    {
        double Verge = -GateSide;
        for (const double Offset : {-1700.,-700.,700.,1800.})
        {
            const bool bKeepVerge=HasVillageHighWall() && FMath::Abs(Offset)==700.;
            const double Distance=bKeepVerge && Offset>0. ? (GateSide<0 ? 1054. : 854.) : Offset;
            const double Shoulder=bKeepVerge ? (GateSide<0 ? 461. : 361.) : 260.;
            const double X = GateSide * (VillageSite.WallHalfSize().X + Distance);
            AddPost({X,VillageSite.GateY(GateSide)+Verge*Shoulder}, {0.,-Verge},bKeepVerge);
            Verge = -Verge;
        }
    }
}
