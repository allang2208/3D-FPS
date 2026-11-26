#include "ColdSteelPreviewScene.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/LineBatchComponent.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "EngineModule.h"
#include "FXSystem.h"
#include "RendererInterface.h"
#include "SceneInterface.h"
#include "Subsystems/WorldSubsystem.h"
#include "UObject/UObjectHash.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

TUniquePtr<FColdSteelPreviewScene> FColdSteelPreviewScene::TryCreate(ConstructionValues Values, FString& Failure)
{
    Failure.Reset();
    // UE 5.8 initializes subsystem CDOs before ShouldCreateSubsystem can reject
    // preview worlds. A stale CDO after class reinstancing asserts inside the
    // base constructor, so this check must happen before allocating the scene.
    TArray<UClass*> Classes;
    GetDerivedClasses(UWorldSubsystem::StaticClass(), Classes, true);
    for (UClass* Class : Classes)
    {
        // Match the engine's eligibility filter; retired reinstanced classes are
        // ignored only when the engine also ignores them.
        if (Class->HasAllClassFlags(CLASS_Abstract) || Class->GetAuthoritativeClass() != Class) continue;
        const UObject* Defaults = Class->GetDefaultObject(); // Deliberately untyped: inspect before casting.
        if (!Defaults || !Defaults->IsA<UWorldSubsystem>() || !Defaults->IsA(Class))
        {
            Failure = FString::Printf(TEXT("Preview world subsystem CDO mismatch: class=%s default=%s default_class=%s. Restart the editor after a regular build; using catalog icons for this session."),
                *Class->GetPathName(), *GetPathNameSafe(Defaults),
                Defaults ? *Defaults->GetClass()->GetPathName() : TEXT("None"));
            return nullptr;
        }
    }
    return MakeUnique<FColdSteelPreviewScene>(Values);
}

FColdSteelPreviewScene::FColdSteelPreviewScene(ConstructionValues Values) : FPreviewScene(Values)
{
    // Base-constructor calls do not dispatch to our AddComponent override.
    for (UActorComponent* Component : {static_cast<UActorComponent*>(DirectionalLight),
        static_cast<UActorComponent*>(SkyLight), static_cast<UActorComponent*>(LineBatcher)})
        if (Component) StudioComponents.Add(Component);
    GetWorld()->SetShouldTick(false);
}

void FColdSteelPreviewScene::AddComponent(UActorComponent* Component, const FTransform& Transform, bool bAttachToRoot)
{
    ResumeRendering();
    StudioComponents.AddUnique(Component);
    FPreviewScene::AddComponent(Component, Transform, bAttachToRoot);
}

void FColdSteelPreviewScene::RemoveComponent(UActorComponent* Component)
{
    StudioComponents.Remove(Component);
    FPreviewScene::RemoveComponent(Component);
}

void FColdSteelPreviewScene::SuspendRendering()
{
#if WITH_EDITOR
    UWorld* World = GetWorld();
    if (bRenderingSuspended || !World || !World->Scene) return;
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Preview_ReleaseScene);
    // Call only after all subjects/captures have retired. Keep the world shell to
    // avoid FPreviewScene::~FPreviewScene requesting a global full-purge GC.
    World->ClearWorldComponents();
    for (const auto& Weak : StudioComponents)
        if (auto* Component = Weak.Get(); Component && Component->IsRegistered()) Component->UnregisterComponent();
    // Scene-bound world subsystems (including DynamicWind) retain FScene
    // references. Queue their unregistration BEFORE the scene release, just
    // as UWorld::RecreateScene does, while preserving the UObject world shell.
    FWorldDelegates::OnPreRecreateScene.Broadcast(World);
    for (ULevel* Level : World->GetLevels()) Level->ReleaseRenderingResources();
    // Follow UWorld::RecreateScene's FX ownership order before releasing FScene.
    bHadFXSystem = World->FXSystem.IsValid();
    if (bHadFXSystem)
    {
        FFXSystemInterface::MarkPendingKill(World->FXSystem.Get());
        World->FXSystem = nullptr;
        World->Scene->SetFXSystem(nullptr);
    }
    // FScene::Release removes itself from the renderer and queues destruction.
    // No rendering flush, GPU wait, global cvar change or gameplay-world change.
    World->Scene->Release();
    World->Scene = nullptr;
    bRenderingSuspended = true;
#else
    // Runtime builds do not expose the scene-recreation delegate contract.
    // Callers already retire subjects/captures/targets; retain this scene until
    // normal world cleanup deinitializes its subsystems before destroying it.
#endif
}

void FColdSteelPreviewScene::ResumeRendering()
{
    if (!bRenderingSuspended) return;
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Preview_RestoreScene);
    UWorld* World = GetWorld();
    GetRendererModule().AllocateScene(World, World->RequiresHitProxies(), bHadFXSystem, World->GetFeatureLevel());
    for (ULevel* Level : World->GetLevels()) Level->InitializeRenderingResources();
#if WITH_EDITOR
    FWorldDelegates::OnPostRecreateScene.Broadcast(World);
#endif
    for (const auto& Weak : StudioComponents)
        if (auto* Component = Weak.Get()) Component->RegisterComponentWithWorld(World);
    bRenderingSuspended = false;
    UpdateCaptureContents();
}
