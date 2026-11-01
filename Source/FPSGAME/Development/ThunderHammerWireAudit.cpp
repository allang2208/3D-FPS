#include "ThunderHammerWireAudit.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/ThunderHammerThrown.h"
#include "../Production/WarhammerShockwave.h"
#include "../Production/ThunderHammerRunes.h"
#include "../Production/ThunderHammerPommel.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/FPSLightningArc.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/NurseZombie.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/World.h"
#include "Engine/StreamableManager.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace ThunderWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("ThunderHammerWireAudit"));}
const TCHAR* Cases[]={TEXT("guest_throw_four_bolts"),TEXT("switch_preserves_ground_hammer"),TEXT("switch_back_recall_and_catch"),
    TEXT("second_throw"),TEXT("unequip_retires_both_peers"),TEXT("jilei_rpc_resources_and_four_bolts"),
    TEXT("echo_and_inspiration_replication"),TEXT("static_field_heavy_status_replication"),TEXT("coil_heavy_damage_arc_replication"),TEXT("throw_before_disconnect")};
void Network(UWorld* World)
{
#if DO_ENABLE_NET_TEST
    if(auto* Driver=World->GetNetDriver())
    {FPacketSimulationSettings S;S.PktLag=60;S.PktLoss=3;Driver->SetPacketSimulationSettings(S);}
#endif
}
FColdSteelProfile Seed(UColdSteelStatusModel* Model,int32 Phase)
{
    auto P=Model->Snapshot();P.Items.Reset();P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();P.DungeonRun={};
    P.Stamina=150;P.Mana=100;P.bSprintExhausted=false;P.StaminaRecoveryDelay=0;
    auto I=Model->CreateItem(TEXT("ue_thunder_god_hammer"));I.InstanceId=TEXT("wire_thor");I.Place=1;I.Cell=6;
    TSharedPtr<FJsonObject> D;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),D);
    const bool GripCase=Phase==7||Phase==8;
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("head_mount"),Phase==5?TEXT("ji_lei_seat"):GripCase?TEXT("factory"):TEXT("guan_lei_seat"));
    Parts->SetStringField(TEXT("pommel"),Phase==6?TEXT("lei_xi_pommel"):GripCase?TEXT("factory"):TEXT("zhen_ting_pommel"));
    if(GripCase)Parts->SetStringField(TEXT("grip"),Phase==7?TEXT("static_field_grip"):TEXT("coil_grip"));
    Parts->SetStringField(TEXT("rune"),TEXT("hui_xiang_rune"));D->SetObjectField(TEXT("gunsmith_parts"),Parts);
    I.Data.Reset();FJsonSerializer::Serialize(D.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));P.Items.Add(I);
    auto Other=Model->CreateItem(TEXT("ue_m1911"));Other.InstanceId=TEXT("wire_pistol");Other.Place=1;Other.Cell=9;P.Items.Add(Other);
    return P;
}
}
void AThunderHammerWireController::Prepare(AFPSGAMECharacter* Controlled,UColdSteelStatusModel* Model,int32 Phase)
{
    auto P=(Phase==1||Phase==2||Phase==4)?Model->Snapshot():ThunderWire::Seed(Model,Phase);
    P.ActiveWeaponSlot=Phase==1?9:6;
    if(Phase==4)for(auto& I:P.Items)if(I.InstanceId==TEXT("wire_thor")){I.Place=0;I.Cell=0;}
    Model->AdoptNetMirror(P);Model->AttachPawn(Controlled);
    Controlled->SetActorLocation(FVector(0,0,100));Controlled->SetActorRotation(FRotator::ZeroRotator);
    Controlled->GetController()->SetControlRotation(FRotator::ZeroRotator);
    // Disabling Tick alone does not stop authority movement driven by already
    // queued client ServerMove packets during initial possession.
    Controlled->GetCharacterMovement()->StopMovementImmediately();Controlled->GetCharacterMovement()->DisableMovement();
    Controlled->GetCharacterMovement()->SetComponentTickEnabled(false);
    Controlled->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Controlled->SetActorTickEnabled(false);
    auto* Tool=Controlled->FindComponentByClass<UProductionToolComponent>();
    if(Controlled->IsLocallyControlled())
    {Tool->RefreshHeldTool();if(Tool->LoadHandle)Tool->LoadHandle->WaitUntilComplete();}
    Tool->SetComponentTickEnabled(false);
    Tool->Character=Controlled;Tool->Kind=TEXT("warhammer");Tool->EquippedId=TEXT("wire_thor");Tool->bUsesArms=false;
    Tool->Elapsed=Tool->EquipElapsed=-1.f;
    if(Phase!=1&&Phase!=2&&Phase!=4)
    {Tool->BluntServerReadyAt=0.;Tool->ThunderCatchStartedAt=-100.;Tool->ApplyToolStats(Model->ActiveProductionTool(),Model);}
    if(Controlled->HasAuthority())
    {
        Controlled->FindComponentByClass<UFPSCombatHealthComponent>()->Health=100;
        if(Phase==4)Tool->CommitThunderEquipmentChange(P);
    }
    Controlled->ForceNetUpdate();
}
void AThunderHammerWireController::ClientCase_Implementation(int32 Phase,AActor* Target)
{
    if(!ThunderWire::Enabled()||HasAuthority()||Phase<0||Phase>=UE_ARRAY_COUNT(ThunderWire::Cases))return;
    // A newly spawned target's NetGUID can be unresolved on the first RPC.
    // Keep the running case's clock, but accept its resolved reference on retry.
    if(Current==Phase){if(IsValid(Target))Subject=Target;return;}
    auto* Controlled=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Controlled||!Model||!Model->IsAudit())return;
    ThunderWire::Network(GetWorld());Prepare(Controlled,Model,Phase);Subject=Target;Current=Phase;Started=GetWorld()->GetRealTimeSeconds();
    Released=Sent=SawReturn=ChargeSent=false;Waves.Reset();Hammers.Reset();Arcs.Reset();Catches=AudioCatches=0;
    auto* Tool=Controlled->FindComponentByClass<UProductionToolComponent>();
    if(Phase==2)Tool->ServerRecallThunderHammer();
}
void AThunderHammerWireController::HammerDestroyed(AActor* Actor)
{
    if(auto* H=Cast<AThunderHammerThrown>(Actor);H&&H->Phase==3)
    {
        ++Catches;if(H->bRecallCatchAudioPlayed)++AudioCatches;
        UE_LOG(LogTemp,Display,TEXT("THUNDER_WIRE_CATCH definition=%s assets=%d completed=%d sound=%s played=%d"),*H->Weapon.Definition,H->Assets.IsValid(),
            H->Assets&&H->Assets->HasLoadCompleted(),*GetNameSafe(H->RecallCatchSound),H->bRecallCatchAudioPlayed);
    }
}
void AThunderHammerWireController::Tick(float Delta)
{
    Super::Tick(Delta);if(!ThunderWire::Enabled()||HasAuthority()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0.){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(Current<0||Sent)return;
    auto* Controlled=Cast<AFPSGAMECharacter>(GetPawn());auto* Tool=Controlled?Controlled->FindComponentByClass<UProductionToolComponent>():nullptr;
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Tool||!Model)return;
    const double Age=Now-Started;
    // Count receipts from this release. A previous heavy's fading shockwave
    // can still be alive (or in transit) during the next case's warm-up.
    if(Released)
    {
        for(TActorIterator<AWarhammerShockwave> It(GetWorld());It;++It)if(It->GetOwner()==Controlled)Waves.Add(*It);
        for(TActorIterator<AFPSLightningArc> It(GetWorld());It;++It)if(It->GetOwner()==Controlled&&It->GetLocalRole()==ROLE_SimulatedProxy)Arcs.Add(*It);
    }
    if(auto* H=Tool->ThrownHammer.Get())
    {
        if(!Hammers.Contains(H)){Hammers.Add(H);H->OnDestroyed.AddUniqueDynamic(this,&AThunderHammerWireController::HammerDestroyed);}
        SawReturn|=H->IsReturning();
    }
    const bool Throw=Current==0||Current==3||Current==9;
    const bool Heavy=Throw||Current==5||Current==7||Current==8;
    if(Heavy&&!ChargeSent&&Age>2.)
    {ChargeSent=true;Tool->BluntAttackId=100+Current;Tool->ServerBeginBluntCharge(100+Current);}
    if(Heavy&&!Released&&Age>5.0)
    {
        Released=true;
        if(Current==5)Tool->ServerReleaseThunderCall(100+Current,FVector(1000,0,0));
        else Tool->ServerBeginBluntAttack(100+Current,true,false);
    }
    bool OK=false;
    if(Throw)OK=Age>8.&&Tool->ThrownHammer&&Tool->ThrownHammer->IsGrounded()&&Tool->IsThunderHammerAway()&&Waves.Num()==4;
    else if(Current==1)OK=Age>.7&&Tool->ThrownHammer&&Tool->ThrownHammer->IsGrounded()&&!Tool->IsThunderHammerAway()&&!Tool->ThunderAwayInstance.IsEmpty();
    else if(Current==2)OK=Age>1.8&&SawReturn&&Catches==1&&AudioCatches==1&&!Tool->ThrownHammer&&Tool->ThunderAwayInstance.IsEmpty()&&Tool->ThunderCatchStartedAt>0.;
    else if(Current==4)OK=Age>.7&&!Tool->ThrownHammer&&Tool->ThunderAwayInstance.IsEmpty();
    else if(Current==5)OK=Age>6.7&&Waves.Num()==4&&!Tool->bThunderCallCharging&&Model->Mana()<99.&&Model->Stamina()<149.&&Tool->ThunderCallResourceRevision>0;
    else if(Current==6)
    {
        const auto* Buff=Controlled->FindComponentByClass<UCombatStatusFormula>();const auto* Debuff=Subject?Subject->FindComponentByClass<UCombatStatusFormula>():nullptr;
        OK=Age>.5&&Buff&&Buff->MagicInspirationAttackSpeed()==1.25f&&Debuff&&Debuff->ElectrifiedCount()==2;
    }
    else if(Current==7||Current==8)
    {
        const auto* Debuff=Subject?Subject->FindComponentByClass<UCombatStatusFormula>():nullptr;
        const auto* Enemy=Cast<ANurseZombie>(Subject);
        OK=Age>5.5&&Debuff&&Debuff->ElectrifiedCount()==2&&Enemy&&
            (Current==7?Enemy->Health==100000.f:(Enemy->Health<100000.f&&Arcs.Num()==1));
    }
    if((Current==0||Current==2||Current==6)&&Now-DiagnosticAt>2.)
    {
        DiagnosticAt=Now;const auto* Buff=Controlled->FindComponentByClass<UCombatStatusFormula>();
        const auto* Debuff=Subject?Subject->FindComponentByClass<UCombatStatusFormula>():nullptr;
        const auto* H=Tool->ThrownHammer.Get();
        UE_LOG(LogTemp,Display,TEXT("THUNDER_WIRE_CLIENT phase=%d age=%.2f pawn=%s aim=%s hammer=%s flight=%d target=%s buff=%.2f stacks=%d"),
            Current,Age,*Controlled->GetActorLocation().ToString(),*Controlled->GetMeleeAimTransform().GetLocation().ToString(),
            H?*H->GetActorLocation().ToString():TEXT("none"),H?H->Phase:-1,*GetNameSafe(Subject),Buff?Buff->MagicInspirationAttackSpeed():-1.f,Debuff?Debuff->ElectrifiedCount():-1);
        if(H)UE_LOG(LogTemp,Display,TEXT("THUNDER_WIRE_VISUAL mode=%d assets=%d completed=%d sound=%s definition=%s"),GetNetMode(),H->Assets.IsValid(),
            H->Assets&&H->Assets->HasLoadCompleted(),*GetNameSafe(H->RecallCatchSound),*H->Weapon.Definition);
    }
    if(OK||Age>17.)
    {
        Sent=true;ServerResult(Current,OK,FString::Printf(TEXT("age=%.2f waves=%d arcs=%d away=%s thrown=%d return=%d catches=%d audio=%d mana=%.2f stamina=%.2f revision=%lld"),
            Age,Waves.Num(),Arcs.Num(),*Tool->ThunderAwayInstance,IsValid(Tool->ThrownHammer),SawReturn,Catches,AudioCatches,Model->Mana(),Model->Stamina(),Tool->ThunderCallResourceRevision));
    }
}
void AThunderHammerWireController::ServerResult_Implementation(int32 Phase,bool OK,const FString& Detail)
{
    if(!ThunderWire::Enabled()||Phase!=Finished)return;
    auto* Controlled=Cast<AFPSGAMECharacter>(GetPawn());auto* Tool=Controlled->FindComponentByClass<UProductionToolComponent>();
    auto* Model=ColdSteelAuthority::ForPawn(Controlled);bool Authority=false;
    if(Phase==0||Phase==3||Phase==9)Authority=Tool->ThrownHammer&&Tool->ThrownHammer->IsGrounded()&&Tool->IsThunderHammerAway();
    else if(Phase==1)Authority=Tool->ThrownHammer&&!Tool->IsThunderHammerAway();
    else if(Phase==2||Phase==4)Authority=!Tool->ThrownHammer&&Tool->ThunderAwayInstance.IsEmpty();
    else if(Phase==5)Authority=!Tool->bThunderCallCharging&&Model->Mana()<99.&&Model->Stamina()<149.&&Tool->BluntLastServerRequestId==105;
    else if(Phase==6)Authority=Controlled->FindComponentByClass<UCombatStatusFormula>()->MagicInspirationAttackSpeed()==1.25f;
    else if(Phase==7||Phase==8)
    {
        const auto* Enemy=Cast<ANurseZombie>(Subject);const auto* Status=Enemy?Enemy->FindComponentByClass<UCombatStatusFormula>():nullptr;
        Authority=Status&&Status->ElectrifiedCount()==2&&Enemy&&(Phase==7?Enemy->Health==100000.f:Enemy->Health<100000.f);
    }
    auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),ThunderWire::Cases[Phase]);R->SetBoolField(TEXT("passed"),OK&&Authority);R->SetStringField(TEXT("client"),Detail);R->SetBoolField(TEXT("authority"),Authority);
    Rows.Add(MakeShared<FJsonValueObject>(R));Passed&=OK&&Authority;++Finished;
    UE_LOG(LogTemp,Display,TEXT("THUNDER_WIRE_CASE %d pass=%d authority=%d %s"),Phase,OK&&Authority,Authority,*Detail);
}
void AThunderHammerWireController::ClientFinish_Implementation()
{if(ThunderWire::Enabled())ExitAt=GetWorld()->GetRealTimeSeconds()+.5;}
AThunderHammerWireGameMode::AThunderHammerWireGameMode()
{PlayerControllerClass=AThunderHammerWireController::StaticClass();PlayerStateClass=AThunderHammerWirePlayerState::StaticClass();DefaultPawnClass=AFPSGAMECharacter::StaticClass();PrimaryActorTick.bCanEverTick=true;}
void AThunderHammerWireGameMode::PostLogin(APlayerController* PC)
{Super::PostLogin(PC);if(ThunderWire::Enabled()&&!PC->IsLocalController()){Guest=Cast<AThunderHammerWireController>(PC);Joined=GetWorld()->GetRealTimeSeconds();}}
void AThunderHammerWireGameMode::Logout(AController* Exiting)
{if(Exiting==Guest)LoggedOut=true;Super::Logout(Exiting);}
void AThunderHammerWireGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!ThunderWire::Enabled())return;const double Now=GetWorld()->GetRealTimeSeconds();
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Model||!Model->IsAudit())return;
    if(!Seeded)
    {
        ThunderWire::Network(GetWorld());auto* Floor=GetWorld()->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Floor);
        Floor->AddInstanceComponent(Box);Floor->SetRootComponent(Box);Box->SetBoxExtent(FVector(10000,10000,20));Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        Box->SetCollisionResponseToAllChannels(ECR_Block);Box->RegisterComponent();Floor->SetActorLocation(FVector(0,0,-20));
        Seeded=true;UE_LOG(LogTemp,Display,TEXT("THUNDER_WIRE_HOST_READY"));
    }
    if(Finishing)
    {
        if(Now<ExitAt)return;
        int32 Remaining=0;for(TActorIterator<AThunderHammerThrown> It(GetWorld());It;++It)++Remaining;
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),TEXT("disconnect_retires_ground_hammer"));Row->SetBoolField(TEXT("passed"),LoggedOut&&Remaining==0);FinalRows.Add(MakeShared<FJsonValueObject>(Row));
        auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),FinalPassed&&LoggedOut&&Remaining==0);R->SetArrayField(TEXT("cases"),FinalRows);R->SetNumberField(TEXT("net_mode"),GetNetMode());
        R->SetStringField(TEXT("scope"),TEXT("real UDP component RPCs, throw/recall/destruction, JiLei resources, effects and status replication; deterministic isolated profiles, no inventory UI/upload or rendering/audio audition"));
        FString Text,Out;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Text));if(FParse::Value(FCommandLine::Get(),TEXT("ThunderWireOutput="),Out))FFileHelper::SaveStringToFile(Text,*Out);
        UE_LOG(LogTemp,Display,TEXT("THUNDER_WIRE_FINISHED %s"),*Text);FPlatformMisc::RequestExit(false);return;
    }
    if(!Guest)return;
    if(Guest->Finished>=UE_ARRAY_COUNT(ThunderWire::Cases)||Now-Joined>175.)
    {FinalRows=Guest->Rows;FinalPassed=Guest->Passed&&Guest->Finished==UE_ARRAY_COUNT(ThunderWire::Cases);Finishing=true;ExitAt=Now+8.;Guest->ClientFinish();return;}
    auto* Controlled=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();if(!Controlled||!PS)return;
    if(!GuestModel){GuestModel=Model->CreateShadowModel(ThunderWire::Seed(Model,0));PS->ShadowModel=GuestModel;Controlled->NetShadowProfile=GuestModel;}
    if(!GuestModel)return;
    if(Prepared!=Guest->Finished)
    {
        Prepared=Guest->Finished;AThunderHammerWireController::Prepare(Controlled,GuestModel,Prepared);LastSetup=-10.;
        if(Prepared==6||Prepared==7||Prepared==8)
        {
            if(Subject)Subject->Destroy();
            FActorSpawnParameters S;S.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            S.CustomPreSpawnInitialization=[](AActor* A){CastChecked<ACharacter>(A)->AutoPossessAI=EAutoPossessAI::Disabled;};
            auto* Enemy=GetWorld()->SpawnActor<ANurseZombie>(FVector(1000,0,100),FRotator::ZeroRotator,S);Enemy->Health=Enemy->MaxHealth=100000.f;Subject=Enemy;Guest->Subject=Enemy;
            if(Prepared==6)
            {
                auto Shot=ColdSteelSkills::Snapshot(Controlled,GuestModel->ActiveProductionTool());
                ThunderHammerRunes::ApplyStacks(Controlled,Enemy,Shot,5);
                ThunderHammerPommel::ConfirmElectricDamage(Controlled,Shot.HammerLightning,10.f);
            }
        }
    }
    if(Prepared==5)GuestModel->TickRuntime(Delta,Controlled);
    if((Prepared==0||Prepared==2||Prepared==6)&&Now-DiagnosticAt>2.)
    {
        DiagnosticAt=Now;const auto* Tool=Controlled->FindComponentByClass<UProductionToolComponent>();const auto* H=Tool->ThrownHammer.Get();
        const auto* Buff=Controlled->FindComponentByClass<UCombatStatusFormula>();
        const auto* Debuff=Subject?Subject->FindComponentByClass<UCombatStatusFormula>():nullptr;
        UE_LOG(LogTemp,Display,TEXT("THUNDER_WIRE_SERVER phase=%d pawn=%s aim=%s hammer=%s velocity=%s flight=%d target=%s buff=%.2f stacks=%d"),
            Prepared,*Controlled->GetActorLocation().ToString(),*Controlled->GetMeleeAimTransform().GetLocation().ToString(),H?*H->GetActorLocation().ToString():TEXT("none"),
            H?*H->Velocity.ToString():TEXT("none"),H?H->Phase:-1,*GetNameSafe(Subject),Buff?Buff->MagicInspirationAttackSpeed():-1.f,Debuff?Debuff->ElectrifiedCount():-1);
    }
    if(Now-LastSetup>1.){LastSetup=Now;Guest->ClientCase(Prepared,Subject);}
}
