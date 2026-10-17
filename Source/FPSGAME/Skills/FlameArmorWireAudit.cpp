#include "SkillWireAudit.h"
#include "FPSFireMagicComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/PlatformMisc.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"

namespace ArmorWire
{
void Save(const FString& Json)
{
    FString Path;if(FParse::Value(FCommandLine::Get(),TEXT("SkillWireOutput="),Path))
    {IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);}
    UE_LOG(LogTemp,Display,TEXT("FLAME_ARMOR_WIRE %s"),*Json);
}
FColdSteelProfile Seed(UColdSteelStatusModel* M)
{
    auto P=M->Snapshot();P.Items.Reset();P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();P.DungeonRun={};P.Mana=1000;
    P.FlameArmorCooldown=P.FlameArmorCooldownDuration=0;P.NetworkProfileId=FGuid::NewGuid();
    for(auto& S:P.Skills){S.Value.Level=1;S.Value.Experience=0;}return P;
}
bool Card(AActor* A)
{
    const auto* S=A?A->FindComponentByClass<UStatusEffectsComponent>():nullptr;
    return S&&S->Snapshot().ContainsByPredicate([](const auto& V){return V.Type==TEXT("flameArmor")&&V.Remaining>0;});
}
}

void ASkillWireAuditController::ClientSetupArmor_Implementation(AFPSGAMECharacter* Existing)
{
    if(!FParse::Param(FCommandLine::Get(),TEXT("FlameArmorWireAudit"))||HasAuthority()||bSetup||!Existing)return;
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* PS=GetPlayerState<AColdSteelPlayerState>();
    if(!P||!M||!M->IsAudit()||!PS||PS->GetPawn()!=P)return;
    P->SetActorTickEnabled(false);P->GetCharacterMovement()->SetComponentTickEnabled(false);PS->SetActorTickEnabled(false);
    M->Current=ArmorWire::Seed(M);M->Current.Mana=M->Derived(TEXT("maxMp"));M->CurrentPawn=P;M->FlameArmorSkill.FireMagic.DurationBase=6;M->FlameArmorSkill.FireMagic.DurationGrowth=0;
    auto* F=P->FindComponentByClass<UFPSFireMagicComponent>();F->CastSnapshot=M->FireMagicStats(TEXT("flameArmor"));
    const float Before=M->Snapshot().Mana;if(!M->BeginFireMagicCast(F->CastSnapshot))return;
    FColdSteelNetCastRequest Req;Req.SkillId=TEXT("flameArmor");ArmorCastId=PS->RequestCastSpell(Req);F->ArmorLocalCastId=ArmorCastId;
    F->ArmorPendingRefund=Before-M->Snapshot().Mana;F->StartArmor();Req.Phase=1;Req.CastId=ArmorCastId;PS->RequestCastSpell(Req);
    // These are later requests on the same channel. Neither may refund/restart
    // the committed cast; its receipt must still reach the armor component.
    PS->RequestCastSpell(Req);Req.Phase=2;Req.CastId=ArmorCastId+123;PS->RequestCastSpell(Req);
    OtherArmor=Existing;bSetup=true;Started=GetWorld()->GetRealTimeSeconds();
}
void ASkillWireAuditController::TickFlameArmor()
{
    if(HasAuthority()||!IsLocalController())return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}if(!bSetup||bDone)return;
    APawn* P=GetPawn();auto* F=P?P->FindComponentByClass<UFPSFireMagicComponent>():nullptr;
    auto* Other=OtherArmor?OtherArmor->FindComponentByClass<UFPSFireMagicComponent>():nullptr;
    if(F&&F->NetArmor.CastId==ArmorCastId&&F->NetArmor.bActive&&!F->bArmorAwaitingReplication&&ArmorWire::Card(P))bArmorOwn=true;
    if(Other&&Other->NetArmor.CastId==700&&Other->ArmorRemaining()>0&&Other->ArmorRemaining()<11.f&&ArmorWire::Card(OtherArmor))bArmorOther=true;
    if(bArmorOwn&&F&&!F->NetArmor.bActive&&F->ArmorRemaining()<=0&&!ArmorWire::Card(P))bArmorOwnEnded=true;
    if(bArmorOther&&Other&&!Other->NetArmor.bActive&&Other->ArmorRemaining()<=0&&!ArmorWire::Card(OtherArmor))bArmorOtherEnded=true;
    if((bArmorOwnEnded&&bArmorOtherEnded)||Now-Started>35.)
    {
        bDone=true;const bool Paid=F&&F->ArmorConfirmedCastId==ArmorCastId&&F->ArmorPendingRefund==0;
        ArmorWire::Save(FString::Printf(TEXT("{\"role\":\"client\",\"confirmed\":%s,\"own_card\":%s,\"late_remote_card\":%s,\"own_expired\":%s,\"remote_expired\":%s}"),
            Paid?TEXT("true"):TEXT("false"),bArmorOwn?TEXT("true"):TEXT("false"),bArmorOther?TEXT("true"):TEXT("false"),bArmorOwnEnded?TEXT("true"):TEXT("false"),bArmorOtherEnded?TEXT("true"):TEXT("false")));
        ServerResult(Paid,bArmorOwn,bArmorOther,bArmorOwnEnded,bArmorOtherEnded);ExitAt=Now+2.;
    }
}
void ASkillWireAuditGameMode::TickFlameArmor()
{
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Guest)return;auto* P=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();if(!P||!PS)return;
    auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Host||!Host->IsAudit())return;
    if(!GuestModel)
    {
        GuestModel=Host->CreateShadowModel(ArmorWire::Seed(Host));GuestModel->FlameArmorSkill.FireMagic.DurationBase=6;GuestModel->FlameArmorSkill.FireMagic.DurationGrowth=0;
        GuestModel->Current.Mana=GuestModel->Derived(TEXT("maxMp"));
        PS->ShadowModel=GuestModel;GuestModel->CurrentPawn=P;P->NetShadowProfile=GuestModel;PS->SetActorTickEnabled(false);
        P->SetActorTickEnabled(false);P->GetCharacterMovement()->SetComponentTickEnabled(false);P->SetActorLocation(FVector(0,0,100));P->ForceNetUpdate();
        ArmorInitialMana=GuestModel->Snapshot().Mana;ArmorManaCost=GuestModel->FireMagicStats(TEXT("flameArmor")).ManaCost;ArmorHostXP=Host->FireMagicProgress(TEXT("flameArmor")).Experience;
        Target=GetWorld()->SpawnActor<ANurseZombie>(FVector(3000,0,100),FRotator::ZeroRotator);Target->Health=Target->MaxHealth=100000;
        if(auto* AI=Cast<AMonsterAIController>(Target->GetController()))AI->SetDecisionEnabled(false);Target->SetActorTickEnabled(false);
        ExistingArmor=GetWorld()->SpawnActor<AFPSGAMECharacter>(FVector(500,0,100),FRotator::ZeroRotator);ExistingArmor->SetActorTickEnabled(false);ExistingArmor->GetCharacterMovement()->SetComponentTickEnabled(false);
        // Hold relevancy until the buff is already two seconds old, then send
        // the actual replicated component as a late observer would receive it.
        ExistingArmor->SetReplicates(false);auto ExistingSpell=Host->FireMagicStats(TEXT("flameArmor"));ExistingSpell.Duration=11;
        FColdSteelNetCastRequest Req;Req.SkillId=TEXT("flameArmor");Req.CastId=700;
        ExistingArmor->FindComponentByClass<UFPSFireMagicComponent>()->NetRelease(ExistingArmor,Req,Host,ExistingSpell);MeteorAt=Now;
    }
    if(Stage==0&&Now-MeteorAt>2.){ExistingArmor->SetReplicates(true);ExistingArmor->ForceNetUpdate();Stage=1;}
    if(Stage==1&&Now-LastSetup>1.){LastSetup=Now;Guest->ClientSetupArmor(ExistingArmor);}
    auto* F=P->FindComponentByClass<UFPSFireMagicComponent>();
    if(Stage==1&&F->NetArmor.bActive)
    {
        const float Before=Target->Health;F->OnWeaponHit(Target,Target->GetActorLocation());Contacts=Target->Health<Before?1:0;Stage=2;
    }
    if(Guest->bReported||Now-Joined>50.)
    {
        const bool Cost=FMath::IsNearlyEqual(GuestModel->Snapshot().Mana,ArmorInitialMana-ArmorManaCost,.01f);
        const bool Training=GuestModel->FireMagicProgress(TEXT("flameArmor")).Experience==GuestModel->FireMagicDefinition(TEXT("flameArmor")).FireMagic.HitExperience
            &&Host->FireMagicProgress(TEXT("flameArmor")).Experience==ArmorHostXP;
        const bool OK=Cost&&Training&&Contacts==1&&!F->NetArmor.bActive&&Guest->bReported&&Guest->bPassed;
        ArmorWire::Save(FString::Printf(TEXT("{\"role\":\"listen_host\",\"passed\":%s,\"cost_once\":%s,\"guest_training_only\":%s,\"bonus_hit\":%d,\"guest_reported\":%s,\"guest_passed\":%s}"),
            OK?TEXT("true"):TEXT("false"),Cost?TEXT("true"):TEXT("false"),Training?TEXT("true"):TEXT("false"),Contacts,Guest->bReported?TEXT("true"):TEXT("false"),Guest->bPassed?TEXT("true"):TEXT("false")));ExitAt=Now+2.;
    }
}
