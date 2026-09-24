#include "ColdSteelMonsterPortraits.h"

#include "Async/Async.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Engine/AssetManager.h"
#include "Engine/Texture2D.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Math/Float16Color.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialRenderProxy.h"
#include "MaterialShared.h"
#include "PreviewScene.h"
#include "RHIGPUReadback.h"
#include "RenderingThread.h"
#include "TextureResource.h"
#include "../Development/DevelopmentSpawnComponent.h"

namespace
{
    /** 捕获画布的纵向半高（cm）：所有怪物共用同一取景尺度，跨身份的体型比例才可比。 */
    constexpr float PortraitHalfHeightCm = 240.f;
}

/** 立绘回读包；定义在全局作用域，与头文件的前置声明是同一类型。 */
struct FColdSteelPortraitReadback
{
    enum EState : int32 { Queued, WaitingGPU, Converting, Ready, Failed };
    TAtomic<int32> State{Queued};
    TAtomic<bool> PollQueued{false}, Cancelled{false};
    TUniquePtr<FRHIGPUTextureReadback> Staging;
    FString Key, Error;
    int32 Width = 0, Height = 0, Visible = 0;
    double SubmittedSeconds = 0.0;
    TArray<FColor> Pixels;
};

bool UColdSteelMonsterPortraits::Supports(const FDevelopmentMonsterEntry& Entry)
{
    return !Entry.CharacterClass.IsNull();
}

FString UColdSteelMonsterPortraits::Key(const FDevelopmentMonsterEntry& Entry)
{
    return Entry.Id.ToString();
}

const FSlateBrush* UColdSteelMonsterPortraits::Find(const FString& KeyValue) const
{
    if (auto* E = Cache.Find(KeyValue)) { E->Use = ++Serial; return &E->Brush; }
    return nullptr;
}

bool UColdSteelMonsterPortraits::EnsureStudio()
{
    if (Studio) return true;
    // 与武器图标同一套工作室参数（灯光方向、天空、无物理），保证两张图的光照风格一致。
    Studio = MakeUnique<FPreviewScene>(FPreviewScene::ConstructionValues()
        .SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false)
        .SetForceMipsResident(false).SetLightBrightness(6.f).SetSkyBrightness(1.f));
    Studio->SetSkyCubemap(LoadObject<UTextureCube>(nullptr, TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment.T_StudioEnvironment")));
    Studio->DirectionalLight->SetWorldRotation(FRotator(-35, -35, 0));

    Capture = NewObject<USceneCaptureComponent2D>(GetTransientPackage(), NAME_None, RF_Transient);
    Capture->SetCaptureSortPriority(INT32_MAX);
    Capture->bCaptureEveryFrame = false;
    Capture->bCaptureOnMovement = false;
    Capture->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
    Capture->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->ShowFlags.SetAtmosphere(false);
    Capture->ShowFlags.SetFog(false);
    Capture->ShowFlags.SetAntiAliasing(true);
    Capture->PostProcessSettings.bOverride_AutoExposureMethod = true;
    Capture->PostProcessSettings.AutoExposureMethod = AEM_Manual;
    Capture->PostProcessSettings.bOverride_AutoExposureBias = true;
    Capture->PostProcessSettings.AutoExposureBias = 0.f;
    Studio->AddComponent(Capture, FTransform::Identity);

    Target = NewObject<UTextureRenderTarget2D>(GetTransientPackage(), NAME_None, RF_Transient);
    Target->RenderTargetFormat = RTF_RGBA16f;
    Target->ClearColor = FLinearColor::Transparent;
    Target->bAutoGenerateMips = false;
    Target->InitAutoFormat(PortraitWidth, PortraitHeight);
    Target->UpdateResourceImmediate(true);
    Capture->TextureTarget = Target;
    return true;
}

void UColdSteelMonsterPortraits::ResetSubject()
{
    if (Subject)
    {
        Subject->SetActorTickEnabled(false);
        Studio->RemoveComponent(Subject->GetMesh());
        Subject->Destroy();
        Subject = nullptr;
    }
    CaptureMaterials.Empty();
    CaptureTextures.Empty();
}

void UColdSteelMonsterPortraits::ResetAsyncLoad()
{
    if (ResourceLoad) { ResourceLoad->CancelHandle(); ResourceLoad.Reset(); }
    RequiredResources.Reset();
}

void UColdSteelMonsterPortraits::BeginAsyncLoad()
{
    // 异步预载怪物类与其依赖，不阻塞游戏线程——这是「不靠超时兜底」的关键：
    // LoadSynchronous 会在游戏线程上硬等包加载与构造，首次进图鉴时即卡帧；
    // RequestAsyncLoad 让加载在后台完成，Tick 只查 HasLoadCompleted()。
    // 与武器图标工作室（ColdSteelIconResources.cpp:196）同一策略。
    ResetAsyncLoad();
    const int32 Index = FMath::Clamp(ActiveIndex, 0, Queue.Num() - 1);
    const FSoftObjectPath Ref = Queue[Index].CharacterClass.ToSoftObjectPath();
    if (!Ref.IsValid()) return;
    RequiredResources.Add(Ref);
    // 手柄保留到本作业结束，避免 GC 在捕获前把预载资源卸掉。
    ResourceLoad = UAssetManager::GetStreamableManager().RequestAsyncLoad(
        RequiredResources, FStreamableDelegate(), FStreamableManager::DefaultAsyncLoadPriority);
}

bool UColdSteelMonsterPortraits::SpawnSubject()
{
    if (Subject) return true;
    UClass* Class = Queue[FMath::Clamp(ActiveIndex, 0, Queue.Num() - 1)].CharacterClass.Get();
    if (!Class) return false;
    // 怪物类在构造里设了 AutoPossessAI=PlacedInWorldOrSpawned，直接 SpawnActor 会在预览场景里
    // 生成一个 AI 控制器并跑行为树；立绘是纯展示，必须关掉自动附身。
    // 用 FActorSpawnParameters::Template 传一个临时模板：生成体复制模板属性而不是 CDO 属性，
    // 因此只影响这一具预览体，绝不改写共享 CDO（改写 CDO 会污染真正的游戏怪物）。
    ACharacter* Template = NewObject<ACharacter>(GetTransientPackage(), Class, NAME_None, RF_Transient);
    if (!Template) return false;
    Template->AutoPossessAI = EAutoPossessAI::Disabled;
    Template->AIControllerClass = nullptr;

    FActorSpawnParameters Spawn;
    Spawn.ObjectFlags = RF_Transient;
    Spawn.Template = Template;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
#if WITH_EDITOR
    Spawn.bTemporaryEditorActor = true;
#endif
    Subject = Studio->GetWorld()->SpawnActor<ACharacter>(Class, FVector::ZeroVector, FRotator::ZeroRotator, Spawn);
    if (!Subject) return false;
    // 纯展示：不参与游戏逻辑，也不跑 AI／动画 Tick。
    Subject->SetActorTickEnabled(false);
    Subject->SetActorEnableCollision(false);
    if (auto* Mesh = Subject->GetMesh())
    {
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        // 用第 0 帧姿势取静息姿态，避免各怪物的随机起始动作相位导致朝向不一致。
        Mesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        Mesh->TickAnimation(0.f, false);
        Mesh->RefreshBoneTransforms();
    }
    return true;
}

bool UColdSteelMonsterPortraits::PoseAndFrame()
{
    auto* Mesh = Subject->GetMesh();
    if (!Mesh || !Mesh->GetSkeletalMeshAsset()) return false;

    // 统一朝向：把所有怪物摆成面向世界 +X（相机沿 +X 看过来即正面），
    // 与武器图标「固定正交相机 + FRotator::ZeroRotator」同理，差异只在被摄体本身。
    Subject->SetActorRotation(FRotator(0.f, 0.f, 0.f));

    // 只显示被摄体自身网格，避免骨骼网格附件或预览场景杂物入镜。
    Capture->ShowOnlyComponents.Reset();
    Capture->ShowOnlyComponent(Mesh);

    const FBoxSphereBounds Bounds = Mesh->Bounds;
    if (Bounds.SphereRadius <= KINDA_SMALL_NUMBER) return false;

    // 固定取景：相机沿 -X 方向看，画面高度锁 240cm，水平按立绘宽高比推出。
    // 重心放在被摄体包围盒中心，保证不同体型的怪物都居中且比例可比。
    const float Aspect = float(PortraitWidth) / float(PortraitHeight);
    const float HalfHeight = FMath::Max(PortraitHalfHeightCm, float(Bounds.BoxExtent.Z) * 1.15f);
    const FVector Center = Bounds.Origin;
    Capture->SetWorldLocation(FVector(Center.X - 4000.f, Center.Y, Center.Z));
    Capture->SetWorldRotation(FRotator::ZeroRotator);
    Capture->bAutoCalculateOrthoPlanes = false;
    Capture->bUseCustomProjectionMatrix = true;
    Capture->OrthoWidth = HalfHeight * 2.f * Aspect;
    Capture->CustomProjectionMatrix = FReversedZOrthoMatrix(HalfHeight, HalfHeight * Aspect, 1.f / 20000.f, -0.1f);

    // 收集材质与其贴图，等 mip 就绪再拍，否则会拍到糊图或灰模。
    for (int32 Slot = 0; Slot < Mesh->GetNumMaterials(); ++Slot)
    {
        if (auto* Material = Mesh->GetMaterial(Slot))
        {
            CaptureMaterials.AddUnique(Material);
            TArray<UTexture*> Used;
            Material->GetUsedTextures(Used);
            for (auto* Texture : Used) if (Texture) CaptureTextures.AddUnique(Texture);
        }
    }
    Studio->GetWorld()->SendAllEndOfFrameUpdates();
    return true;
}

bool UColdSteelMonsterPortraits::IsTextureReady(UTexture* Texture) const
{
    // 与武器图标同一策略：只要与立绘分辨率相称的 mip，别把 4K 怪物贴图钉进常驻内存。
    if (auto* Texture2D = Cast<UTexture2D>(Texture))
    {
        if (Texture2D->VirtualTextureStreaming) return Texture2D->GetResource() != nullptr;
        if (!Texture2D->GetResource()) return false;
        if (!Texture2D->HasPendingInitOrStreaming()) return true;
        // 需要几级 mip 由立绘高度决定；取整到 2 的幂区间即可，不必精确。
        int32 Wanted = 0;
        int32 Size = FMath::Max(Texture2D->GetSizeX(), Texture2D->GetSizeY());
        while (Size > PortraitHeight) { Size >>= 1; ++Wanted; }
        Texture2D->StreamIn(FMath::Max(1, Texture2D->GetNumMips() - Wanted), false);
        return false;
    }
    return Texture->IsFullyStreamedIn();
}

bool UColdSteelMonsterPortraits::SubmitReadiness()
{
    if (!MaterialStatus)
    {
        if (CaptureMaterials.IsEmpty()) return false;
        TArray<const FMaterialRenderProxy*> Proxies;
        for (UMaterialInterface* Material : CaptureMaterials)
        {
            if (!Material) continue;
            Proxies.Add(Material->GetRenderProxy());
        }
        if (Proxies.IsEmpty()) return false;
        MaterialStatus = MakeShared<TAtomic<int32>, ESPMode::ThreadSafe>(-2);
        const auto Status = MaterialStatus;
        const auto Level = Studio->GetScene()->GetFeatureLevel();
        ENQUEUE_RENDER_COMMAND(ColdSteelPortraitMaterialsReady)([Status, Proxies, Level](FRHICommandListImmediate&)
        {
            int32 Result = -1;
            for (int32 Index = 0; Index < Proxies.Num(); ++Index)
            {
                const FMaterialRenderProxy* Fallback = nullptr;
                if (!Proxies[Index]) { Result = Index; break; }
                const auto& Material = Proxies[Index]->GetMaterialWithFallback(Level, Fallback);
                if (Fallback || !Material.IsRenderingThreadShaderMapComplete()) { Result = Index; break; }
            }
            Status->Store(Result);
        });
        ++ReadinessPolls;
        return false;
    }
    if (MaterialStatus->Load() == -2) { ++ReadinessPolls; return false; }
    if (MaterialStatus->Load() >= 0) return false;
    for (UTexture* Texture : CaptureTextures) if (!IsTextureReady(Texture)) return false;
    return true;
}

void UColdSteelMonsterPortraits::BeginReadback()
{
    const FString K = Queue[FMath::Clamp(ActiveIndex, 0, Queue.Num() - 1)].Key;
    auto Packet = MakeShared<FColdSteelPortraitReadback, ESPMode::ThreadSafe>();
    Packet->Key = K;
    Packet->Width = Target->SizeX;
    Packet->Height = Target->SizeY;
    Packet->SubmittedSeconds = FPlatformTime::Seconds();
    PendingReadback = Packet;

    auto* Resource = Target->GameThread_GetRenderTargetResource();
    ENQUEUE_RENDER_COMMAND(ColdSteelPortraitReadbackCopy)([Packet, Resource](FRHICommandListImmediate& RHICmdList)
    {
        if (Packet->Cancelled.Load()) return;
        FRHITexture* Source = Resource ? Resource->GetRenderTargetTexture().GetReference() : nullptr;
        if (!Source || Source->GetDesc().Format != PF_FloatRGBA || Source->GetDesc().Extent != FIntPoint(Packet->Width, Packet->Height))
        {
            Packet->Error = TEXT("立绘回读目标缺失或不是预期尺寸的 RGBA16f 纹理");
            Packet->State.Store(FColdSteelPortraitReadback::Failed);
            return;
        }
        Packet->Staging = MakeUnique<FRHIGPUTextureReadback>(TEXT("ColdSteelMonsterPortrait"));
        RHICmdList.Transition(FRHITransitionInfo(Source, ERHIAccess::Unknown, ERHIAccess::CopySrc));
        Packet->Staging->EnqueueCopy(RHICmdList, Source);
        RHICmdList.Transition(FRHITransitionInfo(Source, ERHIAccess::CopySrc, ERHIAccess::SRVMask));
        Packet->State.Store(FColdSteelPortraitReadback::WaitingGPU);
    });
}

void UColdSteelMonsterPortraits::CancelReadback()
{
    if (!PendingReadback) return;
    auto Packet = MoveTemp(PendingReadback);
    Packet->Cancelled.Store(true);
    ENQUEUE_RENDER_COMMAND(ColdSteelPortraitReleaseReadback)([Packet](FRHICommandListImmediate&) { Packet->Staging.Reset(); });
}

void UColdSteelMonsterPortraits::PollReadback()
{
    const auto Packet = PendingReadback;
    if (!Packet) { FinishJob(false); return; }
    const int32 Status = Packet->State.Load();
    if (Status == FColdSteelPortraitReadback::Ready)
    {
        if (Queue.IsEmpty() || Queue[FMath::Clamp(ActiveIndex, 0, Queue.Num() - 1)].Key != Packet->Key) { CancelReadback(); return; }
        FinishJob(Publish(Packet->Key, Packet->Pixels, Packet->Width, Packet->Height));
        return;
    }
    if (Status == FColdSteelPortraitReadback::Failed) { FinishJob(false); return; }
    if (FPlatformTime::Seconds() - Packet->SubmittedSeconds >= 10.0)
    {
        // GPU 回读超时同样先延后重试，未达上限不记永久失败。
        const double Now = FPlatformTime::Seconds();
        CancelReadback();
        if (Queue[FMath::Clamp(ActiveIndex, 0, Queue.Num() - 1)].Attempts + 1 >= MaxAttempts) FinishJob(false);
        else DeferCurrentJob(Now);
        return;
    }
    if (Status != FColdSteelPortraitReadback::WaitingGPU || Packet->PollQueued.Exchange(true)) return;
    ENQUEUE_RENDER_COMMAND(ColdSteelPortraitPollReadback)([Packet](FRHICommandListImmediate&)
    {
        if (Packet->Cancelled.Load()) { Packet->Staging.Reset(); return; }
        if (!Packet->Staging->IsReady()) { Packet->PollQueued.Store(false); return; }
        int32 RowPitch = 0, BufferHeight = 0;
        const auto* Source = static_cast<const FFloat16Color*>(Packet->Staging->Lock(RowPitch, &BufferHeight));
        if (!Source || RowPitch < Packet->Width || BufferHeight < Packet->Height)
        {
            if (Source) Packet->Staging->Unlock();
            Packet->Staging.Reset();
            Packet->Error = TEXT("立绘 staging 数据不可用");
            Packet->State.Store(FColdSteelPortraitReadback::Failed);
            return;
        }
        TArray<FFloat16Color> Linear;
        Linear.SetNumUninitialized(Packet->Width * Packet->Height);
        for (int32 Y = 0; Y < Packet->Height; ++Y)
            FMemory::Memcpy(Linear.GetData() + Y * Packet->Width, Source + Y * RowPitch, Packet->Width * sizeof(FFloat16Color));
        Packet->Staging->Unlock();
        Packet->Staging.Reset();
        Packet->State.Store(FColdSteelPortraitReadback::Converting);
        Async(EAsyncExecution::ThreadPool, [Packet, Linear = MoveTemp(Linear)]()
        {
            if (Packet->Cancelled.Load()) return;
            TArray<FColor> Pixels;
            Pixels.SetNumUninitialized(Linear.Num());
            int32 Visible = 0;
            for (int32 Index = 0; Index < Linear.Num(); ++Index)
            {
                auto P = Linear[Index].GetFloats();
                // 与武器图标同一约定：捕获纹理 alpha 取反即为被摄体覆盖率。
                const float Alpha = FMath::Clamp(1.f - P.A, 0.f, 1.f);
                if (Alpha > .1f) ++Visible;
                P.A = Alpha;
                auto Color = P.ToFColorSRGB();
                Color.A = FMath::RoundToInt(Alpha * 255);
                Pixels[Index] = Color;
            }
            Packet->Pixels = MoveTemp(Pixels);
            Packet->Visible = Visible;
            Packet->State.Store(FColdSteelPortraitReadback::Ready);
        });
    });
}

bool UColdSteelMonsterPortraits::Publish(const FString& KeyValue, const TArray<FColor>& Pixels, int32 Width, int32 Height)
{
    auto* Texture = UTexture2D::CreateTransient(Width, Height, PF_B8G8R8A8);
    if (!Texture) return false;
    Texture->SRGB = true;
    Texture->NeverStream = true;
    Texture->Filter = TF_Bilinear;
    auto& Mip = Texture->GetPlatformData()->Mips[0];
    void* Data = Mip.BulkData.Lock(LOCK_READ_WRITE);
    FMemory::Memcpy(Data, Pixels.GetData(), Pixels.Num() * sizeof(FColor));
    Mip.BulkData.Unlock();
    Texture->UpdateResource();

    if (Cache.Num() >= 32)
    {
        FString Old; uint64 Use = MAX_uint64;
        for (const auto& Pair : Cache) if (Pair.Value.Use < Use) { Use = Pair.Value.Use; Old = Pair.Key; }
        Cache.Remove(Old);
        Textures.Remove(Old);
    }
    Textures.Add(KeyValue, Texture);
    auto& E = Cache.Add(KeyValue);
    E.Use = ++Serial;
    E.Brush.SetResourceObject(Texture);
    E.Brush.ImageSize = FVector2D(Width, Height);
    E.Brush.DrawAs = ESlateBrushDrawType::Image;
    ++Completed;
    return true;
}

void UColdSteelMonsterPortraits::FinishJob(bool bSuccess)
{
    CancelReadback();
    ResetAsyncLoad();
    ResetSubject();
    FString Finished;
    if (!Queue.IsEmpty())
    {
        const int32 Index = FMath::Clamp(ActiveIndex, 0, Queue.Num() - 1);
        Finished = Queue[Index].Key;
        if (!bSuccess) Failed.Add(Finished);
        Pending.Remove(Finished);
        Queue.RemoveAt(Index);
    }
    Stage = 0;
    ActiveIndex = 0;
    AttemptStartSeconds = 0.0;
    MaterialStatus.Reset();
    ReadinessPolls = 0;
    WaitStartSeconds = 0.0;
    // 广播刚结束的 Key：监听方据此决定是否重建当前详情，成与不成都要通知。
    OnReady.Broadcast(Finished);
}

void UColdSteelMonsterPortraits::DeferCurrentJob(double Now)
{
    // 延后重试而不是永久失败：首次渲染怪物要等着色器编译与贴图首次流送，
    // 单次 10s 超时容易误判为失败，一旦进 Failed 就再也不出图。
    const int32 Index = FMath::Clamp(ActiveIndex, 0, Queue.Num() - 1);
    FJob Job = Queue[Index];
    Queue.RemoveAt(Index);
    ++Job.Attempts;
    Job.RetryAfterSeconds = Now + 1.5;
    Queue.Add(MoveTemp(Job));
    // 先撤掉在途回读与异步句柄，再销毁被摄体，避免回读包引用已释放的渲染目标。
    CancelReadback();
    ResetAsyncLoad();
    ResetSubject();
    Stage = 0;
    ActiveIndex = 0;
    AttemptStartSeconds = 0.0;
    MaterialStatus.Reset();
    WaitStartSeconds = 0.0;
}

void UColdSteelMonsterPortraits::Request(const FDevelopmentMonsterEntry& Entry)
{
    if (!Supports(Entry)) return;
    const FString K = Key(Entry);
    if (Cache.Contains(K) || Pending.Contains(K) || Failed.Contains(K)) return;
    Pending.Add(K);
    FJob Job;
    Job.Key = K;
    Job.CharacterClass = Entry.CharacterClass;
    Job.RequestedSeconds = FPlatformTime::Seconds();
    Queue.Add(MoveTemp(Job));
}

void UColdSteelMonsterPortraits::Tick(float DeltaTime)
{
    if (Queue.IsEmpty()) return;
    // 作业身份一律经 ActiveIndex 取，不假定 Queue[0]：延后重试会把作业移到队尾。
    ActiveIndex = FMath::Clamp(ActiveIndex, 0, Queue.Num() - 1);
    FJob& Active = Queue[ActiveIndex];
    const double Now = FPlatformTime::Seconds();
    // 处于延后冷却中的作业先等待；到位后再开始新的一次尝试。
    if (Active.RetryAfterSeconds > Now) return;
    if (!EnsureStudio())
    {
        if (Active.Attempts + 1 >= MaxAttempts) FinishJob(false);
        else DeferCurrentJob(Now);
        return;
    }
    if (Stage == 0)
    {
        // 起步即发起异步预载，之后只轮询完成状态，游戏线程不等待。
        BeginAsyncLoad();
        Stage = 1;
        AttemptStartSeconds = Now;
        return;
    }
    if (Stage == 1)
    {
        // 异步加载未完成就继续等，不消耗尝试次数、不设人为超时：
        // 加载本身有 UAssetManager 的正常调度，硬等或反复重试都不如静候其完成。
        if (ResourceLoad && !ResourceLoad->HasLoadCompleted()) return;
        if (!Queue[FMath::Clamp(ActiveIndex, 0, Queue.Num() - 1)].CharacterClass.Get())
        {
            if (Queue[FMath::Clamp(ActiveIndex, 0, Queue.Num() - 1)].Attempts + 1 >= MaxAttempts) FinishJob(false);
            else DeferCurrentJob(Now);
            return;
        }
        Stage = 2;
        return;
    }
    if (Stage == 2) { if (!SpawnSubject()) { if (Active.Attempts + 1 >= MaxAttempts) FinishJob(false); else DeferCurrentJob(Now); } else Stage = 3; return; }
    if (Stage == 3) { if (!PoseAndFrame()) { if (Active.Attempts + 1 >= MaxAttempts) FinishJob(false); else DeferCurrentJob(Now); } else { Stage = 4; WaitStartSeconds = Now; } return; }
    if (Stage == 4)
    {
        // 等材质着色器与贴图流送到位再拍；未就绪就停在本阶段，下一帧继续等。
        // 这里的等待是「资源就绪」而非「加载」：加载已由 Stage 1 的异步句柄负责。
        // 仍保留 10s 上限，但只为防止着色器永久失败时占住队列；命中后延后重试而非永久放弃。
        if (!SubmitReadiness())
        {
            if (Now - WaitStartSeconds >= 10.0)
            {
                if (Active.Attempts + 1 >= MaxAttempts) FinishJob(false);
                else DeferCurrentJob(Now);
            }
            return;
        }
        Capture->CaptureScene();
        BeginReadback();
        Stage = 5;
        return;
    }
    PollReadback();
}

void UColdSteelMonsterPortraits::Deinitialize()
{
    CancelReadback();
    ResetAsyncLoad();
    ResetSubject();
    Queue.Empty();
    Pending.Empty();
    Failed.Empty();
    // 一并回零状态机：本对象虽将销毁，但保持「清空即完全空闲」的语义，
    // 避免基类或后续复用路径看到半截状态。
    Stage = 0;
    ActiveIndex = 0;
    AttemptStartSeconds = 0.0;
    MaterialStatus.Reset();
    ReadinessPolls = 0;
    WaitStartSeconds = 0.0;
    OnReady.Clear();
    if (Capture)
    {
        Capture->TextureTarget = nullptr;
        if (Studio) Studio->RemoveComponent(Capture);
        Capture->DestroyComponent();
    }
    Capture = nullptr;
    Studio.Reset();
    Target = nullptr;
    Cache.Empty();
    Textures.Empty();
    Super::Deinitialize();
}