#include "WarhammerSprintAuditCommandlet.h"
#include "ProductionToolComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "ProductionToolMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SceneComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"

int32 UWarhammerSprintAuditCommandlet::Main(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("WarhammerSprintAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("WarhammerSprintAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("WarhammerSprintAuditWorld"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.ProductionSupplyVersion=1;Seed.Stamina=150;Seed.bSprintExhausted=false;
    auto Item=Model->CreateItem(TEXT("ue_steel_warhammer"));Item.Place=1;Item.Cell=6;Seed.Items.Add(Item);
    if(FParse::Param(*Params,TEXT("UserEquipment")))
        if(auto* Saved=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(TEXT("ColdSteelPlayer_PIE_0_A"),0)))
        {
            Seed=Saved->Profile;Seed.Stamina=150;Seed.bSprintExhausted=false;
            Seed.bQuickCombatReserved=false;Seed.QuickCombatCooldown=Seed.QuickCombatCooldownDuration=0.f;
            // The user may have switched weapons before exiting PIE. Retain
            // their armor/skills/hammer modifications, but equip the hammer in
            // this isolated copy rather than testing their last firearm.
            const auto* SavedHammer=Seed.Items.FindByPredicate([](const FColdSteelItem& I){return ColdSteelInventory::IsTwoHandedBlunt(I);});
            FColdSteelItem Selected=SavedHammer?*SavedHammer:Item;
            Seed.Items.RemoveAll([&](const FColdSteelItem& I){return (I.Place==1&&I.Cell==6)||I.InstanceId==Selected.InstanceId;});
            Selected.Place=1;Selected.Cell=6;Seed.Items.Add(Selected);Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
        }
    Seed.Skills.FindOrAdd(TEXT("dashAttack")).Level=1;
    if(!Model->CommitState(Seed))return 2;
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();PC->Possess(Pawn);PC->bShowMouseCursor=false;
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();
    // This commandlet has no engine tick to dispatch deferred load delegates.
    auto* Delay=IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"));
    const int32 SavedDelay=Delay?Delay->GetInt():1;
    if(Delay)Delay->Set(0,ECVF_SetByCode);
    Tool->InitializeLocalTool();
    if(Tool->LoadHandle)Tool->LoadHandle->WaitUntilComplete();
    if(Delay)Delay->Set(SavedDelay,ECVF_SetByCode);
    if(FParse::Param(*Params,TEXT("QuickCombatOnly")))
    {
        // Explicit diagnosis only: this temporary profile never touches the
        // user's inventory, and the ordinary sprint audit is not executed.
        auto* Local=NewObject<ULocalPlayer>(GEngine);
        GI->AddLocalPlayer(Local,FPlatformUserId::CreateFromInternalId(0));PC->SetPlayer(Local);
        if(FParse::Param(*Params,TEXT("UserEquipment")))
        {
            if(Delay)Delay->Set(0,ECVF_SetByCode);
            Pawn->DispatchBeginPlay();
            if(Tool->LoadHandle)Tool->LoadHandle->WaitUntilComplete();
            if(Delay)Delay->Set(SavedDelay,ECVF_SetByCode);
        }
        Model->AttachPawn(Pawn);Pawn->InterruptActionsForPriority(false);
        if(FParse::Param(*Params,TEXT("CachedASH12")))Pawn->bUseASH12=true;
        auto* Quick=Pawn->QuickCombatPistol.Get();
        FString Report;int32 Failed=0;FString Output;
        FParse::Value(*Params,TEXT("Report="),Output);
        if(Output.IsEmpty())Output=FPaths::ProjectSavedDir()/TEXT("WarhammerQuickCombatAudit.txt");
        const auto Record=[&](const TCHAR* Stage)
        {
            const FTransform Wpn=Tool->Viewmodel->GetSocketTransform(TEXT("WPN_root"),RTS_Component);
            auto* Single=Tool->Viewmodel->GetSingleNodeInstance();
            const FString Line=FString::Printf(TEXT("%s style=%d phase=%d age=%.6f active=%d equipped=%d usable=%d ready=%d clip=%s pose=%.6f stamina=%.3f wpn=%s scale=%s sampled=%s\n"),
                Stage,int32(Quick->GetStyle()),int32(Quick->GetPhase()),Quick->GetActionAge(),Tool->IsQuickCombatActive(),
                Tool->IsWarhammerEquipped(),Tool->CanUse(),Tool->HasReadyPresentation(),*GetNameSafe(Tool->CurrentMotion),
                Tool->Viewmodel?Tool->Viewmodel->GetPosition():-1.f,Model->Stamina(),*Wpn.GetLocation().ToString(),*Wpn.GetScale3D().ToString(),
                Single?*GetNameSafe(Single->GetCurrentAsset()):TEXT("none"));
            Report+=Line;UE_LOG(LogTemp,Display,TEXT("WARHAMMER_QUICK %s"),*Line);
        };
        Record(TEXT("ready"));
        Report+=FString::Printf(TEXT("route pawn=%s expected=%s gate=%d reserved=%.3f\n"),*GetPathNameSafe(UGameplayStatics::GetPlayerPawn(Model,0)),*Pawn->GetPathName(),Pawn->CanStartQuickCombatPriority(),Model->QuickCombatCooldown());
        const bool Started=Model->TriggerQuickCombat();Failed+=!Started;
        Record(Started?TEXT("begin accepted"):TEXT("begin rejected"));
        bool Advanced=false,Sampled=false;
        for(int32 Frame=0;Started&&Frame<36;++Frame)
        {
            Pawn->Tick(1.f/60.f);Record(TEXT("after owner"));
            Tool->TickComponent(1.f/60.f,LEVELTICK_All,&Tool->PrimaryComponentTick);Record(TEXT("after tool"));
            Advanced|=Quick->GetActionAge()>.04f;
            Sampled|=Tool->CurrentMotion==Tool->Motions.FindRef(TEXT("QuickCombat"))&&Tool->Viewmodel->GetPosition()>.04f;
        }
        Failed+=!Advanced;Failed+=!Sampled;Failed+=Quick->IsOccupyingLeftHand();
        Report+=FString::Printf(TEXT("RESULT started=%d advanced=%d sampled=%d finished=%d failures=%d\n"),Started,Advanced,Sampled,!Quick->IsOccupyingLeftHand(),Failed);
        FFileHelper::SaveStringToFile(Report,*Output);
        GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
        return Failed?1:0;
    }
    auto* Move=CastChecked<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
    Pawn->bSprintHeld=Pawn->bIsSprinting=true;Move->bWantsToSprint=true;
    Move->SetMovementMode(MOVE_Walking);Move->Velocity=FVector(700,0,0);
    FString Report;int32 Failed=0;
    auto Check=[&](bool OK,const TCHAR* Name)
    {
        Failed+=!OK;
        const FString Line=FString::Printf(TEXT("%s %s seconds=%.6f ready=%.6f busy=%d usable=%d sprint=%d local=%d equip=%.3f elapsed=%.3f presentation=%d\n"),
            OK?TEXT("PASS"):TEXT("FAIL"),Name,Tool->BluntSprintSeconds,Tool->DashReadyFraction(),
            Tool->IsBusy(),Tool->CanUse(),Pawn->IsSprinting(),Pawn->IsLocallyControlled(),
            Tool->EquipElapsed,Tool->Elapsed,Tool->HasReadyPresentation());
        Report+=Line;UE_LOG(LogTemp,Display,TEXT("WARHAMMER_SPRINT %s"),*Line);
    };
    Check(Tool->HasReadyPresentation(),TEXT("formal hammer mesh, grip and clips finish loading"));
    // Read the user's recent PIE prerequisite fields without altering that save.
    if(auto* Saved=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(TEXT("ColdSteelPlayer_PIE_0_A"),0)))
    {
        const auto& State=Saved->Profile;
        const auto* SavedItem=State.Items.FindByPredicate([&](const auto& I){return I.Place==1&&I.Cell==State.ActiveWeaponSlot;});
        const FString Line=FString::Printf(TEXT("SAVED active=%s blunt=%d stamina=%.2f exhausted=%d dash_level=%d\n"),
            SavedItem?*SavedItem->Definition:TEXT("none"),SavedItem&&ColdSteelInventory::IsTwoHandedBlunt(*SavedItem),
            State.Stamina,State.bSprintExhausted,State.Skills.FindRef(TEXT("dashAttack")).Level);
        Report+=Line;UE_LOG(LogTemp,Display,TEXT("WARHAMMER_SPRINT %s"),*Line);
    }
    for(int32 Frame=0;Frame<180;++Frame)
    {
        Tool->AdvanceActionBeforeCamera(1.f/60.f);
        Tool->TickComponent(1.f/60.f,LEVELTICK_All,&Tool->PrimaryComponentTick);
    }
    Check(Tool->DashReadyFraction()>=1.f-UE_SMALL_NUMBER,TEXT("baseline grounded sprint reaches readiness"));
    Tool->BluntSprintSeconds=0.f;
    for(int32 Frame=0;Frame<75;++Frame)
    {
        Pawn->MPSetAutoInput(true,true);Move->Velocity=FVector(700,0,0);
        Pawn->Tick(1.f/60.f);
        Tool->TickComponent(1.f/60.f,LEVELTICK_All,&Tool->PrimaryComponentTick);
    }
    Check(Tool->DashReadyFraction()>=1.f-UE_SMALL_NUMBER,TEXT("actual character and tool tick retain sprint readiness"));
    Tool->bBluntWhirlwind=true;Tool->FinishBluntWhirlwind();
    for(int32 Frame=0;Frame<75;++Frame)Tool->AdvanceActionBeforeCamera(1.f/60.f);
    Check(Tool->DashReadyFraction()>=1.f-UE_SMALL_NUMBER,TEXT("readiness after whirlwind finish"));
    Pawn->bSprintHeld=false;Tool->AdvanceActionBeforeCamera(1.f/60.f);
    Check(Tool->DashReadyFraction()==0.f,TEXT("release Shift clears readiness"));
    FFileHelper::SaveStringToFile(Report,*(FPaths::ProjectSavedDir()/TEXT("WarhammerSprintAudit.txt")));
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failed?1:0;
}
