#include "SkillWireAudit.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/StarMarrowComponent.h"
#include "../Weapons/StarMarrowSpell.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace
{
FColdSteelProfile StarSeed(UColdSteelStatusModel* Model,const FString& Id)
{
    auto Profile=Model->Snapshot();
    auto Item=Model->CreateItem(TEXT("ue_frost_crystal_sword"));
    Item.Place=1;Item.Cell=6;Item.InstanceId=Id;
    TSharedPtr<FJsonObject> Data;
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
    if(!Data)Data=MakeShared<FJsonObject>();
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),TEXT("star_marrow"));
    Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
    Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    Profile.Items={Item};Profile.ActiveWeaponSlot=6;Profile.ActiveProductionTool.Reset();Profile.DungeonRun={};
    Profile.StarMarrowManaSpent=0.;
    return Profile;
}
void StarSave(const TCHAR* Role,bool Passed,int32 Step)
{
    const FString Json=FString::Printf(TEXT("{\"role\":\"%s\",\"passed\":%s,\"stage\":%d}"),Role,Passed?TEXT("true"):TEXT("false"),Step);
    FString Path;if(FParse::Value(FCommandLine::Get(),TEXT("SkillWireOutput="),Path))FFileHelper::SaveStringToFile(Json,*Path);
    UE_LOG(LogTemp,Display,TEXT("STAR_WIRE_RESULT %s"),*Json);
}
void Stationary(AFPSGAMECharacter* Pawn)
{
    Pawn->SetActorTickEnabled(false);
    Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);
}
}

void ASkillWireAuditController::ClientStarStep_Implementation(int32 Step,AFPSGAMECharacter* ObserverPawn)
{
    if(!FParse::Param(FCommandLine::Get(),TEXT("StarMarrowWireAudit"))||HasAuthority()||Step<=StarStep||!ObserverPawn)return;
    auto* Controlled=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Controlled||!Model||!Model->IsAudit()||!GetPlayerState<AColdSteelPlayerState>())return;
    if(!StarStep)
    {
        Stationary(Controlled);Model->Current=StarSeed(Model,TEXT("wire-A"));Model->CurrentPawn=Controlled;
        Model->Current.Mana=Model->Derived(TEXT("maxMp"));StarInitialMana=Model->Mana();
        StarManaCost=StarInitialMana*UStarMarrowComponent::ManaFraction;
        Controlled->ApplyColdSteelProfile(Model);StarObservedPawn=ObserverPawn;
    }
    StarStep=Step;bStarSent=false;Started=GetWorld()->GetRealTimeSeconds();
    UE_LOG(LogTemp,Display,TEXT("STAR_WIRE_CLIENT enter=%d"),Step);
}

void ASkillWireAuditController::ServerStarStep_Implementation(int32 Step,bool Passed)
{
    if(!FParse::Param(FCommandLine::Get(),TEXT("StarMarrowWireAudit"))||Step!=StarReportedStep+1)return;
    StarReportedStep=Step;bStarPassed&=Passed;
}

void ASkillWireAuditController::TickStarMarrow()
{
    if(HasAuthority()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0.){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!StarStep||!StarObservedPawn)return;
    const auto* Other=StarObservedPawn->FindComponentByClass<UStarMarrowComponent>();
    if(Other&&Other->Remaining()>0.f&&Other->Remaining()<28.5f)bLateSeen=true;
    const auto* Status=StarObservedPawn->FindComponentByClass<UCombatStatusFormula>();
    if(Status&&Status->WeaknessCount()==5&&Status->CriticalVulnerabilityCount()==5)
    {
        if(!bSawStatusCap)StarStatusFirstSeen=Now;
        bSawStatusCap=true;
        bSawRefresh|=Now-StarStatusFirstSeen>8.15;
    }
    if(StarReportedStep>=StarStep)return;
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());if(!P)return;
    auto* Core=P->FindComponentByClass<UStarMarrowComponent>();auto* Sword=P->FindComponentByClass<URuneSwordComponent>();
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Core||!Sword||!M)return;
    bool Done=false,OK=false;
    if(StarStep<=3)
    {
        if(!bStarSent&&Now-Started>.4&&Core->CanActivate())
        {
            Core->Trigger();
            bStarSent=Core->IsActivationPending();
            bStartedMotion=Sword->IsStarMarrowChargeMotionPlaying();
            bStarPassed&=FMath::IsNearlyEqual(M->Mana(),StarInitialMana,.01f);
            Core->Trigger(); // same input frame must not open another reservation.
            if(bStarSent&&StarStep==3)
            {
                auto* PS=GetPlayerState<AColdSteelPlayerState>();
                FColdSteelNetCastRequest Replay;
                Replay.SourcePawn=P;Replay.Sequence=PS->LocalCastSequence;
                Replay.SkillId=TEXT("starMarrowCharge");Replay.WeaponInstance=TEXT("wire-A");
                PS->ServerCastSpell(Replay); // exact retransmission must not charge or cancel the accepted cast.
            }
        }
        if(bStarSent&&!Core->IsActivationPending())
        {
            if(StarStep<=2)
            {
                Done=true;OK=bStartedMotion&&!Sword->IsStarMarrowChargeMotionPlaying()&&Core->Remaining()==0.f
                    &&FMath::IsNearlyEqual(M->Mana(),StarInitialMana,.01f)&&M->Snapshot().StarMarrowManaSpent==0.;
            }
            else if(Core->Remaining()>0.f&&FMath::IsNearlyEqual(M->Mana(),StarInitialMana-StarManaCost,.01f))
            {Done=true;OK=bStartedMotion&&Core->HUDVisible()&&bLateSeen;}
        }
    }
    else if(StarStep==4&&Core->Remaining()==0.f&&!Sword->IsStarMarrowChargeMotionPlaying())
    {Done=true;OK=FMath::IsNearlyEqual(M->Mana(),StarInitialMana-StarManaCost,.01f);}
    else if(StarStep==5&&Other&&Other->Remaining()<=0.f&&!Other->IsComponentTickEnabled()&&Status&&Status->WeaknessCount()==0&&Status->CriticalVulnerabilityCount()==0&&GetPlayerState<AColdSteelPlayerState>()->ReceivingMirrorCastSequence==3)
    {Done=true;OK=bLateSeen&&bSawRefresh&&GetPlayerState<AColdSteelPlayerState>()->ReceivingMirrorCastSequence==3&&Status&&Status->WeaknessCount()==0&&Status->CriticalVulnerabilityCount()==0&&!Other->IsComponentTickEnabled()&&Core->Remaining()==0.f&&FMath::IsNearlyEqual(M->Mana(),StarInitialMana-StarManaCost,.01f);}
    if(StarStep==1&&!bStarSent)
    {
        static double LastGateLog=-1.;
        if(Now-LastGateLog>=2.)
        {
            LastGateLog=Now;
            UE_LOG(LogTemp,Display,TEXT("STAR_WIRE_READY wait=%.2f ready=%d sword_equipped=%d core_equipped=%d busy=%d traversing=%d casting=%d local=%d"),
                Now-Started,Sword->IsStarMarrowChargeMotionReady(),Sword->IsEquipped(),Core->IsEquipped(),Sword->IsBusy(),P->IsTraversing(),P->IsLeftHandHeldForCast(),P->IsLocallyControlled());
        }
    }
    // A cold client may still be importing its carried weapon's animation bundles.
    if(!Done&&Now-Started<(StarStep==1?45.:(StarStep==5?36.:14.)))return;
    bStarPassed&=Done&&OK;StarReportedStep=StarStep;
    UE_LOG(LogTemp,Display,TEXT("STAR_WIRE_CLIENT done=%d pass=%d sent=%d motion=%d late=%d mana=%.2f active=%.2f"),StarStep,Done&&OK,bStarSent,bStartedMotion,bLateSeen,M->Mana(),Core->Remaining());
    ServerStarStep(StarStep,Done&&OK);
    if(StarStep==5){UE_LOG(LogTemp,Display,TEXT("STAR_WIRE_REPLICA cap=%d refresh=%d late=%d mirror_sequence=%u"),bSawStatusCap,bSawRefresh,bLateSeen,GetPlayerState<AColdSteelPlayerState>()->ReceivingMirrorCastSequence);StarSave(TEXT("client"),bStarPassed,StarStep);ExitAt=Now+3.;}
}

void ASkillWireAuditGameMode::TickStarMarrow(float Delta)
{
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0.){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Guest)return;
    auto* P=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();
    auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!P||!PS||!Host||!Host->IsAudit())return;
    auto* Core=P->FindComponentByClass<UStarMarrowComponent>();
    if(!GuestModel)
    {
        Stationary(P);GuestModel=Host->CreateShadowModel(StarSeed(Host,TEXT("wire-B")));
        PS->ShadowModel=GuestModel;P->NetShadowProfile=GuestModel;GuestModel->CurrentPawn=P;
        GuestModel->Current.Mana=GuestModel->Derived(TEXT("maxMp"));StarInitialMana=GuestModel->Mana();
        StarManaCost=StarInitialMana*UStarMarrowComponent::ManaFraction;StarHostSpend=Host->Snapshot().StarMarrowManaSpent;
        const FString OriginalData=GuestModel->Current.Items[0].Data;
        TSharedPtr<FJsonObject> CrystalData;
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(OriginalData),CrystalData);
        auto MaterialParts=MakeShared<FJsonObject>();
        MaterialParts->SetStringField(TEXT("blade_material"),TEXT("high_energy_magic_crystal"));
        CrystalData->SetObjectField(TEXT("gunsmith_parts"),MaterialParts);
        auto& Data=GuestModel->Current.Items[0].Data;Data.Reset();
        FJsonSerializer::Serialize(CrystalData.ToSharedRef(),TJsonWriterFactory<>::Create(&Data));
        FStarMarrowSpell CrystalReceipt;StarMarrow::CaptureSpell(P,CrystalReceipt);
        const bool MaterialIndependent=FMath::IsNearlyEqual(CrystalReceipt.ManaRatio,.1f)&&CrystalReceipt.HealthRatio==0.f;
        Host->Current=StarSeed(Host,TEXT("audit-host"));
        Host->Current.Items[0].Data=GuestModel->Current.Items[0].Data;
        StarHostSpend=Host->Current.StarMarrowManaSpent;
        GuestModel->Current.Items[0].Data=OriginalData;
        P->ApplyColdSteelProfile(GuestModel);
        StarObservedPawn=GetWorld()->SpawnActor<AFPSGAMECharacter>(FVector(500,0,100),FRotator::ZeroRotator);
        StarObservedPawn->SetReplicates(false);Stationary(StarObservedPawn);
        StarObserverProfile=Host->CreateShadowModel(StarSeed(Host,TEXT("wire-observer")));
        StarObserverProfile->CurrentPawn=StarObservedPawn;StarObserverProfile->Current.Mana=StarInitialMana;StarObservedPawn->NetShadowProfile=StarObserverProfile;
        const bool ObserverCharged=StarObservedPawn->FindComponentByClass<UStarMarrowComponent>()->ActivateCharge(StarObserverProfile);
        StarObservedPawn->NetShadowProfile=nullptr;
        FStarMarrowSpell Detached;StarMarrow::CaptureSpell(StarObservedPawn,Detached);
        StarObservedPawn->NetShadowProfile=StarObserverProfile;
        bStarPassed=MaterialIndependent&&ObserverCharged&&Detached.ManaRatio==0.f&&Detached.HealthRatio==0.f;
        UE_LOG(LogTemp,Display,TEXT("STAR_WIRE_SETUP independent_material=%.2f observer_charged=%d detached_mana_ratio=%.2f"),CrystalReceipt.ManaRatio,ObserverCharged,Detached.ManaRatio);
        StarGrantedAt=Now;
    }
    if(Stage==0&&Now-StarGrantedAt>=2.)
    {StarObservedPawn->SetReplicates(true);StarObservedPawn->ForceNetUpdate();Stage=1;}
    if(Stage>=1&&Stage<=5&&Now-LastSetup>=1.)
    {LastSetup=Now;Guest->ClientStarStep(Stage,StarObservedPawn);}
    if(Stage==3&&Core->Remaining()>0.f)
    {
        if(auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>())
        {
            const auto State=Body->GetBodyState();
            bSawThirdPersonMotion|=State.WeaponInstance==TEXT("wire-A")&&State.ActionVariant==TEXT("StarMarrowCharge");
        }
        TInlineComponentArray<UNiagaraComponent*> Effects(P);
        for(const auto* FX:Effects)
            if(FX->IsVisible()&&FX->GetAsset()&&FX->GetAsset()->GetFName()==TEXT("NS_StarMarrowDenseBladeFire"))bSawThirdPersonFlame=true;
    }
    if(StarStatusAt>0.&&Now-StarStatusAt>5.)
    {
        auto* Status=UCombatStatusFormula::GetOrAdd(StarObservedPawn);
        Status->AddWeakness();Status->AddCriticalVulnerability();StarStatusAt=-1.;
    }
    if(Stage>=3)PS->TickShadowMirror(Delta); // production paced profile chunks, including the dirty-owner merge.
    // Give the 1 Hz world-equipment rebuild and asynchronous asset load time to produce a rendered attachment.
    if(Stage==3&&Guest->StarReportedStep==3&&Core->Remaining()>24.f)return;
    if(Stage>0&&Guest->StarReportedStep==Stage)
    {
        const bool SameMana=FMath::IsNearlyEqual(GuestModel->Mana(),StarInitialMana,.01f);
        if(Stage==1)
        {
            bStarPassed&=SameMana&&Core->Remaining()==0.f&&PS->ProcessedCastSequence==1;
            GuestModel->Current.Items[0].InstanceId=TEXT("wire-A");GuestModel->Current.Mana=0.f;Core->Configure(GuestModel);
        }
        else if(Stage==2)
        {
            bStarPassed&=GuestModel->Mana()==0.f&&Core->Remaining()==0.f&&PS->ProcessedCastSequence==2;
            GuestModel->Current.Mana=StarInitialMana;
        }
        else if(Stage==3)
        {
            FFlameArmorAttachments Spans;FlameArmorAttachments::Gather(P,Spans);
            FString Meshes;for(const auto& Span:Spans)Meshes+=Span.Section.ToString()+TEXT("=")+GetNameSafe(Span.Geometry.Get())+TEXT(" ");
            auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();
            UE_LOG(LogTemp,Display,TEXT("STAR_WIRE_ATTACHMENT shown=%s spans=%s motion=%d flame=%d"),Body?*Body->DisplayedWeaponInstance():TEXT("(none)"),*Meshes,bSawThirdPersonMotion,bSawThirdPersonFlame);
            if(GetNetMode()==NM_ListenServer)bStarPassed&=bSawThirdPersonMotion&&bSawThirdPersonFlame;
            StarStatusAt=Now;
            auto* Status=UCombatStatusFormula::GetOrAdd(StarObservedPawn);
            for(int32 Stack=0;Stack<6;++Stack){Status->AddWeakness();Status->AddCriticalVulnerability();}
            bStarPassed&=Status->WeaknessCount()==5&&Status->CriticalVulnerabilityCount()==5
                &&FMath::IsNearlyEqual(Status->WeaknessDamageMultiplier(),.5f)&&Status->CriticalVulnerabilityBonusPercent()==25.f;
            CombatFormulaRuntime::WeaponHit Hit;Hit.Target=StarObservedPawn;Hit.Incoming={80.,20.,10.,10.};
            {TGuardValue<CombatFormulaRuntime::WeaponHit*> Scope(CombatFormulaRuntime::ActiveWeaponHit,&Hit);
             CombatFormulaRuntime::MitigateMonster(StarObservedPawn,120.f,nullptr,P);}
            const bool Converted=Hit.bResolved&&Hit.Incoming.BasePhysical==0.&&Hit.Incoming.AddedPhysical==0.
                &&FMath::IsNearlyEqual(Hit.Incoming.BaseMagic,130.)&&FMath::IsNearlyEqual(Hit.Incoming.AddedMagic,26.);
            const auto Paid=GuestModel->Snapshot().StarMarrowManaSpent;
            bStarPassed&=Converted&&Core->Remaining()>0.f&&PS->ProcessedCastSequence==3
                &&FMath::IsNearlyEqual(Paid,double(StarManaCost),.01)&&FMath::IsNearlyEqual(GuestModel->Mana(),StarInitialMana-StarManaCost,.01f);
            UE_LOG(LogTemp,Display,TEXT("STAR_WIRE_DAMAGE base_magic=%.1f added_magic=%.1f guest_paid=%.1f"),Hit.Incoming.BaseMagic,Hit.Incoming.AddedMagic,Paid);
            GuestModel->Current.Items[0].InstanceId=TEXT("wire-B");Core->Configure(GuestModel);
        }
        else if(Stage==4)bStarPassed&=!UStarMarrowComponent::ChargesDamage(P);
        UE_LOG(LogTemp,Display,TEXT("STAR_WIRE_SERVER done=%d pass=%d request=%u"),Stage,bStarPassed,PS->ProcessedCastSequence);
        ++Stage;LastSetup=-10.;
    }
    if(Stage>5||Now-Joined>155.)
    {
        bStarPassed&=Stage>5&&Guest->bStarPassed&&FMath::IsNearlyEqual(Host->Snapshot().StarMarrowManaSpent,double(StarHostSpend));
        UE_LOG(LogTemp,Display,TEXT("STAR_WIRE_THIRD_PERSON motion=%d visible_flame_component=%d"),bSawThirdPersonMotion,bSawThirdPersonFlame);
        const bool Dedicated=GetNetMode()==NM_DedicatedServer;
        const bool ExpectedDedicated=FParse::Param(FCommandLine::Get(),TEXT("StarDedicatedAudit"));
        bStarPassed&=Dedicated==ExpectedDedicated&&(Dedicated?!bSawThirdPersonFlame:GetNetMode()==NM_ListenServer);
        StarSave(Dedicated?TEXT("dedicated_server"):TEXT("listen_host"),bStarPassed,Guest->StarReportedStep);ExitAt=Now+3.;
    }
}
