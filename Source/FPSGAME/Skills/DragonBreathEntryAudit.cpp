// Opt-in real-world first-cast regression. Never runs during ordinary gameplay.
#include "FPSFireMagicComponent.h"
#include "DragonBreathEntryAuditDiagnostics.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraSystemInstanceController.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

#if WITH_EDITOR
namespace
{
struct FDragonEntryAudit : TSharedFromThis<FDragonEntryAudit>
{
    TWeakObjectPtr<UWorld> World;
    FDelegateHandle TickHandle;
    FString Output;
    TSharedRef<FJsonObject> Result=MakeShared<FJsonObject>();
    double Started=FPlatformTime::Seconds(),Entry=-1,Ready=-1,Triggered=-1,Released=-1,FinishAt=-1;
    double NextLog=0;
    float ManaBefore=0,MaxPreparationFrame=0;
    int32 Frames=0,FreePreparationFrames=0,BlockedAfterEntry=0,Shot=0,Level=1;
    bool Seeded=false,Early=false,Requested=false,WasQueued=false,Reused=false;
    TWeakObjectPtr<UNiagaraComponent> PreparedFX;

    UNiagaraComponent* FindFX(AActor* Pawn) const
    {
        TArray<UNiagaraComponent*> Components;Pawn->GetComponents(Components);
        for(auto* FX:Components)if(FX->GetAsset()&&FX->GetAsset()->GetPathName().Contains(TEXT("/DragonBreath20261013/Range2x20261019/NS_DragonVolume")))return FX;
        return nullptr;
    }

    void Capture(const TCHAR* Name)
    {
        FScreenshotRequest::RequestScreenshot(Output/Name,true,false);
        UE_LOG(LogTemp,Display,TEXT("DRAGON_ENTRY_CAPTURE %s"),Name);
    }

    void Finish(bool Passed,const FString& Reason)
    {
        Result->SetBoolField(TEXT("state_passed"),Passed);
        Result->SetStringField(TEXT("reason"),Reason);
        Result->SetBoolField(TEXT("visual_review_required"),true);
        Result->SetNumberField(TEXT("entry_seconds"),Entry);
        Result->SetNumberField(TEXT("ready_seconds"),Ready);
        Result->SetNumberField(TEXT("first_input_seconds"),Triggered);
        Result->SetNumberField(TEXT("first_release_seconds"),Released);
        Result->SetNumberField(TEXT("frames_observed"),Frames);
        Result->SetNumberField(TEXT("input_free_preparation_frames"),FreePreparationFrames);
        Result->SetNumberField(TEXT("input_blocked_after_entry_frames"),BlockedAfterEntry);
        Result->SetNumberField(TEXT("max_preparation_frame_ms"),MaxPreparationFrame*1000.);
        Result->SetBoolField(TEXT("early_request"),Early);
        Result->SetBoolField(TEXT("request_was_queued"),WasQueued);
        Result->SetBoolField(TEXT("reused_prepared_component"),Reused);
        Result->SetNumberField(TEXT("dragon_level"),Level);
        FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json,*(Output/TEXT("result.json")));
        UE_LOG(LogTemp,Display,TEXT("DRAGON_ENTRY_%s %s entry=%.3f ready=%.3f release=%.3f blocked=%d"),
            Passed?TEXT("PASS"):TEXT("FAIL"),*Reason,Entry,Ready,Released,BlockedAfterEntry);
        FWorldDelegates::OnWorldPostActorTick.Remove(TickHandle);
        FPlatformMisc::RequestExitWithStatus(false,Passed?0:1);
    }

    void Tick(float Delta)
    {
        auto* W=World.Get();if(!W)return;
        const double Now=FPlatformTime::Seconds()-Started;++Frames;
        if(Now>150.){Finish(false,TEXT("background preparation / first cast timed out"));return;}
        auto* PC=W->GetFirstPlayerController();
        auto* Pawn=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
        auto* GI=W->GetGameInstance();
        auto* Model=GI?GI->GetSubsystem<UColdSteelStatusModel>():nullptr;
        auto* Loading=GI?GI->GetSubsystem<UTransitLoadingSubsystem>():nullptr;
        auto* Fire=Pawn?Pawn->FindComponentByClass<UFPSFireMagicComponent>():nullptr;
        if(!Pawn||!Fire||!Model||!Loading)return;
        if(!Seeded)
        {
            if(!Model->IsAudit()||!Model->ProfileSlot().StartsWith(TEXT("ColdSteel_DragonEntryAudit_")))
            {Finish(false,TEXT("requires isolated DragonEntryAudit profile"));return;}
            auto P=Model->Snapshot();P.Items.Reset();P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();
            auto Staff=Model->CreateItem(TEXT("ue_apprentice_staff"));Staff.Place=1;Staff.Cell=6;P.Items.Add(Staff);
            P.Attributes.FindOrAdd(TEXT("intt"))=100;P.Attributes.FindOrAdd(TEXT("wis"))=100;
            P.Mana=10000;P.Health=1000;
            int32 Learned=0;
            for(FName Skill:Model->SkillCatalog())
            {
                P.Skills.FindOrAdd(Skill).Level=1;++Learned;
            }
            P.Skills.FindOrAdd(TEXT("dragonBreath")).Level=Level;
            if(!Model->CommitState(P)){Finish(false,Model->ResultMessage());return;}
            Pawn->SetCanBeDamaged(false);
            PC->SetControlRotation(FRotator(-3,0,0));
            Result->SetStringField(TEXT("profile"),Model->ProfileSlot());
            Result->SetStringField(TEXT("map"),W->GetMapName());
            Result->SetNumberField(TEXT("learned_skills"),Learned);
            Seeded=true;
            UE_LOG(LogTemp,Display,TEXT("DRAGON_ENTRY_SEEDED profile=%s skills=%d level=%d"),*Model->ProfileSlot(),Learned,Level);
            return;
        }
        const bool Free=!Loading->IsHoldingGameplayInput()&&!W->IsPaused()&&!PC->IsMoveInputIgnored()&&!PC->IsLookInputIgnored();
        if(Free&&Entry<0){Entry=Now;UE_LOG(LogTemp,Display,TEXT("DRAGON_ENTRY_INPUT_FREE t=%.3f"),Now);}
        if(Entry>=0&&!Free)++BlockedAfterEntry;
        auto* FX=FindFX(Pawn);
        const auto Instance=FX?FX->GetSystemInstanceController():FNiagaraSystemInstanceControllerPtr();
        const bool IsReady=FX&&FX->IsActive()&&FX->IsPaused()&&FX->GetAsset()->IsReadyToRun()
            &&!FX->IsPSOPrecaching()&&Instance&&Instance->GetAreDataInterfacesInitialized()&&!Instance->IsPendingSpawn();
        if(Ready<0&&!Fire->IsDragonBreathActive())
        {
            MaxPreparationFrame=FMath::Max(MaxPreparationFrame,Delta);
            if(Free)++FreePreparationFrames;
            if(IsReady)
            {
                Ready=Now;PreparedFX=FX;Result->SetNumberField(TEXT("prepared_age"),Instance->GetAge());
                UE_LOG(LogTemp,Display,TEXT("DRAGON_ENTRY_READY t=%.3f age=%.3f"),Now,Instance->GetAge());
                if(!Requested){Capture(TEXT("before-first-cast.png"));}
            }
        }
        // In the early-input case, observe the hidden instance while it is still
        // initializing. Never force load, compile, reset or activate any FX here.
        auto* Staff=Pawn->FindComponentByClass<UStaffWeaponComponent>();
        if(!Requested&&Free&&Staff&&Staff->CanBeginCast()&&
            ((Early&&FX&&!IsReady)||(Ready>=0&&Now-Ready>=.4)))
        {
            PreparedFX=FX;ManaBefore=Model->Snapshot().Mana;Triggered=Now;Requested=true;
            if(Ready<0)Capture(TEXT("before-first-cast.png"));
            Fire->Trigger(TEXT("dragonBreath"));
            WasQueued=Fire->HasQueuedAction();
            Result->SetNumberField(TEXT("mana_before_request"),ManaBefore);
            Result->SetNumberField(TEXT("mana_after_request"),Model->Snapshot().Mana);
            UE_LOG(LogTemp,Display,TEXT("DRAGON_ENTRY_FIRST_INPUT t=%.3f queued=%d status=%s"),Now,WasQueued,*Fire->StatusText(TEXT("dragonBreath")));
        }
        if(Requested&&Fire->IsDragonBreathActive()&&Released<0)
        {
            Released=Now;Reused=PreparedFX.Get()==FX;
            Result->SetNumberField(TEXT("mana_on_release"),Model->Snapshot().Mana);
            Result->SetNumberField(TEXT("cooldown_on_release"),Model->FireMagicCooldown(TEXT("dragonBreath")));
            UE_LOG(LogTemp,Display,TEXT("DRAGON_ENTRY_FIRST_RELEASE t=%.3f active=%d visible=%d paused=%d reuse=%d"),Now,FX&&FX->IsActive(),FX&&FX->IsVisible(),FX&&FX->IsPaused(),Reused);
        }
        if(Released>=0)
        {
            if(!FX||!FX->IsActive()||FX->IsPaused()||!FX->IsVisible())
            {Finish(false,TEXT("first cast has no running visible volume"));return;}
            const double Age=Now-Released;
            const double Times[]={.10,.40,1.0,2.0};
            if(Shot<4&&Age>=Times[Shot]&&!FScreenshotRequest::IsScreenshotRequested())
            {
                if(Shot==2&&FParse::Param(FCommandLine::Get(),TEXT("DragonVolumeDiagnostics")))
                    CaptureDragonEntryVolume(FX,Output/TEXT("volume-first-cast.json"));
                const FString Name=FString::Printf(TEXT("first-cast-%02d.png"),Shot++);Capture(*Name);
                if(Shot==4)FinishAt=Now+1.;
            }
            if(FinishAt>0&&Now>=FinishAt)
            {
                Result->SetNumberField(TEXT("volume_age_on_finish"),Instance?Instance->GetAge():-1.);
                Finish(Entry>=0&&Reused&&FreePreparationFrames>0&&BlockedAfterEntry==0&&
                    Model->FireMagicCooldown(TEXT("dragonBreath"))>0,
                    TEXT("entry unlocked during background preparation; first input released with retained volume"));return;
            }
        }
        if(Now>=NextLog)
        {
            NextLog=Now+5.;UE_LOG(LogTemp,Display,TEXT("DRAGON_ENTRY_WAIT t=%.3f fx=%d active=%d paused=%d age=%.3f status=%s"),
                Now,FX!=nullptr,FX&&FX->IsActive(),FX&&FX->IsPaused(),Instance?Instance->GetAge():-1.,*Fire->StatusText(TEXT("dragonBreath")));
        }
    }
};

FAutoConsoleCommandWithWorld DragonEntryAuditCommand(TEXT("fps.DragonEntryAudit"),
    TEXT("Explicit isolated-profile Dragon Breath entry and first-cast regression; writes screenshots and exits."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
    {
        if(!World||!World->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("DragonEntryAudit")))return;
        auto Run=MakeShared<FDragonEntryAudit>();Run->World=World;
        Run->Early=FParse::Param(FCommandLine::Get(),TEXT("DragonEarlyInput"));
        FParse::Value(FCommandLine::Get(),TEXT("DragonAuditLevel="),Run->Level);
        Run->Level=FMath::Clamp(Run->Level,1,20);
        Run->Output=FPaths::ProjectSavedDir()/TEXT("DragonEntryAudit")/FGuid::NewGuid().ToString(EGuidFormats::Digits);
        FParse::Value(FCommandLine::Get(),TEXT("DragonAuditOutput="),Run->Output);
        IFileManager::Get().MakeDirectory(*Run->Output,true);
        Run->TickHandle=FWorldDelegates::OnWorldPostActorTick.AddLambda([Run](UWorld* W,ELevelTick,float Delta)
        {if(Run->World.Get()==W)Run->Tick(Delta);});
        UE_LOG(LogTemp,Display,TEXT("DRAGON_ENTRY_STARTED output=%s"),*Run->Output);
    }));
}
#endif
