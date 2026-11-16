#include "UnknownLifeAudit.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/UnknownHumanoid.h"
#include "../Monsters/UnknownSpellCombat.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/FPSBlizzardComponent.h"
#include "../Skills/FPSBlizzardZone.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Skills/FPSIceArmorComponent.h"
#include "../Skills/FPSLightningHasteComponent.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/LightningDamage.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "BrainComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/JsonSerializer.h"

namespace UnknownLife
{
bool Enabled()
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return FParse::Param(FCommandLine::Get(),TEXT("UnknownLifeAudit"));
#endif
}
TArray<TSharedPtr<FJsonValue>> Rows;
TArray<TWeakObjectPtr<AActor>> PreviousActors;
bool Passed=true;
bool AllGone(){for(const auto& A:PreviousActors)if(A.IsValid()&&A->HasActorBegunPlay())return false;return true;}
int32 Zones(UWorld* W){int32 N=0;for(TActorIterator<AFPSBlizzardZone> It(W);It;++It)++N;return N;}
void Freeze(ACharacter* P)
{
    P->GetCharacterMovement()->DisableMovement();P->GetCharacterMovement()->SetComponentTickEnabled(false);
    if(auto* S=P->FindComponentByClass<UFPSSurvivalComponent>())S->SetComponentTickEnabled(false);
}
void Save(UWorld* W)
{
    FString Root;FParse::Value(FCommandLine::Get(),TEXT("UnknownLifeOutput="),Root);if(Root.IsEmpty())return;
    auto O=MakeShared<FJsonObject>();O->SetBoolField(TEXT("passed"),Passed);O->SetArrayField(TEXT("cases"),Rows);
    O->SetBoolField(TEXT("udp"),W->GetNetDriver()!=nullptr);O->SetBoolField(TEXT("rendered"),false);
#if DO_ENABLE_NET_TEST
    if(auto* N=W->GetNetDriver()){O->SetNumberField(TEXT("lag_ms"),N->PacketSimulationSettings.PktLag);O->SetNumberField(TEXT("loss_percent"),N->PacketSimulationSettings.PktLoss);}
#endif
    FString Json;FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(Root/(W->GetNetMode()==NM_Client?TEXT("client.json"):TEXT("host.json"))));
}
void Row(bool OK,const FString& Name,const FString& Detail)
{
    auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),OK);R->SetStringField(TEXT("name"),Name);R->SetStringField(TEXT("detail"),Detail);
    Rows.Add(MakeShared<FJsonValueObject>(R));Passed&=OK;
    UE_LOG(LogTemp,Display,TEXT("UNKNOWN_LIFE_CHECK %s passed=%d %s"),*Name,OK,*Detail);
}
}

struct FUnknownLifeAuditAccess
{
    static AUnknownHumanoid* Spawn(UWorld* W,int32 Index)
    {
        const FTransform T(FRotator::ZeroRotator,FVector(20000,Index*1200,200));
        auto* A=W->SpawnActorDeferred<AUnknownHumanoid>(AUnknownHumanoid::StaticClass(),T,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!A||!A->Configure(EUnknownRole(Index%4),10+10*(Index%3)))return nullptr;
        A->bAlwaysRelevant=true;UGameplayStatics::FinishSpawningActor(A,T);UnknownLife::Freeze(A);A->HealthRegen=0;
        if(auto* AI=Cast<AMonsterAIController>(A->GetController()))if(AI->GetBrainComponent())AI->GetBrainComponent()->StopLogic(TEXT("Isolated lifecycle stimuli"));
        return A;
    }
    static bool Target(AUnknownHumanoid* A,APawn* P,bool Arm)
    {
        auto* AI=Cast<AMonsterAIController>(A->GetController());if(!AI||!AI->GetBlackboardComponent())return false;
        A->SetAction(EUnknownAction::Ready);A->SetActorLocation(P->GetActorLocation()-FVector(250,0,0));A->Home=A->GetActorLocation();
        AI->SetEncounterTarget(P);
        if(AI->GetBlackboardComponent()->GetValueAsObject(TEXT("Target"))!=P)return false;
        if(Arm)
        {
            const EUnknownAction Actions[]={EUnknownAction::Swing,EUnknownAction::Fire,EUnknownAction::Cast,EUnknownAction::DrawBow};
            A->SetAction(Actions[int32(A->Loadout.Role)],60.f);A->AttackTarget=P;A->bPendingContact=true;
            A->ShotsLeft=3;A->ContactAt=A->ServerTime()+50.f;
        }
        return true;
    }
    static bool Lost(AUnknownHumanoid* A)
    {
        auto* AI=Cast<AMonsterAIController>(A->GetController());if(!AI)return false;AI->UpdateKnowledge();
        return !A->bPendingContact&&!A->AttackTarget.IsValid()&&!A->Busy()&&
            !AI->GetBlackboardComponent()->GetValueAsObject(TEXT("Target"))&&!AI->GetFocusActor();
    }
    static float Hit(AUnknownHumanoid* A,APawn* P,int32 Kind)
    {
        FHitResult H(P,Cast<UPrimitiveComponent>(P->GetRootComponent()),P->GetActorLocation(),FVector::UpVector);
        if(Kind==1)return A->HitWithRound(H,20,FVector::ForwardVector,101);
        if(Kind==3){FColdSteelSkillShot S;S.CriticalChance=0;return A->HitWithArrow(H,20,FVector::ForwardVector,S);}
        if(Kind==2)
        {const float Before=P->FindComponentByClass<UFPSCombatHealthComponent>()->Health;
         UnknownSpell::Hit(A,P,20,0,0,0,0,ULightningDamage::StaticClass());return Before-P->FindComponentByClass<UFPSCombatHealthComponent>()->Health;}
        if(!UnknownSpell::IsTarget(A,P))return 0;
        return UGameplayStatics::ApplyPointDamage(P,20,FVector::ForwardVector,H,A->GetController(),A,UEnemyMeleeDamage::StaticClass());
    }
    static bool StartMagic(AUnknownHumanoid* A)
    {
        auto* M=A->EquipmentModel();auto* Blizzard=A->FindComponentByClass<UFPSBlizzardComponent>();if(!M||!Blizzard)return false;
        FColdSteelNetCastRequest R;R.SourcePawn=A;R.CastId=101;R.SkillId=TEXT("blizzard");
        R.AimPoint=A->GetActorLocation()+FVector(500,0,-200);R.AimNormal=FVector::UpVector;R.AimAxis=FVector::ForwardVector;
        auto B=M->BlizzardStats(2);B.Duration=600;B.TickSeconds=30;
        if(!Blizzard->NetCommitZone(A,R,M,B))return false;
        for(TActorIterator<AFPSBlizzardZone> It(A->GetWorld());It;++It)if(It->GetOwner()==A)It->bAlwaysRelevant=true;
        R.SkillId=TEXT("iceArmor");++R.CastId;auto Ice=M->IceArmorStats(2);Ice.Duration=600;Ice.PulseSeconds=600;
        bool OK=A->FindComponentByClass<UFPSIceArmorComponent>()->NetRelease(A,R,M,Ice);
        R.SkillId=TEXT("lightningHaste");++R.CastId;auto H=M->LightningHasteStats(2);H.Duration=600;
        OK&=A->FindComponentByClass<UFPSLightningHasteComponent>()->NetRelease(A,R,M,H);
        R.SkillId=TEXT("flameArmor");++R.CastId;auto F=M->FireMagicStats(R.SkillId,2);F.Duration=600;
        OK&=A->FindComponentByClass<UFPSFireMagicComponent>()->NetRelease(A,R,M,F);
        R.SkillId=TEXT("stormDomain");++R.CastId;auto D=M->ElectricMagicStats(R.SkillId,2);D.Duration=600;
        OK&=A->FindComponentByClass<UFPSElectricMagicComponent>()->NetRelease(A,R,M,D);
        return OK;
    }
    static bool Ready(AUnknownHumanoid* A){return A&&A->bVisualReady;}
};

void AUnknownLifeAuditController::BeginPlay()
{
    Super::BeginPlay();if(!UnknownLife::Enabled()||!IsLocalController())return;
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!M||!M->IsAudit())return;
    auto P=M->Snapshot();P.Items.Reset();P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();P.DungeonRun={};
    P.Level=30;P.Points=0;P.Attributes.Reset();
    for(FName K:{FName("str"),FName("dex"),FName("intt"),FName("con"),FName("wis"),FName("luck")})P.Attributes.Add(K,10);
    P.Attributes[TEXT("con")]=40;P.Health=300;P.Mana=300;P.Stamina=150;
    auto Weapon=M->CreateItem(TEXT("ue_rune_sword"));Weapon.InstanceId=TEXT("unknown_life_sword");Weapon.Place=1;Weapon.Cell=6;P.Items.Add(Weapon);
    if(!HasAuthority())FGuid::Parse(TEXT("167FE8A0848A4DDA904E158E1A3B2529"),P.NetworkProfileId);
    M->AdoptNetMirror(P);
}
void AUnknownLifeAuditController::Tick(float Delta)
{
    Super::Tick(Delta);if(!UnknownLife::Enabled()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());if(!P)return;
    if(!Attached.IsValid())if(auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    {M->AttachPawn(P);P->ApplyColdSteelProfile(M);Attached=P;}
    UnknownLife::Freeze(P);P->SetActorTickEnabled(false);
    if(HasAuthority()||Probe.Step<0)return;
    const int32 Key=Probe.Stage*100+Probe.Step;if(Key==Reported)return;
    if(Key!=Watching){Watching=Key;WatchingAt=Now;}
    auto* HP=P->FindComponentByClass<UFPSCombatHealthComponent>();
    bool OK=Probe.Pawn==P&&HP&&FMath::IsNearlyEqual(HP->Health,Probe.Health,.02f)&&Probe.Monsters.Num()==4&&UnknownLife::Zones(GetWorld())==Probe.Zones;
    for(const auto& A:Probe.Monsters)OK&=FUnknownLifeAuditAccess::Ready(A);
    if(Probe.Stage==1&&Probe.Step==0)OK&=UnknownLife::AllGone();
    if(Probe.bMageDead)
    {
        auto* A=Probe.Monsters.IsValidIndex(2)?Probe.Monsters[2].Get():nullptr;
        OK&=A&&A->Dead();
        if(A)if(auto* F=A->FindComponentByClass<UFPSFireMagicComponent>())OK&=F->ArmorRemaining()<=0&&!F->IsDragonBreathActive();
        if(A)if(auto* E=A->FindComponentByClass<UFPSElectricMagicComponent>())OK&=E->DomainRemaining()<=0;
    }
    if(OK||Now-WatchingAt>60)
    {
        FString Detail=FString::Printf(TEXT("stage=%d step=%d pawn=%s expected=%s hp=%.2f expected_hp=%.2f zones=%d expected_zones=%d"),Probe.Stage,Probe.Step,*GetNameSafe(P),*GetNameSafe(Probe.Pawn),HP?HP->Health:-1,Probe.Health,UnknownLife::Zones(GetWorld()),Probe.Zones);
        UnknownLife::Row(OK,FString::Printf(TEXT("client_%d"),Key),Detail);Reported=Key;ServerObserved(Key,OK,Detail);
        if(Probe.Stage==0&&Probe.Step==5)
        {UnknownLife::PreviousActors.Reset();UnknownLife::PreviousActors.Add(P);for(const auto& A:Probe.Monsters)UnknownLife::PreviousActors.Add(A);for(TActorIterator<AFPSBlizzardZone> It(GetWorld());It;++It)UnknownLife::PreviousActors.Add(*It);}
    }
}
void AUnknownLifeAuditController::ServerObserved_Implementation(int32 Key,bool OK,const FString& Detail)
{if(!UnknownLife::Enabled()||Key!=Probe.Stage*100+Probe.Step||Key<=Finished)return;Finished=Key;if(auto* G=GetWorld()->GetAuthGameMode<AUnknownLifeAuditGameMode>())G->Observe(Key,OK,Detail);}
void AUnknownLifeAuditController::ClientFinish_Implementation()
{if(!UnknownLife::Enabled())return;UnknownLife::Save(GetWorld());ExitAt=GetWorld()->GetRealTimeSeconds()+1.;}
void AUnknownLifeAuditController::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AUnknownLifeAuditController,Probe);}

AUnknownLifeAuditGameMode::AUnknownLifeAuditGameMode()
{PrimaryActorTick.bCanEverTick=true;PlayerControllerClass=AUnknownLifeAuditController::StaticClass();PlayerStateClass=AColdSteelPlayerState::StaticClass();DefaultPawnClass=AFPSGAMECharacter::StaticClass();HUDClass=nullptr;}
void AUnknownLifeAuditGameMode::StartPlay()
{
    Super::StartPlay();if(!UnknownLife::Enabled())return;Started=GetWorld()->GetRealTimeSeconds();Stage=UGameplayStatics::GetIntOption(OptionsString,TEXT("LifeStage"),0);
    for(int32 I=0;I<4;++I)Monsters.Add(FUnknownLifeAuditAccess::Spawn(GetWorld(),I));
    auto* Floor=GetWorld()->SpawnActor<AStaticMeshActor>(FVector(20000,2400,-50),FRotator::ZeroRotator);
    Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
    Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    Floor->SetActorScale3D(FVector(100,100,1));Floor->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    UE_LOG(LogTemp,Display,TEXT("UNKNOWN_LIFE_HOST_READY stage=%d"),Stage);
}
bool AUnknownLifeAuditGameMode::Record(bool OK,const FString& Name,const FString& Detail)
{
    UnknownLife::Row(OK,Name,Detail);if(!OK){UnknownLife::Save(GetWorld());if(Guest)Guest->ClientFinish();ExitAt=GetWorld()->GetRealTimeSeconds()+3.;}return OK;
}
void AUnknownLifeAuditGameMode::Observe(int32 Key,bool OK,const FString& Detail){Record(OK,FString::Printf(TEXT("remote_%d"),Key),Detail);}
void AUnknownLifeAuditGameMode::Publish(int32 Next,int32 Zones,bool Dead)
{
    Step=Next;Guest->Probe.Stage=Stage;Guest->Probe.Step=Step;Guest->Probe.Pawn=Guest->GetPawn();
    Guest->Probe.Health=Guest->GetPawn()->FindComponentByClass<UFPSCombatHealthComponent>()->Health;
    Guest->Probe.Monsters=Monsters;Guest->Probe.Zones=Zones;Guest->Probe.bMageDead=Dead;Guest->ForceNetUpdate();
}
void AUnknownLifeAuditGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!UnknownLife::Enabled())return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Now-Started>480){Record(false,TEXT("timeout"),FString::FromInt(Step));return;}if(Travelling)return;
    if(!Guest)for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)if(!It->Get()->IsLocalController())Guest=Cast<AUnknownLifeAuditController>(It->Get());
    if(!Guest)return;
    auto* P=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();auto* M=PS?PS->GetShadowModel():nullptr;
    if(!P||!M||M->RuntimePawn()!=P)return;UnknownLife::Freeze(P);P->SetActorTickEnabled(false);PS->SetActorTickEnabled(false);
    auto* HP=P->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Step>=0&&Step!=10&&Step!=11&&Guest->Finished<Stage*100+Step)return;
    if(Stage==1)
    {
        if(Step<0)
        {
            if(!Record(UnknownLife::AllGone()&&UnknownLife::Zones(GetWorld())==0&&!HP->IsDead(),TEXT("travel_old_world_removed")))return;
            Publish(0);return;
        }
        if(Step==0)
        {
            P->SetActorLocation(FVector(20000,0,250));bool OK=true;
            for(int32 I=0;I<4;++I){OK&=FUnknownLifeAuditAccess::Target(Monsters[I],P,false);const float Before=HP->Health,Applied=FUnknownLifeAuditAccess::Hit(Monsters[I],P,I);OK&=Applied>0&&FMath::IsNearlyEqual(Before-HP->Health,Applied,.02f);}
            if(!Record(OK,TEXT("travel_new_pawn_target_and_single_damage")))return;Publish(1);return;
        }
        UnknownLife::Save(GetWorld());UE_LOG(LogTemp,Display,TEXT("UNKNOWN_LIFE_RESULT passed=%d cases=%d"),UnknownLife::Passed,UnknownLife::Rows.Num());Guest->ClientFinish();ExitAt=Now+3.;return;
    }
    if(Step<0){Publish(0);return;}
    if(Step==0)
    {
        P->SetActorLocation(FVector(20000,0,250));bool OK=true;
        for(const auto& A:Monsters)OK&=FUnknownLifeAuditAccess::Target(A,P,true);
        UCombatStatusFormula::GetOrAdd(P)->AddBurn(Monsters[2],10,1,30,.1f,1);
        DeadPawn=P;UnknownSpell::Hit(Monsters[2],P,100000,0,0,0,0,ULightningDamage::StaticClass());
        OK&=HP->IsDead();for(int32 I=0;I<4;++I){OK&=FUnknownLifeAuditAccess::Lost(Monsters[I]);OK&=FUnknownLifeAuditAccess::Hit(Monsters[I],P,I)==0;}
        if(!Record(OK,TEXT("death_drops_four_targets_and_rejects_late_hits")))return;Publish(1);Deadline=Now+4.;return;
    }
    if(Step==1)
    {
        if(P==DeadPawn.Get()||Now<Deadline)return;
        StableHealth=HP->Health;Deadline=Now+1.4;Step=10;return;
    }
    if(Step==10)
    {
        // Step 10 is a local timer, not a network probe.
        if(Now<Deadline)return;
        bool OK=!DeadPawn.IsValid()&&!HP->IsDead()&&FMath::IsNearlyEqual(HP->Health,StableHealth,.02f);
        for(int32 I=0;I<4;++I){OK&=FUnknownLifeAuditAccess::Target(Monsters[I],P,false);const float Before=HP->Health,Applied=FUnknownLifeAuditAccess::Hit(Monsters[I],P,I);OK&=Applied>0&&FMath::IsNearlyEqual(Before-HP->Health,Applied,.02f);}
        if(!Record(OK,TEXT("respawn_no_old_dot_and_four_single_hits")))return;Publish(2);return;
    }
    if(Step==2)
    {
        // Retain an unloaded actor to exercise EndPlay-before-GC, as streaming does.
        auto* Old=FUnknownLifeAuditAccess::Spawn(GetWorld(),1);Old->RouteEndPlay(EEndPlayReason::RemovedFromWorld);
        const float Before=HP->Health;bool OK=!UnknownSpell::IsTarget(Old,P)&&FUnknownLifeAuditAccess::Hit(Old,P,1)==0&&HP->Health==Before;Old->Destroy();
        if(!Record(OK,TEXT("streamed_caster_late_hit_rejected")))return;
        P->SetActorLocation(FVector(0,0,250));Monsters[2]->SetActorLocation(FVector(20000,2400,200));Monsters[2]->Home=Monsters[2]->GetActorLocation();
        Step=11;return;
    }
    if(Step==11)
    {
        if(!FUnknownLifeAuditAccess::StartMagic(Monsters[2]))return;Publish(3,1);return;
    }
    if(Step==3)
    {
        UGameplayStatics::ApplyDamage(Monsters[2],1000000,Guest,P,UDamageType::StaticClass());
        if(!Record(Monsters[2]->Dead()&&UnknownLife::Zones(GetWorld())==0,TEXT("mage_death_removes_blizzard_immediately")))return;Publish(4,0,true);return;
    }
    if(Step==4)
    {
        if(Monsters[2]->Dead()){Monsters[2]->Destroy();Monsters[2]=FUnknownLifeAuditAccess::Spawn(GetWorld(),2);}
        if(!FUnknownLifeAuditAccess::StartMagic(Monsters[2]))return;Publish(5,1);return;
    }
    if(Step==5)
    {
        UnknownLife::PreviousActors.Reset();UnknownLife::PreviousActors.Add(P);for(const auto& A:Monsters)UnknownLife::PreviousActors.Add(A);
        for(TActorIterator<AFPSBlizzardZone> It(GetWorld());It;++It)UnknownLife::PreviousActors.Add(*It);
        bUseSeamlessTravel=true;Travelling=GetWorld()->ServerTravel(TEXT("/Engine/Maps/Entry?game=/Script/FPSGAME.UnknownLifeAuditGameMode?LifeStage=1"),false);
        Record(Travelling,TEXT("seamless_travel_accepted"));
    }
}
