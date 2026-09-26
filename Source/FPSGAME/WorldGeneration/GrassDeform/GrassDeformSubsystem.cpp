#include "GrassDeformSubsystem.h"

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
    static const TCHAR* const CollectionPath = TEXT("/Game/WorldGeneration/GrassDeform/MPC_GrassDeform.MPC_GrassDeform");
    static const TCHAR* const StampPath = TEXT("/Game/WorldGeneration/GrassDeform/M_GrassDeformStamp.M_GrassDeformStamp");
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
    static const FName RadiusUV(TEXT("RadiusUV"));
    static const FName Strength(TEXT("Strength"));
    static const FName BendDir(TEXT("BendDir"));
    static const FName DirStrength(TEXT("DirStrength"));
    static const FName Timestamp(TEXT("Timestamp"));

    // Fade pass.
    static const FName FadeRate(TEXT("FadeRate"));
    static const FName ExpirySeconds(TEXT("ExpirySeconds"));

    // Recenter pass.
    static const FName ShiftUV(TEXT("ShiftUV"));

    // MPC_GrassDeform parameters.
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
        TEXT("Rate of the grass deform regrowth pass. Lower is cheaper, higher regrows smoother.\n")
        TEXT("Clamped to 1..12; default 6."),
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
    // Presentation-only system: it runs anywhere the deformation is visible (Game, PIE and the
    // editor's preview worlds) and is skipped on a dedicated server, which has no renderer to
    // drive. Initialize() re-checks NM_DedicatedServer for the listen-server/standalone cases
    // where a Game world is not a client.
    return Type == EWorldType::Game || Type == EWorldType::PIE || Type == EWorldType::Editor;
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
    bUserEnabled = LastCvarEnabled != 0;

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
    // It does no rendering work: it only latches the level and releases the interaction state when
    // the deform has just been forced off. Passes stop on the next Tick through IsEnabled().
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
    bDirty = false;
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
    FadeMaterialAsset = LoadObject<UMaterialInterface>(nullptr, GrassDeformAssets::FadePath);
    RecenterMaterialAsset = LoadObject<UMaterialInterface>(nullptr, GrassDeformAssets::RecenterPath);
    CollectionAsset = LoadObject<UMaterialParameterCollection>(nullptr, GrassDeformAssets::CollectionPath);
    RenderTargetAssets[0] = LoadObject<UTextureRenderTarget2D>(nullptr, GrassDeformAssets::RTAPath);
    RenderTargetAssets[1] = LoadObject<UTextureRenderTarget2D>(nullptr, GrassDeformAssets::RTBPath);

    const bool bComplete = StampMaterialAsset && FadeMaterialAsset && RecenterMaterialAsset
        && CollectionAsset && RenderTargetAssets[0] && RenderTargetAssets[1];
    if (!bComplete)
    {
        if (!bMissingAssetsLogged)
        {
            bMissingAssetsLogged = true;
            UE_LOG(LogGrassDeform, Warning,
                TEXT("Grass deform disabled: content is incomplete. Missing: %s%s%s%s%s%s")
                TEXT(" Run Tools/GrassDeform/run_asset_setup_m1.ps1 to create them."),
                StampMaterialAsset ? TEXT("") : TEXT("M_GrassDeformStamp "),
                FadeMaterialAsset ? TEXT("") : TEXT("M_GrassDeformFade "),
                RecenterMaterialAsset ? TEXT("") : TEXT("M_GrassDeformRecenter "),
                CollectionAsset ? TEXT("") : TEXT("MPC_GrassDeform "),
                RenderTargetAssets[0] ? TEXT("") : TEXT("RT_GrassDeformA "),
                RenderTargetAssets[1] ? TEXT("") : TEXT("RT_GrassDeformB"));
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
    FadeMaterial = UMaterialInstanceDynamic::Create(FadeMaterialAsset, this);
    RecenterMaterial = UMaterialInstanceDynamic::Create(RecenterMaterialAsset, this);
    bAssetsReady = StampMaterial && FadeMaterial && RecenterMaterial;

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
    bReadSideDirty = true;
    Pending.Reset();

    // Start from a clean mask on every (re)bind: the assets persist across a SetEnabled toggle or
    // a world reload, and a stale flatten mask must never blend back in.
    if (UWorld* World = GetWorld())
    {
        UKismetRenderingLibrary::ClearRenderTarget2D(World, RenderTargets[0], FLinearColor::Black);
        UKismetRenderingLibrary::ClearRenderTarget2D(World, RenderTargets[1], FLinearColor::Black);
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
    for (int32 Index = 0; Index < 2; ++Index) RenderTargets[Index] = nullptr;
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
        && IsFoliageQualityAllowed()
        && bAssetsReady
        && RenderTargets[0] && RenderTargets[1];
}

void UGrassDeformSubsystem::SetEnabled(bool bInEnabled)
{
    bUserEnabled = bInEnabled;
    if (!bInEnabled)
    {
        // Release the interaction state rather than leaving a stale flatten mask on screen.
        DiscardInteractionState();
        ReleaseRenderTargets();
        if (bAssetsReady) RecreateRenderTargets();
    }
}

void UGrassDeformSubsystem::StampTrample(FVector WorldPos, float Radius, float Strength)
{
    EnqueueStamp(WorldPos, Radius, Strength, 0.f, false);
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

    // Convert to window UV. Anything outside the window is dropped instead of being clamped onto
    // the border, which would leave a permanent flat ring at the RT edge.
    const float U = (float(WorldPos.X) - WindowCenter.X) / GrassDeformTuning::WindowSizeCm + 0.5f;
    const float V = (float(WorldPos.Y) - WindowCenter.Y) / GrassDeformTuning::WindowSizeCm + 0.5f;
    const float Margin = FMath::Clamp(FMath::Max(Radius, 1.f) / GrassDeformTuning::WindowSizeCm, 0.f, 0.5f);
    if (U < -Margin || U > 1.f + Margin || V < -Margin || V > 1.f + Margin) return false;

    if (Pending.Num() >= MaxPendingStamps) return false;

    FPendingStamp& Stamp = Pending.AddDefaulted_GetRef();
    Stamp.CenterXY = FVector2D(U, V);
    Stamp.Radius = FMath::Clamp(Radius, GrassDeformTuning::MinStampRadiusCm, GrassDeformTuning::MaxStampRadiusCm);
    Stamp.Strength = FMath::Clamp(Strength, 0.f, GrassDeformTuning::MaxStampStrength);
    Stamp.WaveSpeed = bImpulse ? FMath::Max(WaveSpeed, 0.f) : 0.f;
    Stamp.Timestamp = bImpulse ? float(World->GetTimeSeconds()) : GrassDeformTuning::NoImpulseTimestamp;
    Stamp.bImpulse = bImpulse;

    MarkDirty();
    FadeSecondsRemaining = GrassDeformTuning::RegrowthSeconds;
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
    DrainPendingStamps();
    UpdateFade(DeltaTime);
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
        // Bind the read side on every pass: the ping-pong pair changes sides after each draw, so
        // "Old" must be re-pointed at the texture holding the previous contents. This is the
        // per-event setter the ping-pong contract depends on.
        Material->SetTextureParameterValue(GrassDeformParams::PassSource, GetReadTarget());

        Material->SetVectorParameterValue(GrassDeformParams::CenterUV, FLinearColor(Stamp.CenterXY.X, Stamp.CenterXY.Y, 0.f, 0.f));
        Material->SetScalarParameterValue(GrassDeformParams::RadiusUV, Stamp.Radius * InvWindow);
        Material->SetScalarParameterValue(GrassDeformParams::Strength, Stamp.Strength);
        // BendDir is written already encoded to 0..1 (the STAMP_CODE contract decodes with
        // gb * 2 - 1); PassSource GB is the same encoding, so no direction means (0.5, 0.5).
        Material->SetVectorParameterValue(GrassDeformParams::BendDir, FLinearColor(0.5f, 0.5f, 0.f, 0.f));
        Material->SetScalarParameterValue(GrassDeformParams::DirStrength, 0.f);
        Material->SetScalarParameterValue(GrassDeformParams::Timestamp, Stamp.Timestamp);

        UKismetRenderingLibrary::DrawMaterialToRenderTarget(World, WriteTarget, Material);

        // The wavefront speed and origin are read by MF_GrassDeform at render time, so they are
        // published to the collection here (once per impulse; each setter is skipped when the value
        // already matches, because a redundant write dirties the uniform buffer for every material
        // that references the collection).
        if (Stamp.bImpulse && Stamp.WaveSpeed > 0.f)
        {
            if (UMaterialParameterCollectionInstance* Instance = World->GetParameterCollectionInstance(CollectionAsset))
            {
                if (!FMath::IsNearlyEqual(Stamp.WaveSpeed, LastPublishedWaveSpeed))
                {
                    LastPublishedWaveSpeed = Stamp.WaveSpeed;
                    Instance->SetScalarParameterValue(GrassDeformParams::MpcWaveSpeed, Stamp.WaveSpeed);
                }

                // The origin must track every impulse, not just speed changes: two explosions at
                // different places share the default speed, and a stale origin would sweep the
                // second ring from the first impact.
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
    }

    // A stamp invalidated the fade timer: flatten must not decay on the same frame it was written.
    FadeCooldown = 1.f / ClampFadeHz(CVarGrassDeformFadeHz.GetValueOnGameThread());
    bDirty = true;
    Pending.Reset();
}

void UGrassDeformSubsystem::UpdateFade(float DeltaTime)
{
    if (!bDirty) return;

    FadeCooldown -= DeltaTime;
    if (FadeCooldown > 0.f) return;

    UWorld* World = GetWorld();
    UTextureRenderTarget2D* WriteTarget = GetWriteTarget();
    UTextureRenderTarget2D* ReadTarget = GetReadTarget();
    // Both sides must exist: the pass samples the read side and draws into the write side.
    if (!World || !WriteTarget || !ReadTarget || !FadeMaterial) return;

    const float FadeHz = ClampFadeHz(CVarGrassDeformFadeHz.GetValueOnGameThread());
    const float Step = 1.f / FadeHz;

    FadeMaterial->SetTextureParameterValue(GrassDeformParams::PassSource, ReadTarget);
    FadeMaterial->SetScalarParameterValue(GrassDeformParams::FadeRate, Step / GrassDeformTuning::RegrowthSeconds);
    FadeMaterial->SetScalarParameterValue(GrassDeformParams::ExpirySeconds, GrassDeformTuning::ImpulseExpirySeconds);
    // The fade pass reads WorldTime from the MPC (written below in PublishParameters), so the
    // shader and the CPU agree on the impulse age without a second per-pass write.

    UKismetRenderingLibrary::DrawMaterialToRenderTarget(World, WriteTarget, FadeMaterial);
    FlipReadSide();
    FadeCooldown = Step;

    // The CPU cannot see the RT, so "still flattened" is a conservative timer: the pass keeps
    // running for the full regrowth window after the last stamp, then idles completely.
    FadeSecondsRemaining -= Step;
    if (FadeSecondsRemaining > 0.f) return;

    FadeSecondsRemaining = 0.f;
    bDirty = false;
}

void UGrassDeformSubsystem::RecenterWindow(const FVector& GroundPosition)
{
    const float Snapped = GrassDeformTuning::SnapGridCm;
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
    // material samples the read target at uv - ShiftUV, which is exactly the content move.
    const FVector2D Shift(
        (NewCenter.X - PreviousCenter.X) / GrassDeformTuning::WindowSizeCm,
        (NewCenter.Y - PreviousCenter.Y) / GrassDeformTuning::WindowSizeCm);

    RecenterMaterial->SetVectorParameterValue(GrassDeformParams::ShiftUV, FLinearColor(Shift.X, Shift.Y, 0.f, 0.f));

    // Both sides are moved: the first copy relocates the live contents, and the second discards
    // the stale pre-move contents on the other side so the next pass cannot blend them back in.
    // The source binding is refreshed before each draw because the flip changes the read side.
    for (int32 Pass = 0; Pass < 2; ++Pass)
    {
        UTextureRenderTarget2D* ReadTarget = GetReadTarget();
        UTextureRenderTarget2D* WriteTarget = GetWriteTarget();
        if (!ReadTarget || !WriteTarget) break;

        RecenterMaterial->SetTextureParameterValue(GrassDeformParams::PassSource, ReadTarget);
        UKismetRenderingLibrary::DrawMaterialToRenderTarget(World, WriteTarget, RecenterMaterial);
        FlipReadSide();
    }

    // Plan section 10 risk 2: pause the regrowth pass for one tick after a move so a seam cannot
    // be amplified by a fade that samples across the shifted edge.
    FadeCooldown = FMath::Max(FadeCooldown, 1.f / ClampFadeHz(CVarGrassDeformFadeHz.GetValueOnGameThread()));
}

void UGrassDeformSubsystem::UpdateTrampleSource(float DeltaTime)
{
    TrampleClock += DeltaTime;
    const float Interval = 1.f / GrassDeformTuning::TrampleCheckHz;
    if (TrampleClock < Interval) return;
    TrampleClock = 0.f;

    UWorld* World = GetWorld();
    if (!World) return;

    if (!Trample.Character.IsValid())
    {
        if (APlayerController* Controller = World->GetFirstPlayerController())
        {
            Trample.Character = Cast<ACharacter>(Controller->GetPawn());
        }
        if (!Trample.Character.IsValid()) return;
        Trample.bHasProjection = false;
    }

    ACharacter* Character = Trample.Character.Get();
    const FVector Location = Character->GetActorLocation();

    // Capsule-bottom projection: the pawn origin sits at the capsule centre, so the ground contact
    // point is origin minus (half height - radius). No trace is issued here on purpose (plan
    // section 7): the footprint only needs to be close enough for a 4.7 cm/texel mask.
    float HalfHeight = 0.f;
    float Radius = 0.f;
    if (const UCapsuleComponent* Capsule = Character->GetCapsuleComponent())
    {
        HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
        Radius = Capsule->GetScaledCapsuleRadius();
    }

    const FVector GroundPoint = Location - FVector(0.f, 0.f, FMath::Max(HalfHeight - Radius, 0.f) + GrassDeformTuning::TrampleGroundProbeCm);
    const FVector2D Projection(GroundPoint.X, GroundPoint.Y);

    if (!Trample.bHasProjection)
    {
        Trample.LastProjection = Projection;
        Trample.bHasProjection = true;
        return;
    }

    const FVector2D Movement = Projection - Trample.LastProjection;
    const float Distance = Movement.Size();
    if (Distance < GrassDeformTuning::TrampleDeadZoneCm) return;

    // Keep the sub-threshold remainder so a slow shuffle eventually stamps.
    if (Distance < GrassDeformTuning::TrampleMinTravelCm)
    {
        // Advance the reference only by the threshold contribution: the accumulator is implicit
        // in the distance from LastProjection, so a small step must not reset the clock.
        return;
    }

    const FVector Velocity = Character->GetVelocity();
    const float Speed = FVector(Velocity.X, Velocity.Y, 0.f).Size();
    if (Speed < GrassDeformTuning::TrampleMinSpeed) return;

    const float Alpha = FMath::Clamp(Speed / GrassDeformTuning::TrampleFullStrengthSpeed, 0.f, 1.f);
    const float Strength = FMath::Lerp(GrassDeformTuning::TrampleMinStrength, GrassDeformTuning::TrampleMaxStrength, Alpha);
    const float StampRadius = FMath::Max(Radius, 1.f) * GrassDeformTuning::TrampleRadiusScale;

    Trample.LastProjection = Projection;
    StampTrample(GroundPoint, StampRadius, Strength);
}

void UGrassDeformSubsystem::PublishParameters()
{
    UWorld* World = GetWorld();
    if (!World || !CollectionAsset) return;

    UMaterialParameterCollectionInstance* Instance = World->GetParameterCollectionInstance(CollectionAsset);
    if (!Instance) return;

    // One scalar per frame is the documented budget (plan section 7). Everything else is written
    // only when it actually changes, because each setter marks the uniform buffer dirty.
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

    const float Regrowth = GrassDeformTuning::RegrowthSeconds;
    if (!FMath::IsNearlyEqual(Regrowth, LastPublishedRegrowth))
    {
        LastPublishedRegrowth = Regrowth;
        Instance->SetScalarParameterValue(GrassDeformParams::MpcRegrowthSeconds, Regrowth);
    }

    const int32 Enabled = IsEnabled() ? 1 : 0;
    if (Enabled != LastPublishedEnabled)
    {
        LastPublishedEnabled = Enabled;
        Instance->SetScalarParameterValue(GrassDeformParams::MpcEnabled, float(Enabled));
    }
}

bool UGrassDeformSubsystem::HasLiveContent() const
{
    return bDirty;
}