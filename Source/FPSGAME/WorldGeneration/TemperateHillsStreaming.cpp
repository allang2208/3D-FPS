#include "TemperateHillsWorld.h"
#include "EastRiverRoad.h"
#include "HillsFixedTerrainCells.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "TemperateHillsMap.h"
#include "TemperateHillsQuarryTravel.h"
#include "HillsNightRaidSubsystem.h"
#include "VT/RuntimeVirtualTexture.h"
#include "TemperateHillsChapel.h"
#include "HillsTavernInterior.h"
#include "TemperateHillsPCG.h"
#include "TemperateHillsVisibility.h"
#include "TemperateHillsSurface.h"
#include "TemperateForestHabitat.h"
#include "../FPSWeatherManager.h"
#include "../Production/ProductionOreRocks.h"
#include "TemperateHillsBackdrop.h"
#include "TemperateHillsGroundLayers.h"
#include "RiverPilotFXSubsystem.h"
#include "NiagaraSystem.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Async/Async.h"
#include "Algo/AllOf.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Animation/TransformProviderData.h"
#include "Components/CapsuleComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "RHIGlobals.h"
#include "HAL/IConsoleManager.h"
#include "PCGGraph.h"
#include "PCGComponent.h"
#include "PCGWorldActor.h"
#include "RuntimeGen/PCGGenSourceManager.h"
#include "PCGGraphExecutionStateInterface.h"
#include "Subsystems/PCGSubsystem.h"
#include "ContentStreaming.h"
#include "RenderCommandFence.h"
#include "Misc/ScopeExit.h"

#include "TemperateHillsStreamingPrivate.h"
namespace HillsStreaming
{
// Streaming CVars are process-wide, including when several PIE worlds coexist.
static int32 BudgetWorldCount=0;
static int32 PreparingWorldCount=0;
static bool EntryBudgetActive=false;
static TArray<IConsoleVariable*> BudgetOverrides;
static const FName BudgetTag(TEXT("FPSGAME.HillsStreaming"));
static int32 GHillsQualityPreset = 1;
static FAutoConsoleVariableRef CVarHillsQualityPreset(
    TEXT("fps.Hills.QualityPreset"),
    GHillsQualityPreset,
    TEXT("Hills runtime quality preset: 0 = Epic baseline, 1 = Balanced TSR 75% + tuned Lumen (default), 2 = High-FPS Software Lumen."),
    ECVF_Default);
static TArray<IConsoleVariable*> QualityOverrides;
static const FName QualityTag(TEXT("FPSGAME.HillsQualityPreset"));
static int32 AppliedQualityPreset = -1;
static bool bQualityCallbackBound = false;

void UnsetQualityPreset()
{
    for(auto* C:QualityOverrides)if(C)C->Unset(ECVF_SetByPluginLowPriority,QualityTag);
    QualityOverrides.Reset();
    AppliedQualityPreset = -1;
}

void ApplyQualityPreset(bool bForce=false)
{
    if(BudgetWorldCount<=0 || IsRunningCommandlet() || GUsingNullRHI || IsRunningDedicatedServer())
    {
        if(!QualityOverrides.IsEmpty())UnsetQualityPreset();
        return;
    }
    const int32 Preset = FMath::Clamp(GHillsQualityPreset, 0, 2);
    if(!bForce && Preset == AppliedQualityPreset)return;
    UnsetQualityPreset();
    AppliedQualityPreset = Preset;
    if(Preset == 0)
    {
        UE_LOG(LogTemp,Display,TEXT("HILLS_QUALITY preset=0 (Epic baseline restored)"));
        return;
    }
    struct FQualitySetting { const TCHAR* Key; bool bInt; int32 IntVal; float FloatVal; };
    TArray<FQualitySetting> Settings = {
        {TEXT("r.ScreenPercentage"), false, 0, 75.f},
        {TEXT("r.TSR.History.ScreenPercentage"), false, 0, 100.f},
        {TEXT("r.Lumen.ScreenProbeGather.DownsampleFactor"), true, 32, 0.f},
        {TEXT("r.Lumen.ScreenProbeGather.RadianceCache.ProbeResolution"), true, 16, 0.f},
        {TEXT("r.Lumen.ScreenProbeGather.RadianceCache.NumProbesToTraceBudget"), true, 100, 0.f},
        {TEXT("r.Lumen.ScreenProbeGather.ShortRangeAO.DownsampleFactor"), true, 2, 0.f},
        {TEXT("r.Lumen.ScreenProbeGather.TwoSidedFoliageBackfaceDiffuse"), true, 0, 0.f},
        {TEXT("r.Lumen.HardwareRayTracing.HitLighting.Allowed"), true, 0, 0.f},
        {TEXT("r.LumenScene.SurfaceCache.AtlasSize"), true, 3584, 0.f},
        {TEXT("r.LumenScene.DirectLighting.UpdateFactor"), true, 64, 0.f},
        {TEXT("r.LumenScene.Radiosity.UpdateFactor"), true, 128, 0.f},
        {TEXT("r.Lumen.Reflections.DownsampleFactor"), true, 2, 0.f},
        {TEXT("r.Lumen.Reflections.MaxRoughnessToTraceForFoliage"), false, 0, 0.2f},
        {TEXT("r.Lumen.ScreenProbeGather.MaxRoughnessToEvaluateRoughSpecularForFoliage"), false, 0, 0.4f},
        // UE 5.8 enables CAS VRS (5.52 ms AsyncCompute) and uses 300 m RT culling by default; disable CAS VRS and tighten RT scene radius.
        {TEXT("r.VRS.ContrastAdaptiveShading"), true, 0, 0.f},
        {TEXT("r.VRS.EnableSoftware"), true, 0, 0.f},
        {TEXT("r.RayTracing.Culling"), true, 3, 0.f},
        {TEXT("r.RayTracing.Culling.Radius"), false, 0, Preset == 2 ? 10000.f : 15000.f},
        {TEXT("r.RayTracing.Culling.Angle"), false, 0, Preset == 2 ? 3.0f : 2.0f},
        {TEXT("r.RayTracing.Geometry.LandscapeGrass"), true, 0, 0.f},
        {TEXT("r.LocalFogVolume.HalfResolution"), true, 1, 0.f},
        {TEXT("r.TSR.History.UpdateQuality"), true, 2, 0.f},
        {TEXT("r.TSR.RejectionAntiAliasingQuality"), true, 1, 0.f},
    };
    if(Preset == 2)
    {
        Settings.Add({TEXT("r.Lumen.HardwareRayTracing"), true, 0, 0.f});
        Settings.Add({TEXT("r.Nanite.MaxPixelsPerEdge"), false, 0, 1.5f});
    }
    for(const FQualitySetting& Setting : Settings)
    {
        if(auto* C = IConsoleManager::Get().FindConsoleVariable(Setting.Key))
        {
            QualityOverrides.AddUnique(C);
            if(Setting.bInt) C->Set(Setting.IntVal, ECVF_SetByPluginLowPriority, QualityTag);
            else C->Set(Setting.FloatVal, ECVF_SetByPluginLowPriority, QualityTag);
        }
        else
        {
            UE_LOG(LogTemp,Warning,TEXT("HILLS_QUALITY missing cvar=%s"),Setting.Key);
        }
    }
    const auto* ScreenPct = IConsoleManager::Get().FindConsoleVariable(TEXT("r.ScreenPercentage"));
    const auto* HWRT = IConsoleManager::Get().FindConsoleVariable(TEXT("r.Lumen.HardwareRayTracing"));
    const auto* Downsample = IConsoleManager::Get().FindConsoleVariable(TEXT("r.Lumen.ScreenProbeGather.DownsampleFactor"));
    const auto* CAS = IConsoleManager::Get().FindConsoleVariable(TEXT("r.VRS.ContrastAdaptiveShading"));
    const auto* RTCullRadius = IConsoleManager::Get().FindConsoleVariable(TEXT("r.RayTracing.Culling.Radius"));
    const auto* LFVHalf = IConsoleManager::Get().FindConsoleVariable(TEXT("r.LocalFogVolume.HalfResolution"));
    const auto* TSRUpdateQ = IConsoleManager::Get().FindConsoleVariable(TEXT("r.TSR.History.UpdateQuality"));
    const auto* NaniteEdge = IConsoleManager::Get().FindConsoleVariable(TEXT("r.Nanite.MaxPixelsPerEdge"));
    UE_LOG(LogTemp,Display,TEXT("HILLS_QUALITY preset=%d screen_pct=%.0f hwrt=%d downsample=%d cas=%d rt_rad=%.0f lfv_half=%d tsr_uq=%d nanite_edge=%.2f"),
        Preset,
        ScreenPct ? ScreenPct->GetFloat() : 0.f,
        HWRT ? HWRT->GetInt() : -1,
        Downsample ? Downsample->GetInt() : -1,
        CAS ? CAS->GetInt() : -1,
        RTCullRadius ? RTCullRadius->GetFloat() : -1.f,
        LFVHalf ? LFVHalf->GetInt() : -1,
        TSRUpdateQ ? TSRUpdateQ->GetInt() : -1,
        NaniteEdge ? NaniteEdge->GetFloat() : -1.f);
}

void UpdateStreamingBudget(bool Force=false)
{
    // Only spend more time while every hills world is behind its entry overlay.
    // A second PIE player loading must not increase an already playing world's budget.
    const bool Entry=BudgetWorldCount>0&&PreparingWorldCount==BudgetWorldCount;
    if(!Force&&Entry==EntryBudgetActive)return;
    EntryBudgetActive=Entry;
    for(const auto& Setting:TArray<TPair<const TCHAR*,float>>{
        {TEXT("pcg.FrameTime"),Entry?6.f:2.f},{TEXT("pcg.RuntimeGeneration.NumGeneratingComponents"),8.f},
        {TEXT("s.AsyncLoadingTimeLimit"),Entry?8.f:2.f},{TEXT("s.LevelStreamingActorsUpdateTimeLimit"),Entry?4.f:2.f},{TEXT("s.UnregisterComponentsTimeLimit"),1.f}})
        if(auto* C=IConsoleManager::Get().FindConsoleVariable(Setting.Key))
        {
            // UE 5.8 reports SETBY_ERROR for constructor-only ReplaceCurrent. A tagged
            // layer also restores the actual previous priority/value on last-world
            // exit, without overwriting a console/device-profile override.
            BudgetOverrides.AddUnique(C);
            C->Set(Setting.Value,ECVF_SetByPluginLowPriority,BudgetTag);
            UE_LOG(LogTemp,Display,TEXT("HILLS_BUDGET phase=%s cvar=%s requested=%.1f effective=%.1f"),
                Entry?TEXT("entry"):TEXT("streaming"),Setting.Key,Setting.Value,C->GetFloat());
        }
}

void AcquireStreamingBudget()
{
    if(!bQualityCallbackBound)
    {
        bQualityCallbackBound=true;
        CVarHillsQualityPreset->SetOnChangedCallback(FConsoleVariableDelegate::CreateLambda([](IConsoleVariable*){ApplyQualityPreset(true);}));
    }
    ++BudgetWorldCount;++PreparingWorldCount;
    UpdateStreamingBudget(BudgetWorldCount==1);
    ApplyQualityPreset(BudgetWorldCount==1);
}

void FinishEntryBudgetIfReady(bool& Preparing,bool Ready,bool Failed,const UTransitLoadingSubsystem* Loading)
{
    if(!Preparing || (!Failed && (!Ready || (Loading && Loading->IsHoldingGameplayInput()))))return;
    Preparing=false;
    --PreparingWorldCount;
    UpdateStreamingBudget();
}

void ReleaseStreamingBudget(bool Preparing)
{
    if(Preparing)--PreparingWorldCount;
    if(--BudgetWorldCount!=0){UpdateStreamingBudget();return;}
    for(auto* C:BudgetOverrides)C->Unset(ECVF_SetByPluginLowPriority,BudgetTag);
    BudgetOverrides.Reset();EntryBudgetActive=false;
    UnsetQualityPreset();
}

}
#if !UE_BUILD_SHIPPING
#include "TemperateHillsVisitQuarry.inl"
#endif

void ATemperateHillsWorld::BeginStreaming()
{
    Streaming=MakeShared<FTemperateHillsStreamingState>();
    auto& S=*Streaming;
#if !UE_BUILD_SHIPPING
    S.bVillageVisit=HasAuthority()&&GetWorld()->URL.HasOption(TEXT("VisitVillage"));
#endif
    DetailRadiusMeters=FMath::Clamp(DetailRadiusMeters,96.f,256.f);
    ViewRadiusMeters=FMath::Clamp(ViewRadiusMeters,DetailRadiusMeters+96.f,512.f);
    const double Half=SizeMeters*50;
    const FVector Start=GetGenerationAnchor();
    {
        const bool HasRiver=!Assets->RiverMaterial.IsNull();
        const bool FixedLayout=HasRiver && GeneratorVersion==TemperateHillsMap::GeneratorVersion && Seed==TemperateHillsMap::Seed
            && TemperateHillsChapel::IsChapelWorld(GetWorld());
        S.RiverPending=true;
        S.RiverJob=Async(EAsyncExecution::ThreadPool,[WorldSeed=Seed,Half,Spawn=FVector2D(Start),Relief=Assets->RiverBankReliefCm,Version=GeneratorVersion,HasRiver,FixedLayout,Ecology=EcologyProfile()]() -> TemperateHillsFixedLayout::FLayout
        {
            if(FixedLayout)
            {
                auto Layout=TemperateHillsFixedLayout::Load(WorldSeed,Version,Half,Spawn,Ecology);
                if(Layout.River)return Layout;
                UE_LOG(LogTemp,Warning,TEXT("HILLS_LAYOUT fixed data unavailable for seed=%d size_m=%.0f anchor=%s; reconstructing this layout"),WorldSeed,Half/50.,*Spawn.ToString());
            }
            if(HasRiver)return {TemperateRiver::Generate(WorldSeed,Half,Spawn,Relief,Version,Ecology),{},{}};
            auto Plan=MakeShared<TemperateRiver::FPlan,ESPMode::ThreadSafe>();
            Plan->Ecology=Ecology;
            Plan->GenerationVersion=Version;Plan->BuildRainforest(WorldSeed,Half);return {Plan,{},{}};
        });
    }
    // Entry cells are selected after the village/chapel plan exists.
    HillsStreaming::AcquireStreamingBudget();
    S.LoadingAssets=true;
    // Repair the pilot's original package-only references if an editor saved them
    // on a placed actor. A package can load successfully without being the typed asset.
    if(RiverPilotMaterial.ToSoftObjectPath()==FSoftObjectPath(TEXT("/Game/Fluids/RiverPilot20260923/M_RiverPilot")))
        RiverPilotMaterial=GetDefault<ATemperateHillsWorld>()->RiverPilotMaterial;
    if(RiverPilotSplash.ToSoftObjectPath()==FSoftObjectPath(TEXT("/Game/Fluids/RiverPilot20260923/NS_RiverBulletSplash")))
        RiverPilotSplash=GetDefault<ATemperateHillsWorld>()->RiverPilotSplash;
    TArray<FSoftObjectPath> SurfacePaths={Assets->GroundMaterial.ToSoftObjectPath(),ForestPondMaterial.ToSoftObjectPath()};
    const bool bHasVillage = TemperateHillsChapel::IsChapelWorld(GetWorld());
    if(bHasVillage && Seed==TemperateHillsMap::Seed && GeneratorVersion==TemperateHillsMap::GeneratorVersion)
        EastRiverRoad::AddSurfacePaths(SurfacePaths);
    S.StaggerVillageEntry=bHasVillage;
    if(bHasVillage)
    {
        TemperateHillsChapel::AddMeshPaths(SurfacePaths);
        FHillsTavernInterior::AddBlockingMeshPaths(SurfacePaths);
    }
    if(!Assets->VillageColorCache.IsNull())SurfacePaths.Add(Assets->VillageColorCache.ToSoftObjectPath());
    if(!Assets->VillageHeightCache.IsNull())SurfacePaths.Add(Assets->VillageHeightCache.ToSoftObjectPath());
    if(!Assets->RiverMaterial.IsNull())
    {
        SurfacePaths.Add(Assets->RiverMaterial.ToSoftObjectPath());
        SurfacePaths.Add(RiverPilotMaterial.ToSoftObjectPath());
        SurfacePaths.Add(RiverPilotSplash.ToSoftObjectPath());
    }
    if(!Assets->BackdropMaterial.IsNull())SurfacePaths.Add(Assets->BackdropMaterial.ToSoftObjectPath());
    // The retired hills cloud layer and HDR day/night backdrop are no longer
    // presented (UDS owns the sky); neither asset is streamed anymore.
    auto OnSurfaceLoaded=FStreamableDelegate::CreateWeakLambda(this,[this,bHasVillage]()
    {
        if(!Streaming||Streaming->Stopping)return;
        Streaming->LoadingAssets=false;
        if(bHasVillage && !FHillsTavernInterior::AreBlockingMeshesLoaded())
        {
            Streaming->Failed=true;
            if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
                Loading->FailPreparation(FText::FromString(TEXT("村庄酒馆碰撞资源加载失败，请返回主场景后重试。")));
            return;
        }
        // Check the actual typed objects, not just completion of the package load.
        if(!Assets->RiverMaterial.IsNull()&&(!RiverPilotMaterial.Get()||!RiverPilotSplash.Get()))
        {
            Streaming->Failed=true;
            UE_LOG(LogTemp,Error,TEXT("RIVER_PILOT load failed material=%s resolved=%s splash=%s resolved=%s"),
                *RiverPilotMaterial.ToString(),*GetPathNameSafe(RiverPilotMaterial.Get()),
                *RiverPilotSplash.ToString(),*GetPathNameSafe(RiverPilotSplash.Get()));
            if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
                Loading->FailPreparation(FText::FromString(TEXT("河流特效资源加载失败，请返回主场景后重试。")));
            return;
        }
        if(auto* Ground=Assets->GroundMaterial.Get();Ground&&ForestPondMaterial.IsValid()&&(Assets->RiverMaterial.IsNull()||Assets->RiverMaterial.IsValid())&&
            (Assets->BackdropMaterial.IsNull()||Assets->BackdropMaterial.IsValid())&&
            (!TemperateHillsChapel::IsChapelWorld(GetWorld())||Seed!=TemperateHillsMap::Seed||GeneratorVersion!=TemperateHillsMap::GeneratorVersion||EastRiverRoad::Material()))
        {GroundMID=UMaterialInstanceDynamic::Create(Ground,this);Streaming->GroundReady=true;}
        else
        {
            Streaming->Failed=true;
            if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
                Loading->FailPreparation(FText::FromString(TEXT("地表与天空资源加载失败，请返回主场景。")));
        }
    });
    const auto Handle=UAssetManager::GetStreamableManager().RequestAsyncLoad(SurfacePaths,OnSurfaceLoaded);
    S.Handles.Add(Handle);
    if(!Handle)OnSurfaceLoaded.ExecuteIfBound();
}

void ATemperateHillsWorld::TickStreaming()
{
    TRACE_CPUPROFILER_EVENT_SCOPE(Hills_TickStreaming);
    if(!Streaming||Streaming->Stopping)return;
    auto& S=*Streaming;
    const auto* EntryLoading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
    HillsStreaming::FinishEntryBudgetIfReady(S.PreparingBudget,bReady,S.Failed,EntryLoading);
    if(S.Failed)return;
    if(!S.GroundReady)
    {
        const double Now=FPlatformTime::Seconds();
        if(Now>=S.NextSurfaceWaitLog)
        {
            S.NextSurfaceWaitLog=Now+5.;
            const auto Handle=S.Handles.IsEmpty()?nullptr:S.Handles[0];
            UE_LOG(LogTemp,Display,TEXT("HILLS_PREP phase=surface progress=%.1f elapsed=%.2fs"),
                Handle?Handle->GetProgress()*100.f:0.f,Now-StartSeconds);
        }
        return;
    }
    LoadNextEnvironmentStage();
    if(bReady || !S.StaggerVillageEntry)TickResidentAppearanceLoads();
    // A NullRHI peer still needs the real terrain/collision/PCG and gameplay
    // actors, but it cannot produce shader maps or resident GPU texture mips.
    if(GUsingNullRHI)S.GroundTexturesCollected=true;
    if(!S.GroundTexturesCollected)
    {
        // The uniform expressions needed by GetUsedTextures become available
        // with the ground shader. Let terrain generation run while it compiles.
        const auto Platform=GetFeatureLevelShaderPlatform_Checked(GetWorld()->GetFeatureLevel());
        const auto* Resource=GroundMID->GetMaterialResource(Platform);
        const auto* Map=Resource?Resource->GetGameThreadShaderMap():nullptr;
        if(Map&&Map->IsValidForRendering())
        {
            TArray<UTexture*> UsedTextures;
            GroundMID->GetUsedTextures(UsedTextures,{},Platform);
            for(auto* Used:UsedTextures)if(auto* Texture=Cast<UTexture2D>(Used))
                S.GroundTextures.AddUnique(Texture);
            S.GroundTexturesCollected=true;
            S.NextGroundResidencyRefresh=0;
            UE_LOG(LogTemp,Display,TEXT("HILLS_GROUND requested material=%s textures=%d"),*GetNameSafe(GroundMID->Parent),S.GroundTextures.Num());
            if(S.GroundTextures.IsEmpty())
            {
                S.Failed=true;
                if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())Loading->FailPreparation(FText::FromString(TEXT("地面纹理未能载入，请返回主场景。")));
                return;
            }
        }
    }
    // Dynamic terrain + Custom world-UV sampling has no reliable baked UV
    // density. Renew a short lease for its small, shared texture set only.
    // Keep doing this after entry, otherwise the streamer can evict the detail.
    const double ResidencyNow=FPlatformTime::Seconds();
    if(ResidencyNow>=S.NextGroundResidencyRefresh)
    {
        S.NextGroundResidencyRefresh=ResidencyNow+1;
        for(const auto& Weak:S.GroundTextures)
            if(auto* Texture=Weak.Get())Texture->SetForceMipLevelsToBeResident(5.f);
    }
    TemperateForestWater::FPlanPtr BakedWater;
    if(S.RiverPending)
    {
        if(!S.RiverJob.IsReady())
        {
            if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
                Loading->UpdatePreparation(FText::FromString(TEXT("正在计算河道与河滩…")),.01f);
            return;
        }
        auto Layout=S.RiverJob.Get();S.RiverPending=false;
        RiverPlan=MoveTemp(Layout.River);
        S.FixedLayoutChecksum=Layout.Checksum;
        if(Layout.Water)
        {
            VillageSite=Layout.Village;
            // Persisted terrain edits still recalculate ponds on the immutable
            // river/village plan. A clean landscape can use the baked ponds directly.
            if(TerrainEdits.IsEmpty())
            {
                BakedWater=MoveTemp(Layout.Water);
                S.ForestWaterRevision=TerrainEditRevision;
            }
            UE_LOG(LogTemp,Display,TEXT("HILLS_LAYOUT loaded fixed village, river, lake and quarry; seed=%d edited=%d"),Seed,TerrainEdits.Num());
        }
        if(auto* RiverFX=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())
            RiverFX->BindRiver(this,RiverPlan,RiverPilotMaterial.Get(),RiverPilotSplash.Get());
        UE_LOG(LogTemp,Display,TEXT("HILLS_RIVER seed=%d samples=%d length_m=%.1f"),Seed,RiverPlan->Points.Num(),RiverPlan->Points.IsEmpty()?0:RiverPlan->Points.Last().Distance/100);
    }
    if(S.VillageBiomePending)
    {
        if(!S.VillageBiomeJob.IsReady())
        {
            if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
                Loading->UpdatePreparation(FText::FromString(TEXT("正在划分村庄丘陵与外围雨林…")),.02f);
            return;
        }
        RiverPlan=S.VillageBiomeJob.Get();S.VillageBiomePending=false;
        // Rebuild only the bounded water plan with the final biome. Settlement stays fixed.
        ForestWaterPlan.Reset();
        if(auto* RiverFX=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())
            RiverFX->BindRiver(this,RiverPlan,RiverPilotMaterial.Get(),RiverPilotSplash.Get());
    }
    if(!BakedWater&&!S.ForestWaterPending&&(!ForestWaterPlan||S.ForestWaterRevision!=TerrainEditRevision))
    {
        S.ForestWaterRevision=TerrainEditRevision;S.ForestWaterPending=true;
        S.ForestWaterJob=Async(EAsyncExecution::ThreadPool,[WorldSeed=Seed,Half=double(SizeMeters*50),River=RiverPlan,Edits=TerrainEdits,Version=GeneratorVersion,PlanVillage=!bSettlementPlanned&&!VillageSite.bPlaced]()
        {
            auto Active=TemperateForestWater::Generate(WorldSeed,Half,River,Edits,Version);
            // Keep village selection independent of whether the save already has excavations.
            auto Original=(PlanVillage && !Edits.IsEmpty())?TemperateForestWater::Generate(WorldSeed,Half,River,{},Version):Active;
            return MakeTuple(Active,Original);
        });
    }
    if(BakedWater||S.ForestWaterPending)
    {
        if(!BakedWater&&!S.ForestWaterJob.IsReady())
        {
            if(!bReady)if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
                Loading->UpdatePreparation(FText::FromString(TEXT("正在计算林下洼地与水岸…")),.02f);
            return;
        }
        auto Plans=BakedWater?MakeTuple(BakedWater,BakedWater):S.ForestWaterJob.Get();S.ForestWaterPending=false;
        const auto& Plan=Plans.Get<0>();
        if(S.ForestWaterRevision!=TerrainEditRevision)return;
        // Only cells containing old/new water need refreshing after an edit.
        for(auto& Pair:S.Cells)
        {
            const double X=-SizeMeters*50+Pair.Key.X*HillsStreaming::CellSize,Y=-SizeMeters*50+Pair.Key.Y*HillsStreaming::CellSize;
            if((ForestWaterPlan&&ForestWaterPlan->IntersectsCell(X,Y,HillsStreaming::CellSize))||Plan->IntersectsCell(X,Y,HillsStreaming::CellSize))Pair.Value.Dirty=true;
        }
        ForestWaterPlan=Plan;
        if(!bSettlementPlanned)
        {
            if(VillageSite.bPlaced)
            {
                bSettlementPlanned=true;
                ChapelSite=VillageSite.ChapelLot();
            }
            else PlanAbandonedVillage(Plans.Get<1>());
            if(VillageSite.bPlaced)
            {
                if(!LoadVillageSettlement())
                {
                    ChapelSite={};
                    VillageSite={};
                    UE_LOG(LogTemp,Error,TEXT("HILLS_VILLAGE could not queue sublevel"));
                }
            }
            if(TemperateHillsChapel::IsChapelWorld(GetWorld())&&!ChapelSite.bPlaced)
            {
                S.Failed=true;
                if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
                    Loading->FailPreparation(FText::FromString(TEXT("教堂出生区未能生成，请返回主场景。")));
                return;
            }
            const FVector Entry=GetStartLocation();
            const double EntryHalf=SizeMeters*50.,EntryCellSize=HillsStreaming::CellSize;
            const FIntPoint EntryCell(FMath::FloorToInt((Entry.X+EntryHalf)/EntryCellSize),FMath::FloorToInt((Entry.Y+EntryHalf)/EntryCellSize));
            const int32 EntryCount=FMath::RoundToInt(SizeMeters*100/EntryCellSize);
            S.SpawnCells.Reset();
            for(int32 Y=FMath::Max(0,EntryCell.Y-1);Y<=FMath::Min(EntryCount-1,EntryCell.Y+1);++Y)
                for(int32 X=FMath::Max(0,EntryCell.X-1);X<=FMath::Min(EntryCount-1,EntryCell.X+1);++X)
                    if(HillsStreaming::CellDistanceSquared(Entry,FVector(-EntryHalf+X*EntryCellSize,-EntryHalf+Y*EntryCellSize,0))<=FMath::Square(HillsStreaming::EntryRadius))
                        S.SpawnCells.Emplace(X,Y);
        }
        if(GeneratorVersion>=3&&VillageSite.bHilltop&&RiverPlan&&!RiverPlan->bVillageRainforest)
        {
            S.VillageBiomePending=true;
            S.VillageBiomeJob=Async(EAsyncExecution::ThreadPool,
                [Original=RiverPlan,Village=VillageSite,Entry=FVector2D(GetGenerationAnchor()),WorldSeed=Seed,Half=double(SizeMeters*50)]() -> TemperateRiver::FPlanPtr
                {
                    auto Updated=MakeShared<TemperateRiver::FPlan,ESPMode::ThreadSafe>(*Original);
                    Updated->BuildVillageRainforest(WorldSeed,Half,Village,Entry);
                    Updated->BuildRiverLake(WorldSeed,Half,Village,Entry,Original);
                    return Updated;
                });
            return;
        }
        if(auto* FX=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())FX->BindForestWater(this,Plan,ForestPondMaterial.Get());
        UE_LOG(LogTemp,Display,TEXT("HILLS_FOREST_WATER seed=%d pools=%d edits=%d"),Seed,Plan->Pools.Num(),TerrainEdits.Num());
    }
    PrepareVillageGroundCache();
    constexpr double Size=HillsStreaming::CellSize;
    const int32 Count=FMath::RoundToInt(SizeMeters*100/Size);
    const double Half=SizeMeters*50;
    auto* Pawn=UGameplayStatics::GetPlayerCharacter(this,0);
    const FVector Center=Pawn?Pawn->GetActorLocation():GetStartLocation();
    TArray<FVector> ViewCenters{Center};
    TArray<FVector> RaidCenters;FVector RaidVillage=FVector::ZeroVector;float RaidVillageRadius=0.f;
    if(auto* Raid=GetWorld()->GetSubsystem<UHillsNightRaidSubsystem>())Raid->GetGroundPins(RaidCenters,RaidVillage,RaidVillageRadius);
    if(HasAuthority())
    {
        UPCGSubsystem* PCG=GetNetMode()==NM_ListenServer?GetWorld()->GetSubsystem<UPCGSubsystem>():nullptr;
        FPCGGenSourceManager* Sources=PCG?PCG->GetGenSourceManager():nullptr;
        for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        {
            APlayerController* PC=It->Get();
            if(!PC)continue;
            if(APawn* Player=PC->GetPawn())ViewCenters.AddUnique(Player->GetActorLocation());
            if(!Sources||PC->IsLocalController()||S.GuestSources.Contains(PC))continue;
            auto* Guest=NewObject<UTemperateHillsGuestSource>(this);
            Guest->Controller=PC;
            if(Sources->RegisterGenSource(Guest))S.GuestSources.Add(PC,Guest);
        }
        for(auto It=S.GuestSources.CreateIterator();It;++It)
        {
            const auto* PC=It.Key().Get();
            if(PC&&PC->GetWorld()==GetWorld())continue;
            if(Sources&&It.Value().IsValid())Sources->UnregisterGenSource(It.Value().Get());
            It.RemoveCurrent();
        }
    }
    StreamQuarry(ViewCenters);
    auto CellOrigin=[&](FIntPoint K){return FVector(-Half+K.X*Size,-Half+K.Y*Size,0);};
    auto RaidNeedsGround=[&](FIntPoint K)
    {
        const FVector O=CellOrigin(K);
        if(RaidVillageRadius>0.f&&HillsStreaming::CellDistanceSquared(RaidVillage,O)<=FMath::Square(double(RaidVillageRadius)))return true;
        for(const FVector& P:RaidCenters)if(HillsStreaming::CellDistanceSquared(P,O)<=FMath::Square(6000.))return true;
        return false;
    };
    auto DistanceSquared=[&](FIntPoint K)
    {
        const FVector O=CellOrigin(K);
        double Nearest=DBL_MAX;for(const auto& View:ViewCenters)
            Nearest=FMath::Min(Nearest,HillsStreaming::CellDistanceSquared(View,O));
        return Nearest;
    };
    for(auto It=S.WaitingToSpawn.CreateIterator();It;++It)
        if(const auto* Controller=It->Get();!Controller||Controller->GetWorld()!=GetWorld()||Controller->GetPawn())It.RemoveCurrent();
    const bool KeepSpawn=!bReady||!S.WaitingToSpawn.IsEmpty();
    auto Wanted=[&](FIntPoint K,bool& Detailed)
    {
        if(K.X<0||K.Y<0||K.X>=Count||K.Y>=Count)return false;
#if !UE_BUILD_SHIPPING
        if(S.Visitor.IsValid()&&K==S.VisitCell){Detailed=true;return true;}
#endif
        if(KeepSpawn&&S.SpawnCells.Contains(K)){Detailed=true;return true;}
        if(!bSurfaceReady)return false;
        if(!bReady){Detailed=true;return DistanceSquared(K)<=FMath::Square(HillsStreaming::EntryRadius);}
        if(RaidNeedsGround(K)){Detailed=true;return true;}
        const auto* Existing=S.Cells.Find(K);
        const double FineRadius=DetailRadiusMeters*100+(Existing&&Existing->Detailed?Size:0);
        Detailed=DistanceSquared(K)<=FMath::Square(FineRadius);
        return DistanceSquared(K)<=FMath::Square(ViewRadiusMeters*100.0);
    };
    auto RemoveMesh=[&](UDynamicMeshComponent* C){if(C){InvalidateVillageGroundCache(C);Terrain.Remove(C);RemoveInstanceComponent(C);C->DestroyComponent();}};
    // Poll cooking completion without blocking. Keep the old LOD until replacement is usable.
    for(auto& Pair:S.Cells)
    {
        auto& Cell=Pair.Value;auto* Pending=Cell.Pending.Get();if(!Pending)continue;
        bool Ready=!Cell.PendingDetailed;
        if(!Ready)
        {
            const FVector O=CellOrigin(Pair.Key)+FVector(Size*.5+17,Size*.5+23,0);
            const double Z=Height(O.X,O.Y);FHitResult Hit;FCollisionQueryParams Q;Q.bTraceComplex=true;
            Ready=Pending->LineTraceComponent(Hit,FVector(O.X,O.Y,Z+500),FVector(O.X,O.Y,Z-500),Q);
        }
        if(Ready)
        {
            RemoveMesh(Cell.Mesh.Get());Pending->SetCanEverAffectNavigation(Cell.PendingDetailed&&HasAuthority());Pending->SetVisibility(true);InvalidateVillageGroundCache(Pending);Cell.Mesh=Pending;Cell.Pending.Reset();Cell.Detailed=Cell.PendingDetailed;
            SetBackdropCellVisible(Pair.Key,true);
        }
    }
    // At most one completed mesh is submitted to rendering/physics in a frame.
    for(int32 I=0;I<S.Jobs.Num();++I)
    {
        if(!S.Jobs[I].Future.IsReady())continue;
        const uint32 JobRevision=S.Jobs[I].EditRevision;
        auto Result=S.Jobs[I].Future.Get();S.Jobs.RemoveAt(I);
        bool Detailed=false;
        // An edit that landed while this mesh was cooking makes it stale; drop it
        // and let the cell rebuild from the newer edit list.
        if(!Wanted(Result->Key,Detailed)||Detailed!=Result->Detailed||JobRevision!=TerrainEditRevision)break;
        auto& Cell=S.Cells.FindOrAdd(Result->Key);
        auto* C=NewObject<UDynamicMeshComponent>(this);
        C->ComponentTags.Add(TEXT("HillsGround"));
        AddInstanceComponent(C);C->SetupAttachment(RootComponent);C->SetRelativeLocation(CellOrigin(Result->Key));
        // Cells are replaced when their geometry changes; their transform never moves.
        // Static mobility keeps character corrections in world space, independent of
        // the peers' asynchronous component names and streaming order.
        C->SetMobility(EComponentMobility::Static);C->SetCanEverAffectNavigation(false);
        C->SetVisibility(false);
        C->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);C->SetMaterial(0,GroundMID);
        if(Result->Mesh.HasAttributes() && Result->Mesh.Attributes()->NumUVLayers()>=5)
        {
            auto* RoadMaterial=EastRiverRoad::Material();
            C->SetMaterial(1,RoadMaterial);
        }
        C->bUseAsyncCooking=true;C->SetDeferredCollisionUpdatesEnabled(true,false);
        C->SetComplexAsSimpleCollisionEnabled(Result->Detailed,false);
        C->SetCollisionProfileName(Result->Detailed?TEXT("BlockAll"):TEXT("NoCollision"));
        HillsStreaming::SetCellMesh(C,MoveTemp(Result->Mesh),PCGLayers);C->RegisterComponent();
        BindVillageGroundCache(C);
        if(Result->Detailed)C->UpdateCollision(false);
        // Mark the submitted result current now. A newer water plan can dirty the
        // cell again while physics cooks; promoting the pending mesh must preserve that.
        Terrain.Add(C);Cell.Pending=C;Cell.PendingDetailed=Result->Detailed;Cell.Dirty=false;
        RemoveMesh(Cell.Ponds.Get());Cell.Ponds.Reset();
        if(Result->Ponds.TriangleCount()>0)
        {
            auto* FX=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>();
            if(auto* Material=FX?FX->GetForestWaterMaterial():nullptr)
            {
                auto* Water=NewObject<UDynamicMeshComponent>(this);AddInstanceComponent(Water);
                Water->SetupAttachment(RootComponent);Water->SetRelativeLocation(CellOrigin(Result->Key));
                Water->SetMobility(EComponentMobility::Movable);Water->SetCanEverAffectNavigation(false);
                Water->SetCollisionEnabled(ECollisionEnabled::NoCollision);Water->SetCastShadow(false);
                Water->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);Water->SetMaterial(0,Material);
                HillsStreaming::SetCellMesh(Water,MoveTemp(Result->Ponds),PCGLayers);Water->RegisterComponent();Water->PrecachePSOs();
                Cell.Ponds=Water;Terrain.Add(Water);
            }
        }
        if(!Cell.Water.IsValid()&&Result->Water.TriangleCount()>0&&Assets->RiverMaterial.IsValid())
        {
            auto* Water=NewObject<UDynamicMeshComponent>(this);
            AddInstanceComponent(Water);Water->SetupAttachment(RootComponent);Water->SetRelativeLocation(CellOrigin(Result->Key));
            Water->SetMobility(EComponentMobility::Movable);Water->SetCanEverAffectNavigation(false);
            Water->SetCollisionEnabled(ECollisionEnabled::NoCollision);Water->SetCastShadow(false);
            Water->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
            auto* RiverFX=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>();
            Water->SetMaterial(0,RiverFX&&RiverFX->GetRiverMaterial()?RiverFX->GetRiverMaterial():Assets->RiverMaterial.Get());
            HillsStreaming::SetCellMesh(Water,MoveTemp(Result->Water),PCGLayers);
            Water->RegisterComponent();Water->PrecachePSOs();Cell.Water=Water;Terrain.Add(Water);
        }
        break;
    }
    // A single unload per frame avoids a matching destruction spike when moving.
    for(auto It=S.Cells.CreateIterator();It;++It)
    {
#if !UE_BUILD_SHIPPING
        if(S.Visitor.IsValid()&&It.Key()==S.VisitCell)continue;
#endif
        // A late-joining pawn can already be far from spawn. Do not evict
        // the same spawn cells that Wanted and the initial readiness gate require.
        if((KeepSpawn&&S.SpawnCells.Contains(It.Key()))||RaidNeedsGround(It.Key())||DistanceSquared(It.Key())<=FMath::Square(ViewRadiusMeters*100.0+Size))continue;
        SetBackdropCellVisible(It.Key(),false);
        RemoveMesh(It.Value().Mesh.Get());RemoveMesh(It.Value().Pending.Get());
        RemoveMesh(It.Value().Water.Get());
        RemoveMesh(It.Value().Ponds.Get());
        if(auto* T=It.Value().Trunks.Get()){RemoveInstanceComponent(T);T->DestroyComponent();}
        It.RemoveCurrent();break;
    }
    // Two numerical jobs maximum; workers only receive copied seed/coordinate values.
    while(S.Jobs.Num()<2)
    {
        FIntPoint Best(-1,-1);bool BestDetailed=false;double Score=DBL_MAX;
        for(int32 Y=0;Y<Count;++Y)for(int32 X=0;X<Count;++X)
        {
            const FIntPoint Key(X,Y);bool Detailed=false;if(!Wanted(Key,Detailed))continue;
            const auto* Cell=S.Cells.Find(Key);
            if(Cell&&(Cell->Pending.IsValid()||(!Cell->Dirty&&Cell->Mesh.IsValid()&&Cell->Detailed==Detailed)))continue;
            if(S.Jobs.ContainsByPredicate([&](const auto& J){return J.Key==Key;}))continue;
            double Candidate=DistanceSquared(Key)+(Detailed?0:1.e12);
            if(!S.WaitingToSpawn.IsEmpty()&&S.SpawnCells.Contains(Key))Candidate=-1.;
#if !UE_BUILD_SHIPPING
            if(S.Visitor.IsValid()&&Key==S.VisitCell)Candidate=-1.;
#endif
            if(Candidate<Score){Score=Candidate;Best=Key;BestDetailed=Detailed;}
        }
        if(Best.X<0)break;
        HillsStreaming::FJob Job;Job.Key=Best;Job.EditRevision=TerrainEditRevision;
        Job.Future=Async(EAsyncExecution::ThreadPool,[Best,BestDetailed,Half,WorldSeed=Seed,River=RiverPlan,Edits=TerrainEdits,Version=GeneratorVersion,Ponds=ForestWaterPlan,Chapel=ChapelSite,Village=VillageSite,LayoutChecksum=S.FixedLayoutChecksum]()
        {
            return HillsFixedTerrainCells::LoadOrGenerate(Best,BestDetailed,Half,WorldSeed,River,Edits,Version,Ponds,Chapel,Village,LayoutChecksum);
        });
        S.Jobs.Add(MoveTemp(Job));
    }
    // The worker starts before the first cell can finish; mask uploads follow all
    // cell swaps/removals in this frame. Submit at most one backdrop mesh per tick.
    TickBackdrop(S.CompletedStages==HillsStreaming::BatchCount);
    if(!bSurfaceReady)
    {
        const int32 Ready=S.ReadySpawnCellCount(),Required=S.SpawnCells.Num();
        const auto* EntryLevel=S.VillageLevel.Get();
        if(EntryLevel&&EntryLevel->GetLevelStreamingState()==ELevelStreamingState::FailedToLoad)
        {
            S.Failed=true;
            if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
                Loading->FailPreparation(FText::FromString(TEXT("教堂前院场景加载失败，请返回主场景。")));
            return;
        }
        const bool EntrySceneReady=!ChapelSite.bPlaced||(EntryLevel&&EntryLevel->IsLevelVisible());
        if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
            Loading->UpdatePreparation(FText::FromString(FString::Printf(TEXT("正在生成出生区域 %d/%d…"),Ready,Required)),.1f*Ready/FMath::Max(1,Required));
        if(Ready==Required&&Required>0&&EntrySceneReady)
        {
            bSurfaceReady=true;
            UE_LOG(LogTemp,Display,TEXT("HILLS_SURFACE_READY seed=%d startup_cells=%d ms=%.2f"),Seed,Ready,(FPlatformTime::Seconds()-StartSeconds)*1000);
        }
        return;
    }
    // The neighborhood used by
    // both understory and grass reads tree, rock AND low-plant mesh bounds.
    // Do not freeze a partial neighborhood when those batches finish out of order.
    const bool NeighborhoodAssetsReady=S.Batches[HillsStreaming::Solids].Ready
        &&S.Batches[HillsStreaming::Understory].Ready&&S.Batches[HillsStreaming::GroundCover].Ready;
    for(int32 Layer=0;Layer<4;++Layer)
    {
        const bool AssetsReady=Layer<2?S.Batches[HillsStreaming::Solids].Ready:NeighborhoodAssetsReady;
        if(!S.LayerActive[Layer]&&AssetsReady)
        {
            ActivateVegetationLayer(Layer);S.LayerActive[Layer]=true;
            if(Layer==0)S.TreesActive=true;
            UE_LOG(LogTemp,Display,TEXT("HILLS_VEGETATION active_layer=%d elapsed=%.2fs"),Layer,FPlatformTime::Seconds()-StartSeconds);
            break; // One component registration per frame.
        }
    }
    TickVegetationFrontier();
    if(!bReady)TickPreparation();
#if !UE_BUILD_SHIPPING
    if(S.bVillageVisit&&bReady&&bSettlementPlanned&&!S.Visitor.IsValid())
    {
        auto* PC=GetWorld()->GetFirstPlayerController();
        auto* Player=PC&&PC->IsLocalController()?Cast<ACharacter>(PC->GetPawn()):nullptr;
        const auto* Level=S.VillageLevel.Get();
        if(!VillageSite.bPlaced||!Level||Level->GetLevelStreamingState()==ELevelStreamingState::FailedToLoad)
        {
            if(PC)PC->ClientMessage(TEXT("当前丘陵没有可到达的村庄。"));
            S.bVillageVisit=false;
        }
        else if(Player&&Level->IsLevelVisible())
        {
            const auto* Transit=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
            if(!Transit||!Transit->IsHoldingGameplayInput())
            {
                // Both points lie along the first straight of the authored west entrance.
                const auto& West=TemperateVillageLayout::Roads[0];
                S.StageVisit(Player,VillageSite.World(West.X+West.DX*.5,West.Y+West.DY*.5),
                    VillageSite.World(West.X+West.DX,West.Y+West.DY),Half);
            }
        }
    }
    if(auto* Visitor=S.Visitor.Get())
    {
        const auto* Cell=S.Cells.Find(S.VisitCell);
        if(S.bWhiteCliffsVisit&&S.Quarry.Stage==FTemperateHillsStreamingState::EQuarryStage::Failed)
        {
            if(auto* PC=Cast<APlayerController>(Visitor->GetController()))PC->ClientMessage(TEXT("白崖采石场地标资源载入失败。"));
            S.Visitor.Reset();S.bWhiteCliffsVisit=false;
        }
        else if((!S.bWhiteCliffsVisit||S.Quarry.Stage==FTemperateHillsStreamingState::EQuarryStage::Complete)&&Cell&&Cell->Detailed&&Cell->Mesh.IsValid()&&!Cell->Dirty&&!Cell->Pending.IsValid())
        {
            LandAtVisitTarget(*this,S,Cell->Mesh.Get(),*Visitor);
            S.Visitor.Reset();
            S.bVillageVisit=false;
            S.bWhiteCliffsVisit=false;
        }
    }
#endif
    // Collision is streamed for all server pawns, so each needs its own frontier hold.
    // Clients only hold their autonomous pawn; simulated proxies follow server movement.
    TSet<TWeakObjectPtr<ACharacter>> Guarded;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        auto* Player=Cast<ACharacter>(It->Get()->GetPawn());
        if(!Player||(!HasAuthority()&&!Player->IsLocallyControlled()))continue;
        if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
        {S.HeldPawns.Remove(Player);continue;}
        Guarded.Add(Player);
        auto* Move=Player->GetCharacterMovement();
        const FVector Probe=Player->GetActorLocation()+Player->GetVelocity()*.35;
        const FIntPoint K(FMath::FloorToInt((Probe.X+Half)/Size),FMath::FloorToInt((Probe.Y+Half)/Size));
        const FVector Position=Player->GetActorLocation();
        const FIntPoint PawnCell(FMath::FloorToInt((Position.X+Half)/Size),FMath::FloorToInt((Position.Y+Half)/Size));
        auto* Held=S.HeldPawns.Find(Player);
        // Stopping zeroes velocity. Keep waiting for the original frontier cell,
        // otherwise the next tick would release on the already-cooked current cell.
        if(Held&&Held->PawnCell!=PawnCell){Held->WaitCell=K;Held->PawnCell=PawnCell;}
        const auto* Cell=S.Cells.Find(Held?Held->WaitCell:K);
        const bool WaitingForQuarry=!S.Quarry.HasCollision()&&S.Quarry.Stage!=FTemperateHillsStreamingState::EQuarryStage::Failed&&
            RiverPlan&&RiverPlan->WhiteCliffs.Valid&&RiverPlan->WhiteCliffs.Weight(Probe.X,Probe.Y)>.01;
        const bool Ready=bReady&&Cell&&Cell->Detailed&&Cell->Mesh.IsValid()&&!WaitingForQuarry;
        if(Held)
        {
            if(Ready)
            {
                // Walking resumes through a fresh floor query; preserve swimming.
                if(Move->MovementMode==MOVE_None)Move->SetMovementMode(Held->ResumeMode==MOVE_Swimming?MOVE_Swimming:MOVE_Falling);
                S.HeldPawns.Remove(Player);Player->ForceNetUpdate();
            }
        }
        else if(!Ready&&(Move->IsMovingOnGround()||Move->IsFalling()||Move->IsSwimming()))
        {
            S.HeldPawns.Add(Player,{Move->MovementMode,K,PawnCell});
            Move->StopMovementImmediately();Move->DisableMovement();Player->ForceNetUpdate();
        }
    }
    for(auto It=S.HeldPawns.CreateIterator();It;++It)if(!Guarded.Contains(It.Key()))
    {
        if(auto* Player=It.Key().Get())
        {
            const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
            if(auto* Move=Player->GetCharacterMovement();Move->MovementMode==MOVE_None&&(!Health||!Health->IsDead()))
                Move->SetMovementMode(It.Value().ResumeMode==MOVE_Swimming?MOVE_Swimming:MOVE_Falling);
        }
        It.RemoveCurrent();
    }
    // Only nearby tree trunks own physics, one cell added/removed each frame.
    if(S.TreesActive&&Assets->TrunkCollisionMesh.IsValid())for(auto& Pair:S.Cells)
    {
        auto& Cell=Pair.Value;const double D=DistanceSquared(Pair.Key);
        if(auto* T=Cell.Trunks.Get())
        {if(D>FMath::Square(12800.0)&&!RaidNeedsGround(Pair.Key)){RemoveInstanceComponent(T);T->DestroyComponent();Cell.Trunks.Reset();break;}continue;}
        if((D>FMath::Square(9600.0)&&!RaidNeedsGround(Pair.Key))||!Cell.Detailed||!Cell.Mesh.IsValid())continue;
        const FVector O=CellOrigin(Pair.Key);TArray<FTemperatePlacement> Trees;
        GetPlacements(0,FBox(O+FVector(0,0,-50000),O+FVector(Size,Size,50000)),Trees);
        auto* T=NewObject<UInstancedStaticMeshComponent>(this);AddInstanceComponent(T);T->SetupAttachment(RootComponent);
        T->ComponentTags.Add(TEXT("HillsStandingTrunk"));
        T->SetStaticMesh(Assets->TrunkCollisionMesh.Get());T->SetCollisionProfileName(TEXT("BlockAll"));
        T->SetVisibility(false);T->SetCastShadow(false);T->SetCanEverAffectNavigation(HasAuthority());T->RegisterComponent();
        TArray<FTransform> Transforms;
        for(const auto& Tree:Trees){const double Scale=Tree.Transform.GetScale3D().X;Transforms.Emplace(Tree.Transform.GetRotation(),Tree.Transform.GetLocation()+FVector(0,0,300*Scale),FVector(.42*Scale,.42*Scale,6*Scale));}
        T->AddInstances(Transforms,false,true,HasAuthority());Cell.Trunks=T;break;
    }
    if(S.FogReady&&GetWorld()->GetTimeSeconds()>=S.NextFogTime){BuildValleyFog();S.NextFogTime=GetWorld()->GetTimeSeconds()+.5;}
    // PCG ground cover streams back in with its cell, so edits near the player clear
    // their grass again on a slow cadence. The bounds early-out keeps this cheap.
    {
        const double Now=GetWorld()->GetTimeSeconds();
        if(Now>=NextCoverSweep)
        {
            NextCoverSweep=Now+1.0;
            const FVector Eye=Pawn?Pawn->GetActorLocation():GetStartLocation();
            for(const TemperateHillsSurface::FTerrainEdit& Edit:TerrainEdits)
            {
                if(FVector2D::DistSquared(FVector2D(Edit.X,Edit.Y),FVector2D(Eye.X,Eye.Y))>FMath::Square(8000.0))continue;
                DestroyGroundCover(FVector(Edit.X,Edit.Y,Height(Edit.X,Edit.Y)),
                    Edit.Type==1?FMath::Max(Edit.HalfX,Edit.HalfY)+20:Edit.Radius*1.15);
            }
        }
    }
}

// A runtime crater only dirties the cells it reaches. Their live meshes stay
// visible until a replacement is cooked, so the player never falls through.
void ATemperateHillsWorld::InvalidateTerrainCells(const FVector2D& Center,double Radius)
{
    if(!Streaming||Streaming->Stopping)return;
    auto& S=*Streaming;
    constexpr double Size=HillsStreaming::CellSize;
    const double Half=SizeMeters*50;
    const int32 Count=FMath::RoundToInt(SizeMeters*100/Size);
    const int32 MinX=FMath::Clamp(FMath::FloorToInt((Center.X-Radius+Half)/Size),0,Count-1);
    const int32 MaxX=FMath::Clamp(FMath::FloorToInt((Center.X+Radius+Half)/Size),0,Count-1);
    const int32 MinY=FMath::Clamp(FMath::FloorToInt((Center.Y-Radius+Half)/Size),0,Count-1);
    const int32 MaxY=FMath::Clamp(FMath::FloorToInt((Center.Y+Radius+Half)/Size),0,Count-1);
    int32 Invalidated=0;
    // Reject old geometry that is still on a worker, including a shop repair with no terrain edit.
    for (auto& Job:S.Jobs)
        if (Job.Key.X>=MinX && Job.Key.X<=MaxX && Job.Key.Y>=MinY && Job.Key.Y<=MaxY)
            Job.EditRevision=TerrainEditRevision-1;
    for(int32 Y=MinY;Y<=MaxY;++Y)for(int32 X=MinX;X<=MaxX;++X)
    {
        auto* Cell=S.Cells.Find(FIntPoint(X,Y));
        if(!Cell)continue;
        if(auto* Pending=Cell->Pending.Get())
        {
            // The in-flight mesh was built with the previous crater list.
            Terrain.Remove(Pending);RemoveInstanceComponent(Pending);Pending->DestroyComponent();Cell->Pending.Reset();
        }
        Cell->Dirty=true;++Invalidated;
    }
    UE_LOG(LogTemp,Display,TEXT("HILLS_CRATER invalidate_cells=%d x=%.0f y=%.0f radius=%.0f"),Invalidated,Center.X,Center.Y,Radius);
}

void ATemperateHillsWorld::TickVegetationFrontier()
{
    auto& S=*Streaming;
    const double Now=FPlatformTime::Seconds();
    if(Now<S.NextVegetationFrontierTime)return;
    S.NextVegetationFrontierTime=Now+.25;
    auto* Sub=GetWorld()->GetSubsystem<UPCGSubsystem>();
    auto* Manager=Sub?Sub->GetGenSourceManager():nullptr;
    if(!Manager)return;
    const auto Sources=Manager->GetAllGenSources(Sub->GetPCGWorldActor());
    if(Sources.IsEmpty())return;
    float Frontier=1600.f;
    if(bReady)
    {
        // UE schedules larger grids first, regardless of distance priority.
        // Admit only the nearest unfinished ring across all layers so distant
        // tree cells cannot starve nearby grass. This is O(cell count) at 4 Hz;
        // no placement work, traces, graph refresh or synchronous asset loads.
        // Small admission increments bound the backlog already held by UE's
        // scheduler (it does not withdraw queued cells when radii shrink).
        for(float Ring=1600.f;Ring<=25600.f;Ring+=1600.f)
        {
            Frontier=Ring;
            int32 Required=0,Complete=0;
            for(const auto* Source:Sources)
            {
                const auto Position=Source->GetPosition();
                if(!Position)continue;
                for(int32 Layer=0;Layer<4;++Layer)
                {
                    if(!S.LayerActive[Layer]||(!Source->IsLocal()&&Layer!=1))continue;
                    const double Radius=FMath::Min(Ring,TemperateHillsVisibility::Layers[Layer].GenerateRadius);
                    HillsStreaming::CountVegetationCells(PCGLayers[Layer],*Position,Radius,SizeMeters*50.,Required,Complete);
                }
            }
            if(Complete<Required)break;
        }
    }
    for(int32 Layer=0;Layer<4;++Layer)
        if(S.LayerActive[Layer])SetVegetationGenerationRadius(Layer,Frontier);
}

void ATemperateHillsWorld::EndStreaming()
{
    for (const auto& Handle : PendingResidentAppearances) Handle->CancelHandle();
    PendingResidentAppearances.Reset();
    StreamedTavern.Reset();
    StreamedWindmill.Reset();
    StreamedBakery.Reset();
    StreamedGunshop.Reset();
    OnRep_VillageBakery();
    ReleaseVillageGroundCache();
    ForestWaterPlan.Reset();
    if(auto* RiverFX=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())RiverFX->UnbindRiver(this);
    EndBackdrop();
    if(!Streaming)return;
    auto& S=*Streaming;S.Stopping=true;
    if(ULevelStreamingDynamic* Level=S.VillageLevel.Get())
    {
        Level->OnLevelShown.RemoveDynamic(this,&ATemperateHillsWorld::BindStreamedVillageBuildings);
        Level->SetShouldBeVisible(false);
        Level->SetShouldBeLoaded(false);
        Level->SetIsRequestingUnloadAndRemoval(true);
    }
    if(auto* PCG=GetWorld()->GetSubsystem<UPCGSubsystem>())
        if(auto* Sources=PCG->GetGenSourceManager())
            for(const auto& Guest:S.GuestSources)
                if(Guest.Value.IsValid())Sources->UnregisterGenSource(Guest.Value.Get());
    S.GuestSources.Empty();
    for(const auto& Held:S.HeldPawns)if(auto* Player=Held.Key.Get())
    {
        const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
        if(Health&&Health->IsDead())continue;
        if(auto* Move=Player->GetCharacterMovement();Move->MovementMode==MOVE_None)
            Move->SetMovementMode(Held.Value.ResumeMode==MOVE_Swimming?MOVE_Swimming:MOVE_Falling);
    }
    S.HeldPawns.Reset();
    // Ground residency requests expire naturally after five seconds. Do not
    // clear global flags on textures another world/preview may also be using.
    // Completed handles transferred to the GameInstance keep the curated biome cached.
    for(int32 I=S.RetainedHandleCount;I<S.Handles.Num();++I)
        if(auto& Handle=S.Handles[I]){Handle->CancelHandle();Handle->ReleaseHandle();}
    if(S.Quarry.Handle){S.Quarry.Handle->CancelHandle();S.Quarry.Handle->ReleaseHandle();}
    HillsStreaming::ReleaseStreamingBudget(S.PreparingBudget);
    // Pending numerical jobs contain no actor references and may finish after unload.
    Streaming.Reset();RiverPlan.Reset();
}
