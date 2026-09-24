#pragma once

#include "CoreMinimal.h"
#include "RenderCommandFence.h"

class UWorld;
class AActor;
class UPrimitiveComponent;
class UMaterialInterface;
class UTexture;
class UTexture2D;

/** One world's bounded, nonblocking entry preparation. No asset loads on the HUD path. */
class FGameResourcePreparation
{
public:
    explicit FGameResourcePreparation(UWorld* World);
    ~FGameResourcePreparation();
    void Tick();
    bool IsReady() const { return bReady; }
    bool HasFailed() const { return bFailed; }
    FText Status;
    float Progress = 0;

private:
    void StartCollection();
    void CollectComponent(UPrimitiveComponent* Component);
    void Fail(const FString& Reason);
    void ReleaseProtection();
    TWeakObjectPtr<UWorld> Scene;
    TArray<TWeakObjectPtr<AActor>> Actors;
    TArray<TWeakObjectPtr<UPrimitiveComponent>> Components;
    TSet<TWeakObjectPtr<UPrimitiveComponent>> SeenComponents;
    TArray<TWeakObjectPtr<UMaterialInterface>> Materials;
    TArray<TWeakObjectPtr<UTexture>> Textures;
    TSet<TWeakObjectPtr<UMaterialInterface>> SeenMaterials;
    TSet<TWeakObjectPtr<UMaterialInterface>> QueriedMaterials;
    TSet<TWeakObjectPtr<UTexture>> SeenTextures;
    TSet<TWeakObjectPtr<UTexture2D>> Protected;
    FRenderCommandFence Fence;
    int32 ActorCursor = 0;
    int32 MaterialCursor = 0;
    int32 TextureCursor = 0;
    int32 Pending = 0;
    int32 ReadyTextures = 0;
    int32 LastCollectionCount = -1;
    int64 RequiredTextureBytes = 0;
    double StartedAt = 0;
    double StableSince = 0;
    double NextPass = 0;
    FString PendingName;
    bool bCollecting = true;
    bool bMeasuring = true;
    bool bFenceStarted = false;
    bool bReady = false;
    bool bFailed = false;
};
