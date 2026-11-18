#include "HillsNetLoadAudit.h"
#include "HillsContinuitySupport.h"
#include "../FPSGAMECharacter.h"
#include "../FPSWeatherManager.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/HillsNightRaidSubsystem.h"
#include "../WorldGeneration/HillsNightPortal.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/FatZombie.h"
#include "../Monsters/HumanoidKnockdownComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/NetworkDelegates.h"
#include "Engine/PackageMapClient.h"
#include "EngineUtils.h"
#include "UObject/UObjectGlobals.h"
#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "RHI.h"
#include "Serialization/JsonSerializer.h"

namespace
{
template<class T>T* FindNetLoadActor(UWorld* W){for(TActorIterator<T> It(W);It;++It)return *It;return nullptr;}
constexpr const TCHAR* AuditNursePath=TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C");
}
bool UHillsNetLoadAudit::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    auto* W=Cast<UWorld>(Outer);
    return Super::ShouldCreateSubsystem(Outer)&&W&&W->GetName().Contains(TEXT("TemperateHills"))
        &&FParse::Param(FCommandLine::Get(),TEXT("HillsNetLoadAudit"))
        &&FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("HillsNetLoad20261118"));
#endif
}
bool UHillsNetLoadAudit::DoesSupportWorldType(EWorldType::Type Type) const{return Type==EWorldType::Game;}
TStatId UHillsNetLoadAudit::GetStatId() const{RETURN_QUICK_DECLARE_CYCLE_STAT(UHillsNetLoadAudit,STATGROUP_Tickables);}
void UHillsNetLoadAudit::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);Started=PreviousFrame=FPlatformTime::Seconds();Frames.Reserve(45000);
    FParse::Value(FCommandLine::Get(),TEXT("HillsNetLoadOutput="),Output);
    FParse::Value(FCommandLine::Get(),TEXT("HillsNetLoadRole="),Role);Late=Role==TEXT("late");
    FrameHandle=FCoreDelegates::OnEndFrame.AddUObject(this,&UHillsNetLoadAudit::Frame);
    LoadHandle=FNetDelegates::OnSyncLoadDetected.AddUObject(this,&UHillsNetLoadAudit::SyncLoad);
    SpawnHandle=GetWorld()->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateUObject(this,&UHillsNetLoadAudit::ActorSpawned));
    GcBeginHandle=FCoreUObjectDelegates::GetPreGarbageCollectDelegate().AddWeakLambda(this,[this]()
    {GcStarted=FPlatformTime::Seconds();if(!Done)Event(TEXT("gc_begin"));});
    GcEndHandle=FCoreUObjectDelegates::GetPostGarbageCollect().AddWeakLambda(this,[this]()
    {
        if(!Done&&GcStarted)
        {
            const double Ms=(FPlatformTime::Seconds()-GcStarted)*1000.;Event(TEXT("gc_end"));
            Events.Last()->AsObject()->SetNumberField(TEXT("gc_ms"),Ms);
            UE_LOG(LogTemp,Display,TEXT("HILLS_NETLOAD_GC role=%s duration_ms=%.3f"),*Role,Ms);
        }
        GcStarted=0;
    });
    Event(TEXT("probe_initialized"));
}
void UHillsNetLoadAudit::Deinitialize()
{
    FCoreDelegates::OnEndFrame.Remove(FrameHandle);FNetDelegates::OnSyncLoadDetected.Remove(LoadHandle);
    FCoreUObjectDelegates::GetPreGarbageCollectDelegate().Remove(GcBeginHandle);
    FCoreUObjectDelegates::GetPostGarbageCollect().Remove(GcEndHandle);
    GetWorld()->RemoveOnActorSpawnedHandler(SpawnHandle);
    Super::Deinitialize();
}
void UHillsNetLoadAudit::Save(const FString& Name,const TSharedRef<FJsonObject>& J)
{
    FString Text;FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Text));
    IFileManager::Get().MakeDirectory(*Output,true);FFileHelper::SaveStringToFile(Text,*(Output/Name+TEXT(".json")));
}
bool UHillsNetLoadAudit::Exists(const TCHAR* Name) const{return IFileManager::Get().FileExists(*(Output/Name+TEXT(".json")));}
void UHillsNetLoadAudit::Frame()
{
    const double Now=FPlatformTime::Seconds(),Ms=(Now-PreviousFrame)*1000.;PreviousFrame=Now;if(Done)return;
    Frames.Add({Now-Started,Ms,GFrameCounter,Phase});
}
void UHillsNetLoadAudit::Event(const FString& Name)
{
    auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("name"),Name);J->SetNumberField(TEXT("time"),FPlatformTime::Seconds()-Started);
    J->SetNumberField(TEXT("frame"),double(GFrameCounter));J->SetStringField(TEXT("phase"),Phase);
    J->SetBoolField(TEXT("nurse_class_loaded"),FSoftObjectPath(AuditNursePath).ResolveObject()!=nullptr);
    bool ReactionsLoaded=true;
    for(const TCHAR* MonsterRole:{TEXT("Nurse"),TEXT("FatZombie")})
    {
        auto Paths=UHumanoidKnockdownComponent::DefaultAnimationPaths(MonsterRole);
        Paths.Add(UMonsterCombatComponent::DefaultStunAnimationPath(MonsterRole));
        for(const auto& Path:Paths)ReactionsLoaded&=Path.ResolveObject()!=nullptr;
    }
    J->SetBoolField(TEXT("reaction_defaults_loaded"),ReactionsLoaded);
    Events.Add(MakeShared<FJsonValueObject>(J));UE_LOG(LogTemp,Display,TEXT("HILLS_NETLOAD %s %s t=%.3f"),*Role,*Name,FPlatformTime::Seconds()-Started);
}
void UHillsNetLoadAudit::SyncLoad(const FNetSyncLoadReport& R)
{
    if(Done||R.NetDriver!=GetWorld()->GetNetDriver())return;
    auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("object"),GetPathNameSafe(R.LoadedObject));
    J->SetStringField(TEXT("owner"),GetPathNameSafe(R.OwningObject));J->SetNumberField(TEXT("type"),int32(R.Type));
    J->SetNumberField(TEXT("frame"),double(GFrameCounter));J->SetNumberField(TEXT("time"),FPlatformTime::Seconds()-Started);
    J->SetStringField(TEXT("phase"),Phase);Loads.Add(MakeShared<FJsonValueObject>(J));
}
void UHillsNetLoadAudit::ActorSpawned(AActor* Actor)
{
    if(!Done&&Actor&&Actor->IsA<ANurseZombie>())Event(TEXT("actor_spawn_")+Actor->GetClass()->GetName());
    if(!Done&&Actor&&Actor->IsA<AFPSGAMECharacter>())Event(TEXT("player_spawn"));
}
void UHillsNetLoadAudit::Finish(bool Passed,const FString& Detail)
{
    if(Done)return;Done=true;auto J=MakeShared<FJsonObject>();J->SetBoolField(TEXT("passed"),Passed);J->SetStringField(TEXT("detail"),Detail);
    J->SetStringField(TEXT("role"),Role);J->SetNumberField(TEXT("ready_seconds"),ReadyAt?ReadyAt-Started:-1.);
    J->SetNumberField(TEXT("max_monsters"),MaxMonsters);J->SetBoolField(TEXT("rendered"),!GUsingNullRHI);
    TArray<TSharedPtr<FJsonValue>> Samples;Samples.Reserve(Frames.Num());
    for(const auto& F:Frames){auto S=MakeShared<FJsonObject>();S->SetNumberField(TEXT("time"),F.Time);S->SetNumberField(TEXT("ms"),F.Ms);
        S->SetNumberField(TEXT("frame"),double(F.Frame));S->SetStringField(TEXT("phase"),F.Phase);Samples.Add(MakeShared<FJsonValueObject>(S));}
    J->SetArrayField(TEXT("events"),Events);J->SetArrayField(TEXT("sync_loads"),Loads);J->SetArrayField(TEXT("frames"),Samples);
    if(auto* H=FindNetLoadActor<ATemperateHillsWorld>(GetWorld())){J->SetNumberField(TEXT("seed"),H->Seed);J->SetStringField(TEXT("world_id"),H->WorldId.ToString());}
    if(auto* D=GetWorld()->GetNetDriver())
    {
        J->SetStringField(TEXT("driver"),D->GetClass()->GetName());J->SetBoolField(TEXT("async_net_loading"),D->GuidCache.IsValid()&&D->GuidCache->ShouldAsyncLoad());
#if DO_ENABLE_NET_TEST
        J->SetNumberField(TEXT("lag_ms"),D->PacketSimulationSettings.PktLag);J->SetNumberField(TEXT("loss_percent"),D->PacketSimulationSettings.PktLoss);
#endif
    }
    Save(Role+TEXT("-result"),J);UE_LOG(LogTemp,Display,TEXT("HILLS_NETLOAD_DONE %s passed=%d %s"),*Role,Passed,*Detail);
    FPlatformMisc::RequestExit(false);
}
void UHillsNetLoadAudit::Tick(float Delta)
{
    if(Done)return;const double Now=FPlatformTime::Seconds();if(Now<NextTick)return;NextTick=Now+.2;
    if(Now-Started>900.){Finish(false,TEXT("probe timeout"));return;}
    UWorld* W=GetWorld();auto* H=FindNetLoadActor<ATemperateHillsWorld>(W);auto* Clock=FindNetLoadActor<AFPSWeatherManager>(W);
    auto* Raid=W->GetSubsystem<UHillsNightRaidSubsystem>();if(!H||!Clock||!Raid)return;
    APlayerController* Local=nullptr;APlayerController* Guest=nullptr;
    for(auto It=W->GetPlayerControllerIterator();It;++It)if(auto* PC=It->Get())
        {if(PC->IsLocalController())Local=PC;else Guest=PC;}
    auto* P=HillsContinuity::Character(Local);auto* Body=P?P->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    auto* Loading=W->GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();
    const bool Ready=H->bReady&&P&&Body&&!Body->IsAppearanceLoading()&&(!Loading||!Loading->IsHoldingGameplayInput());
    int32 Count=0,Nurses=0,Fat=0;bool Valid=true;
    for(TActorIterator<ANurseZombie> It(W);It;++It)if(It->Health>0)
    {
        ++Count;if(It->IsA<AFatZombie>())++Fat;else ++Nurses;
        Valid&=It->GetMesh()&&It->GetMesh()->GetSkeletalMeshAsset()!=nullptr;
        const auto* Knockdown=It->FindComponentByClass<UHumanoidKnockdownComponent>();
        const auto* Combat=It->FindComponentByClass<UMonsterCombatComponent>();
        Valid&=Knockdown&&Knockdown->FallClip&&Knockdown->GetUpClip&&Knockdown->ProneGetUpClip&&Combat&&Combat->DizzyClip;
        if(W->GetNetMode()==NM_Client)Valid&=!It->HasAuthority();
    }
    if(Count>MaxMonsters){MaxMonsters=Count;Event(FString::Printf(TEXT("monsters_%d"),Count));}
    if(W->GetNetMode()==NM_Client)
    {
        if(Ready&&!ReadyAt){ReadyAt=Now;Phase=Late?TEXT("late_active"):TEXT("await_spawn");Event(TEXT("input_ready"));Save(Role+TEXT("-ready"),MakeShared<FJsonObject>());}
        if(Ready&&Count==3&&Nurses==2&&Fat==1&&Valid)
        {
            if(!AllAt){AllAt=Now;Phase=Late?TEXT("late_active"):TEXT("spawn_active");Event(TEXT("all_replicas_ready"));}
            if(Now-AllAt>=90.)Finish(true,TEXT("2 nurses + 1 fat zombie, replicated meshes and reaction clips ready; 90s including periodic GC observed"));
        }
        return;
    }
    if(W->GetNetMode()!=NM_ListenServer)return;
    if(Raid->IsSessionReady()&&!ClockSet)
    {auto C=Clock->CapturePersistentState();C.DayTime=.375f;C.DaySeconds=86400.f;Clock->RestorePersistentState(C);ClockSet=true;Event(TEXT("day_set"));}
    if(!Ready||!Raid->IsSessionReady())return;
    if(!ReadyAt){ReadyAt=Now;Phase=TEXT("await_spawn");Event(TEXT("input_ready"));}
    if(Step==0&&Exists(TEXT("client-ready")))
    {auto C=Clock->CapturePersistentState();C.DayTime=.84f;C.DaySeconds=86400.f;Clock->RestorePersistentState(C);Step=1;Event(TEXT("night_set"));}
    if(auto* Portal=FindNetLoadActor<AHillsNightPortal>(W);Portal&&Portal->ClosedAt<0)
    {
        auto Place=[&](APlayerController* PC,float Offset)
        {
            const FVector Look=Portal->GetActorLocation()+FVector(0,0,150);
            FVector At=Portal->GetActorLocation()+Portal->GetActorRightVector()*(1600.+Offset);
            At.Z=H->Height(At.X,At.Y)+5;HillsContinuity::Place(PC,At,Look,false);
        };
        if(!Positioned){Place(Local,350.);Positioned=true;Event(TEXT("host_at_portal"));}
        if(Guest&&Guest->GetPawn()&&PositionedGuest!=Guest->GetPawn())
        {Place(Guest,0);PositionedGuest=Guest->GetPawn();Event(TEXT("guest_at_portal"));}
    }
    if(Count==3&&AllAt==0){AllAt=Now;Phase=TEXT("spawn_active");Event(TEXT("wave_ready"));}
    if(Step==1&&Exists(TEXT("client-result"))&&!Guest)
    {Save(TEXT("late-join-ready"),MakeShared<FJsonObject>());Step=2;Event(TEXT("late_join_ready"));}
    if(Step==2&&Exists(TEXT("late-result")))Finish(Count==3&&Valid,TEXT("native nightly wave preserved across client reconnect"));
}
