#include "KukriNetworkAuditCommandlet.h"
#include "ColdSteelPlayerState.h"
#include "UppercutStaminaReceipt.h"
#include "../Production/WarhammerModificationAuditCommandlet.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/Kukri/KukriAttackTiming.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Characters/FPSBodyKukriMotion.h"
#include "../Characters/FPSPlayerBodyPoses.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSBodyKukriRifts.h"
#include "../Weapons/Kukri/KukriRhythm.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "Materials/MaterialInterface.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace FPSBodyNetwork { bool IsTransition(const FFPSBodyState& A,const FFPSBodyState& B); }

int32 UKukriNetworkAuditCommandlet::Main(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_Kukri_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("KukriNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("KukriReceiptAudit"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    // Use a nonzero fixture clock so past charge starts remain valid timestamps.
    World->TimeSeconds=10.;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool OK,const TCHAR* Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("KUKRI_NETWORK %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Stamina=100.f;Seed.bSprintExhausted=false;Seed.UppercutStaminaSpent=0.;
    for(auto& Entry:Seed.Skills)Entry.Value.Level=1;
    auto Main=Host->CreateItem(TEXT("ue_kukri"));Main.Place=1;Main.Cell=6;
    auto Off=Host->CreateItem(TEXT("ue_kukri"));Off.Place=1;Off.Cell=8;Seed.Items={Main};
    auto* Model=Host->CreateShadowModel(Seed);
    auto* PC=World->SpawnActor<AWarhammerAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    PC->SetPlayerState(PS);PS->SetOwner(PC);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    PS->ShadowModel=Model;Pawn->NetShadowProfile=Model;Model->AttachPawn(Pawn);
    auto* HP=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();HP->Health=HP->MaxHealth;
    auto* Move=CastChecked<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
    auto* Target=World->SpawnActor<AActor>();const float HostStamina=Host->Stamina();
    uint32 Serial=0;bool Dual=false;
    const auto Reset=[&](bool Both)
    {
        PS->ClearKukriAttack();Dual=Both;Seed.Items=Both?TArray<FColdSteelItem>{Main,Off}:TArray<FColdSteelItem>{Main};
        Model->AdoptNetMirror(Seed);PS->KukriReadyAt=PS->KukriChainUntil=0.;PS->KukriNextStage=0;
        PS->KukriChainKey.Reset();PS->KukriSprintPawn=Pawn;PS->KukriSprintKey=Main.InstanceId+TEXT("|")+(Both?Off.InstanceId:FString());
        PS->KukriDashReadyUntil=-1.;PS->KukriSprintSeconds=0.f;HP->Health=HP->MaxHealth;
    };
    const auto Begin=[&](uint8 Stage,bool Dash=false)
    {++Serial;PS->ServerBeginKukriAttack_Implementation(Serial,Pawn,Main.InstanceId,Dual?Off.InstanceId:FString(),Stage,Dash,FVector::ForwardVector,1000+Serial,World->GetTimeSeconds());};
    const auto Report=[&](bool Left=false)
    {
        FColdSteelNetHitReport R;R.KukriAttackSerial=PS->KukriAttack.Serial;R.MasteryAttackSerial=PS->KukriAttack.MasterySerial;
        R.ItemDefinition=Main.Definition;R.ItemInstance=Left?Off.InstanceId:Main.InstanceId;
        R.Target=Target;R.Flags=1<<3;R.AttackMeta=PS->KukriAttack.Dash?0x16:0;return R;
    };
    FString Reason;FVector Direction;float Limit=0.f,Recovery=0.f;
    Reset(false);Check(!PS->ValidateKukriHit(Report(),Pawn,Reason),TEXT("uncommitted contact rejected"));
    Check(!KukriAttackReceipt::SupportedMeta(0x15)&&!KukriAttackReceipt::SupportedMeta(3)&&
        KukriAttackReceipt::SupportedMeta(0x16),TEXT("unsupported attack flags cannot bypass kukri receipt routing"));
    const float SingleCost=ColdSteelMelee::ComboAttackStamina(Model->Equipped(),Model,false);
    Begin(0);Check(PS->KukriAttack.Serial==Serial&&FMath::IsNearlyEqual(Model->Stamina(),100.f-SingleCost),TEXT("single start pays once before contact"));
    const double Spent=Model->Snapshot().UppercutStaminaSpent;
    PS->ServerBeginKukriAttack_Implementation(Serial,Pawn,Main.InstanceId,FString(),0,false,FVector::ForwardVector,1000+Serial,World->GetTimeSeconds());
    Check(PS->KukriAttack.Serial==Serial&&Model->Snapshot().UppercutStaminaSpent==Spent,TEXT("duplicate start preserves attack and payment"));
    Check(Host->Stamina()==HostStamina,TEXT("guest payment leaves host profile untouched"));
    Check(!PS->ValidateKukriHit(Report(),Pawn,Reason),TEXT("early contact rejected"));
    PS->KukriAttack.Started=World->GetTimeSeconds()-PS->KukriAttack.ContactStart[0]-.01;
    Check(PS->ValidateKukriHit(Report(),Pawn,Reason),TEXT("committed contact accepted in window"));
    auto Forged=Report();++Forged.MasteryAttackSerial;
    Check(!PS->ValidateKukriHit(Forged,Pawn,Reason),TEXT("contact cannot change mastery attack identity"));
    PS->KukriAttack.Targets[0].Add(Target);
    Check(!PS->ValidateKukriHit(Report(),Pawn,Reason),TEXT("same blade target replay rejected"));
    PS->ServerFinishKukriAttack_Implementation(Serial,Pawn,true);
    Check(!PS->KukriAttack.Serial&&Model->Snapshot().UppercutStaminaSpent==Spent,TEXT("cancel closes attack without refund"));
    Check(!PS->GetKukriMovement(Serial,uint8(EFPSMeleeMove::Thrust),Direction,Limit,Recovery),TEXT("cancelled attack has no movement authorization"));
    Reset(false);auto EmptyStamina=Seed;EmptyStamina.Stamina=0.f;Model->AdoptNetMirror(EmptyStamina);Begin(0);
    Check(!PS->KukriAttack.Serial&&Model->Snapshot().UppercutStaminaSpent==0.,TEXT("insufficient stamina rejects before opening receipt"));
    Reset(true);const float DualCost=ColdSteelMelee::ComboAttackStamina(Model->Equipped(),Model,true);
    Begin(0);Check(PS->KukriAttack.Serial==Serial&&FMath::IsNearlyEqual(Model->Stamina(),100.f-DualCost),TEXT("dual start pays pair once"));
    PS->KukriAttack.Targets[0].Add(Target);
    PS->KukriAttack.Started=World->GetTimeSeconds()-PS->KukriAttack.ContactStart[1]-.01;
    Check(PS->ValidateKukriHit(Report(true),Pawn,Reason),TEXT("left blade can hit same target independently"));
    PS->KukriAttack.Targets[1].Add(Target);
    Check(!PS->ValidateKukriHit(Report(true),Pawn,Reason),TEXT("left blade target replay rejected"));
    const uint32 First=PS->KukriAttack.Serial;Begin(1);
    Check(PS->KukriAttack.Serial==First,TEXT("next click cannot bypass recovery"));
    PS->KukriReadyAt=0.;PS->ServerFinishKukriAttack_Implementation(First,Pawn,false);Begin(1);
    Check(PS->KukriAttack.Serial==Serial&&PS->KukriAttack.Stage==1,TEXT("accepted stage two follows stage one"));
    PS->KukriReadyAt=0.;PS->ServerFinishKukriAttack_Implementation(Serial,Pawn,false);Begin(2);
    Check(PS->KukriAttack.Serial==Serial&&PS->KukriAttack.Stage==2,TEXT("accepted dual thrust follows stage two"));
    Check(PS->GetKukriMovement(Serial,uint8(EFPSMeleeMove::Thrust),Direction,Limit,Recovery)&&Limit<KukriRhythm::DualThrustLungeCM,
        TEXT("thrust movement budget follows elapsed phase"));
    Check(!PS->GetKukriMovement(Serial-1,uint8(EFPSMeleeMove::Thrust),Direction,Limit,Recovery),TEXT("old movement cannot borrow new attack"));
    auto Changed=Model->Snapshot();Changed.Items.RemoveAll([&](const FColdSteelItem& I){return I.InstanceId==Off.InstanceId;});Model->AdoptNetMirror(Changed);
    Check(!PS->GetKukriMovement(Serial,uint8(EFPSMeleeMove::Thrust),Direction,Limit,Recovery),TEXT("offhand removal revokes paired movement"));
    PS->TickKukriAuthority(0.f);Check(!PS->KukriAttack.Serial,TEXT("offhand removal closes attack receipt"));
    Reset(false);Begin(0,true);Check(!PS->KukriAttack.Serial,TEXT("dash without earned sprint preparation rejected"));
    PS->KukriDashReadyUntil=World->GetTimeSeconds()+1.;Begin(0,true);
    Check(PS->KukriAttack.Serial==Serial&&PS->KukriAttack.Dash,TEXT("prepared dash commits"));
    Check(PS->GetKukriMovement(Serial,uint8(EFPSMeleeMove::AirMomentum),Direction,Limit,Recovery)&&Limit==0.f,
        TEXT("dash authorizes momentum without extra fixed displacement"));
    Check(!PS->GetKukriMovement(Serial,uint8(EFPSMeleeMove::Thrust),Direction,Limit,Recovery),TEXT("dash receipt cannot authorize thrust"));
    FFPSMeleeMoveRequest Request;Request.Sequence=1;Request.Kind=EFPSMeleeMove::AirMomentum;Request.KukriAttackId=Serial;Request.Direction=FVector::ForwardVector;
    float Budget=0.f;Check(Move->AuthorizeMeleeMove(Request,Budget,Recovery),TEXT("CMC accepts matching dash receipt"));
    Request.KukriAttackId=0;Check(!Move->AuthorizeMeleeMove(Request,Budget,Recovery),TEXT("CMC refuses unbound kukri momentum"));
    Check(PS->IsKukriMovementPending(Serial+1)&&!PS->IsKukriMovementPending(Serial),TEXT("only unseen movement may wait for reliable start"));
    PS->ConfirmKukriHit(Report(),Pawn,10.f,true,true);
    Check(PS->KukriAttack.Hits==1&&PS->KukriAttack.Kills==1,TEXT("dash kill retains pre-damage training eligibility"));
    HP->Health=0.f;PS->TickKukriAuthority(0.f);
    Check(!PS->KukriAttack.Serial,TEXT("death closes attack and movement"));
    auto Ledger=Seed;Ledger.Stamina=100.f;Ledger.UppercutStaminaSpent=0.;
    UppercutStaminaReceipt::Merge(Ledger,12.);UppercutStaminaReceipt::Merge(Ledger,12.);UppercutStaminaReceipt::Merge(Ledger,7.);
    Check(Ledger.Stamina==88.f&&Ledger.UppercutStaminaSpent==12.,TEXT("duplicate and older resource receipts do not double debit"));
    FFPSBodyState Body;Body.Family=TEXT("Kukri");Body.Action=EFPSBodyAction::Strike;Body.ActionVariant=TEXT("DualAttack2");
    Check(FPSBodyKukriMotion::Clip(Body)==TEXT("Kukri.FullBody.Slash2"),TEXT("dual second strike selects second fallback"));
    Body.OffhandInstance=Off.InstanceId;
    Check(!FPSBodyKukriMotion::MatchesOffhand(Body,true,Main.InstanceId)&&FPSBodyKukriMotion::MatchesOffhand(Body,true,Off.InstanceId),
        TEXT("body carry requires matching loaded offhand instance"));
    Check(FPSBodyKukriMotion::DualClip(TEXT("Kukri.FullBody.Equip"))==TEXT("Kukri.FullBody.Dual.Equip"),
        TEXT("dual equip selects its two-hand draw"));
    Check(FPSBodyKukriMotion::DualClip(TEXT("Kukri.FullBody.Pommel"))==TEXT("Kukri.FullBody.Dual.Pommel"),
        TEXT("dual quick melee selects the held offhand blade"));
    Body.Family=TEXT("Pistol");Body.Action=EFPSBodyAction::HeavyStrike;Body.ActionVariant=TEXT("OffhandKukriUppercut");
    Body.Motion=EFPSBodyMotion::Ground;
    Check(FPSBodyKukriMotion::Clip(Body)==TEXT("Pistol.KukriUppercut")&&FPSBodyKukriMotion::PreserveHands(Body,true)==0,
        TEXT("mixed uppercut owns both native arms"));
    Check(FPSBodyKukriMotion::UsesAuthoredClock(FPSBodyKukriMotion::Clip(Body)),TEXT("mixed uppercut keeps replicated author clock"));
    Body.bHasActionProgress=true;Body.ActionProgress=.35f;Body.ActionProgressRate=0.f;
    Check(FPSBodyPoses::Progress(Body,100.f)==.35f&&FPSBodyPoses::Progress(Body,101.f)==.35f,
        TEXT("paused authoritative progress freezes the pose clock"));
    Check(FPSBodyKukriMotion::AttackLegWeight(Body,180.f)>.99f,TEXT("mixed uppercut lunge retains authored supporting legs"));
    Body.bOffhandPistol=true;Check(!FPSBodyKukriMotion::IsOffhandUppercut(Body),TEXT("offhand pistol cannot select knife uppercut"));
    Body.bOffhandPistol=false;Body.Motion=EFPSBodyMotion::Mantle;
    Check(FPSBodyKukriMotion::Clip(Body).IsNone(),TEXT("traversal cancels mixed uppercut presentation"));
    auto* BodyComponent=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    auto* Kukri=Pawn->FindComponentByClass<UKukriWeaponComponent>();
    Check(BodyComponent&&Kukri,TEXT("kukri presentation fixture exists"));
    if(BodyComponent&&Kukri)
    {
        BodyComponent->Character=Pawn;
        const auto CheckClock=[&](EFPSBodyAction Action,const TCHAR* Family,const TCHAR* Variant)
        {
            FFPSBodyState Before;Before.Family=Family;Before.Action=Action;Before.ActionVariant=Variant;
            Before.bHasActionProgress=true;Before.ActionProgress=.25f;Before.ActionProgressRate=.75f;
            FFPSBodyState Stopped=Before;Stopped.ActionProgress=.28f;Stopped.ActionProgressRate=0.f;
            Check(FPSBodyNetwork::IsTransition(Stopped,Before),*(FString(Variant)+TEXT(" pause is a reliable transition")));
            BodyComponent->DisplayState=Stopped;BodyComponent->PreviousLocalPresentation=Before;
            BodyComponent->bHasLocalPresentation=true;BodyComponent->SendBodyPresentation(1.f/60.f);
            Check(BodyComponent->DisplayState.ActionProgressRate==0.f,*(FString(Variant)+TEXT(" send preserves new hit-stop")));
            FFPSBodyState Resumed=Stopped;Resumed.ActionProgressRate=.75f;
            Check(FPSBodyNetwork::IsTransition(Resumed,Stopped),*(FString(Variant)+TEXT(" resume is a reliable transition")));
            BodyComponent->DisplayState=Resumed;BodyComponent->PreviousLocalPresentation=Stopped;
            BodyComponent->SendBodyPresentation(1.f/60.f);
            Check(BodyComponent->DisplayState.ActionProgressRate==.75f,*(FString(Variant)+TEXT(" send resumes without a frame of delay")));
            Check(!FPSBodyNetwork::IsTransition(Resumed,Resumed),*(FString(Variant)+TEXT(" steady clock does not resend reliable edges")));
        };
        CheckClock(EFPSBodyAction::Strike,TEXT("Kukri"),TEXT("Attack"));
        CheckClock(EFPSBodyAction::Strike,TEXT("Kukri"),TEXT("DualAttack2"));
        CheckClock(EFPSBodyAction::Thrust,TEXT("Kukri"),TEXT("DualThrust"));
        CheckClock(EFPSBodyAction::HeavyStrike,TEXT("Kukri"),TEXT("Uppercut"));
        CheckClock(EFPSBodyAction::HeavyStrike,TEXT("Kukri"),TEXT("HeavyRelease"));
        CheckClock(EFPSBodyAction::HeavyStrike,TEXT("Kukri"),TEXT("SprintAttack"));
        CheckClock(EFPSBodyAction::Pommel,TEXT("Kukri"),TEXT("QuickCombat"));
        CheckClock(EFPSBodyAction::Whirlwind,TEXT("Kukri"),TEXT("DualWhirlwind"));
        CheckClock(EFPSBodyAction::Charge,TEXT("Kukri"),TEXT("DualHeavyCharge"));
        CheckClock(EFPSBodyAction::Equip,TEXT("Kukri"),TEXT("DualEquip"));
        CheckClock(EFPSBodyAction::Thrust,TEXT("Pistol"),TEXT("OffhandKukriThrust"));
        CheckClock(EFPSBodyAction::HeavyStrike,TEXT("Pistol"),TEXT("OffhandKukriUppercut"));
        FFPSBodyState Gun;Gun.Family=TEXT("Rifle");Gun.Action=EFPSBodyAction::Reload;Gun.bHasActionProgress=true;
        Check(!FPSBodyKukriMotion::HasExecutorClock(Gun),TEXT("unrelated weapon timing keeps its existing path"));
        Kukri->bAttacking=true;Kukri->CurrentClip=TEXT("Attack");Kukri->Stage=0;
        Kukri->Elapsed=.4f;Kukri->PlayRate=1.f;Kukri->PressStop=.2f;Kukri->HitStop=0.f;
        FFPSBodyState Sample;BodyComponent->SampleKukriState(*Kukri,Sample,10.f);
        Check(Sample.ActionProgressRate>0.f,TEXT("saved impact length cannot leave presentation paused"));
        Kukri->HitStop=.1f;BodyComponent->SampleKukriState(*Kukri,Sample,10.f);
        Check(Sample.ActionProgressRate==0.f,TEXT("remaining contact hit-stop pauses presentation"));
        Kukri->bDualSweep=true;Kukri->CurrentClip=TEXT("DualAttack");
        BodyComponent->SampleKukriState(*Kukri,Sample,10.f);
        Check(FMath::IsNearlyEqual(Sample.ReleaseFraction,KukriRhythm::Swings[0].ContactEnd+KukriRhythm::DualSweepOffset(0)),
            TEXT("dual release marker includes the later left blade"));
        Kukri->bDualSweep=false;
        Kukri->HitStop=0.f;Kukri->bAttacking=false;Kukri->bHeavyCharging=true;
        Kukri->HeavyRequiredSeconds=2.f;Kukri->HeavyChargeStartedAt=World->GetTimeSeconds()-.1;
        Kukri->Elapsed=0.f;BodyComponent->SampleKukriState(*Kukri,Sample,10.f);
        Check(Sample.ActionProgressRate==0.f,TEXT("manual charge tap delay stays still remotely"));
        Kukri->HeavyChargeStartedAt=World->GetTimeSeconds()-.5;Kukri->Elapsed=.2f;
        BodyComponent->SampleKukriState(*Kukri,Sample,10.f);
        Check(FMath::IsNearlyEqual(Sample.ActionProgressRate,.5f),TEXT("charge raise follows martial speed"));
        Kukri->Elapsed=.8f;BodyComponent->SampleKukriState(*Kukri,Sample,10.f);
        Check(FMath::IsNearlyEqual(Sample.ActionProgressRate,1.6f/1.4f/2.f),TEXT("charge load follows remaining charge duration"));
        Kukri->Elapsed=2.f;BodyComponent->SampleKukriState(*Kukri,Sample,10.f);
        Check(Sample.ActionProgressRate==0.f,TEXT("full charge stays still remotely"));
        Kukri->bHeavyCharging=false;Kukri->PressStop=0.f;
        Reset(true);
        Kukri->ServerHeavyWeapon=Main.InstanceId;Kukri->ServerHeavyOffhandWeapon=Off.InstanceId;
        const auto ReleaseHeavy=[&]()
        {
            Kukri->bServerHeavyCharging=true;Kukri->ServerHeavyStartedAt=World->GetTimeSeconds()-3.;
            Kukri->ServerHeavyRequired=.3;return Kukri->PayServerHeavyRelease();
        };
        Check(ReleaseHeavy(),TEXT("dual heavy release commits fixture cost"));
        Check(Kukri->IsNetworkHeavyTargetNew(Main.InstanceId,Target)&&Kukri->IsNetworkHeavyTargetNew(Off.InstanceId,Target),
            TEXT("heavy receipt initially permits each blade"));
        Kukri->RecordNetworkHeavyTarget(Main.InstanceId,Target);
        Check(!Kukri->IsNetworkHeavyTargetNew(Main.InstanceId,Target)&&Kukri->IsNetworkHeavyTargetNew(Off.InstanceId,Target),
            TEXT("replayed main heavy contact rejected without blocking the offhand"));
        Kukri->RecordNetworkHeavyTarget(Off.InstanceId,Target);
        Check(!Kukri->IsNetworkHeavyTargetNew(Off.InstanceId,Target),TEXT("replayed offhand heavy contact rejected"));
        Check(!Kukri->IsNetworkHeavyTargetNew(TEXT("unrelated weapon"),Target),TEXT("heavy target receipt requires the released blade"));
        Check(ReleaseHeavy()&&Kukri->IsNetworkHeavyTargetNew(Main.InstanceId,Target)&&Kukri->IsNetworkHeavyTargetNew(Off.InstanceId,Target),
            TEXT("new committed heavy release resets per-blade contacts"));
        Kukri->NetworkHeavyReleaseUntil=World->GetTimeSeconds()-1.;
        Check(!Kukri->IsNetworkHeavyTargetNew(Main.InstanceId,Target),TEXT("expired heavy release rejects contacts"));
    }
    {
        auto* Material=LoadObject<UMaterialInterface>(nullptr,KukriRhythm::RiftMaterial);
        Check(Material!=nullptr,TEXT("observer rift production material loads"));
        FFPSBodyKukriRifts R;
        FTransform Blade;
        for(int32 I=0;I<45;++I)
        {
            const FRotator Turn(0,I*18.f,0);
            Blade=FTransform(Turn,Target->GetActorLocation()+Turn.RotateVector(FVector(70,0,90)));
            R.Sample(Target,0,TEXT("right"),TEXT("Whirlwind"),I/100.f,true,Blade,10.+I*.01);
        }
        auto* Mesh=R.Trails[0].Mesh.Get();
        Check(Mesh&&Mesh->IsVisible()&&Mesh->GetMesh()->VertexCount()==64,TEXT("observer rift keeps a bounded visible ribbon"));
        if(Mesh)
        {
            const FVector Tip=Mesh->GetComponentTransform().TransformPosition(FVector(Mesh->GetMesh()->GetVertex(63)));
            Check(Tip.Equals(Blade.TransformPosition(KukriRhythm::BladeTip*1.35f),.01f),TEXT("observer ribbon head follows the actual blade tip"));
        }
        const auto& Points=R.Trails[0].Points;
        Check(Points.Num()>1&&Points.Last().Travel-Points[0].Travel<=120.f,TEXT("whirlwind history cannot accumulate a full circle"));
        R.Sample(Target,1,TEXT("left"),TEXT("Whirlwind"),.4f,true,FTransform(FVector(0,-80,90)),10.44);
        Check(R.Trails[1].Weapon==TEXT("left")&&R.Trails[0].Weapon==TEXT("right"),TEXT("observer blades keep independent identities"));
        R.Advance(11.);
        Check(Mesh&&!Mesh->IsVisible()&&R.Trails[0].Points.IsEmpty(),TEXT("lost pose updates expire observer ribbon"));
        R.Clear(Target);
        Check(!R.Trails[0].Mesh.IsValid()&&!R.Trails[1].Mesh.IsValid(),TEXT("observer rifts release components on removal"));
        R.SampleWindow(Target,0,TEXT("right"),TEXT("HeavyRelease"),0.f,.1f,.2f,false,FTransform(FVector(0,0,90)),12.);
        Check(!R.Trails[0].Mesh.IsValid(),TEXT("observer windup does not show a cutting ribbon"));
        R.SampleWindow(Target,0,TEXT("right"),TEXT("HeavyRelease"),.3f,.1f,.2f,false,FTransform(FVector(90,0,90)),12.1);
        Check(R.Trails[0].Mesh.IsValid()&&R.Trails[0].Mesh->IsVisible(),TEXT("sparse poses crossing a whole cut window still show its ribbon"));
        Check(FMath::IsNearlyEqual(R.Trails[0].Progress,.2f),TEXT("sparse observer ribbon stops at the release boundary"));
        R.Clear(Target);
        R.RememberPose(0,TEXT("right"),FTransform(FVector(0,0,90)),13.);
        R.SampleWindow(Target,0,TEXT("right"),TEXT("DualHeavyRelease"),.16f,.003f,.133f,false,FTransform(FVector(90,0,90)),13.1);
        Check(R.Trails[0].Mesh.IsValid()&&R.Trails[0].Mesh->IsVisible(),TEXT("first heavy packet past contact bridges the last actual charge pose"));
        R.Clear(Target);
        R.RememberPose(0,TEXT("old_weapon"),FTransform(FVector(0,0,90)),14.);
        R.SampleWindow(Target,0,TEXT("right"),TEXT("HeavyRelease"),.16f,.003f,.133f,false,FTransform(FVector(90,0,90)),14.1);
        Check(!R.Trails[0].Mesh.IsValid(),TEXT("observer cut cannot bridge across an equipment swap"));
        R.Clear(Target);
        R.RememberPose(0,TEXT("right"),FTransform(FVector(0,0,90)),15.);
        R.SampleWindow(Target,0,TEXT("right"),TEXT("HeavyRelease"),.16f,.003f,.133f,false,FTransform(FVector(90,0,90)),15.5);
        Check(!R.Trails[0].Mesh.IsValid(),TEXT("observer cut cannot bridge a stale previous pose"));
        R.Clear(Target);
    }
    {
        Reset(false);
        const double Now=World->GetTimeSeconds();
        const auto StampedBegin=[&](double Stamp)
        {++Serial;PS->ServerBeginKukriAttack_Implementation(Serial,Pawn,Main.InstanceId,FString(),0,false,FVector::ForwardVector,1000+Serial,Stamp);};
        StampedBegin(Now-.5);
        auto R=Report();R.ClientFireTime=PS->KukriAttack.Started+PS->KukriAttack.ContactStart[0]+.01;
        Check(PS->KukriAttack.Serial==Serial&&PS->ValidateKukriHit(R,Pawn,Reason),TEXT("batched begin and hit retain their bounded client server-clock times"));
        const auto Accepted=PS->KukriAttack.Serial;
        const double Paid=Model->Snapshot().UppercutStaminaSpent;
        R.ClientFireTime=PS->KukriAttack.Started;
        Check(!PS->ValidateKukriHit(R,Pawn,Reason),TEXT("late delivery cannot make an early stamped contact valid"));
        StampedBegin(Now-.49);
        Check(PS->KukriAttack.Serial==Accepted&&Model->Snapshot().UppercutStaminaSpent==Paid,TEXT("backdated starts cannot accelerate the accepted combo cadence"));
        StampedBegin(Now-1.);
        Check(PS->KukriAttack.Serial==Accepted&&Model->Snapshot().UppercutStaminaSpent==Paid,TEXT("stale attack starts are rejected without payment"));
        StampedBegin(Now+.5);
        Check(PS->KukriAttack.Serial==Accepted&&Model->Snapshot().UppercutStaminaSpent==Paid,TEXT("future attack starts are rejected without payment"));
    }
    CheckRunes(PS,Pawn,Check);
    // Execute the owning-client receipt handlers with no possessed pawn: an
    // accepted cast can arrive in the gap between death and respawn.
    const auto HostBeforeReceipt=Host->Snapshot();
    auto ClientSeed=Seed;ClientSeed.Stamina=100.f;ClientSeed.UppercutStaminaSpent=0.;
    ClientSeed.MartialCooldownRevision=20;ClientSeed.SwordUppercutCooldown=12.f;ClientSeed.WhirlwindCooldown=9.f;
    Host->AdoptNetMirror(ClientSeed);
    auto* LatePS=World->SpawnActor<AColdSteelPlayerState>();LatePS->SetRole(ROLE_AutonomousProxy);
    LatePS->ClientSwordUppercutResult_Implementation(1,Pawn,true,12.,15.f,15.f,19,World->GetTimeSeconds());
    Check(FMath::IsNearlyEqual(Host->Stamina(),88.f)&&Host->Snapshot().UppercutStaminaSpent==12.,
        TEXT("late accepted uppercut debits once without a current pawn"));
    Check(Host->Snapshot().SwordUppercutCooldown==12.f&&Host->Snapshot().MartialCooldownRevision==20,
        TEXT("older uppercut cooldown receipt cannot overwrite a newer mirror"));
    LatePS->ClientSwordUppercutResult_Implementation(1,Pawn,true,12.,15.f,15.f,19,World->GetTimeSeconds());
    Check(FMath::IsNearlyEqual(Host->Stamina(),88.f),TEXT("duplicate late uppercut receipt does not debit twice"));
    LatePS->ClientSwordWhirlwindResult_Implementation(1,Pawn,true,20.,8.f,10.f,21,World->GetTimeSeconds());
    Check(FMath::IsNearlyEqual(Host->Stamina(),80.f)&&Host->Snapshot().UppercutStaminaSpent==20.,
        TEXT("late accepted whirlwind merges cumulative cost without a current pawn"));
    Check(Host->Snapshot().WhirlwindCooldown==8.f&&Host->Snapshot().MartialCooldownRevision==21,
        TEXT("late whirlwind preserves accepted cooldown"));
    LatePS->ClientSwordWhirlwindResult_Implementation(1,Pawn,true,20.,8.f,10.f,21,World->GetTimeSeconds());
    Check(FMath::IsNearlyEqual(Host->Stamina(),80.f),TEXT("duplicate late whirlwind receipt does not debit twice"));
    LatePS->ClientSwordUppercutResult_Implementation(2,Pawn,false,20.,0.f,0.f,18,World->GetTimeSeconds());
    Check(Host->Snapshot().SwordUppercutCooldown==12.f&&Host->Snapshot().MartialCooldownRevision==21,
        TEXT("late rejected uppercut cannot clear a newer cooldown"));
    LatePS->SetRole(ROLE_Authority);LatePS->Destroy();Host->AdoptNetMirror(HostBeforeReceipt);
    FString Output;if(!FParse::Value(*Params,TEXT("Output="),Output))return 3;
    auto Result=MakeShared<FJsonObject>();Result->SetArrayField(TEXT("checks"),Rows);Result->SetNumberField(TEXT("failures"),Failures);
    Result->SetBoolField(TEXT("udp_or_multiplayer_runtime"),false);Result->SetBoolField(TEXT("visuals_tested"),false);
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    const bool Saved=FFileHelper::SaveStringToFile(Json,*Output);FCommandLine::Set(*Original);
    return Saved?(Failures?1:0):3;
}
