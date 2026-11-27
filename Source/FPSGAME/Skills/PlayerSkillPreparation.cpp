#include "PlayerSkillPreparation.h"
#include "Algo/StableSort.h"
#include "../Weapons/PojunGrip.h"
#include "PlayerSkillRenderPreparation.h"
#include "../Diagnostics/FPSResourceLifecycle.h"
#include "FPSFireMagicComponent.h"
#include "../Production/WarhammerSlamFXSubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelMagicQuickCast.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "../Weapons/ModularSwordVisual.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace
{
TArray<FString> SkillEquipmentSignature(const UColdSteelStatusModel& Model)
{
    TArray<FString> Result;
    for(const auto& Item:Model.Items())
    {
        if(Item.Place!=0&&Item.Place!=1&&Item.Place!=5)continue;
        if(!ColdSteelInventory::IsTwoHandedSword(Item)&&!PojunGrip::UsesHammerMotion(Item))continue;
        // Compare the actual resource choices, not durability/stats in the full
        // item JSON. This uses the cached assembly catalog, never registry scans.
        Result.AddUnique(Item.Definition);
        Result.AddUnique(ColdSteelModularSword::AnimationFolder(Item));
        Result.AddUnique(ColdSteelModularSword::ArmsMesh(Item));
        TArray<FSoftObjectPath> Visuals;ColdSteelModularSword::GatherVisualResources(Item,Visuals);
        for(const auto& Path:Visuals)Result.AddUnique(Path.ToString());
        for(const TCHAR* Key:{TEXT("swing_sound"),TEXT("hit_sound"),TEXT("tool_sound"),TEXT("tool_swing_sound")})
            Result.AddUnique(ColdSteelInventory::Text(Item,Key));
    }
    Result.Sort();return Result;
}

bool IsEquipmentPreparationReview()
{
#if WITH_EDITOR
    // These isolated fixtures exercise equipment/navigation RPC paths, not learned-skill
    // rendering. Background skill residency must not compile unrelated armor
    // and warhammer meshes while the two diagnostic peers run.
    return FParse::Param(FCommandLine::Get(),TEXT("MapMarkerWire"))||FParse::Param(FCommandLine::Get(),TEXT("KukriCombatWireAudit"))||
        FParse::Param(FCommandLine::Get(),TEXT("BackpackWireAudit"))||FParse::Param(FCommandLine::Get(),TEXT("PistolPresentationWire"))||FParse::Param(FCommandLine::Get(),TEXT("PistolAmmoWire"))||
        (FParse::Param(FCommandLine::Get(),TEXT("ShotgunAttachmentAudit"))&&FParse::Param(FCommandLine::Get(),TEXT("PistolBody")));
#else
    return false;
#endif
}
}


void PlayerSkillAssets::Defer(AActor* Owner,FName Skill,FSimpleDelegate Ready,const TArray<FSoftObjectPath>& ExtraPaths)
{
    if(IsEquipmentPreparationReview()||!Owner||!Owner->GetWorld())return;
    // Possession can happen after BeginPlay. Decide local ownership next tick.
    Owner->GetWorld()->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateWeakLambda(Owner,[Owner,Skill,Ready,ExtraPaths]()
    {
        const auto* Pawn=Cast<APawn>(Owner);
        if(Pawn&&!Pawn->GetController()&&Owner->GetNetMode()==NM_Standalone)
        {Defer(Owner,Skill,Ready,ExtraPaths);return;}
        auto* Instance=Owner->GetGameInstance();
        if(Pawn&&Pawn->IsPlayerControlled()&&Pawn->IsLocallyControlled()&&Instance)
            if(auto* Loading=Instance->GetSubsystem<UTransitLoadingSubsystem>())
            {Loading->QueueSkillAssets(Owner,Skill,Ready,ExtraPaths);return;}
        // Remote/server pawns do not consume the local player's learned list.
        TArray<FSoftObjectPath> Paths;Gather(Skill,FColdSteelProfile(),Paths);
        for(const auto& Path:ExtraPaths)if(!Path.IsNull())Paths.AddUnique(Path);
        UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,Ready);
    }));
}

FPlayerSkillPreparation::~FPlayerSkillPreparation()
{
    Cancel();
    Residents.Reset(); Prepared.Reset();
    RecordResourceState(nullptr, TEXT("Skills.Destroyed"));
}

void FPlayerSkillPreparation::RecordResourceState(const UObject* Context, const TCHAR* Phase) const
{
    FPSResourceLifecycle::Record(Context, Phase, {
        {TEXT("resident_handles"), Residents.Num()}, {TEXT("prepared_paths"), Prepared.Num()},
        {TEXT("pending_handle"), Pending.IsValid() ? 1 : 0},
        {TEXT("render_preparation_owner"), RenderPreparation.IsValid() ? 1 : 0},
        {TEXT("deferred_render_paths"), DeferredRenderPaths.Num()},
        {TEXT("jobs"), Jobs.Num()}, {TEXT("consumers"), Consumers.Num()}});
}

void FPlayerSkillPreparation::Cancel()
{
    const UObject* DiagnosticOwner = Model.Get();
    const bool HadWork = bStarted || Pending.IsValid() || RenderPreparation.IsValid();
    if (HadWork) RecordResourceState(DiagnosticOwner, TEXT("Skills.BeforeCancel"));
    if(Model.IsValid()&&ChangedHandle.IsValid())Model->OnChanged.Remove(ChangedHandle);
    ChangedHandle.Reset();Model.Reset();
    if(Pending)Pending->CancelHandle();
    Pending.Reset();RenderPreparation.Reset();RenderPrepared.Reset();
    DeferredRenderPaths.Reset();bWarhammerPreparationPending=bRenderAdmissionPaused=false;
    NextRenderAdmissionSeconds=DeferredRenderStartedAt=0.;
    CarriedEquipmentSignature.Reset();bEquipmentCheckPending=false;NextEquipmentCheckSeconds=0.;
    Jobs.Reset();KnownSkills.Reset();ReadySkills.Reset();Cursor=AssetCursor=0;
    bStarted=bFailed=bAssetPreparationStarted=bPSORequested=bRefreshRequested=bBindingsDelivered=false;Progress=0;
    Consumers.RemoveAll([](const FConsumer& C){return !C.Owner.IsValid()||!C.Ready.IsBound();});
    // Asset handles survive travel; world-bound representatives never do.
    if (HadWork) RecordResourceState(DiagnosticOwner, TEXT("Skills.AfterCancelResidentsKeptForTravel"));
}

void FPlayerSkillPreparation::RegisterConsumer(AActor* Owner,FName Skill,FSimpleDelegate Ready,const TArray<FSoftObjectPath>& ExtraPaths)
{
    if(!Owner||!Ready.IsBound())return;
    if(bStarted&&Model.IsValid()&&Owner->GetWorld()==Model->GetWorld()&&ReadySkills.Contains(Skill))
    {
        const bool NeedsExtra=ExtraPaths.ContainsByPredicate([&](const FSoftObjectPath& Path)
            {return !Path.IsNull()&&!RenderPrepared.Contains(Path)&&!DeferredRenderPaths.Contains(Path);});
        if(!NeedsExtra){Ready.ExecuteIfBound();return;}
        KnownSkills.Remove(Skill);ReadySkills.Remove(Skill);
    }
    Consumers.RemoveAll([](const FConsumer& C){return !C.Owner.IsValid()||!C.Ready.IsBound();});
    Consumers.Add({Owner,Skill,Ready,ExtraPaths});bRefreshRequested=true;
    for(int32 I=Cursor;I<Jobs.Num();++I)if(Jobs[I].Skill==Skill)
        for(const auto& Path:ExtraPaths)if(!Path.IsNull())Jobs[I].Paths.AddUnique(Path);
}

void FPlayerSkillPreparation::Begin(UColdSteelStatusModel& InModel)
{
    Cancel();
    if(IsEquipmentPreparationReview()){bStarted=true;return;}
    Model=&InModel;bStarted=true;
    CarriedEquipmentSignature=SkillEquipmentSignature(InModel);
    Consumers.RemoveAll([&](const FConsumer& C){return !C.Owner.IsValid()||C.Owner->GetWorld()!=InModel.GetWorld();});
    ChangedHandle=InModel.OnChanged.AddLambda([this]()
    {
        bEquipmentCheckPending=true;
        if(bRefreshRequested||!Model.IsValid())return;
        // Only learned-set changes restart jobs here. Equipment path comparison
        // is coalesced separately; health/mana updates never restart warmup.
        for(FName Skill:Model->SkillCatalog())
            if(KnownSkills.Contains(Skill)!=(Model->MasteryProgress(Skill).Level>0))
            {bRefreshRequested=true;break;}
    });
    RenderPreparation=MakeShared<FPlayerSkillRenderPreparation>();RefreshLearnedSkills();
    Status=FText::FromString(TEXT("后台准备已学战技与魔法"));
    RecordResourceState(&InModel, TEXT("Skills.Begin"));
    UE_LOG(LogTemp,Display,TEXT("PlayerSkillBackground: queued %d learned skills (martial -> magic; assets -> shaders/PSO -> bindings)"),Jobs.Num());
}

void FPlayerSkillPreparation::RefreshLearnedSkills()
{
    bRefreshRequested=false;if(!Model.IsValid())return;
    // Rebuild the current requirement set, not an append-only history of past
    // weapons. Already-ready paths remain cached; real consumers stay bound.
    if(Pending)Pending->CancelHandle();Pending.Reset();
    if(RenderPreparation)RenderPreparation->SkipCurrent();
    Jobs.Reset();KnownSkills.Reset();Cursor=AssetCursor=0;
    bAssetPreparationStarted=bBindingsDelivered=bWarhammerPreparationPending=false;
    DeferredRenderStartedAt=0.;NextRenderAdmissionSeconds=0.;
    bResidentCleanupPending=true;
    for(bool bMagic:{false,true})for(FName Skill:Model->SkillCatalog())
    {
        const bool IsMagic=ColdSteelMagicQuickCast::IsMagic(Skill)||Skill==TEXT("magicArrowRain")||Skill==TEXT("elementalArrow")||Skill==TEXT("illuminationArrow");
        if(IsMagic!=bMagic||KnownSkills.Contains(Skill)||Model->MasteryProgress(Skill).Level<=0)continue;
        KnownSkills.Add(Skill);
        FJob Job;Job.Skill=Skill;Job.Name=Model->DevelopmentSkillDefinition(Skill).Name;Job.bMagic=bMagic;
        Jobs.Add(MoveTemp(Job));
    }
    // Load the currently selected wheel spell and actively bound spells before unbound catalog entries.
    const FName SelectedMagic=Model->SelectedMagicSkill();
    const bool bStaffEquipped=Model->HasEquippedStaff();
    TSet<FName> WheelSkills;
    for(FName Skill:Model->MagicBindings())if(!Skill.IsNone())WheelSkills.Add(Skill);
    TSet<FName> QuickSkills;
    for(const auto& Binding:Model->QuickBindings())if(!Binding.Skill.IsNone())QuickSkills.Add(Binding.Skill);
    auto PriorityTier=[&](const FJob& Job)->int32
    {
        if(!SelectedMagic.IsNone()&&Job.Skill==SelectedMagic)return bStaffEquipped?0:1;
        if(bStaffEquipped&&WheelSkills.Contains(Job.Skill))return 1;
        if(QuickSkills.Contains(Job.Skill))return 2;
        if(WheelSkills.Contains(Job.Skill))return 3;
        return Job.bMagic?5:4;
    };
    Algo::StableSortBy(Jobs,PriorityTier);
    for(auto It=ReadySkills.CreateIterator();It;++It)if(!KnownSkills.Contains(*It))It.RemoveCurrent();
    Progress=Jobs.IsEmpty()?1.f:0.f;
}

void FPlayerSkillPreparation::PrioritizeSkill(FName Skill)
{
    if(!bStarted||Skill.IsNone()||ReadySkills.Contains(Skill)||Cursor>=Jobs.Num())return;
    int32 Found=INDEX_NONE;
    for(int32 I=Cursor;I<Jobs.Num();++I)if(Jobs[I].Skill==Skill){Found=I;break;}
    if(Found==INDEX_NONE||Found==Cursor)return;
    // If the active cursor job has not started gathering yet, swap right into Cursor;
    // otherwise place immediately next so the in-flight async asset handle completes cleanly.
    const int32 Target=!Jobs[Cursor].bGathered&&!Pending.IsValid()?Cursor:Cursor+1;
    if(Found<=Target||Target>=Jobs.Num())return;
    FJob Promoted=MoveTemp(Jobs[Found]);
    Jobs.RemoveAt(Found);
    Jobs.Insert(MoveTemp(Promoted),Target);
}

void FPlayerSkillPreparation::CheckEquipmentChanges()
{
    if(!bEquipmentCheckPending||FPlatformTime::Seconds()<NextEquipmentCheckSeconds)return;
    bEquipmentCheckPending=false;NextEquipmentCheckSeconds=FPlatformTime::Seconds()+.5;
    auto Current=SkillEquipmentSignature(*Model);
    if(Current==CarriedEquipmentSignature)return;
    CarriedEquipmentSignature=MoveTemp(Current);bRefreshRequested=true;
}

void FPlayerSkillPreparation::ReleaseUnusedResidents()
{
    // Optional GPU work must not keep an obsolete world's asset handles alive.
    if(!bResidentCleanupPending||bRefreshRequested||Cursor!=Jobs.Num())return;
    // Keep old handles while the new world's consumers are being prepared.
    // Only the completed current job set can prove which old inventory/skill
    // variants are no longer requested. Live components retain their own assets.
    TSet<FSoftObjectPath> Needed;
    for(const auto& Job:Jobs)for(const auto& Path:Job.Paths)Needed.Add(Path);
    for(const auto& Consumer:Consumers)if(Consumer.Owner.IsValid()&&KnownSkills.Contains(Consumer.Skill))
        for(const auto& Path:Consumer.ExtraPaths)Needed.Add(Path);
    DeferredRenderPaths.RemoveAll([&Needed](const auto& Path){return !Needed.Contains(Path);});
    int32 Released=0;
    for(auto It=Residents.CreateIterator();It;++It)
        if(!Needed.Contains(It.Key()))
        {
            if(It.Value())It.Value()->ReleaseHandle();
            Prepared.Remove(It.Key());RenderPrepared.Remove(It.Key());
            It.RemoveCurrent();++Released;
        }
    bResidentCleanupPending=false;
    RecordResourceState(Model.Get(), TEXT("Skills.CurrentSetSettled"));
    if(Released)UE_LOG(LogTemp,Display,TEXT("PlayerSkillBackground: released %d obsolete resource handles; retained %d current resources"),Released,Residents.Num());
}

void FPlayerSkillPreparation::BindConsumers(FName Skill)
{
    ReadySkills.Add(Skill);
    TArray<FSimpleDelegate> Ready;
    for(int32 I=Consumers.Num()-1;I>=0;--I)
        if(Consumers[I].Skill==Skill&&Consumers[I].Owner.IsValid()&&Model.IsValid()&&Consumers[I].Owner->GetWorld()==Model->GetWorld())
        {Ready.Add(Consumers[I].Ready);Consumers.RemoveAt(I);}
    for(auto& Callback:Ready)Callback.ExecuteIfBound();
}

void FPlayerSkillPreparation::Fail(const FString& Reason)
{
    UE_LOG(LogTemp,Warning,TEXT("PlayerSkillBackground: skipped %s; entry remains unlocked"),*Reason);
    if(Pending)Pending->CancelHandle();Pending.Reset();
    if(RenderPreparation&&bAssetPreparationStarted)RenderPreparation->SkipCurrent();
    if(Jobs.IsValidIndex(Cursor))Jobs[Cursor].bHadFailures=true;
    bFailed=false;bAssetPreparationStarted=false;++AssetCursor;
}

void FPlayerSkillPreparation::Tick()
{
    if(!bStarted||!Model.IsValid())return;
    CheckEquipmentChanges();
    if(bRefreshRequested)RefreshLearnedSkills();
    if(Cursor==Jobs.Num()){ReleaseUnusedResidents();TickDeferredRender();return;}
    if(DeferredRenderStartedAt>0.)
    {RenderPreparation->SkipCurrent();DeferredRenderStartedAt=0.;}
    TRACE_CPUPROFILER_EVENT_SCOPE(Gameplay_BackgroundLearnedSkills);
    const double Deadline=FPlatformTime::Seconds()+.0005;
    for(int32 Work=0;Work<8&&Cursor<Jobs.Num()&&FPlatformTime::Seconds()<Deadline;++Work)
    {
        auto& Job=Jobs[Cursor];
        if(!Job.bGathered)
        {
            // Resolve at most one skill's inventory/asset-registry metadata per
            // frame, instead of building every weapon variant on the entry frame.
            PlayerSkillAssets::Gather(Job.Skill,Model->Snapshot(),Job.Paths);
            for(const auto& Consumer:Consumers)if(Consumer.Skill==Job.Skill)
                for(const auto& Path:Consumer.ExtraPaths)if(!Path.IsNull())Job.Paths.AddUnique(Path);
            Job.bGathered=true;
            if(Job.Paths.IsEmpty()){BindConsumers(Job.Skill);++Cursor;AssetCursor=0;Progress=float(Cursor)/Jobs.Num();continue;}
            Job.Paths.Insert(FSoftObjectPath(TEXT("/Engine/BasicShapes/Plane.Plane")),0);
            return;
        }
        if(AssetCursor>=Job.Paths.Num())
        {
            if(!bBindingsDelivered)
            {BindConsumers(Job.Skill);bBindingsDelivered=true;BindingsStartedAt=FPlatformTime::Seconds();return;}
            if(Job.Skill==TEXT("dragonBreath"))
            {
                auto* Pawn=UGameplayStatics::GetPlayerPawn(Model.Get(),0);
                auto* Fire=Pawn?Pawn->FindComponentByClass<UFPSFireMagicComponent>():nullptr;
                if(Fire&&!Fire->IsDragonBreathVisualReady())
                {
                    if(FPlatformTime::Seconds()-BindingsStartedAt<10.)return;
                    UE_LOG(LogTemp,Warning,TEXT("PlayerSkillBackground: dragon instance still preparing; continue later skills without holding entry"));
                    Job.bHadFailures=true;
                }
            }
            if(Job.Skill==TEXT("heavyStrike"))
            {
                const auto& Profile=Model->Snapshot();
                const bool HasHammer=Profile.Items.ContainsByPredicate([](const FColdSteelItem& Item)
                {return (Item.Place==0||Item.Place==1||Item.Place==5)&&PojunGrip::UsesHammerMotion(Item);});
                auto* FX=HasHammer?Model->GetWorld()->GetSubsystem<UWarhammerSlamFXSubsystem>():nullptr;
                if(FX&&!CanPrepareRender()) bWarhammerPreparationPending=true;
                else if(FX&&!FX->PrepareBackground())
                {
                    if(FPlatformTime::Seconds()-BindingsStartedAt<10.)return;
                    UE_LOG(LogTemp,Warning,TEXT("PlayerSkillBackground: warhammer pool still preparing; continue without holding entry"));
                    Job.bHadFailures=true;
                }
            }
            UE_LOG(LogTemp,Display,TEXT("PlayerSkillBackground: %s %d/%d %s (optional render backlog=%d)"),Job.bHadFailures?TEXT("finished with skipped preparation"):TEXT("assets bound"),Cursor+1,Jobs.Num(),*Job.Skill.ToString(),DeferredRenderPaths.Num());
            ++Cursor;AssetCursor=0;bBindingsDelivered=false;Progress=float(Cursor)/Jobs.Num();continue;
        }
        const auto& Path=Job.Paths[AssetCursor];
        if(RenderPrepared.Contains(Path)||DeferredRenderPaths.Contains(Path)){++AssetCursor;continue;}
        UObject* Asset=Path.ResolveObject();
        if(!bAssetPreparationStarted)
        {
            if(!Pending&&!Prepared.Contains(Path))
            {
                JobStartedAt=FPlatformTime::Seconds();
                Pending=UAssetManager::GetStreamableManager().RequestAsyncLoad(Path,FStreamableDelegate(),FStreamableManager::DefaultAsyncLoadPriority);
                if(!Pending)Fail(Path.ToString()+TEXT(" request unavailable"));
                return;
            }
            if(Pending&&!Pending->HasLoadCompleted())
            {if(FPlatformTime::Seconds()-JobStartedAt>30.)Fail(Path.ToString()+TEXT(" package timeout"));return;}
            Asset=Path.ResolveObject();
            if(!Asset){Fail(Path.ToString()+TEXT(" asset unavailable"));return;}
            Prepared.Add(Path);if(Pending)Residents.Add(Path,MoveTemp(Pending));
            JobStartedAt=FPlatformTime::Seconds();bAssetPreparationStarted=true;
        }
        bool Deferred=false;
        if(RenderPreparation->Tick(Asset,Model->GetWorld(),CanPrepareRender(),Deferred))
        {
            if(Deferred)DeferredRenderPaths.AddUnique(Path);
            else RenderPrepared.Add(Path);
            RenderPreparation->SkipCurrent();++AssetCursor;bAssetPreparationStarted=false;
        }
        else if(FPlatformTime::Seconds()-JobStartedAt>10.)
            Fail(Path.ToString()+TEXT(" render preparation timeout"));
        // Even a ready resource may submit work. Never batch new compilation,
        // renderer creation, audio priming or GPU simulation into the same tick.
        return;
    }
    ReleaseUnusedResidents();
}

bool FPlayerSkillPreparation::CanPrepareRender()
{
    auto* World=Model.IsValid()?Model->GetWorld():nullptr;
    if(!World||World->GetNetMode()==NM_DedicatedServer)return false;
    auto* Metrics=World->GetSubsystem<UFPSPerformanceMetricsSubsystem>();
    if(Metrics)Metrics->RefreshRenderBudget(); // Reuse the existing at-most-2Hz observation.
    constexpr uint64 ReserveBytes=1024ull*1024ull*1024ull;
    const bool Allowed=Metrics&&Metrics->HasRecentRenderHeadroom(ReserveBytes);
    if(bRenderAdmissionPaused==Allowed)
    {
        bRenderAdmissionPaused=!Allowed;
        UE_LOG(LogTemp,Display,TEXT("PlayerSkillBackground: optional GPU preparation %s; asset loading and skill bindings remain eligible"),
            Allowed?TEXT("resumed"):TEXT("paused for memory budget"));
    }
    return Allowed;
}

void FPlayerSkillPreparation::TickDeferredRender()
{
    if(DeferredRenderPaths.IsEmpty()&&!bWarhammerPreparationPending)return;
    const double Now=FPlatformTime::Seconds();
    if(Now<NextRenderAdmissionSeconds)return;
    if(!CanPrepareRender())
    {
        // Only temporary warmup components are retired. Never touch a cast's FX.
        if(RenderPreparation)RenderPreparation->SkipCurrent();
        DeferredRenderStartedAt=0.;NextRenderAdmissionSeconds=Now+.5;return;
    }
    NextRenderAdmissionSeconds=0.;
    if(!DeferredRenderPaths.IsEmpty())
    {
        const auto Path=DeferredRenderPaths[0];
        auto* Asset=Path.ResolveObject();
        if(!Asset){DeferredRenderPaths.RemoveAt(0);DeferredRenderStartedAt=0.;return;}
        if(DeferredRenderStartedAt==0.)DeferredRenderStartedAt=Now;
        bool Deferred=false;
        if(RenderPreparation->Tick(Asset,Model->GetWorld(),true,Deferred))
        {
            if(!Deferred)RenderPrepared.Add(Path);
            RenderPreparation->SkipCurrent();DeferredRenderPaths.RemoveAt(0);DeferredRenderStartedAt=0.;
        }
        else if(Now-DeferredRenderStartedAt>10.)
        {
            UE_LOG(LogTemp,Warning,TEXT("PlayerSkillBackground: optional preparation timeout %s; gameplay assets remain bound"),*Path.ToString());
            RenderPreparation->SkipCurrent();DeferredRenderPaths.RemoveAt(0);DeferredRenderStartedAt=0.;
        }
        return; // At most one representative operation, never drain the backlog in a frame.
    }
    if(bWarhammerPreparationPending)
    {
        const bool HasHammer=Model->Items().ContainsByPredicate([](const FColdSteelItem& Item)
            {return (Item.Place==0||Item.Place==1||Item.Place==5)&&PojunGrip::UsesHammerMotion(Item);});
        if(!HasHammer){bWarhammerPreparationPending=false;DeferredRenderStartedAt=0.;return;}
        if(DeferredRenderStartedAt==0.)DeferredRenderStartedAt=Now;
        auto* FX=Model->GetWorld()->GetSubsystem<UWarhammerSlamFXSubsystem>();
        if(!FX||FX->PrepareBackground()||Now-DeferredRenderStartedAt>10.)
        {bWarhammerPreparationPending=false;DeferredRenderStartedAt=0.;}
    }
}
