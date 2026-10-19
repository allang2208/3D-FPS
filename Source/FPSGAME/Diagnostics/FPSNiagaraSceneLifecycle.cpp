#include "FPSNiagaraSceneLifecycle.h"

#if WITH_EDITOR
#include "CoreMinimal.h"
#include "Engine/World.h"
#include "FXSystem.h"
#include "SceneInterface.h"

DEFINE_LOG_CATEGORY_STATIC(LogFPSNiagaraSceneLifecycle, Log, All);

namespace FPSNiagaraSceneLifecycle
{
FDelegateHandle RecreatedHandle;
FDelegateHandle CleanupHandle;
TSet<TWeakObjectPtr<UWorld>> WorldsToRestore;

void OnSceneRecreated(UWorld* World)
{
    check(IsInGameThread());
    // Only the main editor World is purged for PIE. Gameplay, PIE clients,
    // commandlets and intentionally FX-free preview worlds retain their policy.
    if (!World || World->WorldType != EWorldType::Editor || !World->Scene) return;

    if (!World->Scene->GetRenderScene())
    {
        if (World->FXSystem)
        {
            // UE 5.8 RecreateScene can create an FXSystem on FNULLSceneInterface.
            // Niagara's deferred tick flush then creates a real FViewInfo and
            // interprets that NULL interface as FScene, reading beyond it.
            // Detach before components re-register and any World tick can pump it.
            WorldsToRestore.Add(World);
            FFXSystemInterface::MarkPendingKill(World->FXSystem.Get());
            World->Scene->SetFXSystem(nullptr);
            World->FXSystem.Reset();
            UE_LOG(LogFPSNiagaraSceneLifecycle, Display,
                TEXT("Suspended FX on purged editor NULL scene: %s"), *World->GetPathName());
        }
    }
    else if (WorldsToRestore.Remove(World) > 0)
    {
        // RestoreScene chooses bCreateFXSystem from the old World pointer, which
        // we cleared above. Recreate it here, before component re-registration.
        if (!World->FXSystem) World->CreateFXSystem();
        UE_LOG(LogFPSNiagaraSceneLifecycle, Display,
            TEXT("Restored FX on editor render scene: %s"), *World->GetPathName());
    }
}

void OnWorldCleanup(UWorld* World, bool, bool)
{
    WorldsToRestore.Remove(World);
}
}
#endif

void FFPSNiagaraSceneLifecycle::Startup()
{
#if WITH_EDITOR
    using namespace FPSNiagaraSceneLifecycle;
    RecreatedHandle = FWorldDelegates::OnPostRecreateScene.AddStatic(&OnSceneRecreated);
    CleanupHandle = FWorldDelegates::OnWorldCleanup.AddStatic(&OnWorldCleanup);
#endif
}

void FFPSNiagaraSceneLifecycle::Shutdown()
{
#if WITH_EDITOR
    using namespace FPSNiagaraSceneLifecycle;
    FWorldDelegates::OnPostRecreateScene.Remove(RecreatedHandle);
    FWorldDelegates::OnWorldCleanup.Remove(CleanupHandle);
    RecreatedHandle.Reset();
    CleanupHandle.Reset();
    WorldsToRestore.Empty();
#endif
}
