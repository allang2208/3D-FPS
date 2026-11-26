#include "FPSGameSceneLifecycle.h"
#include "Engine/World.h"
#include "RenderingThread.h"
#include "SceneInterface.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "UObject/UObjectIterator.h"

namespace FPSGameSceneLifecycle
{
FDelegateHandle CleanupHandle;

void TearingDown(UWorld* World)
{
    if (!World || !World->IsGameWorld() || !World->Scene ||
        !World->Scene->GetRenderScene()) return;
    // UE 5.8 batch removal reads the old proxy's skinned asset/skeleton. Detach
    // instanced skin primitives BEFORE ClearWorldComponents queues MeshObject's
    // deferred deletion. A post-cleanup rendering flush is already too late.
    // BatchRemovePrimitives clears each component's SceneProxy; its normal later
    // unregister will still release the mesh resources, without removing twice.
    FSceneInterface* Scene = World->Scene;
    TArray<UPrimitiveComponent*> Skins;
    for (TObjectIterator<UInstancedSkinnedMeshComponent> It; It; ++It)
        if (It->IsRegistered() && It->GetScene() == Scene && It->GetSceneProxy()) Skins.Add(*It);
    if (Skins.IsEmpty()) return;
    // FScene::Update requires all render command pipes to be out of replay.
    // Keep removal and the following scene update on the same render timeline.
    UE::RenderCommandPipe::FSyncScope SyncScope;
    Scene->BatchRemovePrimitives(Skins);
    ENQUEUE_RENDER_COMMAND(FPSDrainWorldPrimitives)([Scene](FRHICommandListImmediate& RHICmdList)
    {
        Scene->UpdateAllPrimitiveSceneInfos(RHICmdList);
    });
    FlushRenderingCommands();
    UE_LOG(LogTemp, Display, TEXT("GAME_SCENE drained skin batches=%d before mesh cleanup world=%s"),
        Skins.Num(), *World->GetName());
}
}

void FFPSGameSceneLifecycle::Startup()
{
    FPSGameSceneLifecycle::CleanupHandle = FWorldDelegates::OnWorldBeginTearDown.AddStatic(&FPSGameSceneLifecycle::TearingDown);
}
void FFPSGameSceneLifecycle::Shutdown()
{
    FWorldDelegates::OnWorldBeginTearDown.Remove(FPSGameSceneLifecycle::CleanupHandle);
}
