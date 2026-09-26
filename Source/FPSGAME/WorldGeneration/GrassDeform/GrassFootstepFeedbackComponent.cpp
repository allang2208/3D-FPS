#include "GrassFootstepFeedbackComponent.h"

#include "AutoFootstepEffectContext.h"
#include "GrassDeformSubsystem.h"
#include "Components/DecalComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"

DEFINE_LOG_CATEGORY_STATIC(LogGrassFootstep, Log, All);

namespace GrassFootstepAssets
{
    // Authored by Tools/GrassDeform/setup_assets_m3.py. Used only as a fallback when the component's
    // Config property is unset, so a Blueprint that forgets to set it still behaves like the
    // documented default instead of silently doing nothing.
    static const TCHAR* const DefaultConfigPath =
        TEXT("/Game/WorldGeneration/GrassDeform/DA_GrassFootstepFeedback.DA_GrassFootstepFeedback");
    static const TCHAR* const DefaultPuffPath =
        TEXT("/Game/WorldGeneration/GrassDeform/NS_GrassFootstepPuff.NS_GrassFootstepPuff");
    static const TCHAR* const DefaultDecalPath =
        TEXT("/Game/WorldGeneration/GrassDeform/M_GrassTrampleDecal.M_GrassTrampleDecal");

    /** Material scalar parameter animated by the per-decal MID: 1 = fully visible, 0 = gone.
     *  Must match M_GrassTrampleDecal, authored by setup_assets_m3.py. */
    static const FName DecalFadeParameter(TEXT("Fade"));
}

// Local shorthands so the pool code below stays readable.
using GrassFootstepAssets::DecalFadeParameter;

namespace
{
    /** Default trail length when the config asset could not be resolved. */
    constexpr float FallbackDecalLifeSeconds = 6.f;
    /** Default decal pool size when the config asset could not be resolved. */
    constexpr int32 FallbackDecalPoolSize = 12;
    /** Default live-puff ceiling when the config asset could not be resolved. */
    constexpr int32 FallbackPuffMaxActive = 64;
}

// ---------------------------------------------------------------------------------------------
// Construction / lifetime
// ---------------------------------------------------------------------------------------------

UGrassFootstepFeedbackComponent::UGrassFootstepFeedbackComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    // The component only needs a tick while something is fading; TickComponent disables itself in
    // the same frame the last decal and puff retire (see TickComponent), so an idle player costs
    // nothing beyond the delegate subscription.
    PrimaryComponentTick.bStartWithTickEnabled = false;
    PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UGrassFootstepFeedbackComponent::BeginPlay()
{
    Super::BeginPlay();

    UWorld* World = GetWorld();
    if (!World || World->GetNetMode() == NM_DedicatedServer)
    {
        // Presentation only: the deform RT and the decals have nothing to draw on a server.
        return;
    }

    // A dedicated server check is not enough on its own: this component is presentation, so it
    // only makes sense on the locally controlled pawn. A remote proxy's footsteps arrive through
    // the network, not through the local AutoFootstep notify.
    if (const ACharacter* Character = Cast<ACharacter>(GetOwner()))
    {
        if (!Character->IsLocallyControlled()) return;
    }

    ResolveAssets();
    Subscribe();
}

void UGrassFootstepFeedbackComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    Unsubscribe();
    Super::EndPlay(EndPlayReason);
}

// ---------------------------------------------------------------------------------------------
// Asset resolution
// ---------------------------------------------------------------------------------------------

bool UGrassFootstepFeedbackComponent::ResolveAssets()
{
    if (bReady) return true;

    if (!ResolvedConfig)
    {
        ResolvedConfig = Config.IsNull() ? nullptr : Config.LoadSynchronous();
        if (!ResolvedConfig)
        {
            // Fall back to the asset authored by setup_assets_m3.py so a Blueprint that forgot to
            // set the property still behaves like the documented default.
            ResolvedConfig = LoadObject<UGrassFootstepFeedbackConfig>(nullptr, GrassFootstepAssets::DefaultConfigPath);
        }
    }

    if (!PuffSystemAsset)
    {
        const TSoftObjectPtr<UNiagaraSystem> SoftPuff =
            ResolvedConfig ? ResolvedConfig->PuffSystem : TSoftObjectPtr<UNiagaraSystem>();
        PuffSystemAsset = SoftPuff.IsNull() ? nullptr : SoftPuff.LoadSynchronous();
        if (!PuffSystemAsset)
        {
            PuffSystemAsset = LoadObject<UNiagaraSystem>(nullptr, GrassFootstepAssets::DefaultPuffPath);
        }
    }

    if (!DecalMaterialAsset)
    {
        const TSoftObjectPtr<UMaterialInterface> SoftDecal =
            ResolvedConfig ? ResolvedConfig->DecalMaterial : TSoftObjectPtr<UMaterialInterface>();
        DecalMaterialAsset = SoftDecal.IsNull() ? nullptr : SoftDecal.LoadSynchronous();
        if (!DecalMaterialAsset)
        {
            DecalMaterialAsset = LoadObject<UMaterialInterface>(nullptr, GrassFootstepAssets::DefaultDecalPath);
        }
    }

    // The decal is the only part that is genuinely optional: the plan's documented fallback for a
    // deferred decal that does not project onto the DynamicMesh ground is "RT + Niagara only"
    // (plan section 10.3), so a missing decal material degrades instead of disabling the feature.
    bReady = ResolvedConfig && ResolvedConfig->Surfaces.Num() > 0;
    if (!bReady && !bMissingAssetsLogged)
    {
        bMissingAssetsLogged = true;
        UE_LOG(LogGrassFootstep, Warning,
            TEXT("Grass footstep feedback disabled: %s Run Tools/GrassDeform/run_asset_setup_m3.ps1 to create it."),
            ResolvedConfig
                ? TEXT("the config whitelist (Surfaces) is empty.")
                : TEXT("DA_GrassFootstepFeedback could not be loaded."));
    }
    return bReady;
}

bool UGrassFootstepFeedbackComponent::IsSurfaceAccepted(EPhysicalSurface Surface) const
{
    if (!ResolvedConfig) return false;
    return ResolvedConfig->Surfaces.Contains(TEnumAsByte<EPhysicalSurface>(Surface));
}

// ---------------------------------------------------------------------------------------------
// Subscription
// ---------------------------------------------------------------------------------------------

void UGrassFootstepFeedbackComponent::Subscribe()
{
    if (bSubscribed) return;

    // Bound to the static delegate by this component's name: one subscription per component, never
    // per footstep, and no dependence on which effect context instance happens to play the step.
    FootstepHandle = UAutoFootstepEffectContext::OnFootstepPlayed.AddUObject(
        this, &UGrassFootstepFeedbackComponent::HandleFootstep);
    bSubscribed = FootstepHandle.IsValid();
}

void UGrassFootstepFeedbackComponent::Unsubscribe()
{
    if (!bSubscribed) return;
    UAutoFootstepEffectContext::OnFootstepPlayed.Remove(FootstepHandle);
    FootstepHandle.Reset();
    bSubscribed = false;
}

// ---------------------------------------------------------------------------------------------
// Event path
// ---------------------------------------------------------------------------------------------

void UGrassFootstepFeedbackComponent::HandleFootstep(EPhysicalSurface Surface, const FVector& Location, const FRotator& Rotation)
{
    // Rotation is part of the plugin's contract but is deliberately unused here: on the running-game
    // path it is the character's rotation plus a fixed 90 degrees, not a surface normal, so it
    // cannot be trusted as a ground orientation. The component places everything along world up.
    (void)Rotation;

    if (!ResolveAssets() || !IsSurfaceAccepted(Surface)) return;

    UWorld* World = GetWorld();
    if (!World) return;

    // Throttle: a landing and a stride contact can arrive in the same frame.
    if (Cooldown > 0.f) return;
    Cooldown = StepCooldownSeconds;

    // Teleport / respawn guard: stretching the trail across the map would leave a visible smear.
    if (bHasLastContact && FVector::Dist(LastContact, Location) > TeleportDistanceCm)
    {
        ResetTrail();
    }
    LastContact = Location;
    bHasLastContact = true;

    // The AutoFootstep notify passes the *character's* rotation (plus a fixed 90 degrees), not the
    // floor normal, so the normal is not available from the delegate. A footstep is by definition a
    // ground contact, so the surface normal is taken as up; using the character's pitch here would
    // tilt the decal into the terrain on every uphill step.
    const FVector Normal = FVector::UpVector;

    // Travel direction of the pawn at the moment of the step: the stamp bends the grass the way the
    // player is actually moving rather than radially, which is what makes a trail read as a trail.
    FVector TravelDir = FVector::ZeroVector;
    if (const ACharacter* Character = Cast<ACharacter>(GetOwner()))
    {
        const FVector Velocity = Character->GetVelocity();
        if (Velocity.SizeSquared2D() > FMath::Square(StepDirectionMinSpeed))
        {
            TravelDir = FVector(Velocity.X, Velocity.Y, 0.0).GetSafeNormal();
        }
    }

    StampGround(Location);
    SpawnPuff(Location, Normal);
    PlaceDecal(Location, Normal, TravelDir);

    // Anything that needs fading re-enables the tick; it switches itself off again once idle.
    SetComponentTickEnabled(true);
}

void UGrassFootstepFeedbackComponent::StampGround(const FVector& Location)
{
    UWorld* World = GetWorld();
    if (!World) return;

    if (UGrassDeformSubsystem* Deform = World->GetSubsystem<UGrassDeformSubsystem>())
    {
        // One DrawMaterial on the RT. The subsystem drops the stamp itself when r.GrassDeform is
        // off or the window does not contain the point, so no extra gate is needed here.
        Deform->StampTrample(Location, StepRadiusCm, StepStrength);
    }
}

// ---------------------------------------------------------------------------------------------
// Niagara puff (bounded by an active counter)
// ---------------------------------------------------------------------------------------------

void UGrassFootstepFeedbackComponent::SpawnPuff(const FVector& Location, const FVector& Normal)
{
    if (!PuffSystemAsset) return;

    const int32 MaxActive = ResolvedConfig ? ResolvedConfig->PuffMaxActive : FallbackPuffMaxActive;
    // Skipping is the documented behaviour when the budget is full: the stamp and the decal still
    // land, so a sprint across grass never piles up an unbounded number of live systems.
    if (ActivePuffs >= MaxActive) return;

    // Reuse a free record when one exists, so the array is written once at steady state.
    int32 Index = INDEX_NONE;
    for (int32 I = 0; I < PuffRecords.Num(); ++I)
    {
        if (!PuffRecords[I].bInUse)
        {
            Index = I;
            break;
        }
    }
    if (Index == INDEX_NONE)
    {
        if (PuffRecords.Num() >= MaxPuffRecords) return;
        Index = PuffRecords.AddDefaulted();
    }

    const FVector SpawnLocation = Location + Normal * PuffHeightOffsetCm;
    const FRotator SpawnRotation = FRotationMatrix::MakeFromZ(Normal).Rotator();

    // AutoRelease hands the component back to the pool when the system finishes, so nothing here
    // has to track or destroy it; the counter below is what bounds the *concurrent* count.
    UNiagaraComponent* Component = UNiagaraFunctionLibrary::SpawnSystemAtLocation(
        this, PuffSystemAsset, SpawnLocation, SpawnRotation, FVector(PuffScale),
        /*bAutoDestroy=*/true, /*bAutoActivate=*/true, ENCPoolMethod::AutoRelease);
    if (!Component)
    {
        // Budget was not spent on a failed spawn.
        return;
    }

    FPuffRecord& Record = PuffRecords[Index];
    Record.Component = Component;
    Record.Remaining = PuffFallbackLifeSeconds;
    Record.bInUse = true;
    ++ActivePuffs;

    // The finish delegate releases the slot as soon as the system is really done; the timer in
    // TickComponent is the fallback for a system that never reports back, so a slot can never leak.
    Component->OnSystemFinished.AddUniqueDynamic(this, &UGrassFootstepFeedbackComponent::OnPuffFinished);
}

void UGrassFootstepFeedbackComponent::ReleasePuff(int32 Index)
{
    if (!PuffRecords.IsValidIndex(Index)) return;
    FPuffRecord& Record = PuffRecords[Index];
    if (!Record.bInUse) return;

    Record.bInUse = false;
    Record.Remaining = 0.f;
    Record.Component.Reset();
    ActivePuffs = FMath::Max(0, ActivePuffs - 1);
}

// ---------------------------------------------------------------------------------------------
// Decal trail (fixed pool, oldest recycled)
// ---------------------------------------------------------------------------------------------

void UGrassFootstepFeedbackComponent::EnsureDecalPool()
{
    if (DecalSlots.Num() > 0) return;
    if (!DecalMaterialAsset) return;

    UWorld* World = GetWorld();
    if (!World) return;

    const int32 PoolSize = ResolvedConfig ? FMath::Clamp(ResolvedConfig->DecalPoolSize, 0, 64) : FallbackDecalPoolSize;
    if (PoolSize <= 0) return;

    // Built once, on the first accepted footstep. This is the only allocation the feature ever
    // performs on the event path, and it happens exactly once per component.
    DecalSlots.Reserve(PoolSize);
    for (int32 I = 0; I < PoolSize; ++I)
    {
        FGrassFootstepDecalSlot& Slot = DecalSlots.AddDefaulted_GetRef();
        UDecalComponent* Decal = NewObject<UDecalComponent>(GetOwner());
        if (!Decal) continue;

        Decal->SetMobility(EComponentMobility::Movable);
        Decal->SetAbsolute(true, true, true);
        Decal->SetVisibility(false);
        // Small enough that the trail still reads at range, large enough that the decal stops
        // costing anything once it is a few metres away.
        Decal->SetFadeScreenSize(0.0015f);
        // UDecalComponent derives from USceneComponent (not UPrimitiveComponent): it has no
        // SetCastShadow / bReceivesDecals members, and projected decals never cast or receive
        // shadows or other decals anyway, so there is nothing to disable here.
        Decal->DecalSize = FVector(DecalProjectionDepthCm, DecalRadiusCm, DecalRadiusCm);
        Decal->SetCanEverAffectNavigation(false);

        // One MID per slot: the fade scalar is per-decal, so they cannot share a material instance.
        Slot.Material = UMaterialInstanceDynamic::Create(DecalMaterialAsset, this);
        if (Slot.Material)
        {
            Slot.Material->SetScalarParameterValue(DecalFadeParameter, 0.f);
            Decal->SetDecalMaterial(Slot.Material);
        }
        else
        {
            Decal->SetDecalMaterial(DecalMaterialAsset);
        }

        Decal->RegisterComponent();
        Slot.Decal = Decal;
        Slot.Age = ResolvedConfig ? ResolvedConfig->DecalLifeSeconds : FallbackDecalLifeSeconds;  // free slot
        Slot.bInUse = false;
    }

    UE_LOG(LogGrassFootstep, Log, TEXT("Grass footstep trail pool built: %d decals."), DecalSlots.Num());
}

void UGrassFootstepFeedbackComponent::PlaceDecal(const FVector& Location, const FVector& Normal, const FVector& TravelDir)
{
    EnsureDecalPool();
    if (DecalSlots.Num() == 0) return;

    const float LifeSeconds = FMath::Max(0.1f, ResolvedConfig ? ResolvedConfig->DecalLifeSeconds : FallbackDecalLifeSeconds);

    // Prefer a free slot; otherwise recycle the oldest (largest age), which is what keeps the pool
    // bounded at exactly DecalPoolSize components for the lifetime of the pawn (M3 acceptance).
    int32 Chosen = INDEX_NONE;
    float OldestAge = -1.f;
    for (int32 I = 0; I < DecalSlots.Num(); ++I)
    {
        const FGrassFootstepDecalSlot& Slot = DecalSlots[I];
        if (!Slot.Decal) continue;
        if (!Slot.bInUse)
        {
            Chosen = I;
            break;
        }
        if (Slot.Age > OldestAge)
        {
            OldestAge = Slot.Age;
            Chosen = I;
        }
    }
    if (Chosen == INDEX_NONE) return;

    FGrassFootstepDecalSlot& Slot = DecalSlots[Chosen];
    if (!Slot.Decal) return;

    // Fade 1 covers the recycled decal's old content for one frame; the value is written before the
    // decal is moved, so the previous footprint never flashes at the new location.
    if (Slot.Material)
    {
        Slot.Material->SetScalarParameterValue(DecalFadeParameter, 1.f);
    }

    Slot.Decal->SetWorldLocation(Location + Normal * DecalGroundOffsetCm);
    // UE decals project along local X, so the rotation aims local X into the ground. The yaw is
    // taken from the travel direction where there is one, which makes successive footprints line up
    // into a readable trail instead of a row of identically-oriented blobs.
    const FVector ProjectionAxis = -Normal;
    const FVector UpAxis = TravelDir.IsNearlyZero() ? FVector::ForwardVector : TravelDir;
    Slot.Decal->SetWorldRotation(FRotationMatrix::MakeFromXZ(ProjectionAxis, UpAxis).Rotator());
    Slot.Decal->SetVisibility(true);

    Slot.Age = 0.f;
    Slot.bInUse = true;
}

// ---------------------------------------------------------------------------------------------
// Tick: fade the trail and retire puffs
// ---------------------------------------------------------------------------------------------

void UGrassFootstepFeedbackComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

    if (Cooldown > 0.f) Cooldown = FMath::Max(0.f, Cooldown - DeltaTime);

    int32 LiveDecals = 0;
    const float LifeSeconds = FMath::Max(0.1f, ResolvedConfig ? ResolvedConfig->DecalLifeSeconds : FallbackDecalLifeSeconds);

    for (FGrassFootstepDecalSlot& Slot : DecalSlots)
    {
        if (!Slot.bInUse || !Slot.Decal) continue;

        Slot.Age += DeltaTime;
        if (Slot.Age >= LifeSeconds)
        {
            // Retire: hide first so the decal stops rendering and stop touching its MID.
            Slot.Decal->SetVisibility(false);
            Slot.bInUse = false;
            continue;
        }

        // Linear fade; the material multiplies its darkening by this so a footprint leaves no
        // visible edge when the slot is recycled.
        if (Slot.Material)
        {
            Slot.Material->SetScalarParameterValue(DecalFadeParameter, 1.f - Slot.Age / LifeSeconds);
        }
        ++LiveDecals;
    }

    for (int32 I = 0; I < PuffRecords.Num(); ++I)
    {
        FPuffRecord& Record = PuffRecords[I];
        if (!Record.bInUse) continue;

        // Fallback release: the finish delegate is the normal path, but a system that is killed
        // without firing it (or that never finishes) must not hold the budget forever.
        Record.Remaining -= DeltaTime;
        if (Record.Remaining <= 0.f || !Record.Component.IsValid())
        {
            ReleasePuff(I);
        }
    }

    // Idle again: nothing is fading and no puff is alive, so stop ticking entirely. The next
    // accepted footstep re-enables this from HandleFootstep.
    if (LiveDecals == 0 && ActivePuffs == 0)
    {
        SetComponentTickEnabled(false);
    }
}

void UGrassFootstepFeedbackComponent::OnPuffFinished(UNiagaraComponent* FinishedComponent)
{
    for (int32 I = 0; I < PuffRecords.Num(); ++I)
    {
        FPuffRecord& Record = PuffRecords[I];
        if (!Record.bInUse) continue;
        if (Record.Component.Get() == FinishedComponent)
        {
            ReleasePuff(I);
            return;
        }
    }
}

// ---------------------------------------------------------------------------------------------
// Trail management
// ---------------------------------------------------------------------------------------------

void UGrassFootstepFeedbackComponent::ResetTrail()
{
    for (FGrassFootstepDecalSlot& Slot : DecalSlots)
    {
        if (Slot.Decal) Slot.Decal->SetVisibility(false);
        if (Slot.Material) Slot.Material->SetScalarParameterValue(DecalFadeParameter, 0.f);
        Slot.bInUse = false;
        Slot.Age = FMath::Max(0.1f, ResolvedConfig ? ResolvedConfig->DecalLifeSeconds : FallbackDecalLifeSeconds);
    }

    for (int32 I = 0; I < PuffRecords.Num(); ++I)
    {
        FPuffRecord& Record = PuffRecords[I];
        if (!Record.bInUse) continue;
        // Deactivate rather than destroy: the components come from the Niagara pool, and dropping
        // the record is what returns the budget. The finish delegate is unbound first so the
        // Deactivate() above cannot call back into a record this loop is already retiring.
        if (UNiagaraComponent* Component = Record.Component.Get())
        {
            Component->OnSystemFinished.RemoveDynamic(this, &UGrassFootstepFeedbackComponent::OnPuffFinished);
            Component->Deactivate();
        }
        Record.bInUse = false;
        Record.Remaining = 0.f;
        Record.Component.Reset();
    }
    ActivePuffs = 0;

    bHasLastContact = false;
    LastContact = FVector::ZeroVector;
    Cooldown = 0.f;  // a respawn must not swallow the first step of the new life
}

int32 UGrassFootstepFeedbackComponent::GetActiveDecalCount() const
{
    int32 Count = 0;
    for (const FGrassFootstepDecalSlot& Slot : DecalSlots)
    {
        if (Slot.bInUse) ++Count;
    }
    return Count;
}