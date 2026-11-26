#include "HillsMultiplayerClosure.h"
#include "../FPSGAMECharacter.h"
#include "../FPSWeatherManager.h"
#include "../SceneTestPortal.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickup.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../Building/BuildingDaylight.h"
#include "../Building/ColdSteelDoor.h"
#include "../Movement/FPSDoorPushComponent.h"
#include "../Monsters/WildlifeAnimal.h"
#include "../Monsters/WildlifeSubsystem.h"
#include "../Monsters/WolfMonster.h"
#include "../Monsters/MonsterCorpseRagdollComponent.h"
#include "../Monsters/QuadrupedAnimationTemplate.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Containers/Ticker.h"
#include "Engine/DamageEvents.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Net/UnrealNetwork.h"
#include "SceneView.h"
#include "Serialization/JsonSerializer.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#endif

namespace HillsClosure
{
bool Enabled()
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return FParse::Param(FCommandLine::Get(),TEXT("HillsMultiplayerClosure"));
#endif
}
FString Output(){FString P;FParse::Value(FCommandLine::Get(),TEXT("HillsClosureOutput="),P);return P;}
double Clock(UWorld* W){return W->GetGameState()?W->GetGameState()->GetServerWorldTimeSeconds():W->GetTimeSeconds();}
UColdSteelStatusModel* Model(UWorld* W){return W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();}
int64 Count(UColdSteelStatusModel* M)
{int64 N=0;if(M)for(const auto& I:M->Snapshot().Items)if(I.Definition==TEXT("enhancement_stone")&&I.Place!=2)N+=I.Count;return N;}
int32 WildlifeCount(UWorld* W)
{int32 N=0;for(TActorIterator<AColdSteelAnimal> It(W);It;++It)++N;for(TActorIterator<AWolfMonster> It(W);It;++It)if(UWildlifeSubsystem::IsCatalogClass(FSoftObjectPath(It->GetClass())))++N;return N;}
void Place(APlayerController* PC,const FVector& P)
{
    auto* Pawn=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;if(!Pawn)return;
    Pawn->SetCanBeDamaged(false);Pawn->GetCharacterMovement()->StopMovementImmediately();Pawn->GetCharacterMovement()->DisableMovement();
    Pawn->SetActorLocation(P,false,nullptr,ETeleportType::TeleportPhysics);
}
void Aim(APlayerController* PC,AActor* Target)
{if(!PC||!IsValid(Target))return;PC->bShowMouseCursor=false;FVector Eye;FRotator Rotation;PC->GetPlayerViewPoint(Eye,Rotation);FVector Point=Target->GetActorLocation();if(Target->IsA<AColdSteelDoor>())Point+=FVector(0,0,110);PC->SetControlRotation((Point-Eye).Rotation());}
float Exposure(UWorld* W,const FVector& Eye)
{
    FSceneViewFamilyContext Family(FSceneViewFamily::ConstructionValues(nullptr,W->Scene,FEngineShowFlags(ESFIM_Game)));
    FSceneViewInitOptions Options;Options.ViewFamily=&Family;Options.SetViewRectangle(FIntRect(0,0,64,64));
    Options.ViewOrigin=Eye;Options.ViewRotationMatrix=FMatrix::Identity;Options.ProjectionMatrix=FMatrix::Identity;
    FSceneView View(Options);View.FinalPostProcessSettings.AutoExposureBias=0.f;
    for(TActorIterator<ABuildingDaylight> It(W);It;++It)It->OverrideBlendableSettings(View,1.f);
    return View.FinalPostProcessSettings.AutoExposureBias;
}
FVector OutsideRoom(UWorld* W,ABuildingDaylight* Room)
{
    FVector Local=(Room->RoomMinimum+Room->RoomMaximum)*.5;Local.X=Room->RoomMinimum.X-250.;
    const FVector Candidate=Room->GetActorTransform().TransformPosition(Local);
    if(FMath::Abs(Exposure(W,Candidate+FVector(0,0,64)))<.01f)return Candidate;
    Local.Y=Room->RoomMinimum.Y-500.;return Room->GetActorTransform().TransformPosition(Local);
}
bool Rooms(UWorld* W,FString& Detail)
{
    int32 N=0;bool OK=true;TArray<TSharedPtr<FJsonValue>> Samples;
    for(TActorIterator<ABuildingDaylight> It(W);It;++It)
    {
        ++N;const auto T=It->GetActorTransform();const FVector Center=(It->RoomMinimum+It->RoomMaximum)*.5;
        float Previous=-1.f,Peak=0.f;TArray<TSharedPtr<FJsonValue>> Values;
        for(int32 I=0;I<=20;++I)
        {
            FVector P=Center;P.X=It->RoomMinimum.X-20.+(It->EntranceTransitionCm/T.GetScale3D().X+40.)*I/20.;
            const float V=Exposure(W,T.TransformPosition(P));Values.Add(MakeShared<FJsonValueNumber>(V));
            OK&=FMath::IsFinite(V)&&V>=Previous-.001f&&V<=1.25f;Previous=V;Peak=FMath::Max(Peak,V);
        }
        OK&=Peak>.5f;auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("room"),It->GetName());R->SetArrayField(TEXT("entry_exit_stops"),Values);Samples.Add(MakeShared<FJsonValueObject>(R));
    }
    auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("rooms"),N);R->SetArrayField(TEXT("samples"),Samples);
    FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Detail));return OK&&N>=8;
}
void Save(const FString& Name,const TSharedRef<FJsonObject>& R)
{FString J;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&J));IFileManager::Get().MakeDirectory(*Output(),true);FFileHelper::SaveStringToFile(J,*(Output()/Name+TEXT(".json")));}
}

AHillsMultiplayerClosure::AHillsMultiplayerClosure()
{bReplicates=true;bOnlyRelevantToOwner=true;PrimaryActorTick.bCanEverTick=true;SetNetUpdateFrequency(30.f);}
void AHillsMultiplayerClosure::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AHillsMultiplayerClosure,Command);DOREPLIFETIME(AHillsMultiplayerClosure,Subject);DOREPLIFETIME(AHillsMultiplayerClosure,ItemId);DOREPLIFETIME(AHillsMultiplayerClosure,Place);DOREPLIFETIME(AHillsMultiplayerClosure,ExecuteAt);DOREPLIFETIME(AHillsMultiplayerClosure,ExpectedCount);}
void AHillsMultiplayerClosure::ServerObserved_Implementation(int32 Case,bool OK,const FString& Text,FGuid Id,int64 N)
{if(!HillsClosure::Enabled()||Case!=Command)return;Observed=Case;Passed=OK;Detail=Text;Identity=Id;Count=N;}
void AHillsMultiplayerClosure::ClientFinish_Implementation(bool OK)
{if(!HillsClosure::Enabled())return;auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),OK);R->SetNumberField(TEXT("last_command"),LastCommand);HillsClosure::Save(TEXT("client-finished"),R);FPlatformMisc::RequestExit(false);}
void AHillsMultiplayerClosure::Tick(float Dt)
{
    Super::Tick(Dt);if(!HillsClosure::Enabled()||HasAuthority()||Command<=0)return;
    auto* PC=Cast<APlayerController>(GetOwner());auto* M=HillsClosure::Model(GetWorld());
    auto* PS=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr;if(!PC||!PC->GetPawn()||!M||!PS)return;
    if(Command!=LastCommand){LastCommand=Command;Began=FPlatformTime::Seconds();AssetsIdleAt=0.;Requested=Reported=false;}
    if(Reported)return;const double Age=FPlatformTime::Seconds()-Began;bool Ready=false,OK=false;FString Text;
    auto* Wolf=Cast<AWolfMonster>(Subject);
    if(Wolf)ObservedWolf=Wolf;
    if(Command==50)
    {
        bool Loaded=false;for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)Loaded|=It->bReady;
#if WITH_EDITOR
        Loaded&=FAssetCompilingManager::Get().GetNumRemainingAssets()==0;
#endif
        Loaded&=!PC->IsMoveInputIgnored();
        if(!Loaded)AssetsIdleAt=0.;else if(AssetsIdleAt==0.)AssetsIdleAt=FPlatformTime::Seconds();
        Ready=AssetsIdleAt>0.&&FPlatformTime::Seconds()-AssetsIdleAt>5.;OK=Ready;Text=TEXT("real client hills ready and initial asset compilation idle");
    }
    else if(Command==1)
    {Ready=Wolf!=nullptr;OK=Ready&&!Wolf->Dead();if(Wolf)Text=FString::Printf(TEXT("wolf health=%.2f state=%d"),Wolf->Health,int32(Wolf->State));}
    else if(Command==2||Command==22||Command==23)
    {
        auto* Anim=Wolf?Cast<UQuadrupedTemplateAnimInstance>(Wolf->GetMesh()->GetAnimInstance()):nullptr;
        const FName Wanted=Command==2?TEXT("HitRight"):TEXT("HitLeft");
        Ready=Wolf&&Anim&&Wolf->WildlifeHitPresentation.StartedAt>=ExecuteAt-.01&&Anim->ActiveAction==Wanted;
        OK=Ready&&!Wolf->Dead()&&Wolf->Health<Wolf->MaxHealth;
        if(Wolf&&Anim)Text=FString::Printf(TEXT("health=%.2f action=%s revision=%u started=%.4f expected_after=%.4f"),Wolf->Health,*Anim->ActiveAction.ToString(),Wolf->WildlifeHitPresentation.Revision,Wolf->WildlifeHitPresentation.StartedAt,ExecuteAt);
    }
    else if(Command==3)
    {
        auto* C=Wolf?Wolf->FindComponentByClass<UMonsterCorpseRagdollComponent>():nullptr;
        Ready=Wolf&&Wolf->Dead()&&C&&(C->WasAttempted()||C->IsFrozen()||C->HasSoftDeath());
        OK=Ready&&Wolf->GetCapsuleComponent()->GetCollisionEnabled()==ECollisionEnabled::NoCollision&&Wolf->GetMesh()->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Ignore;
        if(Wolf)Text=FString::Printf(TEXT("state=%d age=%.3f corpse=%d frozen=%d"),int32(Wolf->State),Wolf->StateSeconds,C&&C->WasAttempted(),C&&C->IsFrozen());
    }
    else if(Command==25)
    {Ready=Wolf&&Wolf->State==EWolfState::Flee&&FVector::Dist2D(Wolf->GetActorLocation(),Place)>40.;OK=Ready;Text=Wolf?FString::Printf(TEXT("authority flee replicated; displacement=%.1f"),FVector::Dist2D(Wolf->GetActorLocation(),Place)):TEXT("wolf missing");}
    else if(Command==4){Ready=Age>1.;OK=!ObservedWolf.IsValid();Text=TEXT("previously observed wolf actor destruction observed");}
    else if(Command>=10&&Command<=12)
    {
        HillsClosure::Aim(PC,Subject);
        if(!Requested&&HillsClosure::Clock(GetWorld())>=ExecuteAt)
        {FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Pickup;R.Target=Subject;Requested=PS->RequestInventoryAction(R);}
        Ready=Requested&&!PS->InventoryRequestPending()&&Age>4.;OK=Ready;Text=M->ResultMessage();
    }
    else if(Command==20||Command==21||Command==41)
    {Ready=Age>3.;OK=HillsClosure::Count(M)==ExpectedCount&&M->SaveNow();Text=M->Snapshot().NetworkProfileId.ToString();}
    else if(Command==30||Command==31)
    {
        Ready=Age>3.;FVector Eye;FRotator Rot;PC->GetPlayerViewPoint(Eye,Rot);const float E=HillsClosure::Exposure(GetWorld(),Eye);
        OK=Command==30?FMath::Abs(E)<.01f:E>.5f;Text=FString::Printf(TEXT("local eye=%s exposure_boost=%.4f"),*Eye.ToString(),E);
    }
    else if(Command==33){Ready=Age>2.;OK=HillsClosure::Rooms(GetWorld(),Text);}
    else if(Command==34||Command==35)
    {
        auto* Door=Cast<AColdSteelDoor>(Subject);
        if(Command==34&&Door){HillsClosure::Aim(PC,Door);if(!Requested&&Age>1.5)if(auto* Push=PC->GetPawn()->FindComponentByClass<UFPSDoorPushComponent>())Requested=Push->RequestDoorInteraction(Door);}
        Ready=Door&&Age>2.&&Door->IsDoorOpen()==(Command==34);OK=Ready;Text=TEXT("production door interaction RPC and replicated state");
    }
    else if(Command==40)
    {Ready=Age>3.;const int32 N=HillsClosure::WildlifeCount(GetWorld());OK=N==0&&HillsClosure::Count(M)==ExpectedCount;Text=FString::Printf(TEXT("outside hills wildlife=%d"),N);}
    if(!Ready&&Age<(Command==50?360.:45.))return;
    Reported=true;auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("command"),Command);R->SetBoolField(TEXT("passed"),Ready&&OK);R->SetStringField(TEXT("detail"),Text);
    HillsClosure::Save(FString::Printf(TEXT("client-%02d"),Command),R);
    ServerObserved(Command,Ready&&OK,Text,M->Snapshot().NetworkProfileId,HillsClosure::Count(M));
}

#if !UE_BUILD_SHIPPING
namespace HillsClosure
{
struct FRun
{
    TWeakObjectPtr<UWorld> World;TWeakObjectPtr<APlayerController> Guest,Host;
    TWeakObjectPtr<AHillsMultiplayerClosure> Probe;TWeakObjectPtr<AWolfMonster> Wolf;
    FGuid GuestId,WorldId;FString WorldKey;int64 HostBase=0,GuestBase=0,GuestExpected=0,HostExpected=0;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Stage=0;double Started=FPlatformTime::Seconds(),Next=0.,Killed=0.;
    bool Success=true,HostPicked=false;FVector Base;TWeakObjectPtr<ABuildingDaylight> Room;
    void Record(const FString& Name,bool OK,const FString& Detail=FString())
    {Success&=OK;auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),OK);R->SetStringField(TEXT("detail"),Detail);Rows.Add(MakeShared<FJsonValueObject>(R));UE_LOG(LogTemp,Display,TEXT("HILLS_CLOSURE case=%s passed=%d %s"),*Name,OK,*Detail);}
    bool Finish()
    {auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),Success);R->SetArrayField(TEXT("checks"),Rows);R->SetStringField(TEXT("scope"),TEXT("Production hills, controllers, inventory RPCs, forced process disconnect, same profile reconnect, production team portal travel; NullRHI per-view blendable composition, no rendered visual acceptance."));Save(TEXT("result"),R);if(Probe.IsValid())Probe->ClientFinish(Success);FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([](float){FPlatformMisc::RequestExit(false);return false;}),3.f);return false;}
    void Send(int32 C,AActor* Target=nullptr)
    {Probe->Command=C;Probe->Subject=Target;Probe->Observed=0;Probe->ExpectedCount=GuestExpected;Probe->ForceNetUpdate();Next=FPlatformTime::Seconds()+.25;}
    bool Done(const TCHAR* Name)
    {if(!Probe.IsValid()||Probe->Observed!=Probe->Command)return false;Record(Name,Probe->Passed,Probe->Detail);return true;}
    void Drop(int32 Case,int32 N)
    {
        auto* W=World.Get();auto* M=Model(W);auto Item=M->CreateItem(TEXT("enhancement_stone"),N);Item.InstanceId=FString::Printf(TEXT("hills-closure-%d"),Case);Item.Place=2;Item.Map=TEXT("L_TemperateHills_Initial");Item.Position=Base+FVector(80,0,-50);
        Record(FString::Printf(TEXT("prepare_drop_%d"),Case),W->GetSubsystem<UColdSteelSharedInventorySubsystem>()->AddWorldDrops({Item}));
        for(TActorIterator<AColdSteelPickup> It(W);It;++It)if(It->ItemId==Item.InstanceId){Send(Case,*It);Probe->ItemId=Item.InstanceId;Probe->ExecuteAt=Clock(W)+2.;break;}
        HostPicked=false;
    }
    bool Bind(UWorld* W)
    {
        World=W;Host=nullptr;Guest=nullptr;
        for(auto It=W->GetPlayerControllerIterator();It;++It){if(It->Get()->IsLocalController())Host=It->Get();else Guest=It->Get();}
        auto* PS=Guest.IsValid()?Guest->GetPlayerState<AColdSteelPlayerState>():nullptr;
        return Host.IsValid()&&Host->GetPawn()&&Guest.IsValid()&&Guest->GetPawn()&&PS&&PS->ShadowModel&&PS->ShadowModel->RuntimePawn()==Guest->GetPawn();
    }
    void NewProbe()
    {FActorSpawnParameters P;P.Owner=Guest.Get();Probe=World->SpawnActor<AHillsMultiplayerClosure>(P);}
    bool Travel(const FString& Map,const FString& Options)
    {
        auto* Portal=World->SpawnActor<ASceneTestPortal>(Host->GetPawn()->GetActorLocation()+FVector(80,0,0),FRotator::ZeroRotator);
        Portal->Configure(Map,TEXT("isolated audit transfer"),Options);
        return Host->GetPlayerState<AColdSteelPlayerState>()->RequestTeamTravel(Portal);
    }
    bool Tick(float)
    {
        const double Now=FPlatformTime::Seconds();if(Now<Next)return true;
        if(!Success||Now-Started>1000.){if(Success)Record(TEXT("deadline"),false,FString::FromInt(Stage));return Finish();}
        UWorld* W=nullptr;for(const auto& C:GEngine->GetWorldContexts())if(C.World()&&C.World()->GetNetMode()==NM_ListenServer&&C.World()->HasBegunPlay()){W=C.World();break;}
        if(!W)return true;
        if(Stage==90)
        {
            if(Guest.IsValid()&&IsValid(Guest->GetPawn()))return true;
            Record(TEXT("production_logout_after_process_disconnect"),true);UE_LOG(LogTemp,Display,TEXT("HILLS_CLOSURE_RECONNECT_READY"));Stage=91;return true;
        }
        if(!Bind(W))return true;
        auto* M=Model(W);auto* GM=Guest->GetPlayerState<AColdSteelPlayerState>()->ShadowModel.Get();
        ATemperateHillsWorld* Hills=nullptr;for(TActorIterator<ATemperateHillsWorld> It(W);It;++It){Hills=*It;break;}
        if(Stage==0)
        {
            if(!Hills||!Hills->bReady)return true;
            WorldId=Hills->WorldId;Hills->RequestVillageVisit();Stage=1;Next=Now+12.;return true;
        }
        if(Stage==1)
        {
            for(TActorIterator<ABuildingDaylight> It(W);It;++It){Room=*It;break;}if(!Room.IsValid())return true;
            Base=Host->GetPawn()->GetActorLocation();Place(Host.Get(),Base);Place(Guest.Get(),Base+FVector(0,90,0));
            for(TActorIterator<AFPSWeatherManager> It(W);It;++It){It->SetWeatherState(EFPSWeatherState::Clear);It->RealSecondsPerGameDay=8640000.f;It->AdvanceGameTime(FMath::Fmod(.375f-It->NormalizedDayTime+1.f,1.f)*24.f+.00001f);}
            HostBase=Count(M);GuestBase=Count(GM);GuestExpected=GuestBase;GuestId=GM->Snapshot().NetworkProfileId;
            auto* Shared=W->GetSubsystem<UColdSteelSharedInventorySubsystem>();if(!Shared->InitializeAuthority())return true;WorldKey=Shared->WorldKey();
            NewProbe();const auto* Row=WildlifeCatalog::Get().Find(TEXT("wolf"));FActorSpawnParameters P;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            Wolf=W->SpawnActor<AWolfMonster>(LoadObject<UClass>(nullptr,*Row->CharacterClass),Base+FVector(280,0,0),FRotator(0,180,0),P);
            if(!Wolf.IsValid()){Record(TEXT("wolf_spawn"),false);return true;}
            if(auto* AI=Cast<AAIController>(Wolf->GetController()))if(AI->GetBrainComponent())AI->GetBrainComponent()->StopLogic(TEXT("isolated network stimulus"));
            Wolf->bAlwaysRelevant=true;Send(50,Wolf.Get());Stage=50;return true;
        }
        if(Stage==50&&Done(TEXT("client_real_hills_preparation"))){Send(1,Wolf.Get());Stage=2;return true;}
        if(Stage==2&&Done(TEXT("wolf_alive_replica")))
        {FPointDamageEvent E;E.ShotDirection=-Wolf->GetActorRightVector();Wolf->TakeDamage(20,E,Host.Get(),Host->GetPawn());Wolf->InterruptAttack(1.5f);Send(2,Wolf.Get());Probe->ExecuteAt=Clock(W);Stage=22;return true;}
        if(Stage==22&&Done(TEXT("wolf_right_hit_replica")))
        {FPointDamageEvent E;E.ShotDirection=Wolf->GetActorRightVector();Wolf->TakeDamage(10,E,Host.Get(),Host->GetPawn());Wolf->InterruptAttack(1.5f);Send(22,Wolf.Get());Probe->ExecuteAt=Clock(W);Stage=23;return true;}
        if(Stage==23&&Done(TEXT("wolf_left_hit_replica")))
        {FPointDamageEvent E;E.ShotDirection=Wolf->GetActorRightVector();Wolf->TakeDamage(10,E,Host.Get(),Host->GetPawn());Wolf->InterruptAttack(1.5f);Send(23,Wolf.Get());Probe->ExecuteAt=Clock(W);Stage=3;return true;}
        if(Stage==3&&Done(TEXT("wolf_repeated_left_hit_replica")))
        {Send(25,Wolf.Get());Probe->Place=Base+FVector(280,0,0);Stage=25;return true;}
        if(Stage==25&&Done(TEXT("wolf_authority_flee_movement_replica")))
        {FDamageEvent E;Wolf->TakeDamage(10000000,E,Host.Get(),Host->GetPawn());Killed=Clock(W);Send(3,Wolf.Get());Stage=4;return true;}
        if(Stage==4&&Done(TEXT("wolf_corpse_presentation_collision")))
        {Stage=5;Next=Now+.1;return true;}
        if(Stage==5)
        {
            if(Wolf.IsValid()&&Clock(W)-Killed<7.)return true;
            Record(TEXT("wolf_cleanup_5s"),!Wolf.IsValid()&&Clock(W)-Killed<6.,FString::Printf(TEXT("elapsed %.3f"),Clock(W)-Killed));
            UWildlifeSubsystem::FlushPendingLoot(W);int64 Meat=0;for(const auto& I:W->GetSubsystem<UColdSteelSharedInventorySubsystem>()->Data().Drops)if(I.Definition==TEXT("raw_meat_chunk"))Meat+=I.Count;
            Record(TEXT("wolf_shared_loot"),Meat>=1,FString::Printf(TEXT("raw meat=%lld"),Meat));Send(4);Stage=6;return true;
        }
        if(Stage==6&&Done(TEXT("wolf_destroy_replicated"))){Drop(10,1);Stage=10;return true;}
        if(Stage==10||Stage==11)
        {
            Aim(Host.Get(),Probe->Subject);Aim(Guest.Get(),Probe->Subject);
            if(!HostPicked&&Clock(W)>=Probe->ExecuteAt+(Stage==10?.075:0.))
            {FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Pickup;R.Target=Probe->Subject;Host->GetPlayerState<AColdSteelPlayerState>()->RequestInventoryAction(R);HostPicked=true;}
            if(!Done(Stage==10?TEXT("race_first_client_receipt"):TEXT("race_second_client_receipt")))return true;
            const int64 Expected=HostBase+GuestBase+(Stage==10?1:3);
            Record(Stage==10?TEXT("two_player_single_award_1"):TEXT("two_player_single_award_2"),Count(M)+Count(GM)==Expected,FString::Printf(TEXT("host=%lld guest=%lld expected_total=%lld"),Count(M),Count(GM),Expected));
            if(Stage==10){Drop(11,2);Stage=11;}else{Drop(12,4);Stage=12;}return true;
        }
        if(Stage==12)Aim(Guest.Get(),Probe->Subject);
        if(Stage==12&&Done(TEXT("guest_pickup_receipt")))
        {
            Record(TEXT("owner_shadow_match"),Probe->Count==Count(GM)&&Count(M)+Count(GM)==HostBase+GuestBase+7);
            GuestExpected=Count(GM);HostExpected=Count(M);Send(20);Stage=20;return true;
        }
        if(Stage==20&&Done(TEXT("client_profile_saved_before_disconnect")))
        {Record(TEXT("original_durable_identity"),Probe->Identity==GuestId);if(auto* Driver=W->GetNetDriver())Driver->ConnectionTimeout=12.f;UE_LOG(LogTemp,Display,TEXT("HILLS_CLOSURE_DISCONNECT_CLIENT"));Stage=90;return true;}
        if(Stage==91)
        {if(auto* Driver=W->GetNetDriver())Driver->ConnectionTimeout=180.f;NewProbe();Send(21);Stage=21;return true;}
        if(Stage==21&&Done(TEXT("same_profile_reconnect_owner")))
        {
            Record(TEXT("reconnect_authority_inventory"),GM->Snapshot().NetworkProfileId==GuestId&&Probe->Identity==GuestId&&Count(GM)==GuestExpected&&Count(M)==HostExpected);
            const FVector Center=Room->GetActorTransform().TransformPosition((Room->RoomMinimum+Room->RoomMaximum)*.5);
            Place(Host.Get(),Center);Place(Guest.Get(),OutsideRoom(W,Room.Get()));Send(30);Stage=30;return true;
        }
        if(Stage==30&&Done(TEXT("guest_outside_host_inside")))
        {
            FVector Eye;FRotator Rot;Host->GetPlayerViewPoint(Eye,Rot);Record(TEXT("host_inside_independent"),Exposure(W,Eye)>.5f);
            const FVector Center=Room->GetActorTransform().TransformPosition((Room->RoomMinimum+Room->RoomMaximum)*.5);
            Place(Host.Get(),OutsideRoom(W,Room.Get()));Place(Guest.Get(),Center);Send(31);Stage=31;return true;
        }
        if(Stage==31&&Done(TEXT("guest_inside_host_outside")))
        {FVector Eye;FRotator Rot;Host->GetPlayerViewPoint(Eye,Rot);Record(TEXT("host_outside_independent"),FMath::Abs(Exposure(W,Eye))<.01f);Send(33);Stage=33;return true;}
        if(Stage==33&&Done(TEXT("all_client_rooms_feathering")))
        {
            FString Detail;Record(TEXT("all_host_rooms_feathering"),Rooms(W,Detail),Detail);
            for(TActorIterator<AColdSteelDoor> It(W);It;++It)if(It->GetOwner()==Hills){Place(Guest.Get(),It->GetActorTransform().TransformPosition(FVector(-100,0,100)));Send(34,*It);Stage=34;return true;}
            Record(TEXT("chapel_door_exists"),false);return true;
        }
        if(Stage==34)Aim(Guest.Get(),Probe->Subject);
        if(Stage==34&&Done(TEXT("chapel_guest_open_rpc")))
        {
            auto* Door=CastChecked<AColdSteelDoor>(Probe->Subject);const auto T=Door->GetActorTransform();
            FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(HillsClosureDoor),false);Q.AddIgnoredActor(Guest->GetPawn());Q.AddIgnoredActor(Host->GetPawn());
            const bool Blocked=W->SweepSingleByChannel(Hit,T.TransformPosition(FVector(-160,0,100)),T.TransformPosition(FVector(160,0,100)),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(34,88),Q);
            Record(TEXT("chapel_open_capsule_passage"),Door->IsDoorOpen()&&!Blocked,Hit.GetActor()?Hit.GetActor()->GetName():TEXT("clear"));
            Door->CloseDoor();Send(35,Door);Stage=35;return true;
        }
        if(Stage==35&&Done(TEXT("chapel_close_replicated")))
        {
            Drop(99,3);Record(TEXT("team_travel_request_out"),Travel(TEXT("/Game/GameMaps/DayNight_Lighting"),FString()));Stage=40;Next=Now+5.;return true;
        }
        if(Stage==40&&!Hills)
        {NewProbe();Send(40);Stage=42;return true;}
        if(Stage==42&&Done(TEXT("travel_out_profile_no_animals")))
        {Record(TEXT("hub_no_authority_wildlife"),WildlifeCount(W)==0);Record(TEXT("outgoing_guest_profile"),Count(GM)==GuestExpected);Record(TEXT("team_travel_request_return"),Travel(TEXT("/Game/GameMaps/L_TemperateHills_Initial"),TEXT("HillsContinue")));Stage=43;Next=Now+5.;return true;}
        if(Stage==43&&Hills&&Hills->bReady)
        {
            auto* Shared=W->GetSubsystem<UColdSteelSharedInventorySubsystem>();if(!Shared->InitializeAuthority())return true;
            int64 Remaining=0,Consumed=0;for(const auto& I:Shared->Data().Drops){if(I.InstanceId==TEXT("hills-closure-99"))Remaining+=I.Count;if(I.InstanceId==TEXT("hills-closure-10")||I.InstanceId==TEXT("hills-closure-11")||I.InstanceId==TEXT("hills-closure-12"))Consumed+=I.Count;}
            Record(TEXT("return_same_world_unclaimed_drop_no_duplication"),Hills->WorldId==WorldId&&Shared->WorldKey()==WorldKey&&Remaining==3&&Consumed==0);
            Record(TEXT("return_authority_profiles"),Count(GM)==GuestExpected&&Count(M)==HostExpected&&GM->Snapshot().NetworkProfileId==GuestId);
            NewProbe();Send(41);Stage=41;return true;
        }
        if(Stage==41&&Done(TEXT("return_owner_profile")))return Finish();
        return true;
    }
};
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.HillsMultiplayerClosure"),TEXT("Explicit isolated two-player hills lifecycle check."),FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
{if(!Enabled()||!W||W->GetNetMode()!=NM_ListenServer||Output().IsEmpty())return;auto R=MakeShared<FRun>();FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([R](float D){return R->Tick(D);}),.1f);}));
}
#endif
