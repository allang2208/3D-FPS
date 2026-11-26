#include "RuneSwordAuditCommandlet.h"
#include "RuneSwordComponent.h"
#include "RingChainSweepMotion.h"
#include "../FPSGAMECharacter.h"
#include "../BallisticAuditTarget.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/InputComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonSerializer.h"

int32 URuneSwordAuditCommandlet::AuditRingChainInput()
{
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("SkillNetworkAudit_RingChain_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("RingChainInput -ColdSteelProfile=")+Slot));
    ON_SCOPE_EXIT { FCommandLine::Set(*Original); };
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("RingChainInput"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    ON_SCOPE_EXIT
    {
        TArray<AActor*> Begun;
        for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())Begun.Add(*It);
        for(auto* Actor:Begun)
        {
            Actor->RouteEndPlay(EEndPlayReason::Quit);
            TInlineComponentArray<UActorComponent*> Components(Actor);
            for(auto* Component:Components)if(Component->HasBegunPlay())Component->EndPlay(EEndPlayReason::Quit);
        }
        GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();
    };
    World->InitializeActorsForPlay(FURL());
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetPlayerState(World->SpawnActor<APlayerState>());
    PC->SetAsLocalPlayerController();PC->bShowMouseCursor=false;PC->Possess(Pawn);
    Pawn->SetActorTickEnabled(false);for(auto* C:Pawn->GetComponents())C->SetComponentTickEnabled(false);
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
    Sword->Character=Pawn;Sword->Camera=Pawn->FindComponentByClass<UCameraComponent>();
    auto* Input=NewObject<UInputComponent>(Pawn);Pawn->SetupPlayerInputComponent(Input);
    auto Fire=[&](EInputEvent Edge)
    {
        for(int32 Index=0;Index<Input->GetNumActionBindings();++Index)
        {
            const auto& Binding=Input->GetActionBinding(Index);
            if(Binding.GetActionName()==TEXT("Fire")&&Binding.KeyEvent==Edge)
            {Binding.ActionDelegate.Execute(EKeys::LeftMouseButton);return true;}
        }
        return false;
    };
    auto State=Model->Snapshot();
    auto Item=Model->CreateItem(TEXT("ue_forged_steel_greatsword"));Item.InstanceId=TEXT("RingChainInput");Item.Place=1;Item.Cell=6;
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return 3;
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("pommel"),TEXT("ring_chain_pommel"));
    Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();
    FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.Items={Item};State.Stamina=100.;State.bSprintExhausted=false;
    State.Skills.FindOrAdd(TEXT("heavyStrike")).Level=1;
    State.LearnedSkills.AddUnique(TEXT("heavyStrike"));
    auto* Delay=IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"));
    const int PriorDelay=Delay?Delay->GetInt():0;
    if(Delay)Delay->Set(0,ECVF_SetByCode);
    ON_SCOPE_EXIT {if(Delay)Delay->Set(PriorDelay,ECVF_SetByCode);};
    Model->AdoptNetMirror(State);Pawn->DispatchBeginPlay();Model->AttachPawn(Pawn);Pawn->ApplyColdSteelProfile(Model);
    auto Reset=[&]()
    {
        Sword->CancelAction();Model->AdoptNetMirror(State);Sword->RefreshEquipment(Model);
        FlushAsyncLoading();Sword->CancelAction();Sword->ClearRingChainProgress();Sword->NextSlash=0;
    };
    int Failed=0;
    auto Check=[&](bool OK,const TCHAR* Name)
    {UE_LOG(LogTemp,Display,TEXT("RING_CHAIN_INPUT %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);Failed+=!OK;};
    uint32 Serial=0;
    auto Arm=[&]()
    {
        Sword->ConfirmRingChainHit(Item.InstanceId,++Serial);
        Sword->ConfirmRingChainHit(Item.InstanceId,Serial);
        Check(!RingChainRebound::IsReady(Pawn,Item),TEXT("one swing hitting multiple targets counts once"));
        Sword->ConfirmRingChainHit(Item.InstanceId,++Serial);
        Check(RingChainRebound::IsReady(Pawn,Item),TEXT("two ordinary contacts arm the next hold"));
    };
    auto Advance=[&](double Dt){World->TimeSeconds+=Dt;};
    Advance(10.);Reset();
    Check(Sword->bRingInputInstalled&&Sword->Animations.FindRef(RingChainSweepMotion::Release)!=nullptr&&
        Model->MasteryProgress(TEXT("heavyStrike")).Level==1&&!Pawn->IsSwitchingWeapon(),TEXT("equipped recipe and learned heavy are ready for bound input"));
    const double Base=ColdSteelMelee::Evaluate(Item,Model).HeavyChargeSeconds;
    const double LightCost=ColdSteelMelee::AttackStamina(&Item,Model);
    const double ReleaseCost=ColdSteelMelee::HeavyReleaseStamina(&Item,Model);
    const double DrawRate=Model->HeavyChargeStaminaPerSecond()*ColdSteelMelee::ItemModifiers(&Item,Model).Stamina;
    Arm();Check(Fire(IE_Pressed),TEXT("character binds the fire press"));Advance(.12);Sword->AdvanceRingPrimaryHold();
    Check(!Sword->IsHeavyCharging()&&Model->Stamina()==100.f,TEXT("tap has no charge pose or charge debit"));
    Check(Fire(IE_Released),TEXT("character binds the physical fire release"));Fire(IE_Released);
    UE_LOG(LogTemp,Display,TEXT("RING_CHAIN_TAP clip=%s next=%d paid=%.4f expected=%.4f ready=%d"),
        *Sword->CurrentClip.ToString(),Sword->NextSlash,100.-Model->Stamina(),LightCost,int32(RingChainRebound::IsReady(Pawn,Item)));
    Check(Sword->CurrentClip==TEXT("Slash1")&&Sword->NextSlash==1&&RingChainRebound::IsReady(Pawn,Item)
        &&FMath::IsNearlyEqual(100.-Model->Stamina(),LightCost,.002),TEXT("tap spends only one normal swing and preserves rebound"));
    Reset();Arm();Sword->BeginPrimaryAttack();Sword->CancelAction();Sword->ReleasePrimaryAttack();
    Check(!Sword->bAttacking&&!Sword->bCharging&&RingChainRebound::IsReady(Pawn,Item),TEXT("interrupting a pending click cannot release an attack"));
    Reset();Arm();Sword->BeginPrimaryAttack();Advance(.22);Sword->AdvanceRingPrimaryHold();
    Check(Sword->IsHeavyCharging()&&Sword->bReboundHeavyCharge&&!RingChainRebound::IsReady(Pawn,Item)
        &&FMath::IsNearlyEqual(double(Sword->RequiredChargeSeconds),Base*.5,.002),TEXT("long press consumes one window and halves the charge clock"));
    Model->TickRuntime(.02f,Pawn);
    Advance(Base*.5-.02+.0001);Sword->ReleasePrimaryAttack();Sword->ReleasePrimaryAttack();
    Check(Sword->bHeavyAttack&&Sword->CurrentClip==RingChainSweepMotion::Release,TEXT("full hold releases one horizontal heavy sweep"));
    const double Expected=1.15*(ReleaseCost+Base*DrawRate);
    UE_LOG(LogTemp,Display,TEXT("RING_CHAIN_COST base_charge=%.4f release=%.4f drain_rate=%.4f expected=%.4f paid=%.4f"),Base,ReleaseCost,DrawRate,Expected,100.-Model->Stamina());
    Check(FMath::IsNearlyEqual(100.-Model->Stamina(),Expected,.005),TEXT("complete heavy pays 115 percent including draw and release exactly once"));
    Reset();Arm();Sword->BeginPrimaryAttack();Advance(.22);Sword->AdvanceRingPrimaryHold();
    Sword->ServerHeavyChargeStartedAt=Sword->ServerHeavyChargeLastStartedAt=Sword->ChargeStartedAt;
    Sword->ServerHeavyChargeReceivedAt=Sword->ChargeStartedAt+.07;
    Sword->ServerHeavyRequiredSeconds=Sword->RequiredChargeSeconds;
    const double Full=Sword->ChargeStartedAt+Sword->RequiredChargeSeconds;
    Advance(Full+.09-World->GetTimeSeconds());Model->TickRuntime(.10f,Pawn);
    Check(!Sword->ConsumeNetworkHeavyChargeForRelease(Item.InstanceId,Full-.01,71),
        TEXT("late packet for an early release cannot be promoted to a heavy"));
    const bool Committed=Sword->ConsumeNetworkHeavyChargeForRelease(Item.InstanceId,Full,72);
    Check(Committed&&!Sword->ConsumeNetworkHeavyChargeForRelease(Item.InstanceId,Full,72)
        &&FMath::IsNearlyEqual(100.-Model->Stamina(),Expected,.005),
        TEXT("authority pays once against input timestamps excluding transit"));
    Reset();Arm();Sword->BeginPrimaryAttack();Advance(.20+Base*.5+.0001);Sword->ReleasePrimaryAttack();
    Check(Sword->bHeavyAttack&&Sword->CurrentClip==RingChainSweepMotion::Release,TEXT("timestamp release across a missed tick still recognizes a full hold"));
    Reset();Arm();Sword->BeginPrimaryAttack();Advance(.20+Base*.5-.015);Sword->ReleasePrimaryAttack();
    Check(Sword->bAttacking&&!Sword->bHeavyAttack,TEXT("release just before full follows the light attack path"));
    Reset();Arm();Sword->BeginPrimaryAttack();Advance(.20);Sword->ReleasePrimaryAttack();
    Check(Sword->bAttacking&&!Sword->bHeavyAttack&&RingChainRebound::IsReady(Pawn,Item),
        TEXT("release exactly on the tap threshold preserves the ready window"));
    for(int32 FPS:{30,60,120})
    {
        Reset();Arm();Fire(IE_Pressed);
        const double Stop=World->GetTimeSeconds()+.20+Base*.5+.0001;
        while(World->GetTimeSeconds()<Stop)
        {
            const double Dt=FMath::Min(1./FPS,Stop-World->GetTimeSeconds());
            Advance(Dt);Sword->TickComponent(float(Dt),LEVELTICK_All,nullptr);
            if(Sword->IsHeavyCharging())Model->TickRuntime(float(Dt),Pawn);
        }
        const float HeldPose=Sword->Elapsed;
        const FVector HeldTip=Sword->Viewmodel->GetSocketTransform(TEXT("Blade_Tip"),RTS_Component).GetLocation();
        Fire(IE_Released);
        const FVector ReleasedTip=Sword->Viewmodel->GetSocketTransform(TEXT("Blade_Tip"),RTS_Component).GetLocation();
        const FString Name=FString::Printf(TEXT("%d FPS holds the same chamber pose, releases into the same take and pays once"),FPS);
        Check(Sword->Viewmodel->DoesSocketExist(TEXT("Blade_Tip"))&&HeldTip.Equals(ReleasedTip,.25f)&&
            Sword->CurrentClip==RingChainSweepMotion::Release&&FMath::IsNearlyEqual(HeldPose,Sword->Elapsed,.001f)
            &&FMath::IsNearlyEqual(100.-Model->Stamina(),Expected,.01),*Name);
    }
    auto Receiver=[&](double Degrees)
    {
        auto* Target=World->SpawnActor<ABallisticAuditTarget>();
        auto* Box=Target->FindComponentByClass<UBoxComponent>();
        Box->SetBoxExtent(FVector(4,4,20));Box->SetCollisionObjectType(ECC_Pawn);
        const FVector Forward=Pawn->GetBaseAimRotation().Vector().GetSafeNormal2D();
        Target->SetActorLocation(Pawn->GetActorLocation()+Forward.RotateAngleAxis(Degrees,FVector::UpVector)*105.);
        return Target;
    };
    auto* Left=Receiver(-58.);auto* Right=Receiver(58.);auto* Behind=Receiver(180.);
    Sword->TickComponent(.22f,LEVELTICK_All,nullptr);
    const float LeftDamage=Left->Received,RightDamage=Right->Received;
    Sword->TickComponent(.08f,LEVELTICK_All,nullptr);
    UE_LOG(LogTemp,Display,TEXT("RING_CHAIN_CONTACT left=%.3f right=%.3f behind=%.3f clip=%s"),
        LeftDamage,RightDamage,Behind->Received,*Sword->CurrentClip.ToString());
    Check(LeftDamage>0.f&&RightDamage>0.f&&Behind->Received==0.f&&Left->Received==LeftDamage&&Right->Received==RightDamage,
        TEXT("220ms hitch sweeps both sides once without hitting behind"));
    Left->Destroy();Right->Destroy();Behind->Destroy();
    State.Stamina=LightCost+.01;Reset();Arm();Sword->BeginPrimaryAttack();Advance(.25);Sword->ReleasePrimaryAttack();
    Check(Sword->bAttacking&&!Sword->bHeavyAttack&&RingChainRebound::IsReady(Pawn,Item),
        TEXT("insufficient boosted release cost permits a light swing without spending the window"));
    State.Stamina=100.;
    Reset();Arm();Advance(2.79);Sword->BeginPrimaryAttack();
    Advance(.23+Base*.5);Sword->ReleasePrimaryAttack();
    Check(Sword->bHeavyAttack&&Sword->CurrentClip==RingChainSweepMotion::Release,
        TEXT("hold recognized inside three seconds can finish after the window during a hitch"));
    Reset();Arm();Advance(2.85);Sword->BeginPrimaryAttack();Advance(.22);Sword->AdvanceRingPrimaryHold();
    Check(Sword->IsHeavyCharging()&&!Sword->bReboundHeavyCharge,
        TEXT("pressing before expiry alone cannot reserve an out-of-window charge"));
    Reset();Arm();Advance(3.02);Sword->BeginPrimaryAttack();Advance(.22);Sword->AdvanceRingPrimaryHold();
    Check(Sword->IsHeavyCharging()&&!Sword->bReboundHeavyCharge&&FMath::IsNearlyEqual(double(Sword->RequiredChargeSeconds),Base,.002),
        TEXT("expired rebound uses the normal heavy duration"));
    Advance(Base-.02+.0001);Sword->ReleasePrimaryAttack();
    Check(Sword->bHeavyAttack&&Sword->CurrentClip==RingChainSweepMotion::Release&&
        FMath::IsNearlyEqual(100.-Model->Stamina(),ReleaseCost+Base*DrawRate,.005),
        TEXT("ordinary full hold uses the same sweep with its ordinary stamina cost"));
    Reset();Sword->BeginAttack();Sword->Elapsed=Sword->ContactEnd+.01f;Sword->BeginPrimaryAttack();Advance(.08);Sword->ReleasePrimaryAttack();
    Check(Sword->bQueuedAttack&&!Sword->IsHeavyCharging(),TEXT("recovery tap buffers the next regular combo"));
    Reset();Arm();Sword->BeginAttack();Sword->Elapsed=Sword->ContactEnd+.01f;Sword->BeginPrimaryAttack();Advance(.22);
    Sword->AdvanceRingPrimaryHold();Check(!Sword->bQueuedAttack&&!Sword->bCharging,TEXT("holding in recovery does not queue a light attack"));
    Sword->TickComponent(5.f,LEVELTICK_All,nullptr);Sword->TickComponent(.001f,LEVELTICK_All,nullptr);
    Check(Sword->bCharging&&Sword->bReboundHeavyCharge&&Sword->HeavyChargeFraction()<.01f,TEXT("buffered hold begins charging only after recovery"));
    UE_LOG(LogTemp,Display,TEXT("RING_CHAIN_INPUT failures=%d"),Failed);
    return Failed?1:0;
}
