#include "StableMarketShowcaseSubsystem.h"
#include "StableHorseMarket.h"
#include "StableRidingHorse.h"
#include "../FPSWeatherManager.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"

namespace StableMarketShowcase
{
    constexpr TCHAR AnimRoot[] = TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/Animations/");
    constexpr double MinForecourtSeparationCm = 270.;

    // 4 barn stalls (install_stable.py: X = 3520, 3960, 4400, 4840; HayCrib at X-181, Y=3816,
    // east face at CribX+36.8). Exact measured A_Warhorse_Q_Feed muzzle offset is +120.34 cm forward,
    // -2.17 cm right; placing feeding horses at CribX+125.5 keeps ForebodyCollision (88 cm) clear of
    // the crib (125.5 - 88 = 37.5 > 36.8) while the muzzle chews squarely inside the hay bed!
    struct FStallDef
    {
        double CenterX;
        double CenterY;
        double CribX;
        double CribY;
    };
    constexpr FStallDef Stalls[] = {
        { 3520., 3812., 3339., 3819. },
        { 3960., 3812., 3779., 3819. },
        { 4400., 3812., 4219., 3819. },
        { 4840., 3812., 4659., 3819. },
    };
    constexpr double StallFeedOffsetX = 125.5;
    constexpr double StallFeedOffsetY = -2.17;

    // Obstacle-audited entrance forecourt open yard (right inside the entrance gates,
    // clear of HayWagon X>=5270, west fence/dead-tree X<=4550, north gate swings Y<=1855,
    // and barn stall doors/props Y>=3420 -> ZERO solid obstacles inside this 5.1m x 11.8m box!).
    const FVector2D ForecourtRoamMin(4640., 2060.);
    const FVector2D ForecourtRoamMax(5150., 3240.);

    // Initial spawn anchors spread naturally across the entrance forecourt before roaming begins.
    struct FForecourtSeed
    {
        double X;
        double Y;
        float BaseYaw;
    };
    constexpr FForecourtSeed ForecourtSeeds[] = {
        { 4780., 2360.,  115.f }, // North-west entrance forecourt
        { 5010., 2560., -130.f }, // Central-east forecourt (clear of HayWagon)
        { 4770., 2960.,  -45.f }, // South-west forecourt facing barn / entrance
        { 5040., 3060., -110.f }, // South-east forecourt apron
    };

    template <typename T>
    void Shuffle(TArray<T>& Items, FRandomStream& Rng)
    {
        for (int32 I = Items.Num() - 1; I > 0; --I)
        {
            const int32 J = Rng.RandRange(0, I);
            if (I != J) Items.Swap(I, J);
        }
    }
}

bool UStableMarketShowcaseSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
    const UWorld* World = Cast<UWorld>(Outer);
    return World && World->IsGameWorld() && World->GetNetMode() != NM_DedicatedServer;
}

void UStableMarketShowcaseSubsystem::Deinitialize()
{
    ClearAllShowcase(false);
    Super::Deinitialize();
}

TStatId UStableMarketShowcaseSubsystem::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(UStableMarketShowcaseSubsystem, STATGROUP_Tickables);
}

void UStableMarketShowcaseSubsystem::LoadClipsIfNeeded()
{
    if (ClipIdle) return;
    auto LoadClip = [](const TCHAR* Name) -> UAnimSequence*
    {
        const FString Path = FString(StableMarketShowcase::AnimRoot) + Name + TEXT(".") + Name;
        return LoadObject<UAnimSequence>(nullptr, *Path);
    };
    ClipIdle      = LoadClip(TEXT("A_Warhorse_Idle"));
    ClipFeed      = LoadClip(TEXT("A_Warhorse_Q_Feed"));
    ClipQIdle     = LoadClip(TEXT("A_Warhorse_Q_Idle"));
    ClipQIdleLook = LoadClip(TEXT("A_Warhorse_Q_IdleLook"));
    ClipQHeadLow  = LoadClip(TEXT("A_Warhorse_Q_HeadLow"));
}

bool UStableMarketShowcaseSubsystem::FindWalkableGroundZ(const FVector& WorldRef, bool bStall, double& OutGroundZ) const
{
    UWorld* World = GetWorld();
    if (!World) return false;

    // Trace strictly from +65 cm (below roofs, beams, cribs, fence top rails & tree limbs) down to -160 cm
    // using ECC_Pawn (the exact walkable channel used by HorseRecallGround & UStableHorseGroundMesh).
    FCollisionQueryParams Query(SCENE_QUERY_STAT(StableShowcaseFloor), false);
    TArray<FHitResult> Hits;
    const FVector Start(WorldRef.X, WorldRef.Y, WorldRef.Z + 65.);
    const FVector End(WorldRef.X, WorldRef.Y, WorldRef.Z - 160.);
    if (!World->LineTraceMultiByChannel(Hits, Start, End, ECC_Pawn, Query)) return false;

    const double MaxAllowedZ = WorldRef.Z + (bStall ? 12. : 45.);
    const double MinAllowedZ = WorldRef.Z - (bStall ? 12. : 75.);
    for (const FHitResult& H : Hits)
    {
        if (!H.bBlockingHit || H.bStartPenetrating) continue;
        if (H.ImpactNormal.Z < 0.78f) continue;
        if (Cast<APawn>(H.GetActor())) continue;
        if (H.ImpactPoint.Z > MaxAllowedZ || H.ImpactPoint.Z < MinAllowedZ) continue;
        OutGroundZ = H.ImpactPoint.Z;
        return true;
    }
    return false;
}

bool UStableMarketShowcaseSubsystem::ResolveStableFrame()
{
    if (bHasStableFrame && StableAnchor.IsValid()) return true;
    bHasStableFrame = false;
    StableAnchor.Reset();

    UWorld* World = GetWorld();
    if (!World) return false;

    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!IsValid(Actor) || !Actor->ActorHasTag(TEXT("VillageStable.Assembly"))) continue;
        if (auto* ISM = Actor->FindComponentByClass<UInstancedStaticMeshComponent>())
        {
            const UStaticMesh* Mesh = ISM->GetStaticMesh();
            if (Mesh && Mesh->GetName().Contains(TEXT("PackedFloor")) && ISM->GetInstanceCount() > 0)
            {
                FTransform FloorWorld;
                if (ISM->GetInstanceTransform(0, FloorWorld, true))
                {
                    // PackedFloor instance 0 is authored at exact village-local (4400, 3950, 0), yaw 0.
                    const FTransform LocalFloor(FRotator::ZeroRotator, FVector(4400., 3950., 0.));
                    const FTransform CandidateFrame = LocalFloor.Inverse() * FloorWorld;

                    // Verify live ground collision is actually ready in the entrance forecourt before spawning
                    // (prevents spawning mid-air while streamed ForestVillageFoundation is still building collision).
                    const FVector ProbeForecourt = CandidateFrame.TransformPosition(FVector(4900., 2650., 0.));
                    const FVector ProbeStall = CandidateFrame.TransformPosition(FVector(4400., 3812., 0.));
                    double GroundZ = 0.;
                    VillageToWorld = CandidateFrame;
                    if (!FindWalkableGroundZ(ProbeForecourt, false, GroundZ) ||
                        !FindWalkableGroundZ(ProbeStall, true, GroundZ))
                    {
                        return false;
                    }

                    StableAnchor = Actor;
                    bHasStableFrame = true;
                    return true;
                }
            }
        }
    }
    return false;
}

void UStableMarketShowcaseSubsystem::ClearAllShowcase(bool bFadeOut)
{
    for (auto& Pair : LiveDisplay)
    {
        if (AStableRidingHorse* Horse = Pair.Value.Get())
        {
            if (bFadeOut) Horse->BeginShowcaseFadeOut();
            else Horse->Destroy();
        }
    }
    LiveDisplay.Reset();
    bShowcaseSleeping = false;
}

void UStableMarketShowcaseSubsystem::SetShowcaseSleeping(bool bSleep)
{
    if (bSleep == bShowcaseSleeping) return;
    if (bSleep)
    {
        for (const auto& Pair : LiveDisplay)
        {
            const AStableRidingHorse* Horse = Pair.Value.Get();
            if (Horse && Horse->IsShowcaseFading()) return;
        }
    }
    for (auto& Pair : LiveDisplay)
    {
        AStableRidingHorse* Horse = Pair.Value.Get();
        if (!Horse) continue;
        Horse->SetActorTickEnabled(!bSleep);
        if (auto* Move = Horse->GetCharacterMovement())
        {
            if (bSleep) Move->StopMovementImmediately();
            Move->SetComponentTickEnabled(!bSleep);
        }
    }
    bShowcaseSleeping = bSleep;
}

void UStableMarketShowcaseSubsystem::RefreshShowcase(bool bFadeTransition, int32 InDebugDayOverride)
{
    if (InDebugDayOverride >= 0) DebugDayOverride = InDebugDayOverride;
    ActiveDay = INDEX_NONE;
    ActiveRosterRevision = -1;
    NextScanTime = 0.;
    if (!bFadeTransition) bHasInitializedOnce = false;
}

void UStableMarketShowcaseSubsystem::Tick(float DeltaTime)
{
    UWorld* World = GetWorld();
    if (!World) return;
    const double Now = World->GetTimeSeconds();
    if (Now < NextScanTime) return;
    NextScanTime = Now + 0.5;

    if (!ResolveStableFrame())
    {
        if (!LiveDisplay.IsEmpty())
        {
            ClearAllShowcase(false);
            ActiveDay = INDEX_NONE;
            ActiveRosterRevision = -1;
            bHasInitializedOnce = false;
        }
        return;
    }

    auto* GI = World->GetGameInstance();
    auto* StatusModel = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    if (!StatusModel) return;
    const auto& Profile = StatusModel->ProfileView();
    const FGuid ProfileId = Profile.NetworkProfileId;
    if (!ProfileId.IsValid()) return;

    if (!CachedWeather.IsValid())
    {
        for (TActorIterator<AFPSWeatherManager> It(World); It; ++It)
        {
            CachedWeather = *It;
            break;
        }
    }
    if (DebugDayOverride < 0)
    {
        if (CachedWeather.IsValid())
        {
            if (!CachedWeather->IsWeatherStateReady()) return;
        }
        else if (World->GetNetMode() == NM_Client)
        {
            return;
        }
    }
    const int32 Day = DebugDayOverride >= 0
        ? DebugDayOverride
        : (CachedWeather.IsValid() ? CachedWeather->GetScheduleDay() : 0);
    const int64 RosterRev = Profile.MountRoster.Revision;

    bool bMissingLive = false;
    for (auto It = LiveDisplay.CreateIterator(); It; ++It)
    {
        if (!It.Value().IsValid())
        {
            It.RemoveCurrent();
            bMissingLive = true;
        }
    }

    if (bMissingLive || ProfileId != ActiveProfile || Day != ActiveDay || RosterRev != ActiveRosterRevision)
    {
        const bool bFade = bHasInitializedOnce;
        const TArray<FStableHorseOffer> Stock = StableHorseMarket::Stock(ProfileId, Day);
        ReconcileStock(ProfileId, Day, Stock, Profile.MountRoster, bFade);
        ActiveProfile = ProfileId;
        ActiveDay = Day;
        ActiveRosterRevision = RosterRev;
        bHasInitializedOnce = true;
        bShowcaseSleeping = false;
    }

    // Distance-based performance sleep: pause local showcase ticks & CMC when viewer is > 115 m away (wake < 95 m).
    if (!LiveDisplay.IsEmpty())
    {
        bool bViewerNear = true;
        if (const APlayerController* PC = World->GetFirstPlayerController())
        {
            FVector ViewLoc = FVector::ZeroVector;
            FRotator ViewRot = FRotator::ZeroRotator;
            if (const APawn* Pawn = PC->GetPawn()) ViewLoc = Pawn->GetActorLocation();
            else PC->GetPlayerViewPoint(ViewLoc, ViewRot);
            const FVector StableCenter = VillageToWorld.TransformPosition(FVector(4600., 3100., 0.));
            const double ThresholdCm = bShowcaseSleeping ? 9500. : 11500.;
            bViewerNear = FVector::DistSquared2D(ViewLoc, StableCenter) <= FMath::Square(ThresholdCm);
        }
        SetShowcaseSleeping(!bViewerNear);
    }
}

void UStableMarketShowcaseSubsystem::ReconcileStock(
    const FGuid& ProfileId, int32 Day, const TArray<FStableHorseOffer>& Offers,
    const FStableMountRoster& Roster, bool bFadeTransition)
{
    LoadClipsIfNeeded();

    // Deterministic per-day shuffle across the FULL daily stock so buying one horse
    // fades only that horse out without teleporting the remaining unsold horses.
    const uint32 Seed = HashCombineFast(GetTypeHash(ProfileId), HashCombineFast(uint32(Day), 0x5354424Cu));
    FRandomStream Rng(static_cast<int32>(Seed));

    TArray<int32> StallOrder{ 0, 1, 2, 3 };
    TArray<int32> ForecourtOrder{ 0, 1, 2, 3 };
    StableMarketShowcase::Shuffle(StallOrder, Rng);
    StableMarketShowcase::Shuffle(ForecourtOrder, Rng);

    // Put 2 horses in random barn stalls and 2 roaming freely in the entrance forecourt!
    const int32 Total = Offers.Num();
    int32 StallCount = 0;
    if (Total <= 1) StallCount = Total;
    else if (Total == 2) StallCount = 1;
    else StallCount = FMath::Clamp(Total / 2, 1, FMath::Min(Total - 1, StallOrder.Num()));

    TArray<int32> OfferOrder;
    OfferOrder.Reserve(Total);
    for (int32 I = 0; I < Total; ++I) OfferOrder.Add(I);
    StableMarketShowcase::Shuffle(OfferOrder, Rng);

    TMap<FGuid, FShowcaseSpot> PlannedSpots;
    TArray<FVector2D> UsedForecourtXY;
    int32 StallCursor = 0;
    int32 ForecourtCursor = 0;

    for (int32 Rank = 0; Rank < OfferOrder.Num(); ++Rank)
    {
        const FStableHorseOffer& Offer = Offers[OfferOrder[Rank]];
        FShowcaseSpot Spot;
        if (Rank < StallCount && StallCursor < StallOrder.Num())
        {
            const auto& Def = StableMarketShowcase::Stalls[StallOrder[StallCursor++]];
            const bool bFeed = Rng.FRand() < 0.55f;
            Spot.bStall = true;
            Spot.bFeedingCrib = bFeed;
            if (bFeed)
            {
                Spot.LocalFeet = FVector(
                    Def.CribX + StableMarketShowcase::StallFeedOffsetX,
                    Def.CribY + StableMarketShowcase::StallFeedOffsetY,
                    0.7);
                Spot.LocalYaw = 180.f;
            }
            else
            {
                Spot.LocalFeet = FVector(
                    Def.CenterX + Rng.FRandRange(-12., 18.),
                    Def.CenterY + Rng.FRandRange(-12., 12.),
                    0.7);
                // Face naturally toward the courtyard half-door (-90 deg) or angled inside the stall
                Spot.LocalYaw = Rng.FRand() < 0.55f ? Rng.FRandRange(-115.f, -65.f) : Rng.FRandRange(148.f, 198.f);
            }
        }
        else
        {
            // Place inside the entrance forecourt roam zone with guaranteed separation
            FVector2D ChosenXY(4900., 2650.);
            float ChosenYaw = Rng.FRandRange(-180.f, 180.f);
            bool bPicked = false;
            while (ForecourtCursor < ForecourtOrder.Num())
            {
                const auto& SeedPt = StableMarketShowcase::ForecourtSeeds[ForecourtOrder[ForecourtCursor++]];
                const FVector2D Cand(
                    FMath::Clamp(SeedPt.X + Rng.FRandRange(-45., 45.), StableMarketShowcase::ForecourtRoamMin.X + 40., StableMarketShowcase::ForecourtRoamMax.X - 40.),
                    FMath::Clamp(SeedPt.Y + Rng.FRandRange(-55., 55.), StableMarketShowcase::ForecourtRoamMin.Y + 40., StableMarketShowcase::ForecourtRoamMax.Y - 40.));
                bool bTooClose = false;
                for (const FVector2D& Existing : UsedForecourtXY)
                {
                    if (FVector2D::DistSquared(Cand, Existing) < FMath::Square(StableMarketShowcase::MinForecourtSeparationCm))
                    {
                        bTooClose = true;
                        break;
                    }
                }
                if (!bTooClose)
                {
                    ChosenXY = Cand;
                    ChosenYaw = SeedPt.BaseYaw + Rng.FRandRange(-35.f, 35.f);
                    bPicked = true;
                    break;
                }
            }
            if (!bPicked) continue;
            UsedForecourtXY.Add(ChosenXY);
            Spot.bStall = false;
            Spot.bFeedingCrib = false;
            Spot.LocalFeet = FVector(ChosenXY.X, ChosenXY.Y, 0.);
            Spot.LocalYaw = ChosenYaw;
        }
        PlannedSpots.Add(Offer.Horse.HorseId, Spot);
    }

    TMap<FGuid, const FStableHorseOffer*> Desired;
    for (const FStableHorseOffer& Offer : Offers)
    {
        if (Roster.Find(Offer.Horse.HorseId) != nullptr) continue;
        if (PlannedSpots.Contains(Offer.Horse.HorseId))
            Desired.Add(Offer.Horse.HorseId, &Offer);
    }

    // 1. Fade out removed or purchased display horses using summon dissolve.
    TArray<FGuid> ToRemove;
    for (auto& Pair : LiveDisplay)
    {
        if (!Desired.Contains(Pair.Key))
        {
            if (AStableRidingHorse* Old = Pair.Value.Get())
            {
                if (bFadeTransition) Old->BeginShowcaseFadeOut();
                else Old->Destroy();
            }
            ToRemove.Add(Pair.Key);
        }
    }
    for (const FGuid& Id : ToRemove) LiveDisplay.Remove(Id);

    // 2. Spawn & fade in newly active daily offers.
    for (const auto& Pair : Desired)
    {
        if (LiveDisplay.Contains(Pair.Key)) continue;
        const FShowcaseSpot& Spot = PlannedSpots[Pair.Key];
        if (AStableRidingHorse* Spawned = SpawnShowcaseHorse(*Pair.Value, Spot, Rng, bFadeTransition))
            LiveDisplay.Add(Pair.Key, Spawned);
    }
}

AStableRidingHorse* UStableMarketShowcaseSubsystem::SpawnShowcaseHorse(
    const FStableHorseOffer& Offer, const FShowcaseSpot& Spot, FRandomStream& Rng, bool bFadeIn)
{
    UWorld* World = GetWorld();
    if (!World) return nullptr;

    FVector WorldFeet = VillageToWorld.TransformPosition(Spot.LocalFeet);
    const FRotator WorldRot = VillageToWorld.TransformRotation(FRotator(0.f, Spot.LocalYaw, 0.f).Quaternion()).Rotator();

    // Strict walkable ECC_Pawn ground snap inside safe datum window (never lands on roofs, cribs or tree branches!).
    double GroundZ = WorldFeet.Z;
    if (FindWalkableGroundZ(WorldFeet, Spot.bStall, GroundZ))
    {
        WorldFeet.Z = GroundZ + 0.5;
    }

    const float CapsuleHalf = 94.f;
    const FTransform SpawnTM(WorldRot, WorldFeet + FVector(0., 0., CapsuleHalf));
    // AlwaysSpawn prevents UE's AdjustIfPossible from launching a stall horse onto the barn roof or crib.
    AStableRidingHorse* Horse = World->SpawnActorDeferred<AStableRidingHorse>(
        AStableRidingHorse::StaticClass(),
        SpawnTM,
        nullptr,
        nullptr,
        ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if (!Horse) return nullptr;

    // Local display actor so each player sees their own daily market stock cleanly.
    Horse->SetReplicates(false);
    Horse->SetReplicateMovement(false);
    Horse->MarkMarketShowcase();

    const TArray<UAnimSequence*> AmbientClips = { ClipFeed.Get(), ClipQIdle.Get(), ClipQIdleLook.Get(), ClipQHeadLow.Get() };
    const float Phase = Rng.FRandRange(0.f, 4.5f);

    Horse->FinishSpawning(SpawnTM);
    if (auto* Cap = Horse->GetCapsuleComponent())
    {
        const float Half = Cap->GetScaledCapsuleHalfHeight();
        Horse->SetActorLocationAndRotation(WorldFeet + FVector(0., 0., Half), WorldRot, false, nullptr, ETeleportType::TeleportPhysics);
    }
    Horse->ConfigureMarketShowcase(
        Offer,
        Spot.bStall,
        Spot.bFeedingCrib,
        AmbientClips,
        Phase,
        bFadeIn,
        VillageToWorld,
        StableMarketShowcase::ForecourtRoamMin,
        StableMarketShowcase::ForecourtRoamMax);

    return Horse;
}

#if !UE_BUILD_SHIPPING
static FAutoConsoleCommand StableShowcaseNextDayCmd(
    TEXT("fps.Stable.ShowcaseNextDay"),
    TEXT("Advance the stable market showcase to a specific or next day to preview summon fade transitions."),
    FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
    {
        static int32 PreviewDay = 0;
        if (Args.Num() > 0 && Args[0].IsNumeric()) PreviewDay = FCString::Atoi(*Args[0]);
        else ++PreviewDay;
        for (const FWorldContext& Ctx : GEngine->GetWorldContexts())
            if (UWorld* W = Ctx.World(); W && W->IsGameWorld())
                if (auto* Sub = W->GetSubsystem<UStableMarketShowcaseSubsystem>())
                    Sub->RefreshShowcase(true, PreviewDay);
    }));
#endif
