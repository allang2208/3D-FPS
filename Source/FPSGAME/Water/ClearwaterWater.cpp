#include "ClearwaterWater.h"
#include "../WorldGeneration/RiverPilotFXSubsystem.h"
#include "Components/PostProcessComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace ClearwaterWaterDefaults
{
    // Authored by Tools/Fluids/author_clearwater_water.py. Kept as literal paths because
    // ConstructorHelpers in the constructor needs a compile-time FObjectFinder target.
    static const TCHAR* MeshPath = TEXT("/Game/Clearwater/SM_ClearwaterPlane.SM_ClearwaterPlane");
    static const TCHAR* MaterialPath = TEXT("/Game/Clearwater/MI_ClearwaterWater.MI_ClearwaterWater");
    static const TCHAR* SeabedTag = TEXT("ClearwaterSeabed");
    static const TCHAR* UnderwaterMaterialPath =
        TEXT("/Game/Clearwater/MI_ClearwaterUnderwater.MI_ClearwaterUnderwater");

    // clearwater index.html line 130: DEPTH = 1.6 m. Used to size the caustic light shift.
    static constexpr float WaterDepthCm = 160.f;
    // Clearwater's IORS[1] (line 322), the middle channel, drives the reference shift.
    static constexpr float ReferenceIOR = 1.3335f;
    // Clearwater wraps the caustic pattern over one patch: L = 4.6 m (line 129).
    static constexpr float CausticPatchCm = 460.f;
    // Ripple slot lifetime, matching the material's RippleMaxAge parameter.
    static constexpr float RippleMaxAge = 1.8f;

    static TAutoConsoleVariable<int32> CVarEnabled(
        TEXT("fps.Clearwater.Enabled"), 1,
        TEXT("Drive the Clearwater water effects (caustic scroll, impact ripples, underwater)."));
}

AClearwaterWater::AClearwaterWater()
{
    PrimaryActorTick.bCanEverTick = true;
    // The effects are smooth and slow, so a low rate is invisible and keeps the actor off
    // the hot path; the project's performance rules ask for exactly this.
    PrimaryActorTick.TickInterval = 1.f / 30.f;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));

    Surface = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WaterSurface"));
    Surface->SetupAttachment(RootComponent);
    Surface->SetMobility(EComponentMobility::Movable);
    Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Surface->SetGenerateOverlapEvents(false);
    Surface->SetCanEverAffectNavigation(false);
    // Waves are a material world-position offset, so the component bounds never cover the
    // crests. Widening them once is cheaper than letting the surface pop out of view.
    Surface->SetBoundsScale(2.f);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(
        TEXT("/Game/Clearwater/SM_ClearwaterPlane.SM_ClearwaterPlane"));
    if (Plane.Succeeded()) Surface->SetStaticMesh(Plane.Object);
}

void AClearwaterWater::BeginPlay()
{
    Super::BeginPlay();
    Configure();

    // Automated capture hook, used by Tools/Fluids/run_clearwater_capture.ps1.
    //
    // A screenshot issued from the engine's startup command queue runs on frame 0, while
    // the map is still streaming and texture derived data is still compiling, so the PNG
    // comes back pure black and is indistinguishable from a lighting failure. Firing it
    // from a timer after the level has been up for a few seconds avoids that false negative.
    if (UWorld* World = GetWorld())
    {
        int32 Warmup = 0;
        if (FParse::Value(FCommandLine::Get(), TEXT("ClearwaterShot="), Warmup) && Warmup > 0)
        {
            FTimerHandle Handle;
            // The process is deliberately NOT quit from here. HighResShot is asynchronous,
            // so an immediate `-ExecCmds=quit` tears the engine down before the capture is
            // written and no file appears at all -- which is exactly what happened on the
            // first attempt. The calling script stops the process once the file lands.
            World->GetTimerManager().SetTimer(Handle, FTimerDelegate::CreateWeakLambda(this, [Warmup]()
            {
                if (GEngine && GEngine->GameViewport)
                {
                    // `Shot` rather than `HighResShot`: the high-res path waits on texture
                    // streaming and never completed in this headless run (the log showed the
                    // hook firing but no capture), whereas `Shot` writes the next frame
                    // synchronously to Saved/Screenshots/.
                    GEngine->GameViewport->ConsoleCommand(TEXT("Shot showui"));
                    UE_LOG(LogTemp, Display,
                        TEXT("ClearwaterWater: issued Shot after %d s warmup."), Warmup);
                }
            }), float(Warmup), false);
            UE_LOG(LogTemp, Display,
                TEXT("ClearwaterWater: scheduled a capture %d s after level start."), Warmup);
        }
    }
}

void AClearwaterWater::EndPlay(const EEndPlayReason::Type Reason)
{
    UnregisterFromWaterFX();
    Super::EndPlay(Reason);
}

void AClearwaterWater::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (ClearwaterWaterDefaults::CVarEnabled.GetValueOnGameThread() == 0) return;

    const float Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.f;
    UpdateCaustics(Now);
    UpdateRipples(DeltaSeconds);
    UpdateSubmerged();
}

void AClearwaterWater::Configure()
{
    if (!Surface) return;

    // Prefer whatever the level assigned; fall back to the authored instance so a
    // hand-placed actor works without the authoring pass having touched the level.
    if (!Surface->GetMaterial(0))
    {
        if (auto* Material = LoadObject<UMaterialInterface>(nullptr, ClearwaterWaterDefaults::MaterialPath))
        {
            Surface->SetMaterial(0, Material);
        }
    }
    RegisterWithWaterFX();

    // The FX subsystem already made a dynamic instance for slot 0; reuse it rather than
    // stacking a second one, so the ripple parameters it writes and the ones written here
    // land on the same object.
    if (!WaterMID && Surface->GetMaterial(0))
    {
        WaterMID = Surface->CreateDynamicMaterialInstance(0);
    }

    // Find the seabed by tag rather than by path: the authoring pass tags it, and a level
    // that has no seabed simply gets no caustic animation.
    if (!SeabedMID)
    {
        for (TActorIterator<AActor> It(GetWorld()); It; ++It)
        {
            if (!It->ActorHasTag(FName(ClearwaterWaterDefaults::SeabedTag))) continue;
            if (auto* Mesh = It->FindComponentByClass<UStaticMeshComponent>())
            {
                SeabedMID = Mesh->CreateDynamicMaterialInstance(0);
            }
            break;
        }
    }

    if (!UnderwaterVolume)
    {
        if (auto* Material = LoadObject<UMaterialInterface>(
                nullptr, ClearwaterWaterDefaults::UnderwaterMaterialPath))
        {
            UnderwaterMaterial = Material;
            UnderwaterVolume = NewObject<UPostProcessComponent>(this, TEXT("UnderwaterVolume"));
            UnderwaterVolume->bUnbound = true;
            UnderwaterVolume->Priority = 90.f;
            UnderwaterVolume->BlendWeight = 1.f;
            // There is no bOverride_Blendables in UE 5.8: WeightedBlendables is applied
            // unconditionally, so the weight below is what gates the effect.
            UnderwaterVolume->Settings.WeightedBlendables.Array.Empty();
            UnderwaterVolume->Settings.WeightedBlendables.Array.Add(
                FWeightedBlendable(0.f, Material));
            UnderwaterVolume->SetupAttachment(RootComponent);
            UnderwaterVolume->RegisterComponent();
        }
    }
}

void AClearwaterWater::UpdateCaustics(float TimeSeconds)
{
    if (!WaterMID && !SeabedMID) return;

    // clearwater derives the caustic registration shift from the refracted sun direction
    // (renderCaustics, lines 330-334): the flat-surface refraction offset keeps the pattern
    // registered to the sun, and the per-channel residual is the dispersion fringe.
    const float El = FMath::DegreesToRadians(SunElevationDeg);
    const float Az = FMath::DegreesToRadians(SunAzimuthDeg);
    const float SinI = FMath::Cos(El);
    const float SinT = SinI / ClearwaterWaterDefaults::ReferenceIOR;
    const float CosT = FMath::Sqrt(FMath::Max(1.f - SinT * SinT, 0.f));
    const float TanT = SinT / FMath::Max(CosT, KINDA_SMALL_NUMBER);

    // Direction along the horizontal component of the sun, in UE axes.
    const float SunX = FMath::Cos(El) * FMath::Cos(Az);
    const float SunY = FMath::Cos(El) * FMath::Sin(Az);
    const float Hor = FMath::Max(FMath::Sqrt(SunX * SunX + SunY * SunY), KINDA_SMALL_NUMBER);

    // clearwater: causShift = -sunDir * depth * tan(thetaT), in metres; here in centimetres.
    const float ShiftX = -SunX / Hor * ClearwaterWaterDefaults::WaterDepthCm * TanT;
    const float ShiftY = -SunY / Hor * ClearwaterWaterDefaults::WaterDepthCm * TanT;

    // Scroll the two layers so the web drifts with the sun, and layer B at a different rate
    // so the two never lock into a single sliding image.
    const float Patch = ClearwaterWaterDefaults::CausticPatchCm;
    const float UvA_X = (ShiftX + TimeSeconds * 1.6f) / Patch;
    const float UvA_Y = (ShiftY + TimeSeconds * 0.9f) / Patch;
    const float UvB_X = (ShiftX * 1.7f - TimeSeconds * 1.1f) / Patch;
    const float UvB_Y = (ShiftY * 1.7f + TimeSeconds * 1.4f) / Patch;

    const FLinearColor A(UvA_X, UvA_Y, 0.f, 0.f);
    const FLinearColor B(UvB_X, UvB_Y, 0.f, 0.f);
    const FLinearColor SunDir(SunX, SunY, FMath::Sin(El), 0.f);

    for (UMaterialInstanceDynamic* MID : { WaterMID.Get(), SeabedMID.Get() })
    {
        if (!MID) continue;
        MID->SetVectorParameterValue(TEXT("CausticShiftA"), A);
        MID->SetVectorParameterValue(TEXT("CausticShiftB"), B);
        MID->SetVectorParameterValue(TEXT("SunDirection"), SunDir);
    }
}

void AClearwaterWater::UpdateRipples(float DeltaSeconds)
{
    if (!WaterMID) return;

    bool bAny = false;
    for (int32 I = 0; I < 4; ++I)
    {
        if (RippleSlots[I].Z < 0.f) continue;
        RippleSlots[I].Z += DeltaSeconds;
        if (RippleSlots[I].Z > ClearwaterWaterDefaults::RippleMaxAge)
        {
            // Park the slot exactly the way URiverPilotFXSubsystem parks its own slots.
            RippleSlots[I] = FVector4(0.f, 0.f, -1.f, 0.f);
        }
        else
        {
            bAny = true;
        }
    }

    // Only touch the material while something is actually ringing; a calm surface costs
    // nothing beyond this loop.
    const bool bWasAny = RipplesActive > 0;
    RipplesActive = bAny ? 1 : 0;
    if (!bAny && !bWasAny) return;

    for (int32 I = 0; I < 4; ++I)
    {
        const FVector4& S = RippleSlots[I];
        WaterMID->SetVectorParameterValue(
            FName(*FString::Printf(TEXT("WaterHit%d"), I)),
            FLinearColor(float(S.X), float(S.Y), float(S.Z), float(S.W)));
    }
}

void AClearwaterWater::UpdateSubmerged()
{
    if (!UnderwaterVolume) return;

    bool bNowSubmerged = false;
    if (const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
    {
        FVector ViewLocation;
        FRotator ViewRotation;
        PC->GetPlayerViewPoint(ViewLocation, ViewRotation);
        bNowSubmerged = ViewLocation.Z < GetWaterHeight();
    }

    if (bNowSubmerged == bSubmerged) return;
    bSubmerged = bNowSubmerged;
    // Ramp the blendable rather than switching, so surfacing does not pop.
    UnderwaterVolume->Settings.WeightedBlendables.Array.Empty();
    if (UnderwaterMaterial)
    {
        UnderwaterVolume->Settings.WeightedBlendables.Array.Add(
            FWeightedBlendable(bSubmerged ? 1.f : 0.f, UnderwaterMaterial));
    }
}

void AClearwaterWater::AddImpactRipple(const FVector& WorldLocation, float Strength)
{
    if (!WaterMID) return;
    FVector4& Slot = RippleSlots[RippleCursor];
    RippleCursor = (RippleCursor + 1) % 4;
    Slot = FVector4(WorldLocation.X, WorldLocation.Y, 0.f, FMath::Clamp(Strength, 0.f, 1.f));
    RipplesActive = 1;
}

bool AClearwaterWater::RegisterWithWaterFX()
{
    if (bRegistered || !Surface) return bRegistered;
    UWorld* World = GetWorld();
    if (!World) return false;

    auto* WaterFX = World->GetSubsystem<URiverPilotFXSubsystem>();
    if (!WaterFX) return false;

    // Assign the material first: RegisterWaterSurface creates the dynamic instance from
    // slot 0 and quietly skips the component when there is nothing to instance.
    if (!Surface->GetMaterial(0)) return false;
    if (!Surface->GetStaticMesh()) return false;

    // The shape comes from FindComplementaryWaterFootprint for this mesh; if that ever
    // stops matching, registration is refused and water interaction silently disappears.
    WaterFX->RegisterWaterSurface(Surface);

    bRegistered = HasWaterInteraction();
    if (!bRegistered)
    {
        UE_LOG(LogTemp, Warning,
            TEXT("ClearwaterWater: surface %s has no water impact footprint, so bullets, "
                 "footsteps and bodies will not interact with it. Expected "
                 "/Game/Clearwater/SM_ClearwaterPlane to be covered by "
                 "Source/FPSGAME/WorldGeneration/ClearwaterWaterFootprint.cpp."),
            *Surface->GetStaticMesh()->GetPathName());
    }
    return bRegistered;
}

bool AClearwaterWater::HasWaterInteraction() const
{
    UWorld* World = GetWorld();
    if (!World || !Surface) return false;
    auto* WaterFX = World->GetSubsystem<URiverPilotFXSubsystem>();
    return WaterFX && WaterFX->IsWaterSurfaceRegistered(Surface);
}

void AClearwaterWater::UnregisterFromWaterFX()
{
    if (!bRegistered || !Surface) return;
    if (UWorld* World = GetWorld())
    {
        if (auto* WaterFX = World->GetSubsystem<URiverPilotFXSubsystem>())
        {
            WaterFX->UnregisterWaterSurface(Surface);
        }
    }
    bRegistered = false;
}

float AClearwaterWater::GetDepthAt(const FVector& WorldLocation) const
{
    return FMath::Max(0.f, float(GetActorLocation().Z - WorldLocation.Z));
}

int32 AClearwaterWater::Install(UWorld* World)
{
    if (!World || !World->IsGameWorld()) return 2;

    for (TActorIterator<AClearwaterWater> It(World); It; ++It)
    {
        It->Configure();
        return 1;
    }

    // Only install where the authored assets actually exist. This is what keeps the call
    // in the shared game mode from dropping a water body into every unrelated map.
    if (!LoadObject<UStaticMesh>(nullptr, ClearwaterWaterDefaults::MeshPath)) return 2;
    if (!LoadObject<UMaterialInterface>(nullptr, ClearwaterWaterDefaults::MaterialPath)) return 2;

    // The authoring pass cannot place this actor: it runs through the Python channel,
    // which only sees classes from the already-loaded modules, so the level would have to
    // be re-saved after every code change. Spawning here instead means the water follows
    // the code, and the level only owns lighting, seabed and the spawn point.
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    AClearwaterWater* Spawned = World->SpawnActor<AClearwaterWater>(
        AClearwaterWater::StaticClass(), FTransform::Identity, Params);
    if (!Spawned)
    {
        UE_LOG(LogTemp, Error, TEXT("ClearwaterWater: could not spawn the water body."));
        return 2;
    }
#if WITH_EDITOR
    Spawned->SetActorLabel(TEXT("ClearwaterWater"));
#endif
    Spawned->Configure();
    UE_LOG(LogTemp, Display,
        TEXT("ClearwaterWater: spawned water body in %s (interaction %s)."),
        *World->GetName(), Spawned->HasWaterInteraction() ? TEXT("active") : TEXT("INACTIVE"));
    return 1;
}
