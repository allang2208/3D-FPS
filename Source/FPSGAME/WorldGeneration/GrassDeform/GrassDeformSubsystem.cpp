#include "GrassDeformSubsystem.h"
#include "GrassDeformSettings.h"

#include "Engine/World.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Misc/Paths.h"
#include "Scalability.h"   // Scalability::DefaultQualityLevel, the permissive fallback when the cvar is unresolved

DEFINE_LOG_CATEGORY_STATIC(LogGrassDeform, Log, All);

namespace GrassDeformAssets
{
    // Content authored by Tools/GrassDeform/setup_assets_m1.py. Soft paths only: a world that is
    // loaded before the assets exist simply runs with the system disabled (one warning).
    // The deform parameters ride the pack's wind collection, NOT a dedicated MPC: a material may
    // reference at most 2 collections, and the grass masters' active graphs already use both
    // (PN_WindParameters + PN_BendingParameters), so a third collection fails the whole material
    // to compile ("Material references too many MaterialParameterCollections"). The grass samples
    // the wind collection every frame anyway, so riding it costs no extra uniform buffer. The
    // parameter names (Center / WindowSize / WorldTime / ... / ReadIsB) do not collide with the
    // pack's own WindDirection / WindStrength.
    static const TCHAR* const CollectionPath = TEXT("/Game/PN_GrassLibrary/Materials/PN_WindParameters.PN_WindParameters");
    static const TCHAR* const StampPath = TEXT("/Game/WorldGeneration/GrassDeform/M_GrassDeformStamp.M_GrassDeformStamp");
    static const TCHAR* const StampTimePath = TEXT("/Game/WorldGeneration/GrassDeform/M_GrassDeformStampTime.M_GrassDeformStampTime");
    static const TCHAR* const RecenterTimePath = TEXT("/Game/WorldGeneration/GrassDeform/M_GrassDeformRecenterTime.M_GrassDeformRecenterTime");
    static const TCHAR* const TimeAPath = TEXT("/Game/WorldGeneration/GrassDeform/RT_GrassContactTimeA.RT_GrassContactTimeA");
    static const TCHAR* const TimeBPath = TEXT("/Game/WorldGeneration/GrassDeform/RT_GrassContactTimeB.RT_GrassContactTimeB");
    static const TCHAR* const FadePath = TEXT("/Game/WorldGeneration/GrassDeform/M_GrassDeformFade.M_GrassDeformFade");
    static const TCHAR* const RecenterPath = TEXT("/Game/WorldGeneration/GrassDeform/M_GrassDeformRecenter.M_GrassDeformRecenter");

    /** Persistent RT asset pair (authored by setup_assets_m1.py). The grass shader reaches the
      * deform mask through TextureObjectParameter DEFAULTS on MF_GrassDeform pointing at these two
      * assets, because a MaterialParameterCollection cannot carry textures and a subsystem-owned
      * MID of MA_Grass is never what the foliage actually renders with. Drawing into a loaded RT
      * asset is transient by nature: the pixels are never serialized. */
    static const TCHAR* const RTAPath = TEXT("/Game/WorldGeneration/GrassDeform/RT_GrassDeformA.RT_GrassDeformA");
    static const TCHAR* const RTBPath = TEXT("/Game/WorldGeneration/GrassDeform/RT_GrassDeformB.RT_GrassDeformB");
}

namespace GrassDeformParams
{
    // Material parameters on the three pass materials. Names must match setup_assets_m1.py, which
    // authors those graphs; keep the two files in sync when either side changes.
    static const FName CenterUV(TEXT("CenterUV"));
    static const FName StartUV(TEXT("StartUV"));
    static const FName IsSweep(TEXT("IsSweep"));
    static const FName RadiusUV(TEXT("RadiusUV"));
    static const FName Strength(TEXT("Strength"));

    // Fade pass.
    static const FName FadeRate(TEXT("FadeRate"));

    // Recenter pass.
    static const FName ShiftUV(TEXT("ShiftUV"));

    // Deform parameters published on the pack wind collection (see GrassDeformAssets::CollectionPath).
    static const FName MpcCenter(TEXT("Center"));
    static const FName MpcWindowSize(TEXT("WindowSize"));
    static const FName MpcWorldTime(TEXT("WorldTime"));
    static const FName MpcRegrowthSeconds(TEXT("RegrowthSeconds"));
    static const FName MpcEnabled(TEXT("bEnabled"));
    // Wavefront speed is consumed by MF_GrassDeform at render time, so it lives in the collection
    // rather than on the stamp material.
    static const FName MpcWaveSpeed(TEXT("WaveSpeed"));
    // Origin (window UV) of the most recent impulse. MF_GrassDeform measures the expanding ring
    // from this point, so the wave sweeps out from the impact, not from the window centre.
    static const FName MpcWaveOrigin(TEXT("WaveOrigin"));
    static const FName MpcWaveStartTime(TEXT("GrassWaveStartTime"));
    static const FName MpcWaveRadius(TEXT("GrassWaveRadius"));
    static const FName MpcWaveStrength(TEXT("GrassWaveStrength"));
    // Selects which RT asset is the current read side inside MF_GrassDeform: both assets are wired
    // as texture-parameter defaults, and this scalar (0 = A, 1 = B) picks between them with a
    // uniform branch. Published on every ping-pong flip.
    static const FName MpcReadIsB(TEXT("ReadIsB"));

    // Source texture of the three pass materials: the read side of the ping-pong pair. All three
    // passes read the previous contents through this one parameter name, so the pass contract is
    // uniform and every pass material samples exactly the texture it does not write.
    static const FName PassSource(TEXT("Old"));
}

namespace
{
    // ---------------------------------------------------------------------------------------
    // Console variables. These are the only tunables that survive into a packaged build.
    // ---------------------------------------------------------------------------------------

    TAutoConsoleVariable<int32> CVarGrassDeformEnabled(
        TEXT("r.GrassDeform"), 1,
        TEXT("GPU grass interaction (trample/flatten/wavefront). 0 disables all passes and the shader sampling.\n")
        TEXT("The subsystem is only enabled while this is non-zero AND sg.FoliageQuality > 0 AND the\n")
        TEXT("pass materials / collection are present; see GrassDeform.Status.\n")
        TEXT("0: off, 1: on (default)."),
        ECVF_Scalability);

    /** Scalability group the deform follows, looked up read-only. "sg.FoliageQuality" belongs to the
     *  engine (Engine/Private/Scalability.cpp registers it with ECVF_ScalabilityGroup) and must NOT
     *  be re-registered here: FConsoleManager::AddConsoleObject warns ("already exists but is being
     *  registered again") and overwrites the flags and help text of the surviving object, so a
     *  second project-side TAutoConsoleVariable for this name would log a boot warning and make the
     *  owner depend on static-init order. FindConsoleVariable only reads the engine's variable. */
    const TCHAR* const FoliageQualityCVarName = TEXT("sg.FoliageQuality");

    /** Cached pointer to sg.FoliageQuality. The console manager owns the object for as long as it is
     *  registered, so this is a plain pointer read after the first lookup - no allocation per tick.
     *  The cache is deliberately never invalidated: sg.FoliageQuality is a static-lifetime engine
     *  cvar that is registered once and never unregistered, so the pointer cannot go stale. */
    IConsoleVariable* CachedFoliageQualityCVar = nullptr;
    bool bFoliageQualityLookupAttempted = false;

    /** Read sg.FoliageQuality. Returns the permissive Epic default while the variable is not
     *  resolvable yet (console manager not up), which keeps the deform cvar-driven, not Low. */
    int32 ReadFoliageQualityLevel()
    {
        if (!CachedFoliageQualityCVar && !bFoliageQualityLookupAttempted)
        {
            // The lookup is a name-map find, retried until it resolves. sg.* is normally registered
            // long before the first world ticks, so this happens at most a couple of times per world.
            CachedFoliageQualityCVar = IConsoleManager::Get().FindConsoleVariable(FoliageQualityCVarName);
            bFoliageQualityLookupAttempted = CachedFoliageQualityCVar != nullptr;
        }
        return CachedFoliageQualityCVar ? CachedFoliageQualityCVar->GetInt() : Scalability::DefaultQualityLevel;
    }

    TAutoConsoleVariable<float> CVarGrassDeformFadeHz(
        TEXT("r.GrassDeform.FadeHz"), 6.f,
        TEXT("Retired in v12: regrowth is evaluated continuously from contact timestamps. No fade pass."),
        ECVF_Scalability);

    TAutoConsoleVariable<int32> CVarGrassDeformRTSize(
        TEXT("r.GrassDeform.RTSize"), GrassDeformTuning::DefaultRTSize,
        TEXT("Edge size of the grass deform render targets. Recreating the pair costs a few ms.\n")
        TEXT("512, 1024 (default) or 2048."),
        ECVF_Scalability | ECVF_RenderThreadSafe);

    /** Round an arbitrary requested size to the nearest supported entry. */
    int32 ClampRTSize(int32 Requested)
    {
        if (Requested <= GrassDeformTuning::MinRTSize) return GrassDeformTuning::MinRTSize;
        if (Requested >= GrassDeformTuning::MaxRTSize) return GrassDeformTuning::MaxRTSize;
        // 512 / 1024 / 2048 ladder: snap to the closest power of two in range.
        int32 Size = GrassDeformTuning::MinRTSize;
        while (Size * 2 <= Requested && Size < GrassDeformTuning::MaxRTSize) Size *= 2;
        return Size;
    }

    float ClampFadeHz(float Requested)
    {
        return FMath::Clamp(Requested, GrassDeformTuning::MinFadeHz, GrassDeformTuning::MaxFadeHz);
    }
}

// ---------------------------------------------------------------------------------------------
// Console commands (plan section 3.1). All of them are development/debug entry points; the
// subsystem itself is Blueprint-driven so a packaged build only needs the cvars.
// ---------------------------------------------------------------------------------------------

class FGrassDeformConsoleCommands
{
public:
    static UGrassDeformSubsystem* Resolve(const TArray<FString>& Args, UWorld*& OutWorld)
    {
        OutWorld = nullptr;
        if (!GEngine) return nullptr;
        for (const FWorldContext& Context : GEngine->GetWorldContexts())
        {
            UWorld* World = Context.World();
            if (!World) continue;
            if (World->WorldType != EWorldType::Game && World->WorldType != EWorldType::PIE) continue;
            if (UGrassDeformSubsystem* Subsystem = World->GetSubsystem<UGrassDeformSubsystem>())
            {
                OutWorld = World;
                return Subsystem;
            }
        }
        return nullptr;
    }

    static bool ParseVectorAndRadius(const TArray<FString>& Args, FVector& OutPosition, float& OutRadius, float& OutStrength, float DefaultStrength)
    {
        if (Args.Num() < 4) return false;
        OutPosition.X = FCString::Atof(*Args[0]);
        OutPosition.Y = FCString::Atof(*Args[1]);
        OutPosition.Z = FCString::Atof(*Args[2]);
        OutRadius = FCString::Atof(*Args[3]);
        OutStrength = Args.Num() >= 5 ? FCString::Atof(*Args[4]) : DefaultStrength;
        return true;
    }

    static void Stamp(const TArray<FString>& Args)
    {
        UWorld* World = nullptr;
        UGrassDeformSubsystem* Subsystem = Resolve(Args, World);
        if (!Subsystem)
        {
            UE_LOG(LogGrassDeform, Warning, TEXT("GrassDeform.Stamp: no game world with a grass deform subsystem."));
            return;
        }
        FVector Position;
        float Radius = 0.f;
        float Strength = 0.f;
        if (!ParseVectorAndRadius(Args, Position, Radius, Strength, GrassDeformTuning::TrampleMaxStrength))
        {
            UE_LOG(LogGrassDeform, Warning, TEXT("Usage: GrassDeform.Stamp X Y Z Radius [Strength]"));
            return;
        }
        Subsystem->StampTrample(Position, Radius, Strength);
        UE_LOG(LogGrassDeform, Display, TEXT("GrassDeform.Stamp x=%.1f y=%.1f z=%.1f r=%.1f s=%.2f"),
            Position.X, Position.Y, Position.Z, Radius, Strength);
    }

    static void Impulse(const TArray<FString>& Args)
    {
        UWorld* World = nullptr;
        UGrassDeformSubsystem* Subsystem = Resolve(Args, World);
        if (!Subsystem)
        {
            UE_LOG(LogGrassDeform, Warning, TEXT("GrassDeform.Impulse: no game world with a grass deform subsystem."));
            return;
        }
        FVector Position;
        float Radius = 0.f;
        float Strength = 0.f;
        if (!ParseVectorAndRadius(Args, Position, Radius, Strength, GrassDeformTuning::MaxStampStrength))
        {
            UE_LOG(LogGrassDeform, Warning, TEXT("Usage: GrassDeform.Impulse X Y Z Radius [Strength] [WaveSpeed]"));
            return;
        }
        const float WaveSpeed = Args.Num() >= 6 ? FCString::Atof(*Args[5]) : GrassDeformTuning::DefaultWaveSpeed;
        Subsystem->AddImpulse(Position, Radius, Strength, WaveSpeed);
        UE_LOG(LogGrassDeform, Display, TEXT("GrassDeform.Impulse x=%.1f y=%.1f z=%.1f r=%.1f s=%.2f wave=%.0f"),
            Position.X, Position.Y, Position.Z, Radius, Strength, WaveSpeed);
    }

    static void DumpRT(const TArray<FString>& Args)
    {
#if UE_BUILD_SHIPPING
        UE_LOG(LogGrassDeform, Warning, TEXT("GrassDeform.DumpRT is not available in shipping builds."));
#else
        UWorld* World = nullptr;
        UGrassDeformSubsystem* Subsystem = Resolve(Args, World);
        if (!Subsystem || !World)
        {
            UE_LOG(LogGrassDeform, Warning, TEXT("GrassDeform.DumpRT: no game world with a grass deform subsystem."));
            return;
        }
        // ExportRenderTarget is a blocking readback; it exists only to eyeball the RT by hand.
        const FString Directory = FPaths::ProjectSavedDir() / GrassDeformTuning::DumpDirectory;
        const FString FileName = FString::Printf(TEXT("%s_%s.png"), GrassDeformTuning::DumpFilePrefix,
            *FDateTime::Now().ToString(TEXT("%Y%m%d-%H%M%S")));
        UKismetRenderingLibrary::ExportRenderTarget(World, Subsystem->RenderTargets[Subsystem->ReadIndex], Directory, FileName);
        UE_LOG(LogGrassDeform, Display, TEXT("GrassDeform.DumpRT wrote %s"), *(Directory / FileName));
#endif
    }

    static void Status(const TArray<FString>& Args)
    {
        UWorld* World = nullptr;
        UGrassDeformSubsystem* Subsystem = Resolve(Args, World);
        if (!Subsystem)
        {
            UE_LOG(LogGrassDeform, Warning, TEXT("GrassDeform.Status: no game world with a grass deform subsystem."));
            return;
        }
        UE_LOG(LogGrassDeform, Display,
            TEXT("GrassDeform enabled=%d assets=%d rt=%d center=(%.1f,%.1f) flattenAlive=%d dirty=%d ")
            TEXT("cvar=%d foliageQuality=%d (0 forces off) user=%d"),
            Subsystem->IsEnabled() ? 1 : 0, Subsystem->bAssetsReady ? 1 : 0, Subsystem->ActiveRTSize,
            Subsystem->WindowCenter.X, Subsystem->WindowCenter.Y, Subsystem->FadeSecondsRemaining > 0.f ? 1 : 0, Subsystem->bDirty ? 1 : 0,
            Subsystem->LastCvarEnabled, Subsystem->GetFoliageQualityLevel(), Subsystem->bUserEnabled ? 1 : 0);
    }

    static FAutoConsoleCommand StampCommand;
    static FAutoConsoleCommand ImpulseCommand;
    static FAutoConsoleCommand DumpRTCommand;
    static FAutoConsoleCommand StatusCommand;
};

FAutoConsoleCommand FGrassDeformConsoleCommands::StampCommand(
    TEXT("GrassDeform.Stamp"),
    TEXT("StampTrample at a world location. Usage: GrassDeform.Stamp X Y Z Radius [Strength]"),
    FConsoleCommandWithArgsDelegate::CreateStatic(&FGrassDeformConsoleCommands::Stamp));

FAutoConsoleCommand FGrassDeformConsoleCommands::ImpulseCommand(
    TEXT("GrassDeform.Impulse"),
    TEXT("AddImpulse at a world location. Usage: GrassDeform.Impulse X Y Z Radius [Strength] [WaveSpeed]"),
    FConsoleCommandWithArgsDelegate::CreateStatic(&FGrassDeformConsoleCommands::Impulse));

FAutoConsoleCommand FGrassDeformConsoleCommands::DumpRTCommand(
    TEXT("GrassDeform.DumpRT"),
    TEXT("Export the current grass deform render target to Saved/GrassDeform (development builds only)."),
    FConsoleCommandWithArgsDelegate::CreateStatic(&FGrassDeformConsoleCommands::DumpRT));

FAutoConsoleCommand FGrassDeformConsoleCommands::StatusCommand(
    TEXT("GrassDeform.Status"),
    TEXT("Print the grass deform subsystem state. enabled=1 requires r.GrassDeform, sg.FoliageQuality>0 and the assets."),
    FConsoleCommandWithArgsDelegate::CreateStatic(&FGrassDeformConsoleCommands::Status));

// ---------------------------------------------------------------------------------------------
// Subsystem lifetime
// ---------------------------------------------------------------------------------------------

bool UGrassDeformSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{
    // The RT assets are shared. An idle editor world must not clear the game world's masks.
    // Dedicated servers are also excluded in Initialize.
    return Type == EWorldType::Game || Type == EWorldType::PIE;
}

void UGrassDeformSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    UWorld* World = GetWorld();
    if (!World || World->GetNetMode() == NM_DedicatedServer)
    {
        // The RT and the MPC are presentation only; a dedicated server has nothing to drive.
        bTickEnabled = false;
        // Still latch the real quality level: GrassDeform.Status can be run in this world too, and
        // a sentinel would read as "forced off" instead of "not applicable here".
        RefreshFoliageQualityLevel();
        return;
    }

    LastCvarEnabled = CVarGrassDeformEnabled.GetValueOnGameThread();
    bUserEnabled = true;

    // Scalability gate: latch sg.FoliageQuality here and follow it through a console variable sink
    // registered on the first tick. Level 0 (Low) means "no foliage", so the deform is forced off
    // exactly like r.GrassDeform 0; level 1 and above leave the cvar in charge. The sink is not
    // registered from Initialize because that runs while some world bootstraps are still building
    // the console manager.
    RefreshFoliageQualityLevel();

    // Preallocate the queue once so no stamp event ever grows the array. Reset() keeps the
    // capacity, so the per-event path below is allocation-free for the lifetime of the world
    // (plan section 7: zero per-frame allocation on the tick path).
    Pending.Reserve(MaxPendingStamps);

    Response = GetDefault<UGrassDeformSettings>();
    ResolveAssets();

    // Poll the cvars from Tick instead of registering change delegates: the render target pair is
    // owned by this subsystem, and rebuilding it from a cvar callback would run outside the
    // world's own update. The values are read once per tick, which is a plain atomic load.
    bTickEnabled = true;
}

void UGrassDeformSubsystem::Deinitialize()
{
    // Unregister before anything else is torn down: the sink captures this subsystem, and a stale
    // registration would fire on a half-destroyed object on the next scalability change.
    if (bScalabilitySinkRegistered)
    {
        IConsoleManager::Get().UnregisterConsoleVariableSink_Handle(ScalabilitySinkHandle);
        bScalabilitySinkRegistered = false;
    }

    DiscardInteractionState();
    bTickEnabled = false;
    PublishParameters();
    ReleaseRenderTargets();
    bAssetsReady = false;
    bTickEnabled = false;
    Pending.Reset();
    Super::Deinitialize();
}

// ---------------------------------------------------------------------------------------------
// Scalability gating (M4)
//
// enabled = r.GrassDeform && sg.FoliageQuality > 0 && assets resolved. The three gates are
// deliberately independent: the sink never writes r.GrassDeform (the project's scalability ini
// owns that cvar), it only latches the foliage level and drops the interaction state, so the two
// switches cannot interfere with each other.
// ---------------------------------------------------------------------------------------------

void UGrassDeformSubsystem::RefreshFoliageQualityLevel()
{
    // Read-only lookup of the engine's sg.FoliageQuality (see ReadFoliageQualityLevel): the project
    // never registers this cvar itself, it only follows it. No allocation on either path.
    FoliageQualityLevel = ReadFoliageQualityLevel();
}

void UGrassDeformSubsystem::HandleScalabilityChanged()
{
    // Called from the engine's console variable sinks, on the game thread, after a batch of cvar
    // changes (any cvar change flushes them, so this early-outs on the level comparison below).
    // A transition to Low clears the interaction state once. No per-frame rendering work.
    const int32 PreviousLevel = FoliageQualityLevel;
    RefreshFoliageQualityLevel();
    if (PreviousLevel == FoliageQualityLevel) return;

    // NOTE: no IsEnabled() precondition here. IsEnabled() already includes the foliage gate, so at
    // the moment of the transition to Low it is *already* false - testing it would mean the state
    // release never happens, leaving a stale queue and regrowth timer that a later return to
    // level >= 2 could blend back in. Discarding on an inert system is harmless and idempotent.
    if (FoliageQualityLevel <= GrassDeformTuning::DisabledFoliageQualityLevel)
    {
        DiscardInteractionState();
    }

    UE_LOG(LogGrassDeform, Log, TEXT("Grass deform follows sg.FoliageQuality=%d: %s"),
        FoliageQualityLevel,
        FoliageQualityLevel > GrassDeformTuning::DisabledFoliageQualityLevel
            ? TEXT("allowed (r.GrassDeform decides)") : TEXT("forced off at Low"));
}

void UGrassDeformSubsystem::RegisterScalabilitySink()
{
    if (bScalabilitySinkRegistered) return;

    ScalabilitySinkHandle = IConsoleManager::Get().RegisterConsoleVariableSink_Handle(
        FConsoleCommandDelegate::CreateUObject(this, &UGrassDeformSubsystem::HandleScalabilityChanged));
    bScalabilitySinkRegistered = true;
}

void UGrassDeformSubsystem::DiscardInteractionState()
{
    // The same release r.GrassDeform 0 and SetEnabled(false) perform: nothing queued, nothing left
    // to fade, so the next IsEnabled() check publishes bEnabled=0 and the passes stop for good.
    Pending.Reset();
    FadeSecondsRemaining = 0.f;
    FadeCooldown = 0.f;
    FadeElapsed = 0.f;
    bDirty = false;
    Trample.bHasProjection = false;
    bBodyGrounded = false;
    BodyContactAge = 0.f;
    BodyContact = FLinearColor::Black;
    if (UWorld* World = GetWorld())
    {
        for (UTextureRenderTarget2D* Target : RenderTargets)
        {
            if (Target) UKismetRenderingLibrary::ClearRenderTarget2D(World, Target, FLinearColor(0.f, 0.5f, 0.5f, 0.f));
        }
        for (UTextureRenderTarget2D* Target : ContactTimeTargets)
        {
            if (Target) UKismetRenderingLibrary::ClearRenderTarget2D(World, Target, FLinearColor::Black);
        }
        if (CollectionAsset)
        {
            World->GetParameterCollectionInstance(CollectionAsset)->SetScalarParameterValue(GrassDeformParams::MpcWaveStrength, 0.f);
        }
    }
}

TStatId UGrassDeformSubsystem::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(UGrassDeformSubsystem, STATGROUP_Tickables);
}

void UGrassDeformSubsystem::ResolveAssets()
{
    if (bAssetsReady) return;

    // LoadObject on soft paths at Initialize: these are four small assets resolved once per world,
    // not a hot path refresh. Everything after this point is allocation-free per frame.
    StampMaterialAsset = LoadObject<UMaterialInterface>(nullptr, GrassDeformAssets::StampPath);
    StampTimeMaterialAsset = LoadObject<UMaterialInterface>(nullptr, GrassDeformAssets::StampTimePath);
    RecenterTimeMaterialAsset = LoadObject<UMaterialInterface>(nullptr, GrassDeformAssets::RecenterTimePath);
    ContactTimeTargets[0] = LoadObject<UTextureRenderTarget2D>(nullptr, GrassDeformAssets::TimeAPath);
    ContactTimeTargets[1] = LoadObject<UTextureRenderTarget2D>(nullptr, GrassDeformAssets::TimeBPath);
    RecenterMaterialAsset = LoadObject<UMaterialInterface>(nullptr, GrassDeformAssets::RecenterPath);
    CollectionAsset = LoadObject<UMaterialParameterCollection>(nullptr, GrassDeformAssets::CollectionPath);
    RenderTargetAssets[0] = LoadObject<UTextureRenderTarget2D>(nullptr, GrassDeformAssets::RTAPath);
    RenderTargetAssets[1] = LoadObject<UTextureRenderTarget2D>(nullptr, GrassDeformAssets::RTBPath);

    const bool bComplete = StampMaterialAsset && StampTimeMaterialAsset && RecenterMaterialAsset
        && RecenterTimeMaterialAsset && ContactTimeTargets[0] && ContactTimeTargets[1]
        && CollectionAsset && RenderTargetAssets[0] && RenderTargetAssets[1];
    if (!bComplete)
    {
        if (!bMissingAssetsLogged)
        {
            bMissingAssetsLogged = true;
            UE_LOG(LogGrassDeform, Warning,
                TEXT("Grass deform v12 assets incomplete: author the mask/time pairs and Stamp/StampTime/Recenter/RecenterTime materials with Tools/GrassDeform/run_asset_setup_m1.ps1."));
        }
        // Drop the partial set so a later reload cannot use half of it.
        StampMaterialAsset = nullptr;
        FadeMaterialAsset = nullptr;
        RecenterMaterialAsset = nullptr;
        CollectionAsset = nullptr;
        RenderTargetAssets[0] = nullptr;
        RenderTargetAssets[1] = nullptr;
        bAssetsReady = false;
        return;
    }

    StampMaterial = UMaterialInstanceDynamic::Create(StampMaterialAsset, this);
    StampTimeMaterial = UMaterialInstanceDynamic::Create(StampTimeMaterialAsset, this);
    RecenterTimeMaterial = UMaterialInstanceDynamic::Create(RecenterTimeMaterialAsset, this);
    RecenterMaterial = UMaterialInstanceDynamic::Create(RecenterMaterialAsset, this);
    bAssetsReady = StampMaterial && StampTimeMaterial && RecenterMaterial && RecenterTimeMaterial;

    if (!bAssetsReady)
    {
        if (!bMissingAssetsLogged)
        {
            bMissingAssetsLogged = true;
            UE_LOG(LogGrassDeform, Warning, TEXT("Grass deform disabled: could not create the dynamic material instances."));
        }
        return;
    }

    RecreateRenderTargets();
}

void UGrassDeformSubsystem::RecreateRenderTargets()
{
    // Binds the persistent RT asset pair and resets the window state. The targets are NOT created
    // at runtime any more: the grass shader reaches the mask through TextureObjectParameter
    // defaults on MF_GrassDeform, and those must point at on-disk assets (a MaterialParameter
    // Collection cannot carry textures, and a subsystem-owned MID of MA_Grass is never what the
    // foliage renders with). The pixels stay transient - drawing into a loaded RT asset never
    // marks its package dirty.
    if (!bAssetsReady || !RenderTargetAssets[0] || !RenderTargetAssets[1]) return;

    RenderTargets[0] = RenderTargetAssets[0];
    RenderTargets[1] = RenderTargetAssets[1];

    // r.GrassDeform.RTSize is retired: the size is defined by the assets. Warn once when a stale
    // value is still set in someone's ini.
    const int32 CvarSize = ClampRTSize(CVarGrassDeformRTSize.GetValueOnGameThread());
    if (CvarSize != RenderTargetAssets[0]->SizeX && !bRTSizeWarningLogged)
    {
        bRTSizeWarningLogged = true;
        UE_LOG(LogGrassDeform, Warning,
            TEXT("r.GrassDeform.RTSize is retired; the deform RT size is defined by the RT_GrassDeformA/B assets (%dx%d)."),
            RenderTargetAssets[0]->SizeX, RenderTargetAssets[0]->SizeY);
    }

    ActiveRTSize = RenderTargetAssets[0]->SizeX;
    ReadIndex = 0;
    bWindowInitialized = false;
    bDirty = false;
    FadeSecondsRemaining = 0.f;
    FadeElapsed = 0.f;
    FadeCooldown = 0.f;
    bReadSideDirty = true;
    bResponsePublished = false;
    Pending.Reset();

    // Start from a clean mask on every (re)bind: the assets persist across a SetEnabled toggle or
    // a world reload, and a stale flatten mask must never blend back in.
    if (UWorld* World = GetWorld())
    {
        UKismetRenderingLibrary::ClearRenderTarget2D(World, RenderTargets[0], FLinearColor(0.f, 0.5f, 0.5f, 0.f));
        UKismetRenderingLibrary::ClearRenderTarget2D(World, RenderTargets[1], FLinearColor(0.f, 0.5f, 0.5f, 0.f));
        for (UTextureRenderTarget2D* Target : ContactTimeTargets)
            UKismetRenderingLibrary::ClearRenderTarget2D(World, Target, FLinearColor::Black);
    }

    UE_LOG(LogGrassDeform, Display, TEXT("Grass deform render targets bound to the RT assets (%dx%d, %.0f m window)."),
        ActiveRTSize, ActiveRTSize, GrassDeformTuning::WindowSizeCm / 100.f);
}

void UGrassDeformSubsystem::ReleaseRenderTargets()
{
    // Unbinds the ping-pong pointers only. The RT assets stay loaded (materials reference them),
    // and the pass MIDs survive: they hang off the pass material assets, not off the RT pair, and
    // nothing outside ResolveAssets recreates them - nulling them here used to kill the system
    // permanently after one SetEnabled(false)/SetEnabled(true) round trip.
    for (int32 Index = 0; Index < 2; ++Index)
    {
        RenderTargets[Index] = nullptr;
        ContactTimeTargets[Index] = nullptr;
    }
    ActiveRTSize = 0;
}

// ---------------------------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------------------------

bool UGrassDeformSubsystem::IsEnabled() const
{
    // The single place the enable contract lives: r.GrassDeform && sg.FoliageQuality > 0 && assets
    // resolved. Every pass goes through here (EnqueueStamp, Tick), so a Low quality level stops the
    // system with the same effect as r.GrassDeform 0.
    return bTickEnabled
        && bUserEnabled
        && LastCvarEnabled != 0
        && IsFoliageQualityAllowed()
        && bAssetsReady
        && RenderTargets[0] && RenderTargets[1] && ContactTimeTargets[0] && ContactTimeTargets[1];
}

void UGrassDeformSubsystem::SetEnabled(bool bInEnabled)
{
    bUserEnabled = bInEnabled;
    if (!bInEnabled)
    {
        // Release the interaction state rather than leaving a stale flatten mask on screen.
        DiscardInteractionState();
    }
    PublishParameters();
}

void UGrassDeformSubsystem::StampTrample(FVector WorldPos, float Radius, float Strength)
{
    EnqueueStamp(WorldPos, Radius, Strength, 0.f, false);
}

void UGrassDeformSubsystem::StampDirectionalTrample(FVector WorldPos, float Radius, float Strength, FVector TravelDirection)
{
    if (EnqueueStamp(WorldPos, Radius, Strength, 0.f, false))
    {
        FPendingStamp& Stamp = Pending.Last();
        const FVector2D Direction(TravelDirection.X, TravelDirection.Y);
        Stamp.Direction = Direction.IsNearlyZero() ? BodyDirection : Direction.GetSafeNormal();
        Stamp.DirectionBias = FMath::Clamp(Response->ForwardBias, 0.51f, 1.f);
        Stamp.CoreFraction = FMath::Clamp(Response->FootstepCoreFraction, 0.f, 0.95f);
    }
}

void UGrassDeformSubsystem::AddImpulse(FVector WorldPos, float Radius, float Strength, float WaveSpeed)
{
    EnqueueStamp(WorldPos, Radius, Strength, WaveSpeed, true);
}

bool UGrassDeformSubsystem::EnqueueStamp(const FVector& WorldPos, float Radius, float Strength, float WaveSpeed, bool bImpulse)
{
    if (!IsEnabled()) return false;

    const UWorld* World = GetWorld();
    if (!World) return false;

    // Late resolve: the assets may have been authored after the world started.
    if (!bWindowInitialized) RecenterWindow(WorldPos);

    // Bounds rejection is deferred until DrainPendingStamps, after this tick's recenter.
    if (Pending.Num() >= MaxPendingStamps) return false;

    FPendingStamp& Stamp = Pending.AddDefaulted_GetRef();
    Stamp.CenterXY = FVector2D(WorldPos.X, WorldPos.Y);
    Stamp.StartXY = Stamp.CenterXY;
    Stamp.Radius = FMath::Clamp(Radius, GrassDeformTuning::MinStampRadiusCm, GrassDeformTuning::MaxStampRadiusCm);
    Stamp.Strength = FMath::Clamp(Strength, 0.f, GrassDeformTuning::MaxStampStrength);
    Stamp.WaveSpeed = bImpulse ? FMath::Max(WaveSpeed, 0.f) : 0.f;
    Stamp.Timestamp = bImpulse ? float(World->GetTimeSeconds()) : GrassDeformTuning::NoImpulseTimestamp;
    Stamp.bImpulse = bImpulse;
    Stamp.CoreFraction = bImpulse ? 0.f : FMath::Clamp(Response->FootstepCoreFraction, 0.f, 0.95f);

    return true;
}

void UGrassDeformSubsystem::MarkDirty()
{
    bDirty = true;
}

// ---------------------------------------------------------------------------------------------
// Tick
// ---------------------------------------------------------------------------------------------

void UGrassDeformSubsystem::Tick(float DeltaTime)
{
    UWorld* World = GetWorld();
    if (!World) return;

#if !UE_BUILD_SHIPPING
    // The audit runs before every early-out below on purpose: it must be able to report WHY the
    // system is inert (assets missing, cvar off, quality gate) instead of silently never ticking.
    RunGrassDeformAudit(DeltaTime);
    RunGrassFunctionalAudit(DeltaTime);
    RunGrassResponseAudit(DeltaTime);
#endif

    // One-time sink registration, so a quality change is handled while the engine flushes its
    // console variable sinks instead of one tick later. Idempotent and allocation-free.
    RegisterScalabilitySink();

    // --- cvar handling (one atomic read per tick each) --------------------------------------
    const int32 CvarEnabled = CVarGrassDeformEnabled.GetValueOnGameThread();
    if (CvarEnabled != LastCvarEnabled)
    {
        LastCvarEnabled = CvarEnabled;
        // r.GrassDeform is a scalability switch: it wins over the Blueprint-facing SetEnabled.
        // The deform state is dropped in both directions, because a disabled system must not keep
        // a flatten mask alive and a re-enabled one must not blend a stale mask back in.
        DiscardInteractionState();
    }

    // The sink keeps FoliageQualityLevel current between ticks (the engine flushes its sinks when any
    // cvar is set, and at the top of each frame). Calling the same routine here rather than repeating
    // the comparison keeps the latch and the state release from drifting apart; it early-outs on an
    // unchanged level, so the per-tick cost is one int compare.
    HandleScalabilityChanged();

    // r.GrassDeform.RTSize no longer rebuilds anything: the RT pair is a persistent asset whose
    // size is fixed in the asset itself (see RecreateRenderTargets). The cvar stays registered so
    // old inis do not warn, and RecreateRenderTargets logs once when a stale value disagrees.

    if (!IsEnabled())
    {
        // Still publish bEnabled=0 so the grass shader can drop the sampling (static switch).
        PublishParameters();
        return;
    }

    // --- 10 Hz trample source ---------------------------------------------------------------
    UpdateTrampleSource(DeltaTime);

    // Keep the window under the player even when no stamp is pending, so the accumulation buffer
    // is already in the right place when the next event arrives.
    if (const ACharacter* Character = Trample.Character.Get())
    {
        RecenterWindow(Character->GetActorLocation());
    }

    // --- event-driven passes -----------------------------------------------------------------
    UpdateFade(DeltaTime);
    DrainPendingStamps();
    PublishParameters();
}

// ---------------------------------------------------------------------------------------------
// Ping-pong helpers
//
// Every pass both reads and writes the deform buffer, so a pass can never target the texture it
// samples. Each pass therefore draws into the write side while the material's GrassDeformRT
// parameter still points at the read side; FlipReadSide() then swaps them and rebinds the RT on
// the grass materials. One flip per pass keeps the two sides consistent.
// ---------------------------------------------------------------------------------------------

UTextureRenderTarget2D* UGrassDeformSubsystem::GetReadTarget() const
{
    return RenderTargets[ReadIndex];
}

UTextureRenderTarget2D* UGrassDeformSubsystem::GetWriteTarget() const
{
    return RenderTargets[1 - ReadIndex];
}

void UGrassDeformSubsystem::FlipReadSide()
{
    ReadIndex = 1 - ReadIndex;
    bReadSideDirty = true;
}

void UGrassDeformSubsystem::DrainPendingStamps()
{
    if (Pending.Num() == 0) return;

    UWorld* World = GetWorld();
    UMaterialInstanceDynamic* Material = StampMaterial;
    if (!World || !Material || !GetWriteTarget() || !GetReadTarget()) { Pending.Reset(); return; }

    // Radius arrives in cm; the stamp material needs it in UV. One division per event.
    const float InvWindow = 1.f / GrassDeformTuning::WindowSizeCm;

    // The stamp reads the current read side through its "Old" texture parameter and accumulates
    // into the write side, so the whole queue is chained stamp-on-stamp. Each iteration promotes
    // the target it just wrote (see the flip below) so the next stamp sees the previous one.
    UTextureRenderTarget2D* WriteTarget = GetWriteTarget();

    for (const FPendingStamp& Stamp : Pending)
    {
        const FVector2D StampUV = (Stamp.CenterXY - WindowCenter) * InvWindow + FVector2D(0.5, 0.5);
        const float Margin = Stamp.Radius * InvWindow;
        if (StampUV.X < -Margin || StampUV.X > 1.f + Margin || StampUV.Y < -Margin || StampUV.Y > 1.f + Margin) continue;
        const FVector2D StartUV = (Stamp.StartXY - WindowCenter) * InvWindow + FVector2D(0.5, 0.5);
        // Both outputs sample exactly the same old pair. Only promote after BOTH draws.
        for (UMaterialInstanceDynamic* Pass : {StampMaterial.Get(), StampTimeMaterial.Get()})
        {
            Pass->SetTextureParameterValue(GrassDeformParams::PassSource, GetReadTarget());
            Pass->SetTextureParameterValue(TEXT("OldTime"), ContactTimeTargets[ReadIndex]);
            Pass->SetVectorParameterValue(GrassDeformParams::CenterUV, FLinearColor(StampUV.X, StampUV.Y, 0.f, 0.f));
            Pass->SetVectorParameterValue(GrassDeformParams::StartUV, FLinearColor(StartUV.X, StartUV.Y, 0.f, 0.f));
            Pass->SetVectorParameterValue(TEXT("TravelDirection"), FLinearColor(Stamp.Direction.X, Stamp.Direction.Y, 0.f, 0.f));
            Pass->SetScalarParameterValue(GrassDeformParams::IsSweep, Stamp.bSweep ? 1.f : 0.f);
            Pass->SetScalarParameterValue(GrassDeformParams::RadiusUV, Stamp.Radius * InvWindow);
            Pass->SetScalarParameterValue(GrassDeformParams::Strength, Stamp.Strength);
            Pass->SetScalarParameterValue(TEXT("CoreFraction"), Stamp.CoreFraction);
            Pass->SetScalarParameterValue(TEXT("DirectionBias"), Stamp.DirectionBias);
            Pass->SetScalarParameterValue(TEXT("PressDistanceUV"), Stamp.PressDistance * InvWindow);
            Pass->SetScalarParameterValue(TEXT("ContactNow"), float(World->GetTimeSeconds()));
            Pass->SetScalarParameterValue(TEXT("HoldSeconds"), FMath::Max(Response->HoldSeconds, 0.f));
            Pass->SetScalarParameterValue(TEXT("RecoverSeconds"), FMath::Max(Response->RecoverSeconds, 0.05f));
        }
        UKismetRenderingLibrary::DrawMaterialToRenderTarget(World, WriteTarget, StampMaterial);
        UKismetRenderingLibrary::DrawMaterialToRenderTarget(World, ContactTimeTargets[1 - ReadIndex], StampTimeMaterial);

        // The wavefront speed and origin are read by MF_GrassDeform at render time, so they are
        // published to the collection here (once per impulse; each setter is skipped when the value
        // already matches, because a redundant write dirties the uniform buffer for every material
        // that references the collection).
        if (Stamp.bImpulse && Stamp.WaveSpeed > 0.f)
        {
            if (UMaterialParameterCollectionInstance* Instance = World->GetParameterCollectionInstance(CollectionAsset))
            {
                // Canvas opaque emissive writes RGB, not the fourth component of a Custom node.
                // Keep the one active wave in the MPC; RT RGB holds flatten and radial direction.
                Instance->SetScalarParameterValue(GrassDeformParams::MpcWaveStartTime, Stamp.Timestamp);
                Instance->SetScalarParameterValue(GrassDeformParams::MpcWaveRadius, Stamp.Radius);
                Instance->SetScalarParameterValue(GrassDeformParams::MpcWaveStrength, Stamp.Strength);
                if (!FMath::IsNearlyEqual(Stamp.WaveSpeed, LastPublishedWaveSpeed))
                {
                    LastPublishedWaveSpeed = Stamp.WaveSpeed;
                    Instance->SetScalarParameterValue(GrassDeformParams::MpcWaveSpeed, Stamp.WaveSpeed);
                }

                // World-space origin survives a recenter without an extra parameter update.
                const FLinearColor Origin(float(Stamp.CenterXY.X), float(Stamp.CenterXY.Y), 0.f, 0.f);
                if (!Origin.Equals(LastPublishedWaveOrigin, 1e-4f))
                {
                    LastPublishedWaveOrigin = Origin;
                    Instance->SetVectorParameterValue(GrassDeformParams::MpcWaveOrigin, Origin);
                }
            }
        }

        // A second stamp in the same batch must see the first, so promote the write side to the
        // read side immediately and keep drawing into the other target.
        FlipReadSide();
        WriteTarget = GetWriteTarget();
        bDirty = true;
        FadeSecondsRemaining = FMath::Max(Response->HoldSeconds, 0.f) + FMath::Max(Response->RecoverSeconds, 0.05f);
    }

    // New footsteps never restart the fade clock for older footprints.
    Pending.Reset();
}

void UGrassDeformSubsystem::UpdateFade(float DeltaTime)
{
    // No render pass. The material evaluates age every frame, even between 10 Hz contacts.
    // Peak/time records can remain in the bounded window: expired records evaluate to zero.
    FadeSecondsRemaining = FMath::Max(0.f, FadeSecondsRemaining - DeltaTime);
    bDirty = FadeSecondsRemaining > 0.f;
}

void UGrassDeformSubsystem::RecenterWindow(const FVector& GroundPosition)
{
    // An integer texel shift is a copy, not another blur of the persistent trail.
    // 400 cm is 85.333 texels at 1024/48m; repeated fractional shifts smeared directions.
    const float TexelCm = GrassDeformTuning::WindowSizeCm / FMath::Max(ActiveRTSize, 1);
    const float Snapped = FMath::Max(1.f, FMath::RoundToFloat(GrassDeformTuning::SnapGridCm / TexelCm)) * TexelCm;
    const FVector2D NewCenter(
        FMath::GridSnap(float(GroundPosition.X), Snapped),
        FMath::GridSnap(float(GroundPosition.Y), Snapped));

    if (bWindowInitialized && FVector2D::Distance(NewCenter, WindowCenter) < KINDA_SMALL_NUMBER) return;

    UWorld* World = GetWorld();
    if (!World) return;

    const bool bFirst = !bWindowInitialized;
    const FVector2D PreviousCenter = WindowCenter;
    WindowCenter = NewCenter;
    bWindowInitialized = true;

    if (bFirst || !RenderTargets[0] || !RenderTargets[1] || !RecenterMaterial)
    {
        // Nothing to move on the first placement; both targets start black.
        return;
    }

    // UV offset of the new window centre measured in the old window's UV space. The recenter
    // material samples the read target at uv + ShiftUV, which is exactly the content move
    // (a feature's uv shifts by -Shift when the centre moves by +Shift).
    const FVector2D Shift(
        (NewCenter.X - PreviousCenter.X) / GrassDeformTuning::WindowSizeCm,
        (NewCenter.Y - PreviousCenter.Y) / GrassDeformTuning::WindowSizeCm);

    RecenterMaterial->SetVectorParameterValue(GrassDeformParams::ShiftUV, FLinearColor(Shift.X, Shift.Y, 0.f, 0.f));

    // Only the promoted read side is authoritative. Every next pass fully overwrites the other
    // target, so mirroring it costs a redundant full-screen draw and is unnecessary.
    RecenterMaterial->SetTextureParameterValue(GrassDeformParams::PassSource, GetReadTarget());
    UKismetRenderingLibrary::DrawMaterialToRenderTarget(World, GetWriteTarget(), RecenterMaterial);
    RecenterTimeMaterial->SetVectorParameterValue(GrassDeformParams::ShiftUV, FLinearColor(Shift.X, Shift.Y, 0.f, 0.f));
    RecenterTimeMaterial->SetTextureParameterValue(GrassDeformParams::PassSource, ContactTimeTargets[ReadIndex]);
    UKismetRenderingLibrary::DrawMaterialToRenderTarget(World, ContactTimeTargets[1 - ReadIndex], RecenterTimeMaterial);
    FlipReadSide();
}

void UGrassDeformSubsystem::UpdateTrampleSource(float DeltaTime)
{
    UWorld* World = GetWorld();
    if (!World || !Response) return;
    APlayerController* Controller = World->GetFirstPlayerController();
    ACharacter* Character = Controller ? Cast<ACharacter>(Controller->GetPawn()) : nullptr;
    if (Trample.Character.Get() != Character)
    {
        Trample.Character = Character;
        Trample.bHasProjection = false;
        bBodyGrounded = false;
    }
    const bool bGrounded = Character && Character->GetCharacterMovement()
        && Character->GetCharacterMovement()->IsMovingOnGround();
    if (!bGrounded)
    {
        BodyContact.A = 0.f;
        BodyContactAge = 0.f;
        bBodyGrounded = false;
        Trample.bHasProjection = false;
        TrampleClock = 0.f;
        return;
    }

    const FVector Location = Character->GetActorLocation();
    const FVector2D Projection(Location.X, Location.Y);
    const bool bTeleport = bBodyGrounded && FVector2D::Distance(Projection, PreviousBodyPosition)
        > GrassDeformTuning::TrampleMaxSegmentCm;
    if (!bBodyGrounded || bTeleport)
    {
        BodyContactAge = 0.f;
        Trample.bHasProjection = false;
    }
    PreviousBodyPosition = Projection;
    bBodyGrounded = true;
    BodyContactAge += DeltaTime;
    const FVector Velocity = Character->GetVelocity();
    const FVector2D HorizontalVelocity(Velocity.X, Velocity.Y);
    const float Speed = HorizontalVelocity.Size();
    if (Speed > 1.f) BodyDirection = HorizontalVelocity / Speed;
    const float CapsuleRadius = Character->GetCapsuleComponent()->GetScaledCapsuleRadius();
    const float Radius = FMath::Max(FMath::Max(Response->BodyRadiusCm, 1.f), CapsuleRadius * GrassDeformTuning::TrampleRadiusScale);
    const float PressSeconds = FMath::Max(Response->PressSeconds, 0.01f);
    const float Entry = FMath::SmoothStep(0.f, 1.f, FMath::Clamp(BodyContactAge / PressSeconds, 0.f, 1.f));
    const float Strength = FMath::Clamp(Response->BodyStrength, 0.f, 1.f) * Entry;
    BodyContact = FLinearColor(Projection.X, Projection.Y, Radius, Strength);
    // Leading edge eases down over the distance travelled in PressSeconds.
    BodyMotion = FLinearColor(BodyDirection.X, BodyDirection.Y, Speed * PressSeconds, 0.f);

    TrampleClock += DeltaTime;
    if (TrampleClock < 1.f / GrassDeformTuning::TrampleCheckHz) return;
    TrampleClock = 0.f;
    if (Trample.bHasProjection && FVector2D::Distance(Projection, Trample.LastProjection) > GrassDeformTuning::TrampleMaxSegmentCm)
        Trample.bHasProjection = false;
    // Also refresh while stationary. The continuous body field holds between these writes.
    if (EnqueueStamp(Location, Radius, Strength, 0.f, false))
    {
        FPendingStamp& Stamp = Pending.Last();
        Stamp.StartXY = Trample.bHasProjection ? Trample.LastProjection : Projection;
        Stamp.bSweep = true;
        Stamp.Direction = BodyDirection;
        Stamp.DirectionBias = FMath::Clamp(Response->ForwardBias, 0.51f, 1.f);
        Stamp.CoreFraction = FMath::Clamp(Response->CoreFraction, 0.f, 0.95f);
        Stamp.PressDistance = Speed * PressSeconds;
        Trample.LastProjection = Projection;
        Trample.bHasProjection = true;
    }
}

void UGrassDeformSubsystem::PublishParameters()
{
    UWorld* World = GetWorld();
    if (!World || !CollectionAsset) return;

    UMaterialParameterCollectionInstance* Instance = World->GetParameterCollectionInstance(CollectionAsset);
    if (!Instance) return;

    // Time plus changed body vectors; no per-instance writes or per-frame RT passes.
    if (!BodyContact.Equals(PublishedBodyContact, 0.0001f))
    {
        PublishedBodyContact = BodyContact;
        Instance->SetVectorParameterValue(TEXT("GrassBodyContact"), BodyContact);
    }
    if (!BodyMotion.Equals(PublishedBodyMotion, 0.0001f))
    {
        PublishedBodyMotion = BodyMotion;
        Instance->SetVectorParameterValue(TEXT("GrassBodyMotion"), BodyMotion);
    }
    if (Response && !bResponsePublished)
    {
        Instance->SetScalarParameterValue(TEXT("GrassHoldSeconds"), FMath::Max(Response->HoldSeconds, 0.f));
        Instance->SetScalarParameterValue(TEXT("GrassRecoverSeconds"), FMath::Max(Response->RecoverSeconds, 0.05f));
        Instance->SetScalarParameterValue(TEXT("GrassCoreFraction"), FMath::Clamp(Response->CoreFraction, 0.f, 0.95f));
        Instance->SetScalarParameterValue(TEXT("GrassBendAngle"), FMath::Clamp(Response->BendAngleDegrees, 0.f, 85.f));
        Instance->SetScalarParameterValue(TEXT("GrassFlatWindScale"), FMath::Clamp(Response->FlatWindScale, 0.f, 1.f));
        Instance->SetScalarParameterValue(TEXT("GrassForwardBias"), FMath::Clamp(Response->ForwardBias, 0.51f, 1.f));
        bResponsePublished = true;
    }
    const double Now = World->GetTimeSeconds();
    if (Now != PublishedWorldTime)
    {
        Instance->SetScalarParameterValue(GrassDeformParams::MpcWorldTime, float(Now));
        PublishedWorldTime = Now;
    }

    // The grass shader picks the read side of the ping-pong pair through this scalar: both RT
    // assets are wired into MF_GrassDeform as TextureObjectParameter defaults (a Material
    // Parameter Collection cannot carry textures, and a subsystem-owned MID of MA_Grass never
    // reaches the rendered foliage), and ReadIsB selects between them with a uniform branch.
    // Published on flip only.
    if (bReadSideDirty)
    {
        bReadSideDirty = false;
        const int32 ReadIsB = (ReadIndex == 1) ? 1 : 0;
        if (ReadIsB != LastPublishedReadIsB)
        {
            LastPublishedReadIsB = ReadIsB;
            Instance->SetScalarParameterValue(GrassDeformParams::MpcReadIsB, float(ReadIsB));
        }
    }

    // Publish the off gate even before the first player/window placement.
    const int32 Enabled = IsEnabled() && bWindowInitialized ? 1 : 0;
    if (Enabled != LastPublishedEnabled)
    {
        LastPublishedEnabled = Enabled;
        Instance->SetScalarParameterValue(GrassDeformParams::MpcEnabled, float(Enabled));
    }

    if (!bWindowInitialized) return;

    if (!WindowCenter.Equals(LastPublishedCenter, 0.01f))
    {
        LastPublishedCenter = WindowCenter;
        Instance->SetVectorParameterValue(GrassDeformParams::MpcCenter, FLinearColor(WindowCenter.X, WindowCenter.Y, 0.f, 0.f));
    }

    const float WindowSize = GrassDeformTuning::WindowSizeCm;
    if (!FMath::IsNearlyEqual(WindowSize, LastPublishedWindowSize))
    {
        LastPublishedWindowSize = WindowSize;
        Instance->SetScalarParameterValue(GrassDeformParams::MpcWindowSize, WindowSize);
    }

    const float Regrowth = Response ? FMath::Max(Response->HoldSeconds, 0.f) + FMath::Max(Response->RecoverSeconds, 0.05f) : 2.4f;
    if (!FMath::IsNearlyEqual(Regrowth, LastPublishedRegrowth))
    {
        LastPublishedRegrowth = Regrowth;
        Instance->SetScalarParameterValue(GrassDeformParams::MpcRegrowthSeconds, Regrowth);
    }

}

bool UGrassDeformSubsystem::HasLiveContent() const
{
    return bDirty;
}
