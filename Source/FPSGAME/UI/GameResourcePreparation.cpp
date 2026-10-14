#include "GameResourcePreparation.h"
#include "Components/PrimitiveComponent.h"
#include "ContentStreaming.h"
#include "Engine/LevelStreaming.h"
#include "Engine/Texture.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "PipelineStateCache.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "ShaderPipelineCache.h"
#include "UObject/UObjectGlobals.h"

namespace GameEntryResources
{
bool UsesVisibleResources(const UPrimitiveComponent* Component)
{
    if (!IsValid(Component) || !Component->IsRegistered()) return false;
    const bool Hidden = !Component->IsVisible() || Component->bHiddenInGame ||
        (Component->GetOwner() && Component->GetOwner()->IsHidden());
    return !Hidden || (Component->CastShadow && Component->bCastHiddenShadow);
}

int32 RequiredMips(const UTexture2D* Texture)
{
    const auto& State = Texture->GetStreamableResourceState();
    // Never wait on optional payloads absent from the installed build or cinematic mips.
    return FMath::Min(int32(State.NumNonOptionalLODs),
        FMath::Max(1, int32(State.MaxNumLODs) - Texture->NumCinematicMipLevels));
}
}

FGameResourcePreparation::FGameResourcePreparation(UWorld* World, bool bDuringSceneAssembly)
    : Scene(World), bSceneAssembling(bDuringSceneAssembly)
{
    StartedAt = FPlatformTime::Seconds();
    if(World)
    {
        ActorSpawnedHandle=World->AddOnActorSpawnedHandler(
            FOnActorSpawned::FDelegate::CreateRaw(this,&FGameResourcePreparation::TrackActor));
        for(TActorIterator<AActor> It(World);It;++It)TrackActor(*It);
    }
    if(!bSceneAssembling)StartCollection();
}

FGameResourcePreparation::~FGameResourcePreparation() { StopTrackingActors();ReleaseProtection(); }

void FGameResourcePreparation::TrackActor(AActor* Actor)
{
    if(IsValid(Actor)&&!SeenActors.Contains(Actor))
    {SeenActors.Add(Actor);KnownActors.Add(Actor);}
}

void FGameResourcePreparation::StopTrackingActors()
{
    if(auto* World=Scene.Get();World&&ActorSpawnedHandle.IsValid())World->RemoveOnActorSpawnedHandler(ActorSpawnedHandle);
    ActorSpawnedHandle.Reset();
    KnownActors.Reset();SeenActors.Reset();
    // Reuse the bounded entry-material cache for residency handoff; it contains
    // weak references and is released with the final protected texture.
    if(!bReady)MaterialTextures.Reset();
    WarmActors.Reset();QueuedWarmActors.Reset();WarmMaterials.Reset();
    WarmTextures.Reset();SeenWarmTextures.Reset();RequestedWarmTextures.Reset();
}

void FGameResourcePreparation::QueueAssembledActor(AActor* Actor)
{
    TrackActor(Actor);
    if(bSceneAssembling&&IsValid(Actor)&&!QueuedWarmActors.Contains(Actor))
    {QueuedWarmActors.Add(Actor);WarmActors.Add(Actor);}
}

void FGameResourcePreparation::FinishSceneAssembly()
{
    if(!bSceneAssembling)return;
    bSceneAssembling=false;
    WarmActors.Reset();QueuedWarmActors.Reset();WarmMaterials.Reset();WarmTextures.Reset();SeenWarmTextures.Reset();RequestedWarmTextures.Reset();
    // Final eligibility is evaluated after room visibility is applied. Speculative
    // requests never pin hidden rooms or become part of the final required set.
    StartedAt=FPlatformTime::Seconds();
    StartCollection();
}

void FGameResourcePreparation::GetMaterialTextures(UMaterialInterface* Material,TArray<UTexture*>& Out)
{
    // Dynamic parameters can change during scene finishing/late weapon setup.
    const auto* Resource=Material->GetMaterialResource(GetFeatureLevelShaderPlatform_Checked(Scene->GetFeatureLevel()));
    const auto* ShaderMap=Resource?Resource->GetGameThreadShaderMap():nullptr;
    const bool bCacheable=!Material->IsA<UMaterialInstanceDynamic>()&&ShaderMap&&ShaderMap->IsValidForRendering();
    if(bCacheable)if(const auto* Cached=MaterialTextures.Find(Material))
    {for(const auto& Texture:*Cached)if(auto* Value=Texture.Get())Out.Add(Value);return;}
    Material->GetUsedTextures(Out,{},GetFeatureLevelShaderPlatform_Checked(Scene->GetFeatureLevel()));
    if(bCacheable)
    {
        auto& Cached=MaterialTextures.FindOrAdd(Material);
        for(auto* Texture:Out)if(Texture)Cached.Add(Texture);
    }
}

void FGameResourcePreparation::PumpAssemblyWarmup(double Deadline)
{
    const double CollectionDeadline=FPlatformTime::Seconds()+FMath::Max(0.,Deadline-FPlatformTime::Seconds())*.5;
    while(WarmActorCursor<WarmActors.Num()&&FPlatformTime::Seconds()<CollectionDeadline)
    {
        const auto Weak=WarmActors[WarmActorCursor++];QueuedWarmActors.Remove(Weak);
        if(auto* Actor=Weak.Get();IsValid(Actor))
        {
            TInlineComponentArray<UPrimitiveComponent*> Primitives(Actor);
            for(auto* Component:Primitives)
            {
                if(!Component->IsRegistered())continue;
                TArray<UMaterialInterface*> Used;Component->GetUsedMaterials(Used);
                for(auto* Material:Used)if(Material&&!WarmMaterials.Contains(Material))
                {
                    TArray<UTexture*> UsedTextures;GetMaterialTextures(Material,UsedTextures);
                    if(!UsedTextures.IsEmpty())WarmMaterials.Add(Material);
                    for(auto* UsedTexture:UsedTextures)
                        if(auto* Texture=Cast<UTexture2D>(UsedTexture);Texture&&!Texture->IsCurrentlyVirtualTextured()&&!SeenWarmTextures.Contains(Texture))
                        {SeenWarmTextures.Add(Texture);WarmTextures.Add(Texture);}
                }
            }
        }
    }
    if(WarmActorCursor==WarmActors.Num()){WarmActors.Reset();WarmActorCursor=0;}
    const int64 Pool=IStreamingManager::Get().GetRenderAssetStreamingManager().GetPoolSize();
    for(int32 Remaining=WarmTextures.Num();Remaining>0&&FPlatformTime::Seconds()<Deadline;--Remaining)
    {
        if(WarmTextureCursor>=WarmTextures.Num())WarmTextureCursor=0;
        auto* Texture=WarmTextures[WarmTextureCursor++].Get();
        if(!Texture||RequestedWarmTextures.Contains(Texture)||!Texture->RenderResourceSupportsStreaming())continue;
        const auto& State=Texture->GetStreamableResourceState();
        if(!State.IsValid()||Texture->HasPendingInitOrStreaming())continue;
        const int64 Bytes=Texture->CalcTextureMemorySizeEnum(TMC_AllMipsBiased);
        // Speculative work is bounded and evictable. Final preparation still
        // measures the visible set before registering residency protection.
        if(Pool<=0||WarmRequestBytes+Bytes>Pool*.85)continue;
        const int32 Required=GameEntryResources::RequiredMips(Texture);
        if(State.NumResidentLODs>=Required||Texture->StreamIn(Required,true))
        {WarmRequestBytes+=Bytes;RequestedWarmTextures.Add(Texture);}
    }
}

void FGameResourcePreparation::ReleaseProtection()
{
    if (IStreamingManager::HasShutdown()) return;
    auto& Manager = IStreamingManager::Get().GetRenderAssetStreamingManager();
    for (const auto& Weak : Protected)
        if (auto* Texture = Weak.Get()) Manager.UnregisterStreamOutProtectedAsset(Texture);
    Protected.Reset();
    ResidencyInUse.Reset();ResidencyMaterials.Reset();UnusedSince.Reset();MaterialTextures.Reset();
}

void FGameResourcePreparation::TickResidency()
{
    if (!HasResidencyWork() || IStreamingManager::HasShutdown()) return;
    UWorld* World = Scene.Get();
    if (!World) { ReleaseProtection(); return; }
    if (World->IsPaused()) return;
    const double Now = World->GetTimeSeconds();
    if (Now < NextResidencyPass) return;
    TRACE_CPUPROFILER_EVENT_SCOPE(GameEntry_ReleaseUnusedResidency);
    const double Deadline = FPlatformTime::Seconds() + .001;
    if (ResidencyCursor == INDEX_NONE)
    {
        ResidencyCursor = 0;
        ResidencyInUse.Reset();
        ResidencyMaterials.Reset();
    }
    // Only revisit the prepared component set, never scan the whole world. A
    // shared texture stays protected if any eligible component still uses it.
    while (ResidencyCursor < Components.Num() && FPlatformTime::Seconds() < Deadline)
    {
        auto* Component = Components[ResidencyCursor++].Get();
        if (!GameEntryResources::UsesVisibleResources(Component)) continue;
        TArray<UMaterialInterface*> Used;
        Component->GetUsedMaterials(Used);
        for (auto* Material : Used)
        {
            if (!Material || ResidencyMaterials.Contains(Material)) continue;
            ResidencyMaterials.Add(Material);
            TArray<UTexture*> UsedTextures;
            GetMaterialTextures(Material, UsedTextures);
            for (auto* Texture : UsedTextures)
                if (auto* Texture2D = Cast<UTexture2D>(Texture); Texture2D && Protected.Contains(Texture2D))
                    ResidencyInUse.Add(Texture2D);
        }
    }
    if (ResidencyCursor < Components.Num()) return;
    auto& Manager = IStreamingManager::Get().GetRenderAssetStreamingManager();
    for (auto It = Protected.CreateIterator(); It; ++It)
    {
        const auto Weak = *It;
        auto* Texture = Weak.Get();
        if (Texture && ResidencyInUse.Contains(Weak)) { UnusedSince.Remove(Weak); continue; }
        // Keep entry quality across the fade and brief visibility/equipment
        // transitions. Removing protection permits eviction; it never forces it.
        double* Since = UnusedSince.Find(Weak);
        if (Texture && !Since) { UnusedSince.Add(Weak, Now); continue; }
        if (Texture && Now - *Since < 5.) continue;
        if (Texture) Manager.UnregisterStreamOutProtectedAsset(Texture);
        UnusedSince.Remove(Weak);
        It.RemoveCurrent();
    }
    ResidencyCursor = INDEX_NONE;
    NextResidencyPass = Now + 1.;
    ResidencyInUse.Reset();ResidencyMaterials.Reset();
    if (Protected.IsEmpty()) MaterialTextures.Reset();
}

void FGameResourcePreparation::StartCollection()
{
    Actors.Reset(); QueriedMaterials.Reset(); ActorCursor = 0; bCollecting = true;
    // Spawn tracking includes late callbacks; reuse the registry on quiet passes.
    // Streamed-in level actors can arrive without the spawn delegate.
    if(auto* World=Scene.Get();World&&!World->GetStreamingLevels().IsEmpty())
        for(TActorIterator<AActor> It(World);It;++It)TrackActor(*It);
    Actors=KnownActors;
    Status = FText::FromString(TEXT("正在收集场景与装备资源…"));
}

void FGameResourcePreparation::CollectComponent(UPrimitiveComponent* Component)
{
    if (!GameEntryResources::UsesVisibleResources(Component)) return;
    // Characters keep inactive weapon-family components registered. Those are not
    // equipped resources; loading all of them at full resolution exhausts the pool.
    if(!SeenComponents.Contains(Component)){SeenComponents.Add(Component);Components.Add(Component);}
    TArray<UMaterialInterface*> Used;
    Component->GetUsedMaterials(Used);
    for (auto* Material : Used)
    {
        if (!Material || QueriedMaterials.Contains(Material)) continue;
        QueriedMaterials.Add(Material);
        if(!SeenMaterials.Contains(Material)){SeenMaterials.Add(Material);Materials.Add(Material);}
        TArray<UTexture*> UsedTextures;
        GetMaterialTextures(Material,UsedTextures);
        for (auto* Texture : UsedTextures)
        {
            if (!Texture || SeenTextures.Contains(Texture)) continue;
            SeenTextures.Add(Texture); Textures.Add(Texture);
        }
    }
}

void FGameResourcePreparation::Fail(const FString& Reason)
{
    bFailed = true; Status = FText::FromString(Reason);
    StopTrackingActors();
    ReleaseProtection();
    UE_LOG(LogTemp, Error, TEXT("GameEntryPreparation: %s"), *Reason);
}

void FGameResourcePreparation::Tick()
{
    if (bReady || bFailed) return;
    UWorld* World = Scene.Get();
    if (!World) { Fail(TEXT("场景已离开，请重新选择进入方式。")); return; }
    const double Now = FPlatformTime::Seconds();
    if(bSceneAssembling){PumpAssemblyWarmup(Now+.002);return;}
    // Let the streaming manager consume the selected pool budget on its own tick.
    if(Now-StartedAt<.25)return;
    if (Now - StartedAt > 120)
    {
        Fail(FString::Printf(TEXT("资源准备超时，尚未进入游戏。等待：%s。可重试或返回选择。"),
            PendingName.IsEmpty() ? TEXT("场景资源") : *PendingName));
        return;
    }
    const double Deadline = Now + .002;
    if (bCollecting)
    {
        do
        {
            if (ActorCursor >= Actors.Num()) break;
            if (auto* Actor = Actors[ActorCursor++].Get())
            {
                TInlineComponentArray<UPrimitiveComponent*> Primitives(Actor);
                for (auto* Primitive : Primitives) CollectComponent(Primitive);
            }
        } while (FPlatformTime::Seconds() < Deadline);
        if (ActorCursor < Actors.Num()) return;
        Actors.Reset(); bCollecting = false; bMeasuring = true;
        MaterialCursor = TextureCursor = Pending = ReadyTextures = 0; RequiredTextureBytes = 0;
    }
    auto& Manager = IStreamingManager::Get().GetRenderAssetStreamingManager();
    if (bMeasuring)
    {
        // Establish the whole request's cost before pinning anything. No infinite pool.
        while (TextureCursor < Textures.Num() && FPlatformTime::Seconds() < Deadline)
        {
            auto* Texture = Cast<UTexture2D>(Textures[TextureCursor++].Get());
            if (!Texture || Texture->IsCurrentlyVirtualTextured()) continue;
            const auto& State = Texture->GetStreamableResourceState();
            if (!State.IsValid()) { ++Pending; PendingName = Texture->GetName(); continue; }
            // Exported engine API; this conservative estimate includes all quality-allowed mips.
            RequiredTextureBytes += Texture->CalcTextureMemorySizeEnum(TMC_AllMipsBiased);
        }
        if (TextureCursor < Textures.Num()) return;
        if (Pending)
        {
            TextureCursor = Pending = 0; RequiredTextureBytes = 0;
            Status = FText::FromString(TEXT("正在初始化纹理资源…")); return;
        }
        const int64 Pool = Manager.GetPoolSize();
        if (Pool > 0 && RequiredTextureBytes > Pool * .85)
        {
            Fail(FString::Printf(TEXT("当前场景高清纹理需要约 %lld MB，超过本档可用预算 %lld MB。请返回选择快速测试，或减少同时加载的场景资源。"),
                RequiredTextureBytes / (1024 * 1024), int64(Pool * .85) / (1024 * 1024)));
            return;
        }
        bMeasuring = false; TextureCursor = Pending = ReadyTextures = 0;
    }
    if (Now < NextPass) return;
    while (MaterialCursor < Materials.Num() && FPlatformTime::Seconds() < Deadline)
    {
        auto* Material = Materials[MaterialCursor++].Get();
        if (!Material) continue;
        auto* Resource = Material->GetMaterialResource(GetFeatureLevelShaderPlatform_Checked(World->GetFeatureLevel()));
#if WITH_EDITOR
        if (Resource && !Resource->GetCompileErrors().IsEmpty())
        {
            Fail(FString::Printf(TEXT("材质 %s 编译失败，不能按完整预加载进入。请修复该材质后重试。"), *Material->GetName())); return;
        }
        const bool Compiling = Resource && !Resource->IsCompilationFinished();
#else
        const bool Compiling = false;
#endif
        const auto* ShaderMap = Resource ? Resource->GetGameThreadShaderMap() : nullptr;
        if (Compiling || !ShaderMap || !ShaderMap->IsValidForRendering())
        { ++Pending; PendingName = Material->GetName(); }
    }
    if (MaterialCursor < Materials.Num()) return;
    while (TextureCursor < Textures.Num() && FPlatformTime::Seconds() < Deadline)
    {
        auto* Texture = Textures[TextureCursor++].Get();
        if (!Texture) continue;
        bool Ready = Texture->GetResource() != nullptr;
        if (auto* Texture2D = Cast<UTexture2D>(Texture); Texture2D && !Texture2D->IsCurrentlyVirtualTextured())
        {
            const auto& State = Texture2D->GetStreamableResourceState();
            const int32 Required = GameEntryResources::RequiredMips(Texture2D);
            Ready &= State.IsValid() && !Texture2D->HasPendingInitOrStreaming();
            if (Texture2D->RenderResourceSupportsStreaming())
            {
                // Protection covers only this entry set, not every texture in Content.
                if (!Protected.Contains(Texture2D) && Manager.TryRegisterStreamOutProtectedAsset(Texture2D)) Protected.Add(Texture2D);
                if (Ready && State.NumResidentLODs < Required) Texture2D->StreamIn(Required, true);
                Ready &= State.NumResidentLODs >= Required && Protected.Contains(Texture2D);
            }
        }
        if (Ready) ++ReadyTextures;
        else { ++Pending; PendingName = Texture->GetName(); }
    }
    if (TextureCursor < Textures.Num()) return;
    for (const auto& Weak : Components)
        if (auto* Component = Weak.Get(); Component && Component->IsCompiling()) { ++Pending; PendingName = Component->GetName(); }
    for (auto* Level : World->GetStreamingLevels())
        if (Level && (Level->IsStreamingStatePending() || (Level->ShouldBeLoaded() && !Level->IsLevelLoaded())))
        { ++Pending; PendingName = Level->GetWorldAssetPackageName(); }
    if (IsAsyncLoading()) { ++Pending; PendingName = TEXT("异步场景资源"); }
    const uint32 PSOs = FShaderPipelineCache::NumPrecompilesRemaining() + PipelineStateCache::NumActivePrecacheRequests();
    if (PSOs) { ++Pending; PendingName = TEXT("渲染管线"); }
    Progress = .15f + .8f * float(ReadyTextures) / FMath::Max(1, Textures.Num());
    Status = FText::FromString(FString::Printf(TEXT("高清纹理 %d / %d，待准备项 %d%s%s"),
        ReadyTextures, Textures.Num(), Pending, Pending ? TEXT(" · ") : TEXT(""), Pending ? *PendingName : TEXT("")));
    if (Pending) { StableSince = 0; bFenceStarted = false; }
    else if (StableSince == 0) StableSince = Now;
    else if (Now - StableSince >= 1)
    {
        const int32 Count = Textures.Num() + Materials.Num() + Components.Num();
        if (LastCollectionCount != Count)
        {
            // A second quiet pass includes weapons/components assembled by late callbacks.
            LastCollectionCount = Count; StableSince = 0; StartCollection(); return;
        }
        if (!bFenceStarted) { Fence.BeginFence(); bFenceStarted = true; }
        else if (Fence.IsFenceComplete())
        {
            bReady = true; Progress = 1; Status = FText::FromString(TEXT("资源准备完成"));
            StopTrackingActors();
            UE_LOG(LogTemp, Display, TEXT("GameEntryPreparation: ready textures=%d materials=%d bytes=%lld elapsed=%.2f"),
                Textures.Num(), Materials.Num(), RequiredTextureBytes, Now - StartedAt);
        }
    }
    MaterialCursor = TextureCursor = Pending = ReadyTextures = 0; NextPass = Now + .2;
}
