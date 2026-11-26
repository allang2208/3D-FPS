#include "KukriCombatWireAudit.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/GunsmithSystem.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/WorldSettings.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "Serialization/JsonSerializer.h"

namespace KukriCombatWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("KukriCombatWireAudit"));}
double HitchAt=-1.;
bool HitchInjected=false;
int32 HeavyCyclesDone=0;
FString LegendaryHead()
{
    static const FString Head=[] {FString Name;FParse::Value(FCommandLine::Get(),TEXT("HatchetLegend="),Name);
        if(Name==TEXT("Falcon"))return FString(TEXT("hatchet_falcon_edge"));
        if(Name==TEXT("Ghost"))return FString(TEXT("hatchet_ghost_scythe"));return FString();}();
    return Head;
}
int32 PeakCorrosion=0;
float InitialTargetX=0;
int32 PhaseEvents[2]={};
uint32 ReleaseBefore=0;
double ChargeLagRestoreAt=-1.;
void ChargeLag(UWorld* World,int32 Lag)
{
#if DO_ENABLE_NET_TEST
    if(auto* Driver=World->GetNetDriver())
    {auto Settings=Driver->PacketSimulationSettings;Settings.PktLag=Lag;Driver->SetPacketSimulationSettings(Settings);
        UE_LOG(LogTemp,Display,TEXT("KUKRI_CHARGE_LAG_FIXTURE outgoing_ms=%d"),Lag);}
#endif
}
int32 HeavyCycles(){int32 Count=0;FParse::Value(FCommandLine::Get(),TEXT("KukriWireHeavyCycles="),Count);return FMath::Clamp(Count,0,8);}
constexpr int32 CaseCount=12;
FString Name(int32 Case)
{
    static const TCHAR* Actions[]={TEXT("combo123"),TEXT("heavy"),TEXT("uppercut"),TEXT("whirlwind"),TEXT("quick"),TEXT("dash")};
    return FString(Case>=6?TEXT("dual/"):TEXT("single/"))+Actions[Case%6];
}
void Network(UWorld* W)
{
#if DO_ENABLE_NET_TEST
    if(auto* Driver=W->GetNetDriver())
    {
        FPacketSimulationSettings S;S.PktLag=60;S.PktLoss=3;Driver->SetPacketSimulationSettings(S);
        UE_LOG(LogTemp,Display,TEXT("KUKRI_COMBAT_NETWORK mode=%d lag_ms=%d loss_percent=%d"),
            int32(W->GetNetMode()),Driver->PacketSimulationSettings.PktLag,Driver->PacketSimulationSettings.PktLoss);
    }
#endif
}
ANurseZombie* SpawnTarget(UWorld* W,const FVector& Location)
{
    auto* Class=LoadClass<ANurseZombie>(nullptr,TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C"));
    if(!Class)return nullptr;
    auto* N=W->SpawnActor<ANurseZombie>(Class,Location,FRotator(0,180,0));
    if(!N)return nullptr;
    N->Health=N->MaxHealth=100000;N->SetActorTickEnabled(false);N->GetCharacterMovement()->DisableMovement();
    N->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Overlap);
    N->GetCharacterMovement()->SetComponentTickEnabled(false);
    if(auto* AI=Cast<AMonsterAIController>(N->GetController()))AI->SetDecisionEnabled(false);
    return N;
}
void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Passed,UWorld* W)
{
    auto R=MakeShared<FJsonObject>();R->SetArrayField(TEXT("cases"),Rows);R->SetBoolField(TEXT("passed"),Passed);
    R->SetStringField(TEXT("weapon"),FParse::Param(FCommandLine::Get(),TEXT("HatchetCombatWireAudit"))?TEXT("ue_tactical_hatchet"):TEXT("ue_kukri"));
    R->SetBoolField(TEXT("dedicated"),W->GetNetMode()==NM_DedicatedServer);R->SetBoolField(TEXT("udp"),W->GetNetDriver()!=nullptr);
    R->SetNumberField(TEXT("injected_authority_hitch_ms"),HitchInjected?650:0);
#if DO_ENABLE_NET_TEST
    if(const auto* Driver=W->GetNetDriver())
    {
        R->SetNumberField(TEXT("actual_authority_lag_ms"),Driver->PacketSimulationSettings.PktLag);
        R->SetNumberField(TEXT("actual_authority_loss_percent"),Driver->PacketSimulationSettings.PktLoss);
    }
#endif
    R->SetStringField(TEXT("entry"),TEXT("native Kukri input handlers; real executors, traces, hit RPC, damage and profile upload"));
    FString Path,Json;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json));
    if(FParse::Value(FCommandLine::Get(),TEXT("KukriWireOutput="),Path))FFileHelper::SaveStringToFile(Json,*Path);
}
}
void AKukriCombatWireState::ServerReportHit_Implementation(const FColdSteelNetHitReport& Report)
{
    if(KukriCombatWire::Enabled())
    {
        LastContact=Report;LastWasPaired=false;++Reports;
        UE_LOG(LogTemp,Display,TEXT("KUKRI_CONTACT_CLOCK serial=%u meta=%u age=%.3f now=%.3f stamp=%.3f"),
            Report.KukriAttackSerial,Report.AttackMeta,GetWorld()->GetTimeSeconds()-Report.ClientFireTime,
            GetWorld()->GetTimeSeconds(),Report.ClientFireTime);
    }
    Super::ServerReportHit_Implementation(Report);
}
void AKukriCombatWireState::ServerReportPairedHeavyHit_Implementation(const FColdSteelNetHitReport& First,const FColdSteelNetHitReport& Second)
{
    if(KukriCombatWire::Enabled()){LastContact=First;LastPairedContact=Second;LastWasPaired=true;++Reports;}
    Super::ServerReportPairedHeavyHit_Implementation(First,Second);
}
AKukriCombatWireFloor::AKukriCombatWireFloor()
{
    bReplicates=true;bAlwaysRelevant=true;
    auto* Ground=CreateDefaultSubobject<UBoxComponent>(TEXT("Ground"));SetRootComponent(Ground);
    Ground->InitBoxExtent(FVector(10000,10000,20));Ground->SetCollisionProfileName(TEXT("BlockAll"));
}
AKukriWireMetalWall::AKukriWireMetalWall()
{
    bReplicates=true;bAlwaysRelevant=true;
    auto* Wall=CreateDefaultSubobject<UBoxComponent>(TEXT("Metal"));SetRootComponent(Wall);
    Wall->InitBoxExtent(FVector(3,110,130));Wall->SetCollisionProfileName(TEXT("BlockAll"));
    Wall->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);Wall->ComponentTags.Add(TEXT("Impact.Metal"));
}
void AKukriCombatWireController::ClientSetup_Implementation(int32 Case)
{
    if(!KukriCombatWire::Enabled()||Case==Current||Case<0||Case>=KukriCombatWire::CaseCount)return;
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!P||!M||!Seeded)return;
    const auto* Off=M->FindItem(TEXT("wire_kukri_left"));if(!Off)return;
    const int32 Place=Case>=6?1:0,Cell=Case>=6?8:0;
    if((Off->Place!=Place||Off->Cell!=Cell)&&!M->MoveItem(Off->InstanceId,Place,Cell))return;
    P->SetActorLocationAndRotation(FVector(0,0,100),FRotator::ZeroRotator);SetControlRotation(FRotator::ZeroRotator);
    P->GetCharacterMovement()->StopMovementImmediately();P->MPSetAutoInput(false,false);
    Current=Case;Started=GetWorld()->GetRealTimeSeconds();Fired=0;Sent=false;Running=false;SawAction=false;
    ServerReady(Case);
}
void AKukriCombatWireController::ServerReady_Implementation(int32 Case)
{
    if(KukriCombatWire::Enabled()&&Case==Finished)
    {
        Ready=true;
        // Asset loading can stall a headless peer as well as a rendered one.
        // Each case needs fresh clock evidence after its equipment changes.
        ClockReady=false;ClockStableSamples=0;
    }
}
void AKukriCombatWireController::ServerClockProbe_Implementation(double EstimatedServerTime)
{
    if(!KukriCombatWire::Enabled()||ClockReady)return;
    const double Age=GetWorld()->GetTimeSeconds()-EstimatedServerTime;
    const double Minimum=FParse::Param(FCommandLine::Get(),TEXT("KukriWireVisualSlow"))?-.075:-.025;
    ClockStableSamples=Age>=Minimum&&Age<=.4?ClockStableSamples+1:0;
    ClockReady=ClockStableSamples>=5;
    UE_LOG(LogTemp,Display,TEXT("KUKRI_CLOCK_WARMUP age=%.3f stable=%d ready=%d"),Age,ClockStableSamples,ClockReady);
}
void AKukriCombatWireController::ClientGo_Implementation(int32 Case)
{if(KukriCombatWire::Enabled()&&Current==Case&&!Running){Running=true;Started=GetWorld()->GetRealTimeSeconds();NextInput=Started+(Case==0&&!FParse::Param(FCommandLine::Get(),TEXT("KukriWireNoOutfit"))?10.:.5);}}
void AKukriCombatWireController::ClientReplay_Implementation(const FColdSteelNetHitReport& Report)
{if(KukriCombatWire::Enabled())if(auto* PS=GetPlayerState<AColdSteelPlayerState>()){PS->ServerReportHit(Report);PS->ServerReportHit(Report);}}
void AKukriCombatWireController::ClientReplayPaired_Implementation(const FColdSteelNetHitReport& First,const FColdSteelNetHitReport& Second)
{if(KukriCombatWire::Enabled())if(auto* PS=GetPlayerState<AColdSteelPlayerState>()){PS->ServerReportPairedHeavyHit(First,Second);PS->ServerReportPairedHeavyHit(First,Second);}}
void AKukriCombatWireController::ClientExit_Implementation()
{if(KukriCombatWire::Enabled())ExitAt=GetWorld()->GetRealTimeSeconds()+.5;}
void AKukriCombatWireController::ClientCheckReplacement_Implementation(AFPSGAMECharacter* NewPawn,double Spent)
{
    if(!KukriCombatWire::Enabled()||!NewPawn||GetPawn()!=NewPawn)return;
    const auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* K=NewPawn->FindComponentByClass<UKukriWeaponComponent>();
    if(M&&M->RuntimePawn()==NewPawn&&K&&K->IsEquipped()&&M->Snapshot().UppercutStaminaSpent>=Spent)
        ServerReplacementReady(true);
}
void AKukriCombatWireController::ServerReplacementReady_Implementation(bool Passed)
{if(KukriCombatWire::Enabled())ReplacementReady=Passed;}
void AKukriCombatWireController::ServerDone_Implementation(int32 Case,bool OK,int32 Count,double Spent)
{if(KukriCombatWire::Enabled()&&Case==Finished){Done=true;Completed=OK;Inputs=Count;ClientSpent=Spent;}}
void AKukriCombatWireController::BeginPlay()
{
    Super::BeginPlay();SeedProfile();
    if(KukriCombatWire::Enabled()&&FParse::Param(FCommandLine::Get(),TEXT("KukriWireVisualSlow")))GetWorld()->GetWorldSettings()->SetTimeDilation(.25f);
}
void AKukriCombatWireController::SeedProfile()
{
    if(!KukriCombatWire::Enabled()||!IsLocalController()||Seeded)return;
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!M||!M->IsAudit())return;
    {
        auto S=M->Snapshot();S.Items.Reset();S.ActiveWeaponSlot=6;S.ActiveProductionTool.Reset();S.DungeonRun={};
        FString Head=TEXT("jason");FParse::Value(FCommandLine::Get(),TEXT("KukriWireHead="),Head);
        S.PlayerHeadId=FName(*Head);S.PlayerHairId=NAME_None;
        S.Stamina=150;S.UppercutStaminaSpent=0.;S.bSprintExhausted=false;S.SwordUppercutCooldown=S.WhirlwindCooldown=0;
        for(auto& Skill:S.Skills)Skill.Value.Level=FMath::Max(1,Skill.Value.Level);
        const TCHAR* Weapon=FParse::Param(FCommandLine::Get(),TEXT("HatchetCombatWireAudit"))?TEXT("ue_tactical_hatchet"):TEXT("ue_kukri");
        for(int32 Hand=0;Hand<2;++Hand)
        {
            auto I=M->CreateItem(Weapon);I.InstanceId=Hand?TEXT("wire_kukri_left"):TEXT("wire_kukri_right");I.Place=Hand?0:1;I.Cell=Hand?0:6;
            if(!KukriCombatWire::LegendaryHead().IsEmpty())
            {
                TSharedPtr<FJsonObject> Data;
                if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data)||!Data)return;
                auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),KukriCombatWire::LegendaryHead());
                Data->SetObjectField(TEXT("gunsmith_parts"),Parts);I.Data.Reset();
                FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));
            }
            S.Items.Add(I);
        }
        const TCHAR* Clothes[]={TEXT("ue_st6_sleeves"),TEXT("ue_st6_tactical_pants"),TEXT("ue_st6_tactical_boots")};
        const int32 Slots[]={7,15,13};
        if(!FParse::Param(FCommandLine::Get(),TEXT("KukriWireNoOutfit")))
            for(int32 I=0;I<3;++I){auto Item=M->CreateItem(Clothes[I]);Item.Place=1;Item.Cell=Slots[I];S.Items.Add(Item);}
        FString Id;if(!HasAuthority()&&FParse::Value(FCommandLine::Get(),TEXT("KukriProfileId="),Id))FGuid::Parse(Id,S.NetworkProfileId);
        M->AdoptNetMirror(S);Seeded=true;
    }
}
void AKukriCombatWireController::Tick(float Delta)
{
    Super::Tick(Delta);if(!KukriCombatWire::Enabled()||!IsLocalController())return;SeedProfile();
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!P||!M||!Seeded)return;
    if(!Attached)
    {
        M->AttachPawn(P);P->ApplyColdSteelProfile(M);Attached=true;KukriCombatWire::Network(GetWorld());
        P->SetActorLocation(FVector(HasAuthority()?-600.f:0.f,HasAuthority()?600.f:0.f,100));
    }
    if(HasAuthority())return;
    if(FParse::Param(FCommandLine::Get(),TEXT("HatchetWatchOnly")))
    {SetControlRotation(FRotator(-6,0,0));return;}
    if(KukriCombatWire::LegendaryHead()==TEXT("hatchet_ghost_scythe"))
    {
        static int32 Previous=-1;
        for(TActorIterator<ANurseZombie> It(GetWorld());It;++It)
            if(const auto* State=It->FindComponentByClass<UCombatStatusFormula>())
            {
                const int32 Count=State->ArmorCorrosionCount();
                if(Count!=Previous)UE_LOG(LogTemp,Display,TEXT("HATCHET_GHOST_CLIENT stacks=%d previous=%d"),Count,Previous);
                Previous=Count;break;
            }
    }
    if(KukriCombatWire::ChargeLagRestoreAt>=0.&&Now>=KukriCombatWire::ChargeLagRestoreAt)
    {KukriCombatWire::ChargeLag(GetWorld(),60);KukriCombatWire::ChargeLagRestoreAt=-1.;}
    if(!Running&&Now-LastClockProbe>.5)
    {
        LastClockProbe=Now;
        if(const auto* GS=GetWorld()->GetGameState())ServerClockProbe(GS->GetServerWorldTimeSeconds());
    }
    if(!Running||Sent)return;
    auto* K=P->FindComponentByClass<UKukriWeaponComponent>();if(!K)return;
    if(K->IsDashAttackActive())
        for(TActorIterator<ANurseZombie> It(GetWorld());It;++It)
            UE_LOG(LogTemp,Display,TEXT("KUKRI_DASH_TRACE pawn=%s target=%s range=%.1f velocity=%s"),
                *P->GetActorLocation().ToCompactString(),*It->GetActorLocation().ToCompactString(),M->DashAttackStats().RangeCM,*P->GetVelocity().ToCompactString());
    const int32 Kind=Current%6;const int32 Wanted=Kind==0?3:1;
    if(Now>=NextInput&&Fired<Wanted&&!K->IsBusy())
    {
        bool Began=false;
        if(Kind==0){P->FirePressed();P->FireInputReleased();Began=K->IsAttacking();}
        if(Kind==1)
        {
            int32 Lag=0;FParse::Value(FCommandLine::Get(),TEXT("KukriChargeLagMs="),Lag);
            if(Lag>0){KukriCombatWire::ChargeLag(GetWorld(),FMath::Clamp(Lag,60,800));KukriCombatWire::ChargeLagRestoreAt=Now+.25;}
            Began=K->TriggerHeavySkill();
        }
        if(Kind==2)Began=K->BeginUppercut();
        if(Kind==3)Began=K->BeginWhirlwind();
        if(Kind==4)Began=K->BeginQuickCombat();
        if(Kind==5)
        {
            P->MPSetAutoInput(true,true);
            // Sprint toward a stationary target. Following the lagging server
            // pawn with the target puts it behind the predicted client.
            if(K->DashReadyFraction()>=.999f&&P->GetActorLocation().X>=1800.f)
            {P->FirePressed();P->FireInputReleased();Began=K->IsDashAttackActive();if(Began)P->MPSetAutoInput(false,false);}
        }
        if(Began){++Fired;SawAction=true;NextInput=Now+.05;}
    }
    if((Fired==Wanted&&!K->IsBusy()&&SawAction)||Now-Started>45.)
    {
        Sent=true;P->MPSetAutoInput(false,false);
        ServerDone(Current,Fired==Wanted&&!K->IsBusy(),Fired,M->Snapshot().UppercutStaminaSpent);
    }
}
AKukriCombatWireGameMode::AKukriCombatWireGameMode()
{
    PlayerControllerClass=AKukriCombatWireController::StaticClass();PlayerStateClass=AKukriCombatWireState::StaticClass();
    DefaultPawnClass=AFPSGAMECharacter::StaticClass();PrimaryActorTick.bCanEverTick=true;
}
void AKukriCombatWireGameMode::BeginPlay()
{
    Super::BeginPlay();if(!KukriCombatWire::Enabled())return;Started=GetWorld()->GetRealTimeSeconds();KukriCombatWire::Network(GetWorld());
    if(FParse::Param(FCommandLine::Get(),TEXT("KukriWireVisualSlow")))GetWorld()->GetWorldSettings()->SetTimeDilation(.25f);
    GetWorld()->SpawnActor<AKukriCombatWireFloor>(FVector(0,0,-20),FRotator::ZeroRotator);
    FString CapturePath;
    if(FParse::Value(FCommandLine::Get(),TEXT("KukriWireCapture="),CapturePath))
    {
        CaptureCamera=GetWorld()->SpawnActor<ACameraActor>();CaptureCamera->GetCameraComponent()->SetFieldOfView(50.f);
        auto& PP=CaptureCamera->GetCameraComponent()->PostProcessSettings;
        PP.bOverride_MotionBlurAmount=true;PP.MotionBlurAmount=0.f;
        PP.bOverride_AutoExposureMethod=true;PP.AutoExposureMethod=EAutoExposureMethod::AEM_Manual;
        PP.bOverride_AutoExposureApplyPhysicalCameraExposure=true;PP.AutoExposureApplyPhysicalCameraExposure=false;
        PP.bOverride_AutoExposureBias=true;PP.AutoExposureBias=0.f;
        IFileManager::Get().MakeDirectory(*CapturePath,true);
        auto* LightOwner=GetWorld()->SpawnActor<AActor>();auto* Sun=NewObject<UDirectionalLightComponent>(LightOwner);
        LightOwner->AddInstanceComponent(Sun);Sun->SetMobility(EComponentMobility::Movable);Sun->SetIntensity(5.f);Sun->SetCastShadows(false);Sun->RegisterComponent();Sun->SetWorldRotation(FRotator(-30,130,0));
        auto* Fill=NewObject<UDirectionalLightComponent>(LightOwner);LightOwner->AddInstanceComponent(Fill);
        Fill->SetMobility(EComponentMobility::Movable);Fill->SetIntensity(1.5f);Fill->SetCastShadows(false);Fill->RegisterComponent();Fill->SetWorldRotation(FRotator(-35,-50,0));
        auto* Sky=NewObject<USkyLightComponent>(LightOwner);LightOwner->AddInstanceComponent(Sky);Sky->SetMobility(EComponentMobility::Movable);Sky->SetIntensity(1.f);Sky->RegisterComponent();
        auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
        auto* Grid=LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial"));
        for(int32 I=0;I<2;++I)
        {
            auto* Back=GetWorld()->SpawnActor<AStaticMeshActor>();auto* Mesh=Back->GetStaticMeshComponent();Mesh->SetMobility(EComponentMobility::Movable);
            Mesh->SetStaticMesh(Cube);Mesh->SetMaterial(0,Grid);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Back->SetActorLocation(I?FVector(-180,0,160):FVector(0,0,-10));Back->SetActorScale3D(I?FVector(.2,20,4):FVector(200,200,.2));
        }
    }
    UE_LOG(LogTemp,Display,TEXT("KUKRI_COMBAT_HOST_READY"));
}
FString AKukriCombatWireGameMode::InitNewPlayer(APlayerController* Player,const FUniqueNetIdRepl& Id,const FString& Options,const FString& Portal)
{
    const FString Error=Super::InitNewPlayer(Player,Id,Options,Portal);
    if(auto* C=Cast<AKukriCombatWireController>(Player))C->bWatchOnly=UGameplayStatics::HasOption(Options,TEXT("HatchetViewer"));
    return Error;
}
void AKukriCombatWireGameMode::PostLogin(APlayerController* Player)
{
    Super::PostLogin(Player);if(!KukriCombatWire::Enabled()||Player->IsLocalController())return;
    if(auto* C=Cast<AKukriCombatWireController>(Player);C&&C->bWatchOnly)
    {Watcher=C;UE_LOG(LogTemp,Display,TEXT("HATCHET_VIEWER_READY"));return;}
    Guest=Cast<AKukriCombatWireController>(Player);++JoinedCount;LastSetup=-10.;Started=GetWorld()->GetRealTimeSeconds();
}
void AKukriCombatWireGameMode::Logout(AController* Player)
{
    const bool Ours=Player==Guest;Super::Logout(Player);
    if(Ours){Guest=nullptr;UE_LOG(LogTemp,Display,TEXT("KUKRI_COMBAT_REJOIN_READY"));}
}
void AKukriCombatWireGameMode::CountDamage(AActor*,float Damage,const UDamageType*,AController*,AActor*)
{
    if(!Guest||Prepared<0)return;
    ++Contacts;DamageTotal+=Damage;
    if(const auto* PS=Guest->GetPlayerState<AKukriCombatWireState>();PS&&PS->LastContact.MeleeDamagePhase<2)
        ++KukriCombatWire::PhaseEvents[PS->LastContact.MeleeDamagePhase];
    if(Prepared%6==4)
        if(auto* PS=Guest->GetPlayerState<AKukriCombatWireState>();PS&&PS->ShadowModel)
        {
            // Training stages its profile by move, replacing the item array
            // inside the real ApplyHit call stack (plain mirror copy may reuse it).
            const auto* Before=PS->ShadowModel->Equipped();
            PS->ShadowModel->TrainQuickCombat(1);
            if(Before!=PS->ShadowModel->Equipped())++ReallocatedHits;
        }
}
void AKukriCombatWireGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!KukriCombatWire::Enabled())return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Now-Started>(CaptureCamera?600.:240.)){KukriCombatWire::Save(Rows,false,GetWorld());UE_LOG(LogTemp,Error,TEXT("KUKRI_COMBAT_TIMEOUT"));ExitAt=Now+1.;return;}
    if(Watcher&&!bViewerPlaced&&Watcher->GetPawn())
    {Watcher->GetPawn()->SetActorLocation(FVector(-340,0,100));Watcher->GetPawn()->ForceNetUpdate();bViewerPlaced=true;}
    if(!Guest)return;auto* PS=Guest->GetPlayerState<AKukriCombatWireState>();
    auto* P=Cast<AFPSGAMECharacter>(Guest->GetPawn());if(!PS||!P||!PS->ShadowModel)return;
    if(WaitingReconnect)
    {
        if(JoinedCount<2)return;
        const auto S=PS->ShadowModel->Snapshot();
        auto R=MakeShared<FJsonObject>();const bool OK=S.UppercutStaminaSpent>=ReconnectSpent&&ReconnectSpent>0.;
        R->SetStringField(TEXT("case"),TEXT("same_profile_reconnect"));R->SetBoolField(TEXT("passed"),OK);
        R->SetNumberField(TEXT("spent_before"),ReconnectSpent);R->SetNumberField(TEXT("spent_after"),S.UppercutStaminaSpent);Rows.Add(MakeShared<FJsonValueObject>(R));
        AllPassed&=OK;KukriCombatWire::Save(Rows,AllPassed,GetWorld());Guest->ClientExit();if(Watcher)Watcher->ClientExit();
        ExitAt=Now+2.;UE_LOG(LogTemp,Display,TEXT("KUKRI_COMBAT_FINISHED passed=%d"),AllPassed);return;
    }
    if(Guest->Finished>=KukriCombatWire::CaseCount)
    {
        if(!Replaced)
        {
            ReconnectSpent=PS->ShadowModel->Snapshot().UppercutStaminaSpent;
            Guest->UnPossess();RestartPlayerAtTransform(Guest,FTransform(FRotator::ZeroRotator,FVector(0,0,100)));
            P->Destroy();Replaced=true;LastSetup=-10.;return;
        }
        if(!Guest->ReplacementReady)
        {if(Now-LastSetup>1.){LastSetup=Now;Guest->ClientCheckReplacement(P,ReconnectSpent);}return;}
        auto R=MakeShared<FJsonObject>();const bool OK=PS->ShadowModel->RuntimePawn()==P&&PS->ShadowModel->Snapshot().UppercutStaminaSpent>=ReconnectSpent;
        R->SetStringField(TEXT("case"),TEXT("pawn_replacement_owner_and_authority_rebound"));R->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(R));AllPassed&=OK;KukriCombatWire::Save(Rows,AllPassed,GetWorld());
        WaitingReconnect=true;Guest->ClientExit();return;
    }
    const int32 Case=Guest->Finished;
    const auto Legend=KukriCombatWire::LegendaryHead();
    const bool Legendary=!Legend.IsEmpty(),WallCase=Legendary&&Case==4;
    const bool FalconHeavy=Legend==TEXT("hatchet_falcon_edge")&&Case%6==1;
    const bool Ghost=Legend==TEXT("hatchet_ghost_scythe");
    const bool Split=FalconHeavy&&Case==7&&FParse::Param(FCommandLine::Get(),TEXT("HatchetSplitTargets"));
    if(Prepared!=Case)
    {
        Prepared=Case;Guest->Ready=Guest->Done=false;Contacts=ObservedFrames=RiftFrames=LeftRiftFrames=ReallocatedHits=0;DamageTotal=0.f;Replayed=false;Settling=-1.;LastSetup=-10.;
        PS->Reports=0;PS->LastContact={};PS->LastPairedContact={};PS->LastWasPaired=false;SpentBefore=PS->ShadowModel->Snapshot().UppercutStaminaSpent;
        P->SetActorLocationAndRotation(FVector(0,0,100),FRotator::ZeroRotator);P->GetCharacterMovement()->StopMovementImmediately();P->ForceNetUpdate();
        // A frozen reaction/root-motion target cannot be teleported between
        // cases while its proxy is still consuming the previous hit reaction.
        // Spawn a fresh real monster at the test position on the server; its
        // initial location/collision then travels over normal replication.
        if(Target)Target->Destroy();
        if(SecondTarget){SecondTarget->Destroy();SecondTarget=nullptr;}bReplayedPull=false;
        const float SpawnX=WallCase?1400.f:FalconHeavy?168.f:Case%6==5?2000.f:115.f;
        Target=KukriCombatWire::SpawnTarget(GetWorld(),FVector(SpawnX,Split?-30.f:0.f,100));
        if(!Target){UE_LOG(LogTemp,Error,TEXT("KUKRI_COMBAT_TARGET_MISSING"));ExitAt=Now+1.;return;}
        Target->OnTakeAnyDamage.AddDynamic(this,&ThisClass::CountDamage);
        if(Split)
        {
            SecondTarget=KukriCombatWire::SpawnTarget(GetWorld(),FVector(SpawnX,30,100));
            if(!SecondTarget){KukriCombatWire::Save(Rows,false,GetWorld());ExitAt=Now+1.;return;}
            SecondTarget->OnTakeAnyDamage.AddDynamic(this,&ThisClass::CountDamage);
        }
        KukriCombatWire::InitialTargetX=Target->GetActorLocation().X;KukriCombatWire::PeakCorrosion=0;
        KukriCombatWire::PhaseEvents[0]=KukriCombatWire::PhaseEvents[1]=0;
        if(const auto* K=P->FindComponentByClass<UKukriWeaponComponent>())KukriCombatWire::ReleaseBefore=K->GetNetworkHeavyReleaseSerial();
        if(Ghost&&Case==7)UCombatStatusFormula::GetOrAdd(Target)->AddArmorCorrosion(11);
        if(WallCase)GetWorld()->SpawnActor<AKukriWireMetalWall>(FVector(30,0,110),FRotator::ZeroRotator);
    }
    if(!Guest->Ready){if(Now-LastSetup>1.){LastSetup=Now;Guest->ClientSetup(Case);}return;}
    const bool Dual=PS->ShadowModel->Equipped(8)!=nullptr;
    if(Dual!=(Case>=6))return;
    // Warm the actual observer camera/materials before the first input. A cold
    // view cut plus synchronous screenshot readback must not stall authority.
    if(CaptureCamera)
    {
        const FVector Eye=P->GetActorLocation()+FVector(260,-300,100);
        CaptureCamera->SetActorLocationAndRotation(Eye,(P->GetActorLocation()+FVector(0,0,10)-Eye).Rotation());
        for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
            if(It->IsValid()&&It->Get()->IsLocalController()&&It->Get()->GetViewTarget()!=CaptureCamera)It->Get()->SetViewTarget(CaptureCamera);
        // Appearance swaps load the selected rig, clips and worn outfit as one
        // asynchronous batch. The temporary default body is not review evidence.
        const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();
        const auto* Mesh=Body?Body->GetBodyMesh():nullptr;
        FString Head=TEXT("jason");FParse::Value(FCommandLine::Get(),TEXT("KukriWireHead="),Head);
        if(!Body||Body->IsAppearanceLoading()||!Mesh||!Mesh->GetSkeletalMeshAsset()||
            !Mesh->GetSkeletalMeshAsset()->GetName().Contains(Head,ESearchCase::IgnoreCase))return;
    }
    if(!Guest->ClockReady)return;
    if(!Guest->Done&&Now-LastSetup>1.)
    {
        LastSetup=Now;Guest->ClientGo(Case);
        if(Case==0&&KukriCombatWire::HitchAt<0.&&FParse::Param(FCommandLine::Get(),TEXT("KukriWireHitch")))
            KukriCombatWire::HitchAt=Now+9.98;
    }
    if(Case==0&&!KukriCombatWire::HitchInjected&&KukriCombatWire::HitchAt>=0.&&Now>=KukriCombatWire::HitchAt)
    {
        KukriCombatWire::HitchInjected=true;
        UE_LOG(LogTemp,Display,TEXT("KUKRI_COMBAT_INJECT_HITCH 650ms"));
        FPlatformProcess::Sleep(.65f);return;
    }
    if(auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>())
    {
        const auto S=Body->GetBodyState();
        if(S.Action!=EFPSBodyAction::None)++ObservedFrames;
        FString CapturePath;
        if(FParse::Value(FCommandLine::Get(),TEXT("KukriWireCapture="),CapturePath)&&S.bHasActionProgress)
        {
            const int32 Bin=FMath::FloorToInt(S.ActionProgress*8.f);
            const FString Key=FString::Printf(TEXT("%02d_%s_%d"),Case,*S.ActionVariant.ToString(),Bin);
            if(Bin>=0&&Bin<8&&!Captures.Contains(Key)&&!FScreenshotRequest::IsScreenshotRequested())
            {Captures.Add(Key);FScreenshotRequest::RequestScreenshot(CapturePath/TEXT("frame_")+Key+TEXT(".png"),false,false);}
        }
    }
    TInlineComponentArray<UDynamicMeshComponent*> Meshes(P);
    for(auto* M:Meshes)if((M->ComponentHasTag(TEXT("KukriObserverRiftRight"))||M->ComponentHasTag(TEXT("KukriObserverRiftLeft")))&&M->IsVisible())++RiftFrames;
    for(auto* M:Meshes)if(M->ComponentHasTag(TEXT("KukriObserverRiftLeft"))&&M->IsVisible())++LeftRiftFrames;
    // Replay during the live attack window, not after its authorization expires.
    if(!Replayed&&PS->Reports>0)
    {
        Replayed=true;
        if(PS->LastWasPaired)Guest->ClientReplayPaired(PS->LastContact,PS->LastPairedContact);
        else Guest->ClientReplay(PS->LastContact);
    }
    const auto* Formula=Target?Target->FindComponentByClass<UCombatStatusFormula>():nullptr;
    if(FalconHeavy&&Replayed&&!bReplayedPull&&KukriCombatWire::PhaseEvents[1]>0&&PS->LastContact.MeleeDamagePhase==1)
    {
        bReplayedPull=true;
        if(PS->LastWasPaired)Guest->ClientReplayPaired(PS->LastContact,PS->LastPairedContact);
        else Guest->ClientReplay(PS->LastContact);
    }
    const int32 Stacks=Formula?Formula->ArmorCorrosionCount():0;
    KukriCombatWire::PeakCorrosion=FMath::Max(KukriCombatWire::PeakCorrosion,Stacks);
    if(!Guest->Done)return;
    if(Settling<0.){Settling=Now;return;}
    if(Now-Settling<(Ghost&&Case==7?8.3:1.5))return;
    auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),KukriCombatWire::Name(Case));
    const double Spent=PS->ShadowModel->Snapshot().UppercutStaminaSpent;
    // Ordinary paired swings settle separately. A paired heavy now carries
    // two validated blade reports in one RPC and one combined damage event.
    const int32 Expected=WallCase?0:Split?4:FalconHeavy?2:Case%6==0?(Dual?6:3):1;
    const bool PairOK=!Dual||Case%6!=1||(PS->LastWasPaired&&PS->LastContact.ItemInstance!=PS->LastPairedContact.ItemInstance);
    const bool DamageOK=Contacts==Expected&&(WallCase?DamageTotal==0.f:DamageTotal>0.f)&&PairOK;
    const bool LedgerOK=(Case%6==0||Case%6==2||Case%6==3||Case%6==5)?Spent>SpentBefore&&FMath::IsNearlyEqual(Spent,Guest->ClientSpent,.01):true;
    const bool Dedicated=GetNetMode()==NM_DedicatedServer;
    const bool NeedLeft=Dual&&Case%6!=2&&Case%6!=4;
    const bool VfxOK=Dedicated?RiftFrames==0:Case%6==4?RiftFrames==0:RiftFrames>0&&(!NeedLeft||LeftRiftFrames>0);
    const bool ReentryOK=WallCase||Case%6!=4||ReallocatedHits>0;
    const float Pulled=KukriCombatWire::InitialTargetX-Target->GetActorLocation().X;
    const auto* Gun=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const auto* Main=PS->ShadowModel->Equipped();
    const auto* Off=PS->ShadowModel->Equipped(8);
    const bool LoadoutOK=!Legendary||(Main&&Gun&&Gun->Installed(*Main).FindRef(TEXT("blade_1"))==Legend&&
        (!Dual||(Off&&Gun->Installed(*Off).FindRef(TEXT("blade_1"))==Legend)));
    const auto* Executor=P->FindComponentByClass<UKukriWeaponComponent>();
    const float OtherPull=SecondTarget?KukriCombatWire::InitialTargetX-SecondTarget->GetActorLocation().X:0.f;
    const bool PullOK=!FalconHeavy||(Pulled>10.f&&Pulled<=80.5f&&(!Split||(OtherPull>10.f&&OtherPull<=80.5f))
        &&bReplayedPull&&PS->Reports>=Expected+4&&KukriCombatWire::PhaseEvents[0]==(Split?2:1)&&
        KukriCombatWire::PhaseEvents[1]==(Split?2:1)&&Executor&&Executor->GetNetworkHeavyReleaseSerial()-KukriCombatWire::ReleaseBefore==1);
    const bool CorrosionOK=!Ghost||WallCase||(Case==7?(KukriCombatWire::PeakCorrosion==12&&Stacks==0):
        KukriCombatWire::PeakCorrosion==Expected);
    const bool OK=Guest->Completed&&DamageOK&&ObservedFrames>0&&(WallCase?PS->Reports==0:(Replayed&&PS->Reports>=Expected+2))&&LedgerOK&&VfxOK&&ReentryOK&&LoadoutOK&&PullOK&&CorrosionOK;
    if(Legendary)
    {
        R->SetStringField(TEXT("blade"),Legend);R->SetBoolField(TEXT("loadout_verified"),LoadoutOK);
        R->SetNumberField(TEXT("server_pull_cm"),Pulled);R->SetNumberField(TEXT("peak_corrosion"),KukriCombatWire::PeakCorrosion);
        R->SetNumberField(TEXT("second_target_pull_cm"),OtherPull);R->SetBoolField(TEXT("pull_packets_replayed"),bReplayedPull);
        R->SetNumberField(TEXT("end_corrosion"),Stacks);R->SetBoolField(TEXT("metal_wall_case"),WallCase);
        R->SetNumberField(TEXT("phase0_damage_events"),KukriCombatWire::PhaseEvents[0]);
        R->SetNumberField(TEXT("phase1_damage_events"),KukriCombatWire::PhaseEvents[1]);
        if(Executor)R->SetNumberField(TEXT("paid_heavy_releases"),Executor->GetNetworkHeavyReleaseSerial()-KukriCombatWire::ReleaseBefore);
    }
    R->SetBoolField(TEXT("passed"),OK);R->SetBoolField(TEXT("executor_completed"),Guest->Completed);
    R->SetNumberField(TEXT("input_count"),Guest->Inputs);R->SetNumberField(TEXT("damage_contacts"),Contacts);R->SetNumberField(TEXT("expected_contacts"),Expected);
    R->SetNumberField(TEXT("damage"),DamageTotal);R->SetNumberField(TEXT("hit_reports_including_two_replays"),PS->Reports);
    R->SetNumberField(TEXT("ledger_before"),SpentBefore);R->SetNumberField(TEXT("ledger_authority"),Spent);R->SetNumberField(TEXT("ledger_owner"),Guest->ClientSpent);
    R->SetBoolField(TEXT("ledger_matches"),LedgerOK);R->SetBoolField(TEXT("replay_during_action"),Replayed);
    R->SetBoolField(TEXT("paired_heavy_report"),PS->LastWasPaired);R->SetBoolField(TEXT("paired_heavy_instances_distinct"),PairOK);
    R->SetNumberField(TEXT("inventory_reallocations_during_damage"),ReallocatedHits);
    R->SetNumberField(TEXT("body_frames"),ObservedFrames);R->SetNumberField(TEXT("rift_frames"),RiftFrames);
    R->SetNumberField(TEXT("left_rift_frames"),LeftRiftFrames);R->SetBoolField(TEXT("vfx_routing"),VfxOK);
    Rows.Add(MakeShared<FJsonValueObject>(R));AllPassed&=OK;KukriCombatWire::Save(Rows,AllPassed,GetWorld());
    UE_LOG(LogTemp,Display,TEXT("KUKRI_COMBAT_CASE %d passed=%d contacts=%d/%d damage=%.2f body=%d rift=%d"),Case,OK,Contacts,Expected,DamageTotal,ObservedFrames,RiftFrames);
    ++Guest->Finished;
    if(Legendary)
    {
        Guest->Finished=Case==0?1:Case==1?7:Case==7?4:KukriCombatWire::CaseCount;
    }
    else if(KukriCombatWire::HeavyCycles()>0)
    {
        if(Case==0)Guest->Finished=1;
        else if(Case==1)Guest->Finished=7;
        else if(Case==7)Guest->Finished=++KukriCombatWire::HeavyCyclesDone<KukriCombatWire::HeavyCycles()?1:KukriCombatWire::CaseCount;
    }
}
