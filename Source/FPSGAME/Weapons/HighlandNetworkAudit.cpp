#include "RuneSwordAuditCommandlet.h"
#include "RuneSwordComponent.h"
#include "HighlandRidgeGatherComponent.h"
#include "OathJudgmentVisualComponent.h"
#include "Components/StaticMeshComponent.h"
#include "HighlandRidgeThrust.h"
#include "ModularSwordVisual.h"
#include "../Development/KukriCombatWireAudit.h"
#include "../Monsters/NurseZombie.h"
#include "Camera/CameraComponent.h"
#include "Engine/StaticMesh.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Combat/WeaponDamageTypes.h"
#include "GunsmithModificationTier.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Production/WarhammerModificationAuditCommandlet.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonSerializer.h"
#include <limits>

int32 URuneSwordAuditCommandlet::AuditHighlandNetwork(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("HighlandNetworkAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("HighlandNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("HighlandReceiptAudit"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    ON_SCOPE_EXIT {GI->Shutdown();if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}GI->RemoveFromRoot();FCommandLine::Set(*Original);};
    if(!World||!Host||!Host->IsAudit())return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool OK,const TCHAR* Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("HIGHLAND_NETWORK %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Stamina=100;Seed.bSprintExhausted=false;for(auto& S:Seed.Skills)S.Value.Level=1;
    auto Item=Host->CreateItem(TEXT("ue_highland_claymore"));Item.Place=1;Item.Cell=6;
    const auto Configure=[&](bool Gale)
    {
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),TEXT("highland_ridge_piercer"));
        Parts->SetStringField(TEXT("blade_2"),HighlandOathRune::Id);
        Parts->SetStringField(TEXT("pommel"),Gale?TEXT("highland_gale_oath"):TEXT("factory"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Item.Data));
        Seed.Items={Item};
    };
    Configure(false);auto* Model=Host->CreateShadowModel(Seed);
    auto* PC=World->SpawnActor<AWarhammerAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    PC->SetPlayerState(PS);PS->SetOwner(PC);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    PS->ShadowModel=Model;Pawn->NetShadowProfile=Model;Model->AttachPawn(Pawn);
    auto* HP=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();HP->Health=HP->MaxHealth;
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword->Character=Pawn;Sword->InstanceId=Item.InstanceId;
    Check(!Pawn->IsLocallyControlled()&&Sword->Animations.IsEmpty(),TEXT("remote authority fixture needs no first-person animations"));
    const double BaseSprint=Model->SprintStaminaPerSecond();const auto BaseStats=ColdSteelMelee::Evaluate(Item,Model);
    Configure(true);Model->AdoptNetMirror(Seed);Host->AdoptNetMirror(Seed);
    const auto Stats=ColdSteelMelee::Evaluate(Item,Model),OwnerStats=ColdSteelMelee::Evaluate(Item,Host);
    Check(FMath::IsNearlyEqual(double(Model->SprintStaminaPerSecond()),BaseSprint*.85,.001),TEXT("Gale sprint cost is 85 percent on shadow profile"));
    UE_LOG(LogTemp,Display,TEXT("HIGHLAND_CHARGE_VALUES base=%.6f base_bonus=%.6f server=%.6f bonus=%.6f owner=%.6f"),BaseStats.HeavyChargeSeconds,BaseStats.HeavyChargeSpeedBonus,Stats.HeavyChargeSeconds,Stats.HeavyChargeSpeedBonus,OwnerStats.HeavyChargeSeconds);
    Check(FMath::IsNearlyEqual(Stats.HeavyChargeSpeedBonus,BaseStats.HeavyChargeSpeedBonus+.2,.001)&&
        FMath::IsNearlyEqual(Stats.HeavyChargeSeconds,BaseStats.HeavyChargeSeconds*(1.+BaseStats.HeavyChargeSpeedBonus)/(1.+Stats.HeavyChargeSpeedBonus),.001)&&
        FMath::IsNearlyEqual(Stats.HeavyChargeSeconds,OwnerStats.HeavyChargeSeconds,.001),TEXT("Gale charge speed is plus 20 percent on owner and authority"));
    Check(ColdSteelModification::Tier(Item.Definition,TEXT("pommel"),TEXT("highland_gale_oath"))==EGunsmithModificationTier::Special, TEXT("Gale pommel is special tier"));
    Check(ColdSteelModification::Tier(Item.Definition,TEXT("blade_1"),TEXT("highland_ridge_piercer"))==EGunsmithModificationTier::Legendary,TEXT("Ridge blade is legendary tier"));
    Check(FMath::IsNearlyEqual(Stats.Modifiers.Range,1.25)&&FMath::IsNearlyEqual(Stats.Modifiers.ComboMultiplier(3),2.1),TEXT("Ridge passive range and previous third-hit damage times 1.5 retained"));
    Check(FMath::IsNearlyEqual(HighlandRidgeThrust::AddPenetration(.1f,3),.3f,.0001f)&&FMath::IsNearlyEqual(HighlandRidgeThrust::AddPenetration(.1f,0x10),.9f,.0001f),TEXT("thrust penetration adds 20 or 80 percentage points"));
    const auto Reset=[&]()
    {
        Model->AdoptNetMirror(Seed);World->TimeSeconds=10.;Sword->bCharging=false;
        Sword->NetworkHeavyReleaseUntil=Sword->ServerHeavyChargeStartedAt=Sword->ServerHeavyChargeReceivedAt=Sword->ServerHeavyChargeLastStartedAt=-1.;
    };
    const auto Start=[&](double Stamp){Sword->ServerSetSwordHeavyCharge_Implementation(Item.InstanceId,true,false,Stamp,0);};
    const auto Stop=[&](bool Release){Sword->ServerSetSwordHeavyCharge_Implementation(Item.InstanceId,false,Release,World->GetTimeSeconds(),0);};
    const auto Advance=[&](double Seconds){Model->SpendStamina(Seconds*Model->HeavyChargeStaminaPerSecond());World->TimeSeconds+=Seconds;};
    Reset();for(double Stamp:{9.,10.5,std::numeric_limits<double>::quiet_NaN()})
    {Start(Stamp);Check(!Sword->bCharging&&Model->Stamina()==100.f,TEXT("out of bounds or invalid charge timestamp rejected"));}
    Start(9.6);Check(Sword->bCharging&&FMath::IsNearlyEqual(Sword->ServerHeavyChargeStartedAt,9.6),TEXT("400 ms late begin preserves actual hold start"));
    Start(9.3);Check(FMath::IsNearlyEqual(Sword->ServerHeavyChargeStartedAt,9.6),TEXT("duplicate begin cannot backdate charge"));
    Sword->ServerSetSwordHeavyCharge_Implementation(TEXT("wrong weapon"),false,true,10.,0);
    Check(Sword->bCharging,TEXT("wrong weapon stop cannot cancel real charge"));
    Advance(.2);Stop(true);Check(!Sword->IsNetworkHeavyReleaseWindowOpen(Item.InstanceId),TEXT("partial hold cannot become a heavy attack"));
    Start(9.6);Check(!Sword->bCharging,TEXT("replayed cancelled begin cannot reopen charge"));
    Reset();Start(9.6);Stop(false);Check(Model->Stamina()==100.f,TEXT("cancelled hold does not bill network transit"));
    Reset();Start(9.6);const double Required=Sword->ServerHeavyRequiredSeconds,Rate=Model->HeavyChargeStaminaPerSecond();
    const double ReleaseCost=ColdSteelMelee::HeavyReleaseStamina(Model->Equipped(),Model);
    Advance(Required-.4);
    Check(World->GetTimeSeconds()-Sword->ServerHeavyChargeReceivedAt<Required-.15,TEXT("fixture reproduces old arrival-clock rejection"));
    Check(Sword->ConsumeNetworkHeavyChargeForRelease(Item.InstanceId),TEXT("hit-before-stop commits fully charged delayed release"));
    Check(FMath::IsNearlyEqual(double(Model->Stamina()),100.-Required*Rate-ReleaseCost,.001),TEXT("missing hold stamina and release settled exactly once"));
    const float Paid=Model->Stamina();Stop(true);Stop(true);
    Check(Model->Stamina()==Paid&&!Sword->ConsumeNetworkHeavyChargeForRelease(Item.InstanceId),TEXT("duplicate stop or hit cannot pay a second time"));
    World->TimeSeconds+=.61;Check(!Sword->IsNetworkHeavyReleaseWindowOpen(Item.InstanceId),TEXT("heavy release receipt expires"));
    Reset();Start(9.6);Advance(Required-.4);
    auto Poor=Model->Snapshot();Poor.Stamina=ReleaseCost+.4*Rate-.05;Model->AdoptNetMirror(Poor);const float Before=Model->Stamina();Stop(true);
    Check(!Sword->IsNetworkHeavyReleaseWindowOpen(Item.InstanceId)&&Model->Stamina()==Before,TEXT("insufficient combined hold and release cost denies atomically"));
    Reset();Start(9.6);Advance(Required-.4);auto Unequipped=Model->Snapshot();Unequipped.ActiveWeaponSlot=9;Model->AdoptNetMirror(Unequipped);
    Check(!Sword->ConsumeNetworkHeavyChargeForRelease(Item.InstanceId),TEXT("unequipping before receipt cannot release old sword"));
    Check(FMath::IsNearlyEqual(double(Model->SprintStaminaPerSecond()),BaseSprint,.001),TEXT("inactive sword removes sprint reduction"));
    // The accepted input clock may lead the server by up to 100 ms.
    Reset();Start(10.08);
    const double Full=10.08+Sword->ServerHeavyRequiredSeconds;
    World->TimeSeconds=Full+.24;
    Check(Sword->ConsumeNetworkHeavyChargeForRelease(Item.InstanceId,Full+.32,21),
        TEXT("ridge hit arriving first commits the precise heavy release"));
    Check(Sword->OathPresentation().Phase==2,TEXT("positive input clock skew retains the last part of the judgment window"));
    const double Settled=Model->Stamina();
    World->TimeSeconds+=.65;
    Sword->ServerSetSwordHeavyCharge_Implementation(Item.InstanceId,false,true,Full+.32,21);
    Check(Sword->OathPresentation().Phase==2 && Model->Stamina()==Settled,TEXT("late duplicate release preserves judgment and does not spend twice"));
    auto Shot=ColdSteelSkills::Snapshot(Pawn,Model->Equipped(),false);
    Shot.AttackMeta=0x10;Shot.GuardAttackSerial=21;Shot.ArmorPenetration=HighlandRidgeThrust::AddPenetration(.1f,Shot.AttackMeta);
    Shot.DamagePanel={80.,10.,20.,0.};Shot.CriticalRoll=1.f;
    Sword->ApplyOathToShot(Shot);
    Check(FMath::IsNearlyEqual(Shot.OathPhysicalMultiplier,1.5525f,.0001f)&&FMath::IsNearlyEqual(Shot.ToughnessDamageMultiplier,1.5f,.0001f),
        TEXT("judged ridge heavy combines physical and toughness bonuses"));
    auto* Target=World->SpawnActor<AActor>();FWeaponDamageResult DamageResult;
    ColdSteelSkills::ApplyHit(Pawn,FHitResult(Target,nullptr,FVector::ZeroVector,FVector::UpVector),110.f,FVector::ForwardVector,Shot,&DamageResult);
    Check(FMath::IsNearlyEqual(DamageResult.BeforeDefense.BasePhysical,124.2,.001) &&
        FMath::IsNearlyEqual(DamageResult.BeforeDefense.AddedPhysical,31.05,.001) &&
        FMath::IsNearlyEqual(DamageResult.BeforeDefense.Total(),165.25,.001),
        TEXT("damage pipeline scales both physical channels once and preserves magic"));
    for(uint8 Meta:{uint8(3),uint8(0x16),uint8(0x15),uint8(0x10)})
    {
        auto Other=ColdSteelSkills::Snapshot(Pawn,Model->Equipped(),false);
        Other.AttackMeta=Meta;Other.GuardAttackSerial=22;Sword->ApplyOathToShot(Other);
        Check(FMath::IsNearlyEqual(Other.OathPhysicalMultiplier,(Meta==0x15||Meta==0x10)?1.15f:1.f,.0001f),
            TEXT("finisher, dash, counter and other serial do not inherit judgment"));
    }
    const float BeforeRefund=Model->Stamina();
    Sword->ConfirmOathHit(Shot,0.f,FVector::ZeroVector);
    Check(Model->Stamina()==BeforeRefund,TEXT("zero damage does not consume first effective hit"));
    Sword->ConfirmOathHit(Shot,10.f,FVector::ZeroVector);Sword->ConfirmOathHit(Shot,10.f,FVector::ZeroVector);
    Check(FMath::IsNearlyEqual(double(Model->Stamina()-BeforeRefund),ReleaseCost*.25,.001),TEXT("multiple targets refund the release cost once"));
    auto Foreign=Sword->OathPresentation();Foreign.Weapon+=TEXT("_other");
    Check(Sword->OathImpactTime(Foreign)<0. && Sword->OathImpactTime(Sword->OathPresentation())>0.,TEXT("impact belongs to one weapon and release"));
    Foreign=Sword->OathPresentation();Foreign.ReleaseAt+=2.;
    Check(Sword->OathImpactTime(Foreign)<0.,TEXT("earlier impact cannot replay on next judgment"));
    Reset();Start(10.08);World->TimeSeconds=Full-.035;
    Sword->ConsumeNetworkHeavyChargeForRelease(Item.InstanceId,Full-.025,23);
    Check(Sword->OathPresentation().Phase!=2,TEXT("positive input skew cannot grant an early judgment"));
    auto AlmostFull=Model->Snapshot();AlmostFull.Stamina=Model->MaxStamina()-1.f;Model->AdoptNetMirror(AlmostFull);
    const double BeforeCredit=Model->Snapshot().OathStaminaRestored;
    const double Capped=Model->RefundOathStamina(12.f);
    Check(FMath::IsNearlyEqual(Capped-BeforeCredit,1.,.001),TEXT("refund ledger records only stamina actually credited at cap"));
    Model->SpendStamina(5.f);const float AfterSpend=Model->Stamina();Model->ApplyOathRefundReceipt(Capped);
    Check(Model->Stamina()==AfterSpend,TEXT("a repeated cumulative refund cannot overwrite later spending"));
    Reset();PS->RidgeStrike={};
    PS->ServerBeginRidgeStrike_Implementation(Pawn,Item.InstanceId,1,1,9.6);
    Check(FMath::IsNearlyEqual(PS->RidgeStrike.NextSwingAt,9.6+Stats.AttackSeconds,.001),TEXT("late first swing uses input clock for combo recovery"));
    const double SecondAt=PS->RidgeStrike.NextSwingAt;World->TimeSeconds=SecondAt+.06;
    PS->ServerBeginRidgeStrike_Implementation(Pawn,Item.InstanceId,2,2,SecondAt);
    Check(PS->RidgeStrike.Meta==2,TEXT("second swing remains valid when network delay drops from 400 to 60 ms"));
    const double ThirdAt=PS->RidgeStrike.NextSwingAt;World->TimeSeconds=ThirdAt+.4;
    PS->ServerBeginRidgeStrike_Implementation(Pawn,Item.InstanceId,3,3,ThirdAt);
    Check(PS->RidgeStrike.Serial==3&&FMath::IsNearlyEqual(double(PS->RidgeStrike.Length),Stats.ThrustReach,.001),TEXT("third combo authority receipt uses extended rectangle"));
    const double HitUntil=PS->RidgeStrike.HitUntil;PS->ServerBeginRidgeStrike_Implementation(Pawn,Item.InstanceId,3,3,ThirdAt);
    Check(PS->RidgeStrike.HitUntil==HitUntil,TEXT("duplicate thrust begin cannot reopen contact window"));
    World->TimeSeconds+=10;PS->ServerBeginRidgeStrike_Implementation(Pawn,Item.InstanceId,4,0x10,World->GetTimeSeconds());
    Check(FMath::IsNearlyEqual(double(PS->RidgeStrike.Length),Stats.SlashReach*Stats.Modifiers.MartialRange*1.25,.001),TEXT("heavy authority receipt uses extended rectangle"));
    World->TimeSeconds+=10;PS->ServerBeginRidgeStrike_Implementation(Pawn,Item.InstanceId,5,0x16,World->GetTimeSeconds());
    Check(FMath::IsNearlyEqual(double(PS->RidgeStrike.Length),double(Model->DashAttackStats().RangeCM),.001),TEXT("dash authority receipt matches skill rectangle"));
    // Dispatch loaded material delegates immediately in this fixture, which
    // has no engine frame loop. Production retains its normal async loading.
    auto* DelegateDelay=IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"));
    const int32 OldDelay=DelegateDelay?DelegateDelay->GetInt():0;
    if(DelegateDelay)DelegateDelay->Set(0);
    ON_SCOPE_EXIT {if(DelegateDelay)DelegateDelay->Set(OldDelay);};
    for(bool FirstPerson:{true,false})
    {
        auto* FX=UHighlandRidgeGatherComponent::CreateFor(Pawn,FirstPerson);FlushAsyncLoading();
        const FVector Tip(120,10,560);const FTransform Eye(FRotator::ZeroRotator,FVector(0,0,550));
        FX->Present(Eye,Tip,FVector::ForwardVector,.02f,.066f);
        Check(FX->IsVisible()&&FX->GetComponentLocation().Equals(Tip,.001),TEXT("first and world emitters start on actual tip"));
        const auto Pattern=FX->GetCustomPrimitiveData().Data;
        const FVector Moved(-30,250,610);FX->Present(FTransform(FRotator(10,90,0),FVector(-20,100,580)),Moved,FVector::RightVector,.25f,.066f);
        Check(FX->GetComponentLocation().Equals(Moved,.001)&&FX->GetForwardVector().Equals(FVector::RightVector,.001)&&FX->GetCustomPrimitiveData().Data==Pattern,
            TEXT("moving and turning during hold keeps tip, direction and random pattern"));
        const FVector Recovery(-55,270,600);FX->Present(Eye,Recovery,FVector::UpVector,.48f,.066f);
        Check(FX->IsVisible()&&FX->GetComponentLocation().Equals(Recovery,.001),TEXT("late afterglow follows recovering tip instead of freezing"));
        FX->Present(Eye,Recovery,FVector::UpVector,.56f,.066f);Check(!FX->IsVisible(),TEXT("afterglow hides after duration"));
        FX->DestroyComponent();
    }
    {
        auto* FX=UOathJudgmentVisualComponent::CreateFor(Pawn,false);
        auto* Blade=NewObject<UStaticMeshComponent>(Pawn);
        const FVector Base(0,0,500),Tip(100,0,500);
        FHighlandOathPresentation Judged;Judged.Phase=2;Judged.Weapon=Item.InstanceId;Judged.ReleaseAt=20.;
        FX->Present(Blade,Base,Tip,{},20.04,-100.,Base,EOathStroke::Thrust);
        Check(!FX->NeedsThrustEndpoint(Judged),TEXT("body keeps its sampled thrust while success is in transit"));
        FX->Present(Blade,Base,Tip,Judged,20.16,-100.,Base,EOathStroke::None);
        Check(!FX->NeedsThrustEndpoint(Judged),TEXT("late judgment consumes the stored thrust once"));
        Judged.ReleaseAt=23.;FX->Present(Blade,Base,Tip,Judged,23.12,-100.,Base,EOathStroke::None);
        Check(FX->NeedsThrustEndpoint(Judged),TEXT("first update during fixed hold requests the missed thrust endpoint"));
        FX->Present(Blade,Base,Tip,Judged,23.13,-100.,Base,EOathStroke::Thrust);
        Check(!FX->NeedsThrustEndpoint(Judged),TEXT("fixed endpoint is emitted once even at identical consecutive poses"));
        FX->DestroyComponent();
    }
    // Use the same paid release and player-state entry points as an actual guest.
    {
        Configure(false);
        TSharedPtr<FJsonObject> Data;
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
        Data->GetObjectField(TEXT("gunsmith_parts"))->SetStringField(TEXT("guard"),TEXT("highland_gale_wing"));
        Item.Data.Reset();FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Item.Data));Seed.Items={Item};
        Reset();
        const float SwingStart=Model->Stamina();
        PS->ServerPayGaleSwing_Implementation(Pawn,Item.InstanceId,81,false);
        const uint64 Swing=GaleWing::Key(GaleWing::EAttack::Swing,81);
        const float AfterSwing=Model->Stamina();
        Check(AfterSwing<SwingStart && Sword->HasGalePayment(Swing,Item.InstanceId) && Sword->GaleMoveScale()==1.f,
            TEXT("Gale swing is actually billed, a miss grants no buff"));
        PS->ServerPayGaleSwing_Implementation(Pawn,Item.InstanceId,81,false);
        Sword->ConfirmGaleKill(Swing,TEXT("wrong sword"));
        Check(Model->Stamina()==AfterSwing && Sword->GaleMoveScale()==1.f,TEXT("duplicate payment and foreign weapon grant no stamina or speed"));
        Sword->ConfirmGaleKill(Swing,Item.InstanceId);
        UE_LOG(LogTemp,Display,TEXT("GALE_SWING paid_to=%.3f restored_to=%.3f cap=%.3f credit=%.3f seconds=%.3f health=%.3f"),AfterSwing,Model->Stamina(),Model->MaxStamina(),Model->Snapshot().OathStaminaRestored,Sword->GaleSwiftRemaining(),HP->Health);
        Check(FMath::IsNearlyEqual(Model->Stamina(),SwingStart) && FMath::IsNearlyEqual(Sword->GaleSwiftRemaining(),3.f) && Sword->GaleMoveScale()==1.25f,
            TEXT("Gale kill refunds exact cost and grants 25 percent speed for three seconds"));
        Model->SpendStamina(7.f);World->TimeSeconds+=2.;
        Sword->ConfirmGaleKill(Swing,Item.InstanceId);
        Check(FMath::IsNearlyEqual(Model->Stamina(),SwingStart-7.f) && FMath::IsNearlyEqual(Sword->GaleSwiftRemaining(),3.f),
            TEXT("second kill refreshes without refunding the swing twice"));
        Sword->RecordGalePayment(Swing,Item.InstanceId,7.f,true);
        Sword->RecordGalePayment(Swing,Item.InstanceId,7.f,true);
        Check(FMath::IsNearlyEqual(Model->Stamina(),SwingStart),TEXT("short hold payment arriving after the kill is refunded exactly once"));
        World->TimeSeconds+=3.01;Sword->TickGaleSwift();
        Check(Sword->GaleSwiftRemaining()==0.f && Sword->GaleMoveScale()==1.f,TEXT("Gale speed returns to baseline on expiry"));
        Reset();const float HeavyStart=Model->Stamina();
        const double CreditBeforeHeavy=Model->Snapshot().OathStaminaRestored;
        Start(10.);
        const double Hold=Sword->ServerHeavyRequiredSeconds;
        Model->TickRuntime(float(Hold),Pawn);World->TimeSeconds+=Hold;
        const bool Released=Sword->ConsumeNetworkHeavyChargeForRelease(Item.InstanceId,World->GetTimeSeconds(),82);
        const uint64 Heavy=GaleWing::Key(GaleWing::EAttack::Heavy,82);
        auto HeavyShot=ColdSteelSkills::Snapshot(Pawn,Model->Equipped(),false);
        HeavyShot.GuardAttackSerial=82;HeavyShot.AttackMeta=0x10;HeavyShot.GalePaymentKey=Heavy;
        Sword->ApplyOathToShot(HeavyShot);
        const float HeavyPaid=HeavyStart-Model->Stamina();
        Sword->ConfirmOathHit(HeavyShot,10.f,FVector::ZeroVector);
        const double OathCredit=Model->Snapshot().OathStaminaRestored-CreditBeforeHeavy;
        Sword->ConfirmGaleKill(Heavy,Item.InstanceId);
        UE_LOG(LogTemp,Display,TEXT("GALE_HEAVY released=%d paid=%.3f restored_to=%.3f credit=%.3f oath=%.3f seconds=%.3f cap=%.3f"),Released,HeavyPaid,Model->Stamina(),Model->Snapshot().OathStaminaRestored,OathCredit,Sword->GaleSwiftRemaining(),Model->MaxStamina());
        Check(Released && HeavyPaid>ColdSteelMelee::HeavyReleaseStamina(Model->Equipped(),Model) && OathCredit>0.f &&
            FMath::IsNearlyEqual(Model->Stamina(),HeavyStart,.002f) && FMath::IsNearlyEqual(Model->Snapshot().OathStaminaRestored-CreditBeforeHeavy,double(HeavyPaid),.002),
            TEXT("charged heavy kill repays hold and release once after an Oath hit refund"));
        auto* Local=World->SpawnActor<AFPSGAMECharacter>(FVector(0,1500,500),FRotator::ZeroRotator);
        auto* LocalPC=World->SpawnActor<APlayerController>();LocalPC->SetAsLocalPlayerController();LocalPC->Possess(Local);
        auto* LocalSword=Local->FindComponentByClass<URuneSwordComponent>();
        LocalSword->Character=Local;LocalSword->Camera=Local->FindComponentByClass<UCameraComponent>();
        Host->AdoptNetMirror(Seed);Host->AttachPawn(Local);LocalSword->RefreshEquipment(Host);LocalSword->CancelAction();FlushAsyncLoading();
        bool LocalGuard=false;
        if(LocalSword->ModularSword)for(auto* Part:ColdSteelModularSword::Components(LocalSword->ModularSword))
            if(Part->ComponentHasTag(TEXT("SwordSlot=guard")) && Part->GetStaticMesh())
                LocalGuard=Part->GetStaticMesh()->GetName()==TEXT("SM_GaleFeather_Ridge");
        Check(LocalGuard,TEXT("first-person sword mounts the saved ridge-fitted wing guard"));
        const float LocalStart=Host->Stamina();
        const bool Started=LocalSword->StartSwing(TEXT("Slash1"),false);
        auto* WeakTarget=KukriCombatWire::SpawnTarget(World,Local->GetActorLocation()+FVector(100,0,0));
        FWeaponDamageResult LocalDamage;
        if(Started && WeakTarget)
        {
            WeakTarget->Health=1.f;
            const FHitResult Contact(WeakTarget,nullptr,WeakTarget->GetActorLocation(),-FVector::ForwardVector);
            ColdSteelSkills::ApplyHit(Local,Contact,LocalSword->SwingDamage,FVector::ForwardVector,LocalSword->SwingSkills,&LocalDamage);
        }
        Check(Started && LocalDamage.bKilled && LocalSword->SwingSkills.GalePaymentKey &&
            FMath::IsNearlyEqual(LocalStart,Host->Stamina(),.002f) && LocalSword->GaleMoveScale()==1.25f,
            TEXT("standalone swing stamps its payment and an actual lethal contact activates the guard"));
        Configure(true);Model->AdoptNetMirror(Seed);
        const uint64 Other=GaleWing::Key(GaleWing::EAttack::Chain,83);
        Sword->RecordGalePayment(Other,Item.InstanceId,0.f);
        Check(!Sword->HasGalePayment(Other,Item.InstanceId),TEXT("Gale pommel without wing guard cannot grant the kill effect"));
    }
    FString Output;FParse::Value(*Params,TEXT("Output="),Output);auto Result=MakeShared<FJsonObject>();
    Result->SetArrayField(TEXT("checks"),Rows);Result->SetNumberField(TEXT("failures"),Failures);
    Result->SetBoolField(TEXT("udp_or_multiplayer_runtime"),false);Result->SetBoolField(TEXT("rendered"),false);
    Result->SetStringField(TEXT("scope"),TEXT("isolated authority implementations, data evaluation and live emitter transforms; not packet transport or rendered animation"));
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    return !Output.IsEmpty()&&FFileHelper::SaveStringToFile(Json,*Output)?(Failures?1:0):3;
}
