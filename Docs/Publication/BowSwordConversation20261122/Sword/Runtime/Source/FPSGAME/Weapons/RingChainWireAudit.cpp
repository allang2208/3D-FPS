// The fixture uses the existing sword wire game mode for a real PlayerState channel and
// isolated profiles. Inputs, contact reports, the ready cue and heavy release use production RPCs.
#include "RuneSwordComponent.h"
#include "RingChainSweepMotion.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Development/KukriCombatWireAudit.h"
#include "../Monsters/NurseZombie.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelProfileTransfer.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/CapsuleComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

struct FRingChainWireProbe
{
    UColdSteelStatusModel* Model=nullptr;
    TWeakObjectPtr<AFPSGAMECharacter> Subject;
    TArray<TWeakObjectPtr<ANurseZombie>> Targets;
    TArray<float> HealthBeforeHeavy;
    TWeakObjectPtr<ANurseZombie> Behind;
    int32 Stage=0,Taps=0;
    bool SawReady=false,SawBoost=false,Complete=false;
    int32 MaxHits=0;
    double TraceAt=0.;
    double AttachedAt=0.,Edge=0.,ChargeAt=0.,Cost=0.,Before=0.,SeenRelease=-1.,Expected=0.,ExpectedLight=0.;
    bool ReplayRejected=false,RearRejected=false;
    bool SawRelease=false,SawOwnerRibbon=false,SawObserverRibbon=false;
    double ChargeDuration=0.,FullHoldRate=0.,Overhold=0.,HoldAfterFull=0.;
    FGuid UploadProfileId;
    TArray<uint8> PreAttackBlob;
    bool SentOldProfile=false,ReceivedOldProfile=false,KeptAuthorityStamina=false;
    float LastChargeStamina=-1.f,StaminaBeforeMerge=-1.f,StaminaAfterMerge=-1.f;
    FColdSteelProfile Seed(UColdSteelStatusModel* Profile)
    {
        auto S=Profile->Snapshot();S.Items.Reset();S.ActiveWeaponSlot=6;S.ActiveProductionTool.Reset();
        S.Stamina=100.f;S.bSprintExhausted=false;S.LearnedSkills.AddUnique(TEXT("heavyStrike"));S.Skills.FindOrAdd(TEXT("heavyStrike")).Level=1;
        if(UploadProfileId.IsValid()){S.NetworkProfileId=UploadProfileId;S.Name=TEXT("RingWireBeforeUpload");}
        auto I=Profile->CreateItem(TEXT("ue_forged_steel_greatsword"));I.Place=1;I.Cell=6;I.InstanceId=TEXT("RingWireSword");
        TSharedPtr<FJsonObject> Data;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data)||!Data)return S;
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("pommel"),TEXT("ring_chain_pommel"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);I.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));
        S.Items.Add(I);return S;
    }
    void Attach(UWorld* W,AFPSGAMECharacter* P,APlayerController* PC)
    {
        Subject=P;auto* Base=W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if(!Base||!Base->IsAudit())return;
        FString ProfileId;FParse::Value(FCommandLine::Get(),TEXT("RingChainProfileId="),ProfileId);
        FParse::Value(FCommandLine::Get(),TEXT("RingChainHoldAfterFull="),HoldAfterFull);
        FGuid::Parse(ProfileId,UploadProfileId);
        const bool Host=W->GetNetMode()==NM_ListenServer;auto S=Seed(Base);
        if(S.Items.IsEmpty())return;
        Model=Host?Base->CreateShadowModel(S):Base;
        if(Host)
        {
            P->NetShadowProfile=Model;PC->GetPlayerState<AColdSteelPlayerState>()->ShadowModel=Model;
        }
        else
        {
            Model->AdoptNetMirror(S);
            if(UploadProfileId.IsValid())
            {
                auto* Save=NewObject<UColdSteelProfileSave>();
                Save->Profile=S;Save->Profile.Name=TEXT("RingUploadDuringCharge");
                ColdSteelProfileTransfer::SaveToBlob(Save,PreAttackBlob);
            }
        }
        Model->AttachPawn(P);P->ApplyColdSteelProfile(Model);
        P->SetActorLocation(FVector(0,0,300));PC->SetControlRotation(FRotator::ZeroRotator);
        P->SetActorTickEnabled(false);P->GetCharacterMovement()->StopMovementImmediately();P->GetCharacterMovement()->SetComponentTickEnabled(false);
        P->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);P->ForceNetUpdate();
        AttachedAt=W->GetTimeSeconds();
        if(Host)
        {
            for(int32 I=0;I<8;++I)
            {
                const FVector Offset=FVector(135,0,0).RotateAngleAxis(-66.f+I*19.f,FVector::UpVector);
                if(auto* N=KukriCombatWire::SpawnTarget(W,P->GetActorLocation()+Offset))Targets.Add(N);
            }
            Behind=KukriCombatWire::SpawnTarget(W,P->GetActorLocation()-FVector(160,0,0));
        }
#if DO_ENABLE_NET_TEST
        if(auto* D=W->GetNetDriver())
        {
            FPacketSimulationSettings Settings;Settings.PktLag=40;Settings.PktLoss=2;
            FParse::Value(FCommandLine::Get(),TEXT("RingChainLagMs="),Settings.PktLag);
            FParse::Value(FCommandLine::Get(),TEXT("RingChainLossPercent="),Settings.PktLoss);
            D->SetPacketSimulationSettings(Settings);
        }
#endif
        UE_LOG(LogTemp,Display,TEXT("RING_WIRE_ATTACHED host=%d targets=%d pawn=%s"),Host,Targets.Num(),*P->GetName());
    }
    void Finish(UWorld* W,bool Good,const FString& Detail)
    {
        Complete=true;auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),Good);
        R->SetStringField(TEXT("detail"),Detail);R->SetBoolField(TEXT("udp"),W->GetNetDriver()!=nullptr);
        R->SetNumberField(TEXT("taps"),Taps);R->SetBoolField(TEXT("rebound_ready"),SawReady);R->SetBoolField(TEXT("boosted_charge"),SawBoost);
        R->SetNumberField(TEXT("heavy_cost"),Cost);R->SetNumberField(TEXT("expected_cost"),Expected);
        R->SetNumberField(TEXT("seconds_held_past_full"),Overhold);
        R->SetNumberField(TEXT("two_light_cost"),100.-Before);R->SetNumberField(TEXT("expected_two_light_cost"),ExpectedLight);
        R->SetNumberField(TEXT("server_sweep_targets"),MaxHits);R->SetBoolField(TEXT("same_target_rejected"),ReplayRejected);
        R->SetBoolField(TEXT("rear_target_rejected"),RearRejected);
        R->SetBoolField(TEXT("release_presented"),SawRelease);
        R->SetBoolField(W->GetNetMode()==NM_Client?TEXT("owner_ribbon"):TEXT("observer_ribbon"),
            W->GetNetMode()==NM_Client?SawOwnerRibbon:SawObserverRibbon);
        if(UploadProfileId.IsValid())
        {
            R->SetNumberField(TEXT("pre_attack_snapshot_stamina"),100.);
            if(W->GetNetMode()==NM_Client)
            {
                R->SetBoolField(TEXT("sent_old_profile_while_charging"),SentOldProfile);
                R->SetNumberField(TEXT("compressed_upload_bytes"),PreAttackBlob.Num());
                Good&=SentOldProfile;
            }
            else
            {
                R->SetBoolField(TEXT("received_name_marker_while_charging"),ReceivedOldProfile);
                R->SetNumberField(TEXT("stamina_before_merge"),StaminaBeforeMerge);
                R->SetNumberField(TEXT("stamina_after_merge"),StaminaAfterMerge);
                R->SetBoolField(TEXT("kept_authority_stamina"),KeptAuthorityStamina);
                Good&=ReceivedOldProfile&&KeptAuthorityStamina;
            }
            R->SetBoolField(TEXT("passed"),Good);
        }
#if DO_ENABLE_NET_TEST
        if(const auto* Driver=W->GetNetDriver())
        {
            R->SetNumberField(TEXT("lag_ms"),Driver->PacketSimulationSettings.PktLag);
            R->SetNumberField(TEXT("loss_percent"),Driver->PacketSimulationSettings.PktLoss);
        }
#endif
        FString File,Json;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json));
        if(FParse::Value(FCommandLine::Get(),TEXT("RingChainWireOutput="),File))FFileHelper::SaveStringToFile(Json,*File);
        UE_LOG(LogTemp,Display,TEXT("RING_WIRE_FINISHED %s"),*Json);
    }
    void Step(UWorld* W,float Delta)
    {
        if(Complete||!W||W->WorldType!=EWorldType::Game)return;
        const bool Host=W->GetNetMode()==NM_ListenServer;if(!Host&&W->GetNetMode()!=NM_Client)return;
        if(!Model)
        {
            for(auto It=W->GetPlayerControllerIterator();It;++It)
            {
                auto* PC=It->Get();if(!PC||PC->IsLocalController()==Host||!PC->GetPlayerState<AColdSteelPlayerState>())continue;
                auto* P=Cast<AFPSGAMECharacter>(PC->GetPawn());if(P&&P->HasActorBegunPlay())Attach(W,P,PC);
                break;
            }
            return;
        }
        auto* P=Subject.Get();if(!P)return;
        auto* Sword=P->FindComponentByClass<URuneSwordComponent>();auto* Item=Model->Equipped();
        if(!Sword||!Item)return;
        const double Now=W->GetTimeSeconds();
        if(Host)
        {
            if(const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>())
                SawRelease|=Body->GetBodyState().ActionVariant==RingChainSweepMotion::Release;
            if(SawRelease&&!SawObserverRibbon)
            {
                TInlineComponentArray<UDynamicMeshComponent*> Trails(P);
                for(const auto* Trail:Trails)
                    if(Trail->IsVisible()&&Trail->GetMaterial(0)&&Trail->GetMaterial(0)->GetName()==TEXT("M_RuneRift"))
                        SawObserverRibbon=true;
            }
        }
        else if(Stage==3)
        {
            const auto* Ribbon=Sword->RiftVisual.Get();
            SawOwnerRibbon|=Sword->bRiftActive&&Ribbon&&Ribbon->IsVisible()&&Ribbon->GetStaticMesh()
                &&Ribbon->GetStaticMesh()->GetName().StartsWith(TEXT("SM_Highland_SweepRift_"));
            if(SawOwnerRibbon||Now-SeenRelease>1.)
                Finish(W,Taps==2&&SawReady&&SawBoost&&SawRelease&&SawOwnerRibbon&&FMath::Abs(Cost-Expected)<.55&&FMath::Abs(100.-Before-ExpectedLight)<.55,
                    FString::Printf(TEXT("guest release after %.3fs charge"),SeenRelease-ChargeAt));
            return;
        }
        if(Now>TraceAt)
        {
            TraceAt=Now+4.;
            UE_LOG(LogTemp,Display,TEXT("RING_WIRE_PROGRESS host=%d stage=%d taps=%d clip=%s equipped=%d busy=%d stamina=%.2f grant=%u acknowledged=%u last_swing=%u hits=%d"),
                Host,Stage,Taps,*Sword->CurrentClip.ToString(),Sword->IsEquipped(),Sword->IsBusy(),Model->Stamina(),
                Sword->RingChainGrant,Sword->RingChainAcknowledged,Sword->RingChainProgress.LastSwing,Sword->RingSweepTargets.Num());
        }
        if(Now-AttachedAt>50.){Finish(W,false,FString::Printf(TEXT("timeout stage=%d clip=%s busy=%d"),
            Stage,*Sword->CurrentClip.ToString(),Sword->IsBusy()));return;}
        SawReady|=RingChainRebound::IsReady(P,*Item);
        if(Sword->IsHeavyCharging())
        {
            if(!SawBoost&&Sword->bReboundHeavyCharge)
            {
                ChargeAt=Now;Before=Model->Stamina();
                ExpectedLight=2.*ColdSteelMelee::AttackStamina(Item,Model);
                for(const auto& Target:Targets)HealthBeforeHeavy.Add(Target.IsValid()?Target->Health:0.f);
                const auto Stats=ColdSteelMelee::Evaluate(*Item,Model);
                ChargeDuration=Stats.HeavyChargeSeconds*.5;
                FullHoldRate=1.15*Model->HeavyChargeStaminaPerSecond()*Stats.Modifiers.Stamina;
                Expected=1.15*(ColdSteelMelee::HeavyReleaseStamina(Item,Model)+
                    Stats.HeavyChargeSeconds*Model->HeavyChargeStaminaPerSecond()*Stats.Modifiers.Stamina);
            }
            SawBoost|=Sword->bReboundHeavyCharge;
            if(UploadProfileId.IsValid()&&Sword->bReboundHeavyCharge)
            {
                if(Host&&!ReceivedOldProfile&&Model->Snapshot().Name==TEXT("RingUploadDuringCharge"))
                {
                    ReceivedOldProfile=true;StaminaBeforeMerge=LastChargeStamina;StaminaAfterMerge=Model->Stamina();
                    KeptAuthorityStamina=StaminaBeforeMerge>=0.f&&StaminaBeforeMerge<Before
                        &&FMath::IsNearlyEqual(StaminaAfterMerge,StaminaBeforeMerge,.02f);
                }
                if(!Host&&!SentOldProfile&&!PreAttackBlob.IsEmpty()&&Now-ChargeAt>.18)
                {
                    auto* PS=P->GetPlayerState<AColdSteelPlayerState>();
                    const int32 Size=ColdSteelProfileTransfer::ChunkSize;
                    const int32 Count=FMath::DivideAndRoundUp(PreAttackBlob.Num(),Size);
                    for(int32 Index=0;Index<Count;++Index)
                    {
                        const int32 Offset=Index*Size;TArray<uint8> Chunk;
                        Chunk.Append(PreAttackBlob.GetData()+Offset,FMath::Min(Size,PreAttackBlob.Num()-Offset));
                        PS->ServerSubmitProfileChunk(1,Index,Count,Chunk,0,P,0,0,0);
                    }
                    SentOldProfile=true;
                }
            }
            Model->TickRuntime(Delta,P);
            LastChargeStamina=Model->Stamina();
        }
        if(Host)
        {
            if(!Sword->RingSweepReleaseSerial)return;
            if(SeenRelease<0.)
            {
                SeenRelease=Now;Cost=Before-Model->Stamina();
                // The server sees the two input edges after transport. The existing
                // tolerance covers jitter; keeping a fully charged sword held still costs stamina.
                Overhold=FMath::Max(0.,Now-Sword->ServerHeavyChargeReceivedAt-ChargeDuration);
                Expected+=Overhold*FullHoldRate;
            }
            int32 Damaged=0;
            for(int32 Idx=0;Idx<HealthBeforeHeavy.Num();++Idx)
                if(Targets[Idx].IsValid()&&Sword->RingSweepTargets.Contains(Targets[Idx].Get())&&Targets[Idx]->Health<HealthBeforeHeavy[Idx])++Damaged;
            MaxHits=FMath::Max(MaxHits,Damaged);
            if(Now-SeenRelease>.33&&Now-SeenRelease<.57)
            {
                for(const auto& Target:Targets)if(Target.IsValid()&&Sword->RingSweepTargets.Contains(Target.Get()))
                {ReplayRejected=!Sword->AcceptRingChainSweepContact(Item->InstanceId,Sword->RingSweepReleaseSerial,Target.Get(),false);break;}
                if(Behind.IsValid())RearRejected=!Sword->AcceptRingChainSweepContact(Item->InstanceId,Sword->RingSweepReleaseSerial,Behind.Get(),false);
            }
            if(Now-SeenRelease>1.5)
                Finish(W,SawReady&&SawBoost&&SawRelease&&SawObserverRibbon&&MaxHits==8&&ReplayRejected&&RearRejected&&FMath::Abs(Cost-Expected)<.55&&FMath::Abs(100.-Before-ExpectedLight)<.55,
                    TEXT("guest authority: two-hit grant, heavy payment and distinct targets of one sweep"));
            return;
        }
        if(Now-AttachedAt<12.||Sword->bEquipping||!Sword->Animations.FindRef(RingChainSweepMotion::Release))return;
        if(Stage==0&&!Sword->IsBusy()&&Now>=Edge)
        {
            if(RingChainRebound::IsReady(P,*Item)){Sword->BeginPrimaryAttack();Stage=2;Edge=Now;}
            else if(Taps<5){Sword->BeginPrimaryAttack();Stage=1;Edge=Now;}
        }
        else if(Stage==1&&Now-Edge>.07)
        {Sword->ReleasePrimaryAttack();++Taps;Stage=0;Edge=Now+.12;}
        else if(Stage==2&&Sword->IsHeavyCharging()&&Sword->HeavyChargeFraction()>=1.
            &&Now>=Sword->ChargeStartedAt+ChargeDuration+HoldAfterFull)
        {
            Overhold=FMath::Max(0.,Now-Sword->ChargeStartedAt-ChargeDuration);
            Expected+=Overhold*FullHoldRate;
            Sword->ReleasePrimaryAttack();Cost=Before-Model->Stamina();
            SawRelease=Sword->bHeavyAttack&&Sword->CurrentClip==RingChainSweepMotion::Release;
            SeenRelease=Now;Stage=3;
        }
    }
};

namespace
{
void RingChainWireTick(UWorld* W,ELevelTick,float Delta){static FRingChainWireProbe Probe;Probe.Step(W,Delta);}
struct FRingChainWireRegistration
{
    FRingChainWireRegistration(){FCoreDelegates::GetOnPostEngineInit().AddLambda([](){
        if(FParse::Param(FCommandLine::Get(),TEXT("RingChainWireAudit")))
            FWorldDelegates::OnWorldPostActorTick.AddStatic(&RingChainWireTick);});}
} Registration;
}
