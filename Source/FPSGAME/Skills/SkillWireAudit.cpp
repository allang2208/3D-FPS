#include "SkillWireAudit.h"
#include "FPSMeteorStrike.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "SwordUppercutTuning.h"
#include "Components/BoxComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameStateBase.h"
#include "HAL/PlatformMisc.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "LeapMovementWireAudit.inl"

namespace SkillWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("SkillWireAudit"));}
void Save(const FString& Json)
{
    FString Path;
    if(FParse::Value(FCommandLine::Get(),TEXT("SkillWireOutput="),Path))
    {IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);}
    UE_LOG(LogTemp,Display,TEXT("SKILL_WIRE_AUDIT %s"),*Json);
}
FColdSteelProfile Seed(UColdSteelStatusModel* Model,const FString& Id)
{
    auto P=Model->Snapshot();P.Items.Reset();P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();P.DungeonRun={};
    auto Item=Model->CreateItem(TEXT("ue_rune_sword"));Item.InstanceId=Id;Item.Place=1;Item.Cell=6;P.Items={Item};
    P.SwordUppercutCooldown=P.SwordUppercutCooldownDuration=0;P.UppercutStaminaSpent=0;P.Stamina=150;P.StaminaRecoveryDelay=0;P.bSprintExhausted=false;
    for(auto& Skill:P.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
    return P;
}
}

void ASkillWireAuditController::ClientSetup_Implementation(ANurseZombie* InSubject,const FString& Id,float Stamina,float Cost)
{
    if(FParse::Param(FCommandLine::Get(),TEXT("SessionChainWire"))){SetupSessionChain(InSubject,Id);return;}
    if(!SkillWire::Enabled()||HasAuthority()||bSetup||!InSubject)return;
    auto* Controlled=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* PS=GetPlayerState<AColdSteelPlayerState>();if(!Controlled||!Model||!PS||PS->GetPawn()!=Controlled||!Model->IsAudit())return;
    Subject=InSubject;Weapon=Id;InitialStamina=Stamina;ExpectedCost=Cost;
    PS->SetActorTickEnabled(false);Controlled->SetActorTickEnabled(false);Controlled->GetCharacterMovement()->SetComponentTickEnabled(false);
    Model->Current=SkillWire::Seed(Model,Id);Model->Current.Stamina=Stamina;Model->CurrentPawn=Controlled;
    bSetup=true;Started=GetWorld()->GetRealTimeSeconds();
    Model->CommitSwordUppercutRelease();
}
void ASkillWireAuditController::ClientRestoreStamina_Implementation()
{
    if(!SkillWire::Enabled()||HasAuthority())return;
    if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    {Model->Current.Stamina=100.f;Model->Current.bSprintExhausted=false;}
}
void ASkillWireAuditController::Tick(float Delta)
{
    if(FParse::Param(FCommandLine::Get(),TEXT("ForgedBladeWire"))){Super::Tick(Delta);TickForgedBlade();return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("LeapMovementWire"))){Super::Tick(Delta);TickLeapWire(Delta);return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("SessionChainWire"))){Super::Tick(Delta);TickSessionChain();return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("ConversationCombatWire"))){Super::Tick(Delta);TickConversationCombat();return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("StarMarrowWireAudit"))){Super::Tick(Delta);TickStarMarrow();return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("MeteorWireAudit"))){Super::Tick(Delta);TickMeteor();return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("FlameArmorWireAudit"))){Super::Tick(Delta);TickFlameArmor();return;}
    Super::Tick(Delta);if(!SkillWire::Enabled()||HasAuthority()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!bSetup||bDone)return;
    auto* Controlled=Cast<AFPSGAMECharacter>(GetPawn());auto* PS=GetPlayerState<AColdSteelPlayerState>();
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Controlled||!PS||!Model)return;
    if(!bHit&&Model->Current.UppercutStaminaSpent>0)
    {
        bPaid=FMath::IsNearlyEqual(Model->Stamina(),InitialStamina-ExpectedCost,.01f);
        bCooldown=Model->SwordUppercutCooldown()>0.f;bHit=true;
        FColdSteelNetHitReport Hit;Hit.Target=Subject;Hit.ItemDefinition=TEXT("ue_rune_sword");Hit.AttackMeta=SwordUppercut::AttackMeta;
        Hit.UppercutSerial=PS->UppercutSequence;Hit.Flags=1<<3;Hit.AimOrigin=Controlled->GetPawnViewLocation();Hit.ImpactPoint=Subject->GetActorLocation();
        Hit.HitNormal=-FVector::ForwardVector;Hit.Direction=FVector::ForwardVector;
        Hit.ClientFireTime=GetWorld()->GetGameState()?GetWorld()->GetGameState()->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
        PS->ServerReportHit(Hit);PS->ServerReportHit(Hit);PS->FinishSwordUppercut();
    }
    const auto* Status=Controlled->FindComponentByClass<UCombatStatusFormula>();
    if(Status&&Status->ExhaustionRemaining()>0.f)
    {
        auto* Move=CastChecked<UFPSCharacterMovementComponent>(Controlled->GetCharacterMovement());
        Move->UpdateFromCompressedFlags(FSavedMove_Character::FLAG_Custom_0);
        bLocked|=!Move->bWantsToSprint&&!Model->CanSprint()&&Model->Stamina()>0.f;
    }
    else if(bLocked)
    {
        auto* Move=CastChecked<UFPSCharacterMovementComponent>(Controlled->GetCharacterMovement());Move->UpdateFromCompressedFlags(FSavedMove_Character::FLAG_Custom_0);
        bUnlocked=Move->bWantsToSprint&&Model->CanSprint();
    }
    for(TActorIterator<AFPSMeteorStrike> It(GetWorld());It;++It)
    {
        auto* M=*It;
        if(!M->HasAuthority()&&M->bNetInit&&M->bImpacted&&M->LavaAge>=1.f&&M->Fragments.IsEmpty())bMeteor=true;
    }
    if((bHit&&bLocked&&bUnlocked&&bMeteor)||Now-Started>55.)
    {
        bDone=true;
        SkillWire::Save(FString::Printf(TEXT("{\"role\":\"client\",\"paid_once\":%s,\"cooldown\":%s,\"exhaustion_lock\":%s,\"exhaustion_unlock\":%s,\"late_meteor\":%s}"),
            bPaid?TEXT("true"):TEXT("false"),bCooldown?TEXT("true"):TEXT("false"),bLocked?TEXT("true"):TEXT("false"),bUnlocked?TEXT("true"):TEXT("false"),bMeteor?TEXT("true"):TEXT("false")));
        ServerResult(bPaid,bCooldown,bLocked,bUnlocked,bMeteor);ExitAt=Now+2.;
    }
}
void ASkillWireAuditController::ServerResult_Implementation(bool Paid,bool Cooldown,bool Locked,bool Unlocked,bool CorrectMeteor)
{if(SkillWire::Enabled()){bReported=true;bPassed=Paid&&Cooldown&&Locked&&Unlocked&&CorrectMeteor;}}

ASkillWireAuditGameMode::ASkillWireAuditGameMode()
{
    PlayerControllerClass=ASkillWireAuditController::StaticClass();PlayerStateClass=ASkillWireAuditPlayerState::StaticClass();DefaultPawnClass=AFPSGAMECharacter::StaticClass();
    PrimaryActorTick.bCanEverTick=true;
}
void ASkillWireAuditGameMode::BeginPlay()
{
    Super::BeginPlay();if(!SkillWire::Enabled())return;
    auto* Floor=GetWorld()->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Floor);Floor->SetRootComponent(Box);Floor->AddInstanceComponent(Box);
    Box->SetBoxExtent(FVector(5000,5000,20));Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();Floor->SetActorLocation(FVector(0,0,-20));
    if(FParse::Param(FCommandLine::Get(),TEXT("LeapMovementWire")))Box->SetMobility(EComponentMobility::Static);
    UE_LOG(LogTemp,Display,TEXT("SKILL_WIRE_HOST_READY"));
}
void ASkillWireAuditGameMode::PostLogin(APlayerController* Player)
{
    Super::PostLogin(Player);if(!SkillWire::Enabled())return;
    if(auto* PS=Player->GetPlayerState<AColdSteelPlayerState>())PS->SetActorTickEnabled(false);
    if(Player->IsLocalController())return;
    if(FParse::Param(FCommandLine::Get(),TEXT("PojunObserverWire"))&&!ChainObserver)
    {
        ChainObserver=CastChecked<ASkillWireAuditController>(Player);
        UE_LOG(LogTemp,Display,TEXT("POJUN_WIRE_OBSERVER_JOINED"));
        return;
    }
    Guest=Cast<ASkillWireAuditController>(Player);Joined=GetWorld()->GetRealTimeSeconds();
}
void ASkillWireAuditGameMode::CountContact(AActor* Actor,float Damage,const UDamageType* Type,AController* DamageController,AActor* Causer)
{if(SkillWire::Enabled()&&Damage>0.f)++Contacts;}
void ASkillWireAuditGameMode::Tick(float Delta)
{
    if(FParse::Param(FCommandLine::Get(),TEXT("ForgedBladeWire"))){Super::Tick(Delta);TickForgedBlade();return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("LeapMovementWire"))){Super::Tick(Delta);TickLeapWire(Delta);return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("SessionChainWire"))){Super::Tick(Delta);TickSessionChain();return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("ConversationCombatWire"))){Super::Tick(Delta);TickConversationCombat();return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("StarMarrowWireAudit"))){Super::Tick(Delta);TickStarMarrow(Delta);return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("MeteorWireAudit"))){Super::Tick(Delta);TickMeteor();return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("FlameArmorWireAudit"))){Super::Tick(Delta);TickFlameArmor();return;}
    Super::Tick(Delta);if(!SkillWire::Enabled())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Guest)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();
    if(!Pawn||!PS)return;
    if(!GuestModel)
    {
        auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Host||!Host->IsAudit())return;
        Weapon=FGuid::NewGuid().ToString();GuestModel=Host->CreateShadowModel(SkillWire::Seed(Host,Weapon));
        PS->ShadowModel=GuestModel;GuestModel->CurrentPawn=Pawn;Pawn->NetShadowProfile=GuestModel;
        PS->SetActorTickEnabled(false);Pawn->SetActorTickEnabled(false);Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);
        Pawn->SetActorLocation(FVector(0,0,100));Pawn->ForceNetUpdate();
        Target=GetWorld()->SpawnActor<ANurseZombie>(FVector(140,0,100),FRotator::ZeroRotator);
        Target->Health=Target->MaxHealth=100000;Target->Combat->ConfigureToughnessBar(FMonsterToughnessBarTuning());
        if(auto* AI=Cast<AMonsterAIController>(Target->GetController()))AI->SetDecisionEnabled(false);
        Target->SetActorTickEnabled(false);Target->OnTakeAnyDamage.AddDynamic(this,&ThisClass::CountContact);
        InitialStamina=GuestModel->Stamina();ExpectedCost=GuestModel->SwordUppercutStaminaCost();
    }
    if(Stage==0&&Now-LastSetup>2.){LastSetup=Now;Guest->ClientSetup(Target,Weapon,InitialStamina,ExpectedCost);}
    if(Stage==0&&GuestModel->MasteryProgress(TEXT("swordUppercut")).Experience>0)
    {
        Stage=1;ExhaustedAt=Now;UCombatStatusFormula::GetOrAdd(Pawn)->AddExhaustion();Guest->ClientRestoreStamina();
        auto Spell=GuestModel->FireMagicStats(TEXT("meteor"));Spell.Duration=20.f;
        Meteor=GetWorld()->SpawnActor<AFPSMeteorStrike>();Meteor->SetReplicates(false);
        Meteor->InitializeStrike(Pawn,Spell,FVector(2500,0,0),FVector::UpVector);MeteorAt=Now;
    }
    if(Stage==1&&Meteor&&Now-MeteorAt>GuestModel->FireMagicStats(TEXT("meteor")).FallSeconds+1.5)
    {Meteor->SetReplicates(true);Meteor->ForceNetUpdate();Stage=2;}
    if(Guest->bReported||Now-Joined>75.)
    {
        const bool ServerOK=Contacts==1&&FMath::IsNearlyEqual(GuestModel->Stamina(),InitialStamina-ExpectedCost,.01f)
            &&GuestModel->MasteryProgress(TEXT("swordUppercut")).Experience==GuestModel->MasteryDefinition(TEXT("swordUppercut")).HitExperience;
        SkillWire::Save(FString::Printf(TEXT("{\"role\":\"listen_host\",\"passed\":%s,\"contacts\":%d,\"server_cost_once\":%s,\"guest_reported\":%s,\"guest_passed\":%s}"),
            ServerOK&&Guest->bReported&&Guest->bPassed?TEXT("true"):TEXT("false"),Contacts,ServerOK?TEXT("true"):TEXT("false"),Guest->bReported?TEXT("true"):TEXT("false"),Guest->bPassed?TEXT("true"):TEXT("false")));
        ExitAt=Now+2.;
    }
}
