#include "SkillWireAudit.h"
#include "ChainSlashAssets.h"
#include "ChainSlashMotion.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/MonsterAIController.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "UObject/StrongObjectPtr.h"

namespace SessionChainWire
{
FColdSteelProfile Seed(UColdSteelStatusModel* M,const FString& Id)
{
    auto P=M->Snapshot();P.Items.Reset();P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();P.DungeonRun={};
    auto Item=M->CreateItem(TEXT("ue_rune_sword"));Item.InstanceId=Id;Item.Place=1;Item.Cell=6;P.Items={Item};
    P.ChainSlashCooldown=P.ChainSlashCooldownDuration=0;P.UppercutStaminaSpent=0;P.Stamina=150;P.StaminaRecoveryDelay=0;P.bSprintExhausted=false;
    for(auto& S:P.Skills){S.Value.Level=1;S.Value.Experience=0;}return P;
}
void Equip(AFPSGAMECharacter* P,UColdSteelStatusModel* M)
{
    static TStrongObjectPtr<UAnimSequence> Clip(LoadObject<UAnimSequence>(nullptr,ChainSlash::Standard));
    P->ApplyColdSteelProfile(M);
    P->SetActorTickEnabled(false);P->GetCharacterMovement()->SetComponentTickEnabled(false);
    P->SetActorLocation(FVector(0,0,100));P->SetActorRotation(FRotator::ZeroRotator);
    if(auto* PC=Cast<APlayerController>(P->GetController()))PC->SetControlRotation(FRotator::ZeroRotator);
    P->FindComponentByClass<URuneSwordComponent>()->RefreshEquipment(M);
    P->RefreshQuickCombatCamera();
}
void Save(const FString& Json)
{
    FString Out;if(FParse::Value(FCommandLine::Get(),TEXT("SkillWireOutput="),Out))FFileHelper::SaveStringToFile(Json,*Out);
    UE_LOG(LogTemp,Display,TEXT("SESSION_CHAIN_WIRE %s"),*Json);
}
}
void ASkillWireAuditController::SetupSessionChain(ANurseZombie* InTarget,const FString& Id)
{
    if(HasAuthority()||bSetup||!InTarget)return;
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* PS=GetPlayerState<AColdSteelPlayerState>();
    if(!P||!M||!M->IsAudit()||!PS||PS->GetPawn()!=P)return;
    PS->SetActorTickEnabled(false);M->Current=SessionChainWire::Seed(M,Id);M->CurrentPawn=P;
    SessionChainWire::Equip(P,M);SetControlRotation(FRotator::ZeroRotator);
    Subject=InTarget;Weapon=Id;InitialStamina=150;ExpectedCost=M->ChainSlashStats().StaminaCost;
    Started=GetWorld()->GetRealTimeSeconds();bSetup=true;ConversationCase=0;
}
void ASkillWireAuditController::TickSessionChain()
{
    if(HasAuthority()||!IsLocalController())return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!bSetup||bDone)return;
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* Sword=P?P->FindComponentByClass<URuneSwordComponent>():nullptr;if(!Sword||!M)return;
    if(!bHit&&Now-Started>3&&Sword->ChainSlashStatusText().IsEmpty())bHit=Sword->BeginChainSlash();
    bLocked|=Sword->IsChainSlashActive();
    if(auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>())
        for(int32 I=0;I<4;++I)if(Body->GetBodyState().ActionVariant==ChainSlashMotion::Variant(I))ConversationCase|=1<<I;
    bPaid|=FMath::IsNearlyEqual(M->Stamina(),InitialStamina-ExpectedCost,.01f);bCooldown|=M->ChainSlashCooldown()>0;
    if((bLocked&&!Sword->IsBusy())||Now-Started>35)
    {
        bDone=true;const bool Finished=bLocked&&!Sword->IsBusy();
        SessionChainWire::Save(FString::Printf(TEXT("{\"passed\":%s,\"owner_started\":%s,\"owner_finished\":%s,\"cost_once\":%s,\"cooldown\":%s,\"owner_body_cut_mask\":%d}"),
            bHit&&Finished&&bPaid&&bCooldown&&ConversationCase==15?TEXT("true"):TEXT("false"),bHit?TEXT("true"):TEXT("false"),Finished?TEXT("true"):TEXT("false"),bPaid?TEXT("true"):TEXT("false"),bCooldown?TEXT("true"):TEXT("false"),ConversationCase));
        ServerResult(bHit,Finished,bPaid,bCooldown,ConversationCase==15);ExitAt=Now+4;
    }
}
void ASkillWireAuditGameMode::TickSessionChain()
{
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Guest)return;auto* P=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();if(!P||!PS)return;
    if(!GuestModel)
    {
        auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Host||!Host->IsAudit())return;
        Weapon=FGuid::NewGuid().ToString();GuestModel=Host->CreateShadowModel(SessionChainWire::Seed(Host,Weapon));
        PS->ShadowModel=GuestModel;GuestModel->CurrentPawn=P;P->NetShadowProfile=GuestModel;PS->SetActorTickEnabled(false);
        SessionChainWire::Equip(P,GuestModel);P->ForceNetUpdate();
        Target=GetWorld()->SpawnActor<ANurseZombie>(FVector(120,0,100),FRotator::ZeroRotator);
        Target->Health=Target->MaxHealth=100000;Target->Combat->ConfigureToughnessBar(FMonsterToughnessBarTuning());
        // Frozen NullRHI target: use its capsule as explicit hit geometry, rather
        // than depending on asynchronously loaded/rendered skeletal collision.
        Target->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
        if(auto* AI=Cast<AMonsterAIController>(Target->GetController()))AI->SetDecisionEnabled(false);
        Target->SetActorTickEnabled(false);Target->GetCharacterMovement()->SetComponentTickEnabled(false);
        Target->OnTakeAnyDamage.AddDynamic(this,&ThisClass::CountContact);
        InitialStamina=150;ExpectedCost=GuestModel->ChainSlashStats().StaminaCost;
    }
    if(Now-LastSetup>2&&!Guest->bReported)
    {
        LastSetup=Now;Guest->ClientSetup(Target,Weapon,InitialStamina,ExpectedCost);
        const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();const auto S=Body?Body->GetBodyState():FFPSBodyState();
        UE_LOG(LogTemp,Display,TEXT("SESSION_CHAIN_STATE pawn=%s target=%s eye=%s forward=%s family=%s weapon=%s instance=%s action=%s body_tick=%d hp=%.1f"),
            *P->GetActorLocation().ToCompactString(),*Target->GetActorLocation().ToCompactString(),*P->GetMeleeAimTransform().GetLocation().ToCompactString(),
            *P->GetMeleeAimTransform().GetUnitAxis(EAxis::X).ToCompactString(),*S.Family.ToString(),*S.Weapon.ToString(),*S.WeaponInstance,*S.ActionVariant.ToString(),Body&&Body->IsComponentTickEnabled(),Target->Health);
    }
    if(auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>())
        for(int32 I=0;I<4;++I)if(Body->GetBodyState().ActionVariant==ChainSlashMotion::Variant(I))Stage|=1<<I;
    if(Guest->bReported||Now-Joined>60)
    {
        const bool Paid=FMath::IsNearlyEqual(GuestModel->Stamina(),InitialStamina-ExpectedCost,.01f);
        const bool Trained=GuestModel->MasteryProgress(TEXT("chainSlash")).Experience==GuestModel->MasteryDefinition(TEXT("chainSlash")).UseExperience;
        const bool Passed=Guest->bReported&&Guest->bPassed&&Contacts==4&&Stage==15&&Paid&&Trained;
        SessionChainWire::Save(FString::Printf(TEXT("{\"passed\":%s,\"contacts\":%d,\"body_cut_mask\":%d,\"cost_once\":%s,\"release_training_once\":%s,\"client_reported\":%s,\"client_passed\":%s}"),
            Passed?TEXT("true"):TEXT("false"),Contacts,Stage,Paid?TEXT("true"):TEXT("false"),Trained?TEXT("true"):TEXT("false"),Guest->bReported?TEXT("true"):TEXT("false"),Guest->bPassed?TEXT("true"):TEXT("false")));
        ExitAt=Now+5;
    }
}
