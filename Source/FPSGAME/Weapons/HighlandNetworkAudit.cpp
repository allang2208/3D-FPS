#include "RuneSwordAuditCommandlet.h"
#include "RuneSwordComponent.h"
#include "HighlandRidgeGatherComponent.h"
#include "HighlandRidgeThrust.h"
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
    const auto Start=[&](double Stamp){Sword->ServerSetSwordHeavyCharge_Implementation(Item.InstanceId,true,false,Stamp);};
    const auto Stop=[&](bool Release){Sword->ServerSetSwordHeavyCharge_Implementation(Item.InstanceId,false,Release,World->GetTimeSeconds());};
    const auto Advance=[&](double Seconds){Model->SpendStamina(Seconds*Model->HeavyChargeStaminaPerSecond());World->TimeSeconds+=Seconds;};
    Reset();for(double Stamp:{9.,10.5,std::numeric_limits<double>::quiet_NaN()})
    {Start(Stamp);Check(!Sword->bCharging&&Model->Stamina()==100.f,TEXT("out of bounds or invalid charge timestamp rejected"));}
    Start(9.6);Check(Sword->bCharging&&FMath::IsNearlyEqual(Sword->ServerHeavyChargeStartedAt,9.6),TEXT("400 ms late begin preserves actual hold start"));
    Start(9.3);Check(FMath::IsNearlyEqual(Sword->ServerHeavyChargeStartedAt,9.6),TEXT("duplicate begin cannot backdate charge"));
    Sword->ServerSetSwordHeavyCharge_Implementation(TEXT("wrong weapon"),false,true,10.);
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
    FString Output;FParse::Value(*Params,TEXT("Output="),Output);auto Result=MakeShared<FJsonObject>();
    Result->SetArrayField(TEXT("checks"),Rows);Result->SetNumberField(TEXT("failures"),Failures);
    Result->SetBoolField(TEXT("udp_or_multiplayer_runtime"),false);Result->SetBoolField(TEXT("rendered"),false);
    Result->SetStringField(TEXT("scope"),TEXT("isolated authority implementations, data evaluation and live emitter transforms; not packet transport or rendered animation"));
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    return !Output.IsEmpty()&&FFileHelper::SaveStringToFile(Json,*Output)?(Failures?1:0):3;
}
