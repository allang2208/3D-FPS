#include "HeQueDungeonAudit.h"
#include "AuthoredDungeonGenerator.h"
#include "DungeonRunSubsystem.h"
#include "FacilityHallEncounter.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../SceneTestPortal.h"
#include "../Monsters/HeQueMonster.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../UI/ColdSteelContainerSearchSubsystem.h"
#include "../UI/ColdSteelDungeonLoot.h"
#include "Components/CapsuleComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "NavigationSystem.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonSerializer.h"

namespace HeQueDungeonAudit
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("HeQueDungeonAudit"));}
double Clock(UWorld* W){const auto* GS=W->GetGameState();return GS?GS->GetServerWorldTimeSeconds():W->GetTimeSeconds();}
FString Encode(const TSharedRef<FJsonObject>& J)
{FString S;FJsonSerializer::Serialize(J,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&S));return S;}
TSharedPtr<FJsonObject> Decode(const FString& S)
{TSharedPtr<FJsonObject> J;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(S),J);return J;}
AActor* Named(UWorld* W,const FString& Name)
{if(!Name.IsEmpty())for(TActorIterator<AActor> It(W);It;++It)if(It->GetName()==Name)return *It;return nullptr;}
TMap<FString,int64> Counts(const FColdSteelProfile& P)
{
    TMap<FString,int64> R;
    for(const auto& I:P.Items)if(!I.Container.StartsWith(TEXT("NetView."))&&I.Place!=2)R.FindOrAdd(I.Definition)+=I.Count;
    for(const auto& I:P.AmmoPouch)R.FindOrAdd(I.Key)+=I.Value;
    return R;
}
FString Reward(const FColdSteelProfile& P)
{return FString::Printf(TEXT("%d/%lld/%d/%lld"),P.Kills,P.Souls,P.Level,P.Experience);}
TSharedRef<FJsonObject> CountJson(const TMap<FString,int64>& C)
{auto J=MakeShared<FJsonObject>();for(const auto& P:C)J->SetNumberField(P.Key,P.Value);return J;}
bool SameCounts(const TMap<FString,int64>& A,const TMap<FString,int64>& B)
{for(const auto& P:A)if(B.FindRef(P.Key)!=P.Value)return false;for(const auto& P:B)if(A.FindRef(P.Key)!=P.Value)return false;return true;}
UColdSteelProfileSave* LatestLocalSave(UColdSteelStatusModel* M)
{
    UColdSteelProfileSave* Latest=nullptr;
    for(const TCHAR* S:{TEXT("_A"),TEXT("_B")})
        if(auto* V=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(M->ProfileSlot()+S,0));V&&(!Latest||V->Profile.Generation>Latest->Profile.Generation))Latest=V;
    return Latest;
}
bool Goal(const FTrackedTaskView& V,FName Id,bool Complete)
{const auto* G=V.Objectives.FindByPredicate([Id](const auto& X){return X.Id==Id;});return G&&(G->State==ETrackedObjectiveState::Completed)==Complete;}
}

AHeQueDungeonAuditPeer::AHeQueDungeonAuditPeer()
{bReplicates=true;bOnlyRelevantToOwner=true;PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickInterval=.2f;SetNetUpdateFrequency(10.f);}
void AHeQueDungeonAuditPeer::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AHeQueDungeonAuditPeer,Phase);DOREPLIFETIME(AHeQueDungeonAuditPeer,AuditRole);DOREPLIFETIME(AHeQueDungeonAuditPeer,RunId);
    DOREPLIFETIME(AHeQueDungeonAuditPeer,ChestName);DOREPLIFETIME(AHeQueDungeonAuditPeer,PortalName);
    DOREPLIFETIME(AHeQueDungeonAuditPeer,ExpectedReward);
    DOREPLIFETIME(AHeQueDungeonAuditPeer,ContainerRevision);DOREPLIFETIME(AHeQueDungeonAuditPeer,ExecuteAt);
}
void AHeQueDungeonAuditPeer::ServerReport_Implementation(int32 InPhase,const FString& Json)
{
    if(!HeQueDungeonAudit::Enabled()||InPhase!=Phase||Json.Len()>32000)return;
    ReportPhase=InPhase;Report=Json;
    UE_LOG(LogTemp,Display,TEXT("HEQUE_DUNGEON_PEER role=%s phase=%d %s"),*AuditRole,Phase,*Json);
}
void AHeQueDungeonAuditPeer::Tick(float Dt)
{
    Super::Tick(Dt);if(!HeQueDungeonAudit::Enabled()||Phase<=0||SentPhase==Phase)return;
    auto* PC=Cast<APlayerController>(GetOwner());if(!PC||!PC->IsLocalController())return;
    auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();auto* Pawn=Cast<AFPSGAMECharacter>(PC->GetPawn());
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!PS||!Pawn||!M||M->RuntimePawn()!=Pawn)return;
    if(LocalPhase!=Phase){LocalPhase=Phase;BeganAt=FPlatformTime::Seconds();Requested=false;}
    auto* Run=UDungeonRunSubsystem::Get(GetWorld());
    if(!CachedChest.IsValid())CachedChest=HeQueDungeonAudit::Named(GetWorld(),ChestName);
    if(!CachedPortal.IsValid())CachedPortal=HeQueDungeonAudit::Named(GetWorld(),PortalName);
    auto* Chest=CachedChest.Get();auto* Portal=Cast<ASceneTestPortal>(CachedPortal.Get());
    const double Age=FPlatformTime::Seconds()-BeganAt;
    const bool Active=Run&&Run->IsRunActive()&&Run->RunId()==RunId;
    bool Pass=Active;
    if(Phase==1)Pass&=M->Snapshot().DungeonRun.RunId==RunId;
    if(Phase==2)Pass&=Run->IsWelcomeEliteDefeated();
    if(Phase==3)
    {
        Pass&=Run->AnyThemedRouteCleared();
        for(const auto& N:Run->AllNodes())if(N.Route==TEXT("Archive")&&N.bCombatRoom)Pass&=Run->IsRoomCleared(N.Id);
    }
    FTrackedTaskView View;
    if(Active)
    {
        TArray<FTrackedTaskView> Tasks;Run->AppendTrackedTasks(Pawn,Tasks);
        if(const auto* Task=Tasks.FindByPredicate([](const FTrackedTaskView& T){return T.Id==TEXT("dungeon.exploration");}))View=*Task;
    }
    if(Phase==4||Phase==5||Phase==10)
    {
        const bool Defeated=Phase>=5,Looted=Phase==10;
        Pass&=Chest&&Portal&&Run->IsFinalBossDefeated()==Defeated&&Run->IsFinalTreasureLooted()==Looted
            &&Chest->ActorHasTag(TEXT("DungeonReward.Locked"))==!Defeated&&Portal->ActorHasTag(TEXT("DungeonReward.Locked"))==!Defeated
            &&HeQueDungeonAudit::Goal(View,TEXT("final.heque"),Defeated);
        if(Defeated)Pass&=HeQueDungeonAudit::Goal(View,TEXT("final.treasure"),Looted)&&HeQueDungeonAudit::Goal(View,TEXT("final.return"),false);
        if(Phase==4){int32 Bosses=0;for(TActorIterator<AHeQueMonster> It(GetWorld());It;++It)if(!It->Dead())++Bosses;Pass&=Bosses==1;}
    }
    if(Phase>=6&&Phase<=9)
    {
        Pass&=Chest&&UColdSteelContainerSearchSubsystem::CanAccess(Pawn,Chest);
        if(Pass&&!Requested&&!PS->InventoryRequestPending()&&HeQueDungeonAudit::Clock(GetWorld())>=ExecuteAt)
        {
            FColdSteelInventoryRequest Request;Request.Target=Chest;Request.ContainerRevision=ContainerRevision;
            Request.Action=(Phase==6||Phase==9)?EColdSteelInventoryAction::ContainerOpen:EColdSteelInventoryAction::ContainerRetrieveAll;
            Requested=PS->RequestInventoryAction(Request);
            UE_LOG(LogTemp,Display,TEXT("HEQUE_DUNGEON_REQUEST role=%s phase=%d dispatched=%d revision=%lld"),*AuditRole,Phase,Requested,ContainerRevision);
        }
        Pass&=Requested&&!PS->InventoryRequestPending()&&M->HasNetworkContainerView()&&Age>1.;
        if(Phase==6)
        {
            auto* Search=GetWorld()->GetSubsystem<UColdSteelContainerSearchSubsystem>();
            Pass&=Search&&Search->IsActive(PC,Chest)&&!Search->IsSearching(PC,M->ActiveContainer);
            for(const auto& I:M->Items())if(I.Container.StartsWith(TEXT("NetView.")))Pass&=I.Definition!=TEXT("container_unsearched");
        }
    }
    if(Phase==11)
    {
        Pass&=Portal&&Portal->IsWithinInteractionRange(Pawn);
        if(Pass&&!Requested&&!PS->InventoryRequestPending())
        {
            if(auto* FPS=Cast<AFPSGAMEPlayerController>(PC);FPS&&FPS->GetColdSteelHUD()&&FPS->GetColdSteelHUD()->IsInventoryOpen())FPS->GetColdSteelHUD()->ToggleInventory();
            else M->EndStorageSession();
            if(AuditRole==TEXT("guest"))Requested=PS->RequestTeamTravel(Portal);else Requested=true;
        }
        Pass&=Requested;
    }
    auto Profile=M->Snapshot();
    if(Phase==5||Phase==10||Phase==12)Pass&=HeQueDungeonAudit::Reward(Profile)==ExpectedReward;
    if(Phase==12)
    {
        Pass=HeQueDungeonAudit::Reward(Profile)==ExpectedReward&&!Active&&UGameplayStatics::GetCurrentLevelName(this,true)==TEXT("DayNight_Lighting")
            &&Profile.DungeonRun.RunId==RunId&&Profile.DungeonRun.bCompleted&&!PS->InventoryRequestPending();
        if(Age<5.)return;
    }
    const double Timeout=Phase<=3?180.:Phase==6?90.:40.;
    if(!Pass&&Age<Timeout)return;
    auto J=MakeShared<FJsonObject>();J->SetBoolField(TEXT("pass"),Pass);J->SetStringField(TEXT("map"),UGameplayStatics::GetCurrentLevelName(this,true));
    J->SetStringField(TEXT("run"),Active?Run->RunId():FString());J->SetStringField(TEXT("profile_run"),Profile.DungeonRun.RunId);
    J->SetBoolField(TEXT("completed"),Profile.DungeonRun.bCompleted);J->SetBoolField(TEXT("boss"),Active&&Run->IsFinalBossDefeated());
    J->SetBoolField(TEXT("looted"),Active&&Run->IsFinalTreasureLooted());J->SetNumberField(TEXT("nodes"),Active?Run->NumNodes():0);
    J->SetNumberField(TEXT("kills"),Profile.Kills);J->SetNumberField(TEXT("souls"),Profile.Souls);J->SetNumberField(TEXT("level"),Profile.Level);
    J->SetNumberField(TEXT("experience"),Profile.Experience);J->SetNumberField(TEXT("inventory_revision"),Profile.CampfireInventoryRevision);
    J->SetObjectField(TEXT("items"),HeQueDungeonAudit::CountJson(HeQueDungeonAudit::Counts(Profile)));
    J->SetStringField(TEXT("message"),M->ResultMessage());J->SetBoolField(TEXT("requested"),Requested);
    FString Goals;for(const auto& G:View.Objectives)Goals+=FString::Printf(TEXT("%s:%d;"),*G.Id.ToString(),G.State==ETrackedObjectiveState::Completed?1:0);J->SetStringField(TEXT("goals"),Goals);
    if(Phase==12)
    {
        const auto* Save=HeQueDungeonAudit::LatestLocalSave(M);
        J->SetStringField(TEXT("slot"),M->ProfileSlot());J->SetBoolField(TEXT("disk_completed"),Save&&Save->Profile.DungeonRun.RunId==RunId&&Save->Profile.DungeonRun.bCompleted);
        J->SetObjectField(TEXT("disk_items"),HeQueDungeonAudit::CountJson(Save?HeQueDungeonAudit::Counts(Save->Profile):TMap<FString,int64>()));
        J->SetNumberField(TEXT("disk_souls"),Save?Save->Profile.Souls:-1);
    }
    SentPhase=Phase;ServerReport(Phase,HeQueDungeonAudit::Encode(J));
}

bool UHeQueDungeonAuditSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{return HeQueDungeonAudit::Enabled();}
void UHeQueDungeonAuditSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{Super::Initialize(Collection);Started=StepAt=FPlatformTime::Seconds();}
TStatId UHeQueDungeonAuditSubsystem::GetStatId() const
{RETURN_QUICK_DECLARE_CYCLE_STAT(HeQueDungeonAudit,STATGROUP_Tickables);}
void UHeQueDungeonAuditSubsystem::Check(bool Pass,const FString& Detail)
{
    ++Checks;if(!Pass)Failures.Add(Detail);
    UE_LOG(LogTemp,Display,TEXT("HEQUE_DUNGEON_CHECK pass=%d %s"),Pass,*Detail);
}
void UHeQueDungeonAuditSubsystem::Finish(const FString& Reason)
{
    if(Done)return;Done=true;auto J=MakeShared<FJsonObject>();J->SetBoolField(TEXT("passed"),Failures.IsEmpty());
    J->SetNumberField(TEXT("checks"),Checks);J->SetStringField(TEXT("reason"),Reason);J->SetStringField(TEXT("run"),RunId);
    TArray<TSharedPtr<FJsonValue>> Errors;for(const auto& F:Failures)Errors.Add(MakeShared<FJsonValueString>(F));J->SetArrayField(TEXT("failures"),Errors);
    const FString Json=HeQueDungeonAudit::Encode(J);FString Path;
    if(FParse::Value(FCommandLine::Get(),TEXT("HeQueDungeonOutput="),Path))FFileHelper::SaveStringToFile(Json,*Path);
    UE_LOG(LogTemp,Display,TEXT("HEQUE_DUNGEON_RESULT %s"),*Json);FPlatformMisc::RequestExit(false);
}
void UHeQueDungeonAuditSubsystem::Command(int32 Phase)
{
    Step=Phase;StepAt=FPlatformTime::Seconds();
    for(AHeQueDungeonAuditPeer* P:Peers)
    {
        P->Phase=Phase;P->RunId=RunId;P->ChestName=Chest.IsValid()?Chest->GetName():FString();P->PortalName=Portal.IsValid()?Portal->GetName():FString();
        P->ContainerRevision=RaceRevision;P->ExecuteAt=HeQueDungeonAudit::Clock(GetWorld())+1.;P->ForceNetUpdate();
        if(const auto* PC=Cast<APlayerController>(P->GetOwner()))if(const auto* M=ColdSteelAuthority::ForPawn(PC->GetPawn()))P->ExpectedReward=HeQueDungeonAudit::Reward(M->Snapshot());
    }
    UE_LOG(LogTemp,Display,TEXT("HEQUE_DUNGEON_PHASE %d"),Phase);
}
bool UHeQueDungeonAuditSubsystem::ReportsReady(int32 Phase)
{
    if(ValidatedPhase==Phase)return true;
    if(Peers.Num()!=2)return false;
    for(const AHeQueDungeonAuditPeer* P:Peers)if(!IsValid(P)||P->ReportPhase!=Phase)return false;
    ValidatedPhase=Phase;bool Okay=true;
    for(const AHeQueDungeonAuditPeer* P:Peers)
    {
        const auto J=HeQueDungeonAudit::Decode(P->Report);const bool Pass=J&&J->GetBoolField(TEXT("pass"));
        Check(Pass,FString::Printf(TEXT("peer %s phase %d"),*P->AuditRole,Phase));Okay&=Pass;
    }
    if(!Okay)Finish(TEXT("peer transition timed out"));
    return Okay;
}
void UHeQueDungeonAuditSubsystem::CaptureProfiles(TMap<FString,FColdSteelProfile>& Into)
{
    Into.Reset();for(const AHeQueDungeonAuditPeer* P:Peers)
        if(const auto* PC=Cast<APlayerController>(P->GetOwner()))if(auto* M=ColdSteelAuthority::ForPawn(PC->GetPawn()))Into.Add(P->AuditRole,M->Snapshot());
}
void UHeQueDungeonAuditSubsystem::CheckPeerProfiles()
{
    for(const AHeQueDungeonAuditPeer* P:Peers)
    {
        const auto* PC=Cast<APlayerController>(P->GetOwner());const auto* M=PC?ColdSteelAuthority::ForPawn(PC->GetPawn()):nullptr;
        const auto J=HeQueDungeonAudit::Decode(P->Report);if(!M||!J){Check(false,TEXT("missing peer profile"));continue;}
        const auto Profile=M->Snapshot();TMap<FString,int64> ClientCounts;
        for(const auto& V:J->GetObjectField(TEXT("items"))->Values)ClientCounts.Add(FString(*V.Key),int64(V.Value->AsNumber()));
        Check(HeQueDungeonAudit::SameCounts(HeQueDungeonAudit::Counts(Profile),ClientCounts),P->AuditRole+TEXT(" owner inventory equals authority"));
        Check(int64(J->GetNumberField(TEXT("souls")))==Profile.Souls&&int32(J->GetNumberField(TEXT("kills")))==Profile.Kills
            &&int32(J->GetNumberField(TEXT("level")))==Profile.Level&&int64(J->GetNumberField(TEXT("experience")))==Profile.Experience,P->AuditRole+TEXT(" reward/progression equals authority"));
    }
}
bool UHeQueDungeonAuditSubsystem::PlaceRoom(int32 Id)
{
    const auto* Run=UDungeonRunSubsystem::Get(GetWorld());const auto* Node=Run?Run->NodeById(Id):nullptr;if(!Node)return false;
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());int32 Index=0;
    for(AHeQueDungeonAuditPeer* Peer:Peers)
    {
        auto* PC=Cast<APlayerController>(Peer->GetOwner());auto* Pawn=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;if(!Pawn)return false;
        TArray<FVector> Candidates;for(const auto& Door:Node->Doors)Candidates.Add(Door.FloorCenter-Door.OutwardNormal*(450.f+Index*140.f));
        for(const auto& Cell:Node->WalkCells)Candidates.Add(FVector(Cell.GetCenter().X,Cell.GetCenter().Y,Cell.Min.Z));
        Candidates.Add(Node->Origin);bool Placed=false;
        for(const auto& Candidate:Candidates)
        {
            FNavLocation At;if(!Nav||!Nav->ProjectPointToNavigation(Candidate,At,FVector(350,350,220))||!Node->AllowsSpawn(At.Location))continue;
            Pawn->GetCharacterMovement()->StopMovementImmediately();Pawn->SetActorLocation(At.Location+FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3.f),false,nullptr,ETeleportType::TeleportPhysics);
            Pawn->SetCanBeDamaged(false);Pawn->ForceNetUpdate();Placed=true;break;
        }
        if(!Placed){UE_LOG(LogTemp,Warning,TEXT("HEQUE_DUNGEON_PLACE waiting for nav node=%d module=%s"),Id,*Node->Module);return false;}++Index;
    }
    LastPlacedRoom=Id;LastMove=FPlatformTime::Seconds();UE_LOG(LogTemp,Display,TEXT("HEQUE_DUNGEON_ROOM node=%d module=%s route=%s"),Id,*Node->Module,*Node->Route);return true;
}
bool UHeQueDungeonAuditSubsystem::PlaceNear(AActor* Target,bool IsPortal)
{
    if(!Target)return false;int32 Index=0;
    for(AHeQueDungeonAuditPeer* Peer:Peers)
    {
        auto* PC=Cast<APlayerController>(Peer->GetOwner());auto* Pawn=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;if(!Pawn)return false;
        bool Placed=false;
        for(int32 I=0;I<24;++I)
        {
            const float Angle=FMath::DegreesToRadians(float(I*15+Index*180));FVector At=Target->GetActorLocation()+FVector(FMath::Cos(Angle)*145.f,FMath::Sin(Angle)*145.f,0);
            FCollisionQueryParams Q(SCENE_QUERY_STAT(HeQueDungeonAuditGround),false,Target);for(AHeQueDungeonAuditPeer* P:Peers)if(auto* C=Cast<APlayerController>(P->GetOwner()))Q.AddIgnoredActor(C->GetPawn());
            FHitResult Hit;if(!GetWorld()->LineTraceSingleByChannel(Hit,At+FVector(0,0,180),At-FVector(0,0,200),ECC_WorldStatic,Q))continue;
            Pawn->GetCharacterMovement()->StopMovementImmediately();Pawn->SetActorLocation(Hit.ImpactPoint+FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3.f),false,nullptr,ETeleportType::TeleportPhysics);
            Placed=IsPortal?CastChecked<ASceneTestPortal>(Target)->IsWithinInteractionRange(Pawn):UColdSteelContainerSearchSubsystem::CanAccess(Pawn,Target);
            if(Placed){Pawn->ForceNetUpdate();break;}
        }
        if(!Placed)return false;++Index;
    }
    return true;
}
void UHeQueDungeonAuditSubsystem::KillSpawned()
{
    const double Now=FPlatformTime::Seconds();if(Now-LastKill<.25)return;LastKill=Now;
    auto* PC=Peers.IsEmpty()?nullptr:Cast<APlayerController>(Peers[0]->GetOwner());if(!PC)return;
    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        if(It->IsA<AHeQueMonster>()||!It->Tags.ContainsByPredicate([](FName T){return T.ToString().StartsWith(TEXT("DungeonEnemy."));}))continue;
        auto* C=It->FindComponentByClass<UMonsterCombatComponent>();float HP=0,Max=0;FText Name;
        if(C&&C->GetVitals(HP,Max,Name)&&HP>0){UGameplayStatics::ApplyDamage(*It,1.e8f,PC,PC->GetPawn(),UDamageType::StaticClass());return;}
    }
}
void UHeQueDungeonAuditSubsystem::Tick(float Dt)
{
    UWorld* W=GetWorld();if(Done||!W||!W->IsGameWorld()||W->GetNetMode()==NM_Client||W->GetNetMode()==NM_Standalone)return;
    const double Now=FPlatformTime::Seconds();
    if(!StartedLogged){StartedLogged=true;UE_LOG(LogTemp,Display,TEXT("HEQUE_DUNGEON_HOST_READY"));}
    if(Now-Started>1200.||Now-StepAt>(Step==0?600.:240.))
    {Check(false,FString::Printf(TEXT("timeout phase %d map %s"),Step,*UGameplayStatics::GetCurrentLevelName(this,true)));Finish(TEXT("timeout"));return;}
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    if(Step==0&&Now-LastDiagnostic>15.)
    {
        LastDiagnostic=Now;
        const auto* PendingRun=UDungeonRunSubsystem::Get(W);
        UE_LOG(LogTemp,Display,TEXT("HEQUE_DUNGEON_WAIT peers=%d controllers=%d active=%d"),Peers.Num(),W->GetNumPlayerControllers(),PendingRun&&PendingRun->IsRunActive());
        for(TActorIterator<AAuthoredDungeonGenerator> It(W);It;++It)
        {
            const auto Metrics=HeQueDungeonAudit::Decode(It->GetGenerationMetricsJson());
            if(Metrics)UE_LOG(LogTemp,Display,TEXT("HEQUE_DUNGEON_GENERATION %s"),*HeQueDungeonAudit::Encode(Metrics.ToSharedRef()));
            if(It->ActorHasTag(TEXT("DungeonAssembly.Failed"))){Check(false,It->LayoutDescription);Finish(TEXT("dungeon generation failed"));return;}
        }
    }
    if(Step==11&&Map==TEXT("DayNight_Lighting"))
    {Peers.Reset();AuditWorld=W;Step=12;StepAt=Now;}
    if(Step!=0&&Step!=12&&AuditWorld.Get()!=W)return;
    if(Step==0||Step==12)
    {
        for(auto It=W->GetPlayerControllerIterator();It;++It)
        {
            auto* PC=It->Get();auto* PS=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr;
            if(!PC||!PC->GetPawn()||!PS||!ColdSteelAuthority::ForPawn(PC->GetPawn()))continue;
            if(Peers.ContainsByPredicate([PC](const AHeQueDungeonAuditPeer* P){return IsValid(P)&&P->GetOwner()==PC;}))continue;
            FActorSpawnParameters Params;Params.Owner=PC;auto* Peer=W->SpawnActor<AHeQueDungeonAuditPeer>(Params);
            Peer->AuditRole=PC->IsLocalController()?TEXT("host"):TEXT("guest");Peers.Add(Peer);
        }
        if(Peers.Num()!=2)return;
        if(Step==12&&Peers[0]->Phase!=12){Command(12);return;}
    }
    auto* Run=UDungeonRunSubsystem::Get(W);
    if(Step==0)
    {
        if(!Run||!Run->IsRunActive())return;
        RunId=Run->RunId();AuditWorld=W;
        for(TActorIterator<AActor> It(W);It;++It){if(It->ActorHasTag(TEXT("DungeonFinalTreasure")))Chest=*It;if(It->ActorHasTag(TEXT("DungeonFinalReturn")))Portal=*It;}
        if(!Chest.IsValid()||!Portal.IsValid())return;
        Destination=CastChecked<ASceneTestPortal>(Portal)->DestinationMap();
        int32 Best=MAX_int32;
        for(int32 R=1;R<=3;++R)
        {
            TArray<int32> Rooms;for(const auto& N:Run->AllNodes())if(N.bCombatRoom&&N.Route==FString::Printf(TEXT("Route%d"),R))Rooms.Add(N.Id);
            if(!Rooms.IsEmpty()&&Rooms.Num()<Best){Best=Rooms.Num();RouteRooms=MoveTemp(Rooms);}
        }
        Check(!RouteRooms.IsEmpty(),TEXT("generated complete themed route exists"));if(RouteRooms.IsEmpty()){Finish(TEXT("route unavailable"));return;}
        Command(1);return;
    }
    if(Step==1&&ReportsReady(1))
    {
        for(const auto& N:Run->AllNodes())if(N.Module==TEXT("FacilityTransit"))if(PlaceRoom(N.Id)){Command(2);return;}
    }
    if(Step==2||Step==3)KillSpawned();
    if(Step==2&&Run->IsWelcomeEliteDefeated()&&ReportsReady(2))
    {if(PlaceRoom(RouteRooms[0])){RouteCursor=1;Command(3);}return;}
    if(Step==3)
    {
        if(!Run->AnyThemedRouteCleared()&&Now-LastMove>6.){PlaceRoom(RouteRooms[RouteCursor%RouteRooms.Num()]);++RouteCursor;}
        if(Run->AnyThemedRouteCleared())for(const auto& N:Run->AllNodes())if(N.Route==TEXT("Archive")&&N.bCombatRoom&&!Run->IsRoomCleared(N.Id))
        {if(LastPlacedRoom!=N.Id)PlaceRoom(N.Id);return;}
        if(Run->AnyThemedRouteCleared()&&ReportsReady(3))
            for(const auto& N:Run->AllNodes())if(N.Module==TEXT("BossPumpHall"))if(PlaceRoom(N.Id)){Command(4);return;}
    }
    if(Step==4&&ReportsReady(4))
    {
        AHeQueMonster* Boss=nullptr;for(TActorIterator<AHeQueMonster> It(W);It;++It)if(!It->Dead()){Boss=*It;break;}
        auto* Guest=Peers.FindByPredicate([](const AHeQueDungeonAuditPeer* P){return P->AuditRole==TEXT("guest");});
        auto* PC=Guest?Cast<APlayerController>((*Guest)->GetOwner()):nullptr;auto* M=PC?ColdSteelAuthority::ForPawn(PC->GetPawn()):nullptr;
        if(!Boss||!M){Check(false,TEXT("actual final boss or guest missing"));Finish(TEXT("boss missing"));return;}
        const auto Before=M->Snapshot();
        UE_LOG(LogTemp,Display,TEXT("HEQUE_DUNGEON_BOSS reward=%d health=%.1f killer=guest"),Boss->ExperienceReward,Boss->Health);
        UGameplayStatics::ApplyDamage(Boss,1.e8f,PC,PC->GetPawn(),UDamageType::StaticClass());const auto After=M->Snapshot();
        UGameplayStatics::ApplyDamage(Boss,1.e8f,PC,PC->GetPawn(),UDamageType::StaticClass());
        Check(Boss->Dead()&&Run->IsFinalBossDefeated(),TEXT("real final boss death advances objective"));
        Check(After.Kills==Before.Kills+1&&After.Souls>Before.Souls,TEXT("guest receives final boss kill reward"));
        Check(M->Snapshot().Kills==After.Kills&&M->Snapshot().Souls==After.Souls,TEXT("duplicate fatal hit does not reward twice"));
        Command(5);return;
    }
    if(Step==5&&ReportsReady(5))
    {
        if(Now-StepAt<3.)return;
        CheckPeerProfiles();CaptureProfiles(BeforeLoot);
        if(PlaceNear(Chest.Get(),false)){Command(6);return;}
    }
    auto* Shared=W->GetSubsystem<UColdSteelSharedInventorySubsystem>();
    if(Step==6&&ReportsReady(6))
    {
        ChestKey=FColdSteelDungeonLoot::ChestStorageKey(Chest.Get());const auto* C=Shared?Shared->Data().Containers.Find(ChestKey):nullptr;
        if(!C){Check(false,TEXT("shared final chest missing"));Finish(TEXT("chest unavailable"));return;}
        Check(C->bSeeded&&!C->Items.IsEmpty(),TEXT("concurrent open seeds one nonempty shared chest"));
        Loot.Reset();for(const auto& I:C->Items)Loot.FindOrAdd(I.Definition)+=I.Count;
        RaceRevision=C->Revision;SharedSlot=Shared->WorldKey();Check(RaceRevision==1,TEXT("concurrent open did not reroll or recommit"));
        Check(!Run->IsFinalTreasureLooted(),TEXT("opening/searching is not looting"));Command(7);return;
    }
    if(Step==7&&ReportsReady(7))
    {
        const auto* C=Shared->Data().Containers.Find(ChestKey);Check(C&&C->Items.IsEmpty()&&C->Revision==RaceRevision+1,TEXT("same revision race commits once and drains chest"));
        if(!C){Finish(TEXT("chest lost"));return;}PostRaceRevision=C->Revision;CaptureProfiles(AfterLoot);CheckPeerProfiles();
        TMap<FString,int64> Expected,Actual;int32 Winners=0;
        for(const auto& Pair:BeforeLoot)for(const auto& I:HeQueDungeonAudit::Counts(Pair.Value))Expected.FindOrAdd(I.Key)+=I.Value;
        for(const auto& I:Loot)Expected.FindOrAdd(I.Key)+=I.Value;
        for(const auto& Pair:AfterLoot)
        {const auto Counts=HeQueDungeonAudit::Counts(Pair.Value);for(const auto& I:Counts)Actual.FindOrAdd(I.Key)+=I.Value;Winners+=!HeQueDungeonAudit::SameCounts(Counts,HeQueDungeonAudit::Counts(BeforeLoot.FindChecked(Pair.Key)));}
        Check(HeQueDungeonAudit::SameCounts(Expected,Actual)&&Winners==1,TEXT("loot conserved across both inventories; exactly one winner"));
        Command(8);return;
    }
    if((Step==8||Step==9)&&ReportsReady(Step))
    {
        const auto* C=Shared->Data().Containers.Find(ChestKey);Check(C&&C->Items.IsEmpty()&&C->bSeeded&&C->Revision==PostRaceRevision,TEXT("stale retry/reopen does not duplicate rewards"));
        TMap<FString,FColdSteelProfile> Current;CaptureProfiles(Current);
        for(const auto& P:Current)Check(HeQueDungeonAudit::SameCounts(HeQueDungeonAudit::Counts(P.Value),HeQueDungeonAudit::Counts(AfterLoot.FindChecked(P.Key))),P.Key+TEXT(" loot unchanged by retry"));
        Command(Step+1);return;
    }
    if(Step==10&&ReportsReady(10))
    {CheckPeerProfiles();if(PlaceNear(Portal.Get(),true)){Command(11);return;}}
    if(Step==12&&ReportsReady(12))
    {
        CheckPeerProfiles();
        for(const AHeQueDungeonAuditPeer* P:Peers)
        {
            const auto J=HeQueDungeonAudit::Decode(P->Report);const auto* PC=Cast<APlayerController>(P->GetOwner());const auto* PS=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr;
            const auto* M=PC?ColdSteelAuthority::ForPawn(PC->GetPawn()):nullptr;
            Check(M&&M->Snapshot().DungeonRun.RunId==RunId&&M->Snapshot().DungeonRun.bCompleted,P->AuditRole+TEXT(" authority completion survived ServerTravel"));
            Check(J&&J->GetBoolField(TEXT("disk_completed")),P->AuditRole+TEXT(" owner disk contains completed run"));
            TMap<FString,int64> Disk;if(J)for(const auto& V:J->GetObjectField(TEXT("disk_items"))->Values)Disk.Add(FString(*V.Key),int64(V.Value->AsNumber()));
            Check(HeQueDungeonAudit::SameCounts(Disk,HeQueDungeonAudit::Counts(AfterLoot.FindChecked(P->AuditRole))),P->AuditRole+TEXT(" owner disk preserves loot"));
            if(PS&&P->AuditRole==TEXT("guest"))
            {
                const auto* Save=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(PS->CampfireGuestSlot(),0));
                Check(Save&&Save->Profile.DungeonRun.RunId==RunId&&Save->Profile.DungeonRun.bCompleted&&HeQueDungeonAudit::SameCounts(HeQueDungeonAudit::Counts(Save->Profile),HeQueDungeonAudit::Counts(AfterLoot.FindChecked(P->AuditRole))),TEXT("host guest shadow disk preserves completion and loot"));
            }
        }
        const auto* SavedWorld=Cast<UColdSteelSharedInventorySave>(UGameplayStatics::LoadGameFromSlot(SharedSlot,0));const auto* C=SavedWorld?SavedWorld->Data.Containers.Find(ChestKey):nullptr;
        Check(C&&C->bSeeded&&C->Items.IsEmpty()&&C->Revision==PostRaceRevision,TEXT("dungeon shared chest persisted drained"));
        Finish(TEXT("generated dungeon route, final boss, concurrent loot and real team return finished"));
    }
}


