#include "FacilityMonsterGpuWarmup.h"
#include "../Monsters/NurseZombie.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "RHI.h"
#include "RHICommandList.h"
#include "RenderingThread.h"

struct FFacilityWarmupCompletion
{
    FGPUFenceRHIRef Fence;
    TAtomic<bool> Ready{false};
    TAtomic<bool> PollQueued{false};
};

FFacilityMonsterGpuWarmup::FFacilityMonsterGpuWarmup(ANurseZombie* Monster)
{
    if (!Monster || Monster->HasActorBegunPlay() || !Monster->VisualMesh || !Monster->IdleClip) return;
    auto* Mesh = Monster->GetMesh();
    Body = Mesh;
    OriginalRelativeTransform = Mesh->GetRelativeTransform();
    OriginalForcedLOD = Mesh->GetForcedLOD();
    bOriginalCastShadow = Mesh->CastShadow;
    bOriginalAffectLighting = Mesh->bAffectDynamicIndirectLighting;
    bOriginalRayTracing = Mesh->bVisibleInRayTracing;
    bOriginalCaptureOnly = Mesh->bVisibleInSceneCaptureOnly;
    bOriginalHidden = Mesh->bHiddenInGame;
    bOriginalVisible = Mesh->IsVisible();
    bOriginalTick = Mesh->PrimaryComponentTick.bStartWithTickEnabled;
    // Register only the real visual body. Capsule, movement, combat and AI remain
    // unregistered until the existing FinishSpawning path runs at its original time.
    Monster->SetActorHiddenInGame(false);
    Mesh->SetSkeletalMeshAsset(Monster->VisualMesh);
    Mesh->SetVisibleInSceneCaptureOnly(true);
    Mesh->SetHiddenInGame(false);
    Mesh->SetVisibility(true);
    Mesh->SetCastShadow(false);
    Mesh->SetAffectDynamicIndirectLighting(false);
    Mesh->SetVisibleInRayTracing(false);
    // Exclude this temporary view from other scene captures as well by staging far
    // below the level. It never contributes collision, shadows, GI or reflections.
    Mesh->SetRelativeLocation(OriginalRelativeTransform.GetLocation() + FVector(0, 0, -1000000.));
    Mesh->SetForcedLOD(1);
    Mesh->SetComponentTickEnabled(false);
    Mesh->RegisterComponentWithWorld(Monster->GetWorld());
    Mesh->PlayAnimation(Monster->IdleClip, false);
    Mesh->SetPosition(0.f, false);
    Mesh->TickAnimation(0.f, false);
    Mesh->RefreshBoneTransforms();
    Mesh->UpdateComponentToWorld();
    Mesh->MarkRenderDynamicDataDirty();
    Completion = MakeShared<FFacilityWarmupCompletion, ESPMode::ThreadSafe>();
    UFPSPerformanceMetricsSubsystem::RecordMarker(Monster, TEXT("Hall.GpuWarmupBegin"), Monster->GetPathName(), true);
}

FFacilityMonsterGpuWarmup::~FFacilityMonsterGpuWarmup()
{
    RestoreForActivation();
}

bool FFacilityMonsterGpuWarmup::Tick(bool bAllowSubmission)
{
    auto* Mesh = Body.Get();
    if (!Mesh || bRestored || !Completion) return false;
    if (IsReady()) { ReleaseCapture(); return false; }
    if (bSubmitted)
    {
        if (Completion->PollQueued.Exchange(true)) return false;
        const auto State = Completion;
        ENQUEUE_RENDER_COMMAND(FacilityWarmupPoll)([State](FRHICommandListImmediate&)
        {
            if (State->Fence.IsValid() && State->Fence->Poll()) State->Ready.Store(true);
            State->PollQueued.Store(false);
        });
        return false;
    }
    // Let normal end-of-frame updates register the render state. Do not block
    // the gameplay thread waiting for compilation, render commands or the GPU.
    if (!bAllowSubmission) { WaitReason = TEXT("budget_or_spawn_priority"); return false; }
    if (Mesh->IsPSOPrecaching()) { WaitReason = TEXT("pso_pending"); return false; }
    if (!Mesh->MeshObject || Mesh->IsRenderStateDirty())
    { WaitReason = TEXT("render_registration_pending"); return false; }
    // Waiting for a budget or PSO is not a failed attempt. This reservation is
    // bounded by the hall scheduler and consumed/cancelled at its real lifecycle
    // boundary; an elapsed wall-clock cutoff would strand it permanently.
    Target.Reset(NewObject<UTextureRenderTarget2D>(GetTransientPackage(), NAME_None, RF_Transient));
    Target->RenderTargetFormat = RTF_RGBA8;
    Target->InitAutoFormat(64, 64);
    Capture.Reset(NewObject<USceneCaptureComponent2D>(GetTransientPackage(), NAME_None, RF_Transient));
    Capture->TextureTarget = Target.Get();
    Capture->bCaptureEveryFrame = false;
    Capture->bCaptureOnMovement = false;
    Capture->bUseRayTracingIfEnabled = false;
    Capture->CaptureSource = SCS_SceneColorHDR;
    Capture->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->ShowOnlyComponent(Mesh);
    Capture->ShowFlags.SetLighting(false);
    Capture->ShowFlags.SetDynamicShadows(false);
    Capture->ShowFlags.SetPostProcessing(false);
    Capture->ShowFlags.SetAtmosphere(false);
    Capture->ShowFlags.SetFog(false);
    Capture->ShowFlags.SetVolumetricFog(false);
    Capture->ShowFlags.SetLumenGlobalIllumination(false);
    Capture->ShowFlags.SetLumenReflections(false);
    const FVector Center = Mesh->Bounds.Origin;
    Capture->SetWorldLocation(Center - FVector(FMath::Max(300., double(Mesh->Bounds.SphereRadius) * 3.), 0, 0));
    Capture->SetWorldRotation(FRotator::ZeroRotator);
    Capture->RegisterComponentWithWorld(Mesh->GetWorld());
    Capture->CaptureScene();
    const auto State = Completion;
    ENQUEUE_RENDER_COMMAND(FacilityWarmupFence)([State](FRHICommandListImmediate& RHICmdList)
    {
        State->Fence = RHICreateGPUFence(TEXT("FacilityStaffBodyWarmup"));
        RHICmdList.WriteGPUFence(State->Fence);
    });
    bSubmitted = true;
    return true;
}

bool FFacilityMonsterGpuWarmup::IsReady() const
{
    return Completion.IsValid() && Completion->Ready.Load();
}

FName FFacilityMonsterGpuWarmup::Stage() const
{
    if (bRestored) return TEXT("released");
    if (!Body.IsValid() || !Completion) return TEXT("unavailable");
    if (IsReady()) return TEXT("ready");
    if (bSubmitted) return TEXT("gpu_pending");
    return WaitReason;
}

void FFacilityMonsterGpuWarmup::Cancel()
{
    // The deferred owner is about to be destroyed. Do not restore its shadow,
    // GI and RT contribution only to enqueue another render-state teardown.
    bRestored = true;
    ReleaseCapture();
    Body.Reset();
}

void FFacilityMonsterGpuWarmup::ReleaseCapture()
{
    if (Capture.IsValid())
    {
        Capture->TextureTarget = nullptr;
        Capture->DestroyComponent();
        Capture.Reset();
    }
    if (Target.IsValid()) { Target->ReleaseResource(); Target.Reset(); }
}

void FFacilityMonsterGpuWarmup::RestoreForActivation()
{
    if (bRestored) return;
    bRestored = true;
    ReleaseCapture();
    if (auto* Mesh = Body.Get())
    {
        UFPSPerformanceMetricsSubsystem::RecordMarker(Mesh, TEXT("Hall.GpuWarmupEnd"),
            FString::Printf(TEXT("body=%s submitted=%d gpu_complete=%d scope=raster_skin_morph"), *Mesh->GetPathName(), bSubmitted, IsReady()), true);
        Mesh->SetRelativeTransform(OriginalRelativeTransform);
        Mesh->SetForcedLOD(OriginalForcedLOD);
        Mesh->SetVisibleInSceneCaptureOnly(bOriginalCaptureOnly);
        Mesh->SetCastShadow(bOriginalCastShadow);
        Mesh->SetAffectDynamicIndirectLighting(bOriginalAffectLighting);
        Mesh->SetVisibleInRayTracing(bOriginalRayTracing);
        Mesh->SetVisibility(bOriginalVisible);
        Mesh->SetHiddenInGame(bOriginalHidden);
        Mesh->SetComponentTickEnabled(bOriginalTick);
        // Keep this registered component. UE 5.8 render-state recreation transfers
        // its morph buffers and skin-cache entry; unregistering would discard them.
    }
}
