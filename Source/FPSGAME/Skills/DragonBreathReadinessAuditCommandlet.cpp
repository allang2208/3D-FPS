#include "DragonBreathReadinessAuditCommandlet.h"
#include "FPSFireMagicComponent.h"
#include "FPSFireballComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffArmsMeshComponent.h"
#include "../Weapons/Staff/StaffCastMotion.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "Camera/CameraComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "UObject/UObjectGlobals.h"
#include <limits>

int32 UDragonBreathReadinessAuditCommandlet::Main(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Profile=TEXT("DragonAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("DragonBreathReadinessAudit -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("DragonReadinessAudit"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 2;
    int32 Failed=0;
    auto Check=[&](bool Passed,const TCHAR* Name,const FString& Detail=FString())
    {
        UE_LOG(LogTemp,Display,TEXT("DRAGON_READY %s %s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),Name,*Detail);
        if(!Passed)++Failed;
    };
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    auto StaffItem=Model->CreateItem(TEXT("ue_apprentice_staff"));StaffItem.Place=1;StaffItem.Cell=6;Seed.Items.Add(StaffItem);
    Seed.Attributes.FindOrAdd(TEXT("int"))=100;Seed.Health=100;Seed.Mana=10000;
    Seed.Skills.FindOrAdd(TEXT("dragonBreath")).Level=1;
    FString SourceSlot;
    if(FParse::Value(*Params,TEXT("SourceProfile="),SourceSlot))
    {
        // Read an existing save into the unique audit slot; never write to SourceSlot.
        auto* Source=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(SourceSlot,0));
        if(!Source){UE_LOG(LogTemp,Error,TEXT("DRAGON_READY source profile unavailable"));return 2;}
        Seed=Source->Profile;
        for(const auto& Item:Seed.Items)if(Item.Place==1&&ColdSteelStaff::IsStaff(Item))
        {Seed.ActiveWeaponSlot=Item.Cell;Seed.ActiveProductionTool.Reset();break;}
    }
    Check(Model->CommitState(Seed),TEXT("seed isolated staff profile"),Model->ResultMessage());
    const auto Spell=Model->FireMagicStats(TEXT("dragonBreath"));
    UE_LOG(LogTemp,Display,TEXT("DRAGON_READY profile source=%s weapon=%s mana=%.2f cost=%.2f castSpeed=%.4f cooldown=%.2f"),*SourceSlot,Model->Equipped()?*Model->Equipped()->Definition:TEXT("none"),Model->Snapshot().Mana,Spell.ManaCost,Spell.CastSpeed,Model->FireMagicCooldown(TEXT("dragonBreath")));
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();PC->Possess(Pawn);
    auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>();
    auto* Hands=Pawn->FindComponentByClass<UFPSFireballComponent>();
    auto* Staff=Pawn->FindComponentByClass<UStaffWeaponComponent>();
    // This commandlet has no game tick to dispatch the deferred load callbacks.
    IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"))->Set(0,ECVF_SetByCode);
    // No gameplay map, viewport, or whole-pawn BeginPlay is needed for this gate.
    Staff->BeginPlay();Fire->BeginPlay();FlushAsyncLoading();
    float CameraForward=0.f;FParse::Value(*Params,TEXT("CameraForward="),CameraForward);
    auto* Camera=Pawn->FindComponentByClass<UCameraComponent>();
    Camera->AddRelativeLocation(FVector(CameraForward,0,0));
    Staff->TickComponent(1.f,LEVELTICK_All,nullptr);
    Check(Model->HasEquippedStaff()&&Staff->CanBeginCast(),TEXT("staff available"));
    Check(Fire->DragonSystem!=nullptr,TEXT("authored dragon system loaded"));
    auto* Arms=Cast<UStaffArmsMeshComponent>(Staff->ArmsMesh());
    Check(Arms&&Arms->GetSkeletalMeshAsset(),TEXT("authored staff arm mesh loaded"));
    if(Arms)
    {
        auto Pose=StaffCastMotion::Swing(StaffCastMotion::ContactSeconds);
        Pose.Contact=Arms->AuthoredContactInCamera(Pose,Staff->GripVariant(),true);
        const FVector Tip=Camera->GetComponentTransform().TransformPosition(StaffCastMotion::Tip(Pose));
        const FVector Offset=Pawn->GetBaseAimRotation().UnrotateVector(Tip-Pawn->GetPawnViewLocation());
        UE_LOG(LogTemp,Display,TEXT("DRAGON_READY authored contact tip=%s eye=%s nozzle=%s"),*Tip.ToString(),*Pawn->GetPawnViewLocation().ToString(),*Offset.ToString());
    }
    Fire->Trigger(TEXT("dragonBreath"));
    UE_LOG(LogTemp,Display,TEXT("DRAGON_READY trigger committed=%s reserved=%d notice=%s"),*Fire->CommittedSkill.ToString(),Model->Snapshot().bDragonBreathReserved,*Fire->StatusText(TEXT("dragonBreath")));
    for(int32 Step=0;Step<100&&!Fire->IsDragonBreathActive();++Step)
    {
        if(Hands->GetHandPhase()==EFireballHandPhase::Releasing)
            UE_LOG(LogTemp,Display,TEXT("DRAGON_READY precontact step=%d reserved=%d nozzle=%s"),Step,Model->Snapshot().bDragonBreathReserved,*Fire->CaptureDragonNozzle().ToString());
        static_cast<UActorComponent*>(Hands)->TickComponent(.02f,LEVELTICK_All,nullptr);
        Fire->TickComponent(.02f,LEVELTICK_All,nullptr);
        if(Fire->CommittedSkill.IsNone()&&Fire->QueuedSkill.IsNone())break;
    }
    Check(Fire->IsDragonBreathActive(),TEXT("actual gesture contact starts dragon"),FString::Printf(TEXT("reserved=%d nozzle=%s notice=%s"),Model->Snapshot().bDragonBreathReserved,*Fire->CaptureDragonNozzle().ToString(),*Fire->StatusText(TEXT("dragonBreath"))));
    Fire->ClearEffects();
    for(const FVector Bad:{FVector(400,0,0),FVector(-10,0,0),FVector(std::numeric_limits<double>::quiet_NaN(),0,0)})
    {
        FString Failure;
        Check(!Fire->StartDragonBreath(Spell,false,0,Bad,&Failure)&&Failure==TEXT("龙息喷口位置异常"),
            TEXT("invalid nozzle still rejected"),Bad.ToString());
    }
    Staff->EndPlay(EEndPlayReason::Destroyed);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    UE_LOG(LogTemp,Display,TEXT("DRAGON_READY complete failures=%d profile=%s"),Failed,*Profile);
    return Failed?1:0;
}
