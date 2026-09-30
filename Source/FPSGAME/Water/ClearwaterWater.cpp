#include "ClearwaterWater.h"
#include "../WorldGeneration/RiverPilotFXSubsystem.h"
#include "Components/PostProcessComponent.h"
#include "Components/DirectionalLightComponent.h"
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
    static const TCHAR* SeabedMaterialPath = TEXT("/Game/Clearwater/MI_ClearwaterSeabed.MI_ClearwaterSeabed");
    static const TCHAR* UnderwaterMaterialPath =
        TEXT("/Game/Clearwater/MI_ClearwaterUnderwater.MI_ClearwaterUnderwater");

    static TAutoConsoleVariable<int32> CVarEnabled(
        TEXT("fps.Clearwater.Enabled"), 1,
        TEXT("Drive Clearwater scene-light parameters and underwater presentation."));
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
    if (ClearwaterWaterDefaults::CVarEnabled.GetValueOnGameThread() == 0)
    {
        bSubmerged = false;
        SubmergedBlend = 0.f;
        if (UnderwaterVolume) UnderwaterVolume->BlendWeight = 0.f;
        return;
    }

    const float Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.f;
    UpdateCaustics(Now);
    UpdateSubmerged(DeltaSeconds);
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

    // Registration owns this MID. A second CreateDynamicMaterialInstance would leave
    // the shared subsystem writing into a material no longer bound to the surface.
    if (auto* WaterFX = GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())
        WaterMID = WaterFX->GetWaterSurfaceMaterial(Surface);
    if (!WaterMID && Surface->GetMaterial(0))
    {
        WaterMID = Surface->CreateDynamicMaterialInstance(0);
    }

    if (!SceneSun.IsValid())
    {
        float BestIntensity = -1.f;
        for (TActorIterator<AActor> It(GetWorld()); It; ++It)
        {
            TInlineComponentArray<UDirectionalLightComponent*> Lights;
            It->GetComponents(Lights);
            for (UDirectionalLightComponent* Light : Lights)
            {
                if (Light->IsVisible() && Light->Intensity > BestIntensity)
                {
                    SceneSun = Light;
                    BestIntensity = Light->Intensity;
                }
            }
        }
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
                // Earlier maps bound the old master directly. Use the stable instance
                // so installing the new optics does not require rebuilding the level.
                if (auto* BedMaterial = LoadObject<UMaterialInterface>(nullptr, ClearwaterWaterDefaults::SeabedMaterialPath))
                    Mesh->SetMaterial(0, BedMaterial);
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
            UnderwaterMID = UMaterialInstanceDynamic::Create(Material, this);
            UnderwaterMID->SetScalarParameterValue(TEXT("UnderwaterAmount"), 1.f);
            UnderwaterVolume = NewObject<UPostProcessComponent>(this, TEXT("UnderwaterVolume"));
            UnderwaterVolume->bUnbound = true;
            UnderwaterVolume->Priority = 90.f;
            UnderwaterVolume->BlendWeight = 0.f;
            // There is no bOverride_Blendables in UE 5.8: WeightedBlendables is applied
            // unconditionally, so the weight below is what gates the effect.
            UnderwaterVolume->Settings.WeightedBlendables.Array.Empty();
            UnderwaterVolume->Settings.WeightedBlendables.Array.Add(
                FWeightedBlendable(1.f, UnderwaterMID.Get()));
            UnderwaterVolume->SetupAttachment(RootComponent);
            UnderwaterVolume->RegisterComponent();
        }
    }
    NextSunUpdate = 0.f;
    UpdateCaustics(GetWorld()->GetTimeSeconds());
}

void AClearwaterWater::UpdateCaustics(float TimeSeconds)
{
    if (TimeSeconds < NextSunUpdate) return;
    NextSunUpdate = TimeSeconds + 0.25f;
    const UDirectionalLightComponent* Sun = SceneSun.Get();
    const FVector Direction = Sun ? -Sun->GetForwardVector() : FVector::UpVector;
    // Native water reflection/scattering uses UE lighting directly. These values only
    // project the baked pattern and fade its contrast at night or under dimmed sunlight.
    const float Daylight = Sun && Sun->IsVisible()
        ? FMath::Clamp(Sun->Intensity / 10.f, 0.f, 1.f)
          * FMath::Clamp(float(Direction.Z) * 3.f, 0.f, 1.f) : 0.f;
    if (SeabedMID)
    {
        SeabedMID->SetVectorParameterValue(TEXT("SunDirection"),
            FLinearColor(Direction.X, Direction.Y, Direction.Z, 0.f));
        SeabedMID->SetScalarParameterValue(TEXT("CausticDaylight"), Daylight);
        SeabedMID->SetScalarParameterValue(TEXT("WaterLevelCm"), GetWaterHeight());
    }
    if (UnderwaterMID)
    {
        UnderwaterMID->SetScalarParameterValue(TEXT("WaterLevelCm"), GetWaterHeight());
        UnderwaterMID->SetScalarParameterValue(TEXT("WaterDaylight"), Daylight);
    }
}

void AClearwaterWater::UpdateSubmerged(float DeltaSeconds)
{
    if (!UnderwaterVolume || !Surface || !Surface->GetStaticMesh()) return;
    float Target = 0.f;
    if (const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
    {
        FVector ViewLocation;
        FRotator ViewRotation;
        PC->GetPlayerViewPoint(ViewLocation, ViewRotation);
        const FVector Local = Surface->GetComponentTransform().InverseTransformPosition(ViewLocation);
        const FBox Bounds = Surface->GetStaticMesh()->GetBoundingBox();
        const bool Inside = Local.X >= Bounds.Min.X && Local.X <= Bounds.Max.X
            && Local.Y >= Bounds.Min.Y && Local.Y <= Bounds.Max.Y;
        if (Inside) Target = FMath::Clamp((GetWaterHeight() - float(ViewLocation.Z)) / 12.f, 0.f, 1.f);
    }
    bSubmerged = Target > 0.f;
    SubmergedBlend = FMath::FInterpTo(SubmergedBlend, Target, DeltaSeconds, 12.f);
    if (Target == 0.f && SubmergedBlend < 0.001f) SubmergedBlend = 0.f;
    UnderwaterVolume->BlendWeight = SubmergedBlend;
}

void AClearwaterWater::AddImpactRipple(const FVector& WorldLocation, float Strength)
{
    if (auto* WaterFX = GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())
        WaterFX->SubmitSurfaceImpact(Surface, WorldLocation, Strength);
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

    // Existing, explicitly placed water actors above remain supported. Automatic spawning
    // is restricted to the dedicated candidate map, including PIE package prefixes.
    const FString Map = UGameplayStatics::GetCurrentLevelName(World, true);
    if (Map != TEXT("L_ClearwaterWater")) return 2;

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
