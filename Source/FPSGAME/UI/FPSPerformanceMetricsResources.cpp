#include "FPSPerformanceMetrics.h"

#include "../Monsters/FatZombieAnimInstance.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Dungeons/FacilityHallSpawnSubsystem.h"
#include "Animation/AnimSequence.h"
#include "Animation/MorphTarget.h"
#include "Async/Async.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "DynamicRHI.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "ProfilingDebugging/CountersTrace.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "RenderingThread.h"
#include "RHICommandList.h"
#include "RHIStats.h"
#include "SkeletalRenderPublic.h"

namespace FPSRenderResources
{
TAutoConsoleVariable<int32> Sampling(TEXT("fps.Perf.RenderResourceSampling"), 1,
    TEXT("Passively record published GPU memory and staff morph state at most twice per second."));
TRACE_DECLARE_INT_COUNTER(LocalBudget, TEXT("FPS/Resources/LocalBudgetBytes"));
TRACE_DECLARE_INT_COUNTER(LocalUsed, TEXT("FPS/Resources/LocalUsedBytes"));
TRACE_DECLARE_INT_COUNTER(LocalOverBudget, TEXT("FPS/Resources/LocalOverBudgetBytes"));
TRACE_DECLARE_INT_COUNTER(StaffActiveMorphs, TEXT("FPS/Resources/ObservedStaffActiveMorphs"));
TRACE_DECLARE_INT_COUNTER(MonstersAlive, TEXT("FPS/Resources/MonstersAlive"));
TRACE_DECLARE_INT_COUNTER(MonstersPrepared, TEXT("FPS/Resources/MonstersNotBegunPlay"));
TRACE_DECLARE_INT_COUNTER(HallPendingSpawns, TEXT("FPS/Resources/HallPendingSpawns"));

constexpr int32 MaxStaff = 64;
constexpr int32 MaxMorphDetails = 8;

struct FStaff
{
    FString Path, Asset, Clip, OutgoingClip;
    bool bParallelEvaluation = false, bVisible = false, bMorphsKnown = false, bAnimationKnown = false;
    int32 CapturedCurves = -1;
    float BlendAlpha = 1.f;
    struct FMorph { FString Name; int32 Index; float Weight; };
    TArray<FMorph> Morphs;
    // Used only by the immediately enqueued render command, never by the RHI callback.
    const FSkeletalMeshObject* MeshObject = nullptr;
    uint64 MeshHandle = 0, SkinCacheHandle = 0;
    int32 Lod = INDEX_NONE, Vertices = 0, Sections = 0, StoredMorphs = 0;
    uint32 AllMorphBatches = 0, ActiveMorphBatches = 0;
    uint64 MorphBufferBytes = 0;
    bool bRenderDataKnown = false, bSkinCacheKnown = false, bSeparateRayTracingCache = false;
};

struct FSample
{
    double GameSeconds = 0, RenderSeconds = 0, RhiSeconds = 0, GatherMs = 0;
    uint64 GameFrame = 0, RenderFrame = 0;
    int32 StaffCount = 0;
    int32 PreparedInstances = 0, PendingSpawns = 0;
    FName PreparationDecision;
    struct FMonsterCounts { int32 Alive=0,Dead=0,Prepared=0,Simulating=0,MeshTick=0; };
    TMap<FString,FMonsterCounts> Monsters;
    TArray<FStaff> Staff;
    FRHIMemoryStats Memory;
};

void SetMemorySegment(FJsonObject& Row, const TCHAR* Name, uint64 Budget, uint64 Used,
    uint64 Available, uint64 OverBudget)
{
    if (Budget == 0)
    {
        Row.SetField(Name, MakeShared<FJsonValueNull>());
        return;
    }
    const auto Segment = MakeShared<FJsonObject>();
    Segment->SetNumberField(TEXT("budget_bytes"), static_cast<double>(Budget));
    Segment->SetNumberField(TEXT("used_bytes"), static_cast<double>(Used));
    Segment->SetNumberField(TEXT("available_bytes"), static_cast<double>(Available));
    Segment->SetNumberField(TEXT("over_budget_bytes"), static_cast<double>(OverBudget));
    Row.SetObjectField(Name, Segment);
}
}

void UFPSPerformanceMetricsSubsystem::SampleRenderResources(double Now)
{
    using namespace FPSRenderResources;
    if (!Sampling.GetValueOnGameThread() || bRenderResourceSamplePending || Now < NextRenderResourceSampleSeconds
        || !GDynamicRHI || GetWorld()->GetNetMode() == NM_DedicatedServer)
        return;

    NextRenderResourceSampleSeconds = Now + 0.5;
    bRenderResourceSamplePending = true;
    const uint64 Generation = CaptureGeneration;
    const TWeakObjectPtr<UFPSPerformanceMetricsSubsystem> WeakThis(this);
    const auto Sample = MakeShared<FSample, ESPMode::ThreadSafe>();
    Sample->GameSeconds = FPlatformTime::Seconds();
    Sample->GameFrame = GFrameCounter;
    if (const auto* Spawns=GetWorld()->GetSubsystem<UFacilityHallSpawnSubsystem>())
    {
        Sample->PreparedInstances=Spawns->PreparedCount();
        Sample->PendingSpawns=Spawns->PendingCount();
        Sample->PreparationDecision=Spawns->PreparationLastDecision();
    }
    for (TActorIterator<ACharacter> It(GetWorld()); It; ++It)
    {
        const auto* Combat=It->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat)continue;
        auto& Counts=Sample->Monsters.FindOrAdd(It->GetClass()->GetPathName());
        if(!It->HasActorBegunPlay())++Counts.Prepared;
        else if(Combat->IsDead())++Counts.Dead;
        else ++Counts.Alive;
        if(const auto* Body=It->GetMesh())
        {
            Counts.Simulating+=Body->IsSimulatingPhysics();
            Counts.MeshTick+=Body->IsComponentTickEnabled()&&Body->IsRegistered();
        }
        if (!It->ActorHasTag(TEXT("FacelessResearcher")) && !It->ActorHasTag(TEXT("FacelessReceptionist")))
            continue;
        ++Sample->StaffCount;
        if (Sample->Staff.Num() >= MaxStaff) continue;
        USkeletalMeshComponent* Mesh = It->GetMesh();
        if (!Mesh) continue;
        FStaff& Staff = Sample->Staff.AddDefaulted_GetRef();
        Staff.Path = Mesh->GetPathName();
        Staff.Asset = GetPathNameSafe(Mesh->GetSkeletalMeshAsset());
        Staff.bVisible = Mesh->IsVisible();
        Staff.bParallelEvaluation = Mesh->IsRunningParallelEvaluation();
        Staff.MeshObject = Mesh->GetMeshObject();
        Staff.MeshHandle = reinterpret_cast<UPTRINT>(Staff.MeshObject);
        // Never wait for parallel animation to inspect its mutable results/proxy.
        if (Staff.bParallelEvaluation) continue;
        Staff.bMorphsKnown = true;
        for (const auto& Morph : Mesh->ActiveMorphTargets)
        {
            if (!Morph.Key || !Mesh->MorphTargetWeights.IsValidIndex(Morph.Value)) continue;
            const float Weight = Mesh->MorphTargetWeights[Morph.Value];
            if (Weight != 0.f)
                Staff.Morphs.Add({Morph.Key->GetName(), Morph.Value, Weight});
        }
        if (const auto* Anim = Cast<UFatZombieAnimInstance>(Mesh->GetAnimInstance()))
        {
            Staff.bAnimationKnown = true;
            Staff.Clip = GetPathNameSafe(Anim->ActiveClip);
            Staff.OutgoingClip = GetPathNameSafe(Anim->OutgoingLoop);
            Staff.BlendAlpha = Anim->BlendAlpha;
            Staff.CapturedCurves = Anim->GetCapturedClothingCurveCount();
        }
    }
    Sample->GatherMs = (FPlatformTime::Seconds() - Sample->GameSeconds) * 1000.0;

    ENQUEUE_RENDER_COMMAND(FPSObserveStaffRenderResources)(
        [Sample, WeakThis, Generation](FRHICommandListImmediate& RHICmdList)
        {
            Sample->RenderSeconds = FPlatformTime::Seconds();
            Sample->RenderFrame = GFrameNumberRenderThread;
            // Mesh-object destruction is also ordered on the render command queue.
            for (FStaff& Staff : Sample->Staff)
            {
                const FSkeletalMeshObject* Object = Staff.MeshObject;
                Staff.MeshObject = nullptr;
                if (!Object) continue;
                Staff.Lod = Object->GetLOD();
                const auto& RenderData = Object->GetSkeletalMeshRenderData();
                if (RenderData.LODRenderData.IsValidIndex(Staff.Lod))
                {
                    const auto& Lod = RenderData.LODRenderData[Staff.Lod];
                    Staff.bRenderDataKnown = true;
                    Staff.Vertices = Lod.GetNumVertices();
                    Staff.Sections = Lod.RenderSections.Num();
                    const auto& Morphs = Lod.MorphTargetVertexInfoBuffers;
                    Staff.StoredMorphs = Morphs.GetNumMorphs();
                    Staff.AllMorphBatches = Morphs.GetNumBatches();
                    Staff.MorphBufferBytes = Morphs.MorphDataBuffer.IsValid() ? Morphs.MorphDataBuffer->GetSize() : 0;
                    for (const auto& Morph : Staff.Morphs)
                        if (Morph.Index >= 0 && Morph.Index < Staff.StoredMorphs)
                            Staff.ActiveMorphBatches += Morphs.GetNumBatches(Morph.Index);
                }
#if RHI_RAYTRACING
                Staff.bSkinCacheKnown = true;
                Staff.bSeparateRayTracingCache = Object->ShouldUseSeparateSkinCacheEntryForRayTracing();
                Staff.SkinCacheHandle = reinterpret_cast<UPTRINT>(Object->GetSkinCacheEntryForRayTracing());
#endif
            }
            // D3D12 publishes these counters at RHI EndFrame. Read in that same
            // command stream; never flush or query/update texture-streaming state.
            RHICmdList.EnqueueLambda([Sample, WeakThis, Generation](FRHICommandListBase&)
            {
                Sample->RhiSeconds = FPlatformTime::Seconds();
                if (GDynamicRHI) RHIGetMemoryStats(Sample->Memory);
                AsyncTask(ENamedThreads::GameThread, [Sample, WeakThis, Generation]
                {
                    UFPSPerformanceMetricsSubsystem* Self = WeakThis.Get();
                    if (!Self || Self->CaptureGeneration != Generation) return;
                    Self->bRenderResourceSamplePending = false;
                    Self->RenderBudgetBytes = Sample->Memory.BudgetLocal;
                    Self->RenderUsedBytes = Sample->Memory.UsedLocal;
                    Self->RenderBudgetSeconds = Sample->RhiSeconds;
                    if (!Self->bRecording) return;
                    const double PublishStart = FPlatformTime::Seconds();
                    const auto Row = MakeShared<FJsonObject>();
                    Row->SetNumberField(TEXT("game_seconds"), Sample->GameSeconds);
                    Row->SetNumberField(TEXT("render_seconds"), Sample->RenderSeconds);
                    Row->SetNumberField(TEXT("rhi_seconds"), Sample->RhiSeconds);
                    Row->SetNumberField(TEXT("completed_seconds"), PublishStart);
                    Row->SetStringField(TEXT("game_frame"), LexToString(Sample->GameFrame));
                    Row->SetStringField(TEXT("render_frame"), LexToString(Sample->RenderFrame));
                    Row->SetNumberField(TEXT("game_gather_ms"), Sample->GatherMs);
                    Row->SetNumberField(TEXT("async_latency_ms"), (PublishStart - Sample->GameSeconds) * 1000.0);
                    Row->SetBoolField(TEXT("memory_valid"), Sample->Memory.IsValid());
                    SetMemorySegment(*Row, TEXT("local_memory"), Sample->Memory.BudgetLocal, Sample->Memory.UsedLocal,
                        Sample->Memory.AvailableLocal, Sample->Memory.DemotedLocal);
                    SetMemorySegment(*Row, TEXT("system_memory"), Sample->Memory.BudgetSystem, Sample->Memory.UsedSystem,
                        Sample->Memory.AvailableSystem, Sample->Memory.DemotedSystem);
                    if (Sample->Memory.BudgetLocal)
                    {
                        TRACE_COUNTER_SET(LocalBudget, Sample->Memory.BudgetLocal);
                        TRACE_COUNTER_SET(LocalUsed, Sample->Memory.UsedLocal);
                        TRACE_COUNTER_SET(LocalOverBudget, Sample->Memory.DemotedLocal);
                    }
                    Row->SetNumberField(TEXT("staff_count"), Sample->StaffCount);
                    Row->SetNumberField(TEXT("hall_prepared_instances"), Sample->PreparedInstances);
                    Row->SetNumberField(TEXT("hall_pending_spawn_requests"), Sample->PendingSpawns);
                    Row->SetStringField(TEXT("hall_preparation_last_decision"), Sample->PreparationDecision.ToString());
                    TArray<TSharedPtr<FJsonValue>> MonsterRows;
                    int32 Alive=0,Dead=0,Prepared=0,Simulating=0;
                    for(const auto& Pair:Sample->Monsters)
                    {
                        auto Counts=MakeShared<FJsonObject>();Counts->SetStringField(TEXT("class"),Pair.Key);
                        Counts->SetNumberField(TEXT("alive"),Pair.Value.Alive);Counts->SetNumberField(TEXT("dead"),Pair.Value.Dead);
                        Counts->SetNumberField(TEXT("not_begun_play"),Pair.Value.Prepared);
                        Counts->SetNumberField(TEXT("body_simulating_physics"),Pair.Value.Simulating);
                        Counts->SetNumberField(TEXT("registered_body_tick_enabled"),Pair.Value.MeshTick);
                        MonsterRows.Add(MakeShared<FJsonValueObject>(Counts));
                        Alive+=Pair.Value.Alive;Dead+=Pair.Value.Dead;Prepared+=Pair.Value.Prepared;Simulating+=Pair.Value.Simulating;
                    }
                    Row->SetArrayField(TEXT("monster_classes"),MonsterRows);
                    Row->SetNumberField(TEXT("monsters_alive"),Alive);Row->SetNumberField(TEXT("monsters_dead"),Dead);
                    Row->SetNumberField(TEXT("monsters_not_begun_play"),Prepared);
                    TRACE_COUNTER_SET(MonstersAlive, Alive);
                    TRACE_COUNTER_SET(MonstersPrepared, Prepared);
                    TRACE_COUNTER_SET(HallPendingSpawns, Sample->PendingSpawns);
                    Row->SetNumberField(TEXT("monster_bodies_simulating_physics"),Simulating);
                    Row->SetBoolField(TEXT("staff_details_truncated"), Sample->StaffCount > Sample->Staff.Num());
                    TArray<TSharedPtr<FJsonValue>> StaffRows;
                    TMap<FString, FObservedRenderHandles> CurrentHandles;
                    int32 ObservedMorphs = 0;
                    for (const FStaff& Staff : Sample->Staff)
                    {
                        const auto Item = MakeShared<FJsonObject>();
                        Item->SetStringField(TEXT("component"), Staff.Path);
                        Item->SetStringField(TEXT("asset"), Staff.Asset);
                        Item->SetBoolField(TEXT("visible_flag"), Staff.bVisible);
                        Item->SetBoolField(TEXT("parallel_evaluation_pending"), Staff.bParallelEvaluation);
                        if (Staff.bAnimationKnown)
                        {
                            Item->SetStringField(TEXT("active_clip"), Staff.Clip);
                            Item->SetStringField(TEXT("outgoing_clip"), Staff.OutgoingClip);
                            Item->SetNumberField(TEXT("transition_alpha"), Staff.BlendAlpha);
                        }
                        else
                        {
                            Item->SetField(TEXT("active_clip"), MakeShared<FJsonValueNull>());
                            Item->SetField(TEXT("outgoing_clip"), MakeShared<FJsonValueNull>());
                            Item->SetField(TEXT("transition_alpha"), MakeShared<FJsonValueNull>());
                        }
                        if (Staff.CapturedCurves >= 0)
                            Item->SetNumberField(TEXT("captured_clothing_curves"), Staff.CapturedCurves);
                        else Item->SetField(TEXT("captured_clothing_curves"), MakeShared<FJsonValueNull>());
                        if (Staff.bMorphsKnown)
                        {
                            ObservedMorphs += Staff.Morphs.Num();
                            Item->SetNumberField(TEXT("active_morph_count"), Staff.Morphs.Num());
                            TArray<TSharedPtr<FJsonValue>> MorphRows;
                            for (int32 I = 0; I < FMath::Min(Staff.Morphs.Num(), MaxMorphDetails); ++I)
                            {
                                const auto MorphRow = MakeShared<FJsonObject>();
                                MorphRow->SetStringField(TEXT("name"), Staff.Morphs[I].Name);
                                MorphRow->SetNumberField(TEXT("index"), Staff.Morphs[I].Index);
                                MorphRow->SetNumberField(TEXT("weight"), Staff.Morphs[I].Weight);
                                MorphRows.Add(MakeShared<FJsonValueObject>(MorphRow));
                            }
                            Item->SetArrayField(TEXT("active_morphs"), MorphRows);
                            Item->SetBoolField(TEXT("morph_details_truncated"), Staff.Morphs.Num() > MaxMorphDetails);
                        }
                        else Item->SetField(TEXT("active_morph_count"), MakeShared<FJsonValueNull>());
                        if (Staff.bRenderDataKnown)
                        {
                            Item->SetNumberField(TEXT("observed_render_lod"), Staff.Lod);
                            Item->SetNumberField(TEXT("lod_vertices"), Staff.Vertices);
                            Item->SetNumberField(TEXT("lod_sections"), Staff.Sections);
                            Item->SetNumberField(TEXT("stored_morph_count"), Staff.StoredMorphs);
                            Item->SetNumberField(TEXT("stored_morph_batches"), Staff.AllMorphBatches);
                            Item->SetNumberField(TEXT("shared_morph_buffer_logical_bytes"), static_cast<double>(Staff.MorphBufferBytes));
                            if (Staff.bMorphsKnown)
                                Item->SetNumberField(TEXT("observed_active_morph_batches"), Staff.ActiveMorphBatches);
                            else Item->SetField(TEXT("observed_active_morph_batches"), MakeShared<FJsonValueNull>());
                        }
                        else Item->SetField(TEXT("observed_render_lod"), MakeShared<FJsonValueNull>());
                        const FObservedRenderHandles* Previous = Self->PreviousRenderHandles.Find(Staff.Path);
                        Item->SetBoolField(TEXT("render_object_present"), Staff.MeshHandle != 0);
                        if (Previous)
                            Item->SetBoolField(TEXT("render_object_changed_since_sample"), Previous->Mesh != Staff.MeshHandle);
                        else Item->SetField(TEXT("render_object_changed_since_sample"), MakeShared<FJsonValueNull>());
                        if (Staff.bSkinCacheKnown)
                        {
                            Item->SetBoolField(TEXT("rt_skin_cache_entry_present"), Staff.SkinCacheHandle != 0);
                            Item->SetBoolField(TEXT("rt_skin_cache_separate"), Staff.bSeparateRayTracingCache);
                            if (Previous)
                                Item->SetBoolField(TEXT("rt_skin_cache_entry_changed_since_sample"), Previous->SkinCache != Staff.SkinCacheHandle);
                            else Item->SetField(TEXT("rt_skin_cache_entry_changed_since_sample"), MakeShared<FJsonValueNull>());
                        }
                        else Item->SetField(TEXT("rt_skin_cache_entry_present"), MakeShared<FJsonValueNull>());
                        CurrentHandles.Add(Staff.Path, {Staff.MeshHandle, Staff.SkinCacheHandle});
                        StaffRows.Add(MakeShared<FJsonValueObject>(Item));
                    }
                    TRACE_COUNTER_SET(StaffActiveMorphs, ObservedMorphs);
                    Row->SetArrayField(TEXT("staff"), StaffRows);
                    Self->PreviousRenderHandles = MoveTemp(CurrentHandles);
                    Row->SetNumberField(TEXT("game_publish_ms"), (FPlatformTime::Seconds() - PublishStart) * 1000.0);
                    if (Self->RenderResourceSamples.Num() < MaxRenderResourceSamples)
                        Self->RenderResourceSamples.Add(Row);
                    else
                    {
                        Self->RenderResourceSamples[Self->RenderResourceWriteIndex] = Row;
                        Self->RenderResourceWriteIndex = (Self->RenderResourceWriteIndex + 1) % MaxRenderResourceSamples;
                        ++Self->RenderResourceSamplesOverwritten;
                    }
                });
            });
        });
}
