// Explicit user-requested visual diagnosis, enabled only in an isolated audit run.
#include "FPSFireMagicComponent.h"
#include "FlameArmorAttachments.h"
#include "../FPSGAMECharacter.h"
#include "../Production/ProductionToolComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Components/SceneComponent.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "NiagaraComponent.h"
#include "NiagaraEmitterInstance.h"
#include "NiagaraSystem.h"
#include "NiagaraSystemInstance.h"
#include "NiagaraSystemInstanceController.h"
#include "NiagaraSimCache.h"
#include "NiagaraSimCacheFunctionLibrary.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

#if WITH_EDITOR
namespace
{
struct FHammerFlameVisualReview
{
    TWeakObjectPtr<UWorld> World;
    bool Finished=false;
    FString Output,Weapon=TEXT("ue_steel_warhammer");
    double Started=FPlatformTime::Seconds(),EquippedAt=-1,ActiveAt=-1,NextLog=0,LastTrigger=-10;
    bool Seeded=false,Triggered=false,Attack=false,Released=false,Inspect=false,Motion=false;
    int32 Shot=0,MotionShot=0;
    double NextMotion=2.5;
    TArray<TSharedPtr<FJsonValue>> Samples;

    void Finish(const FString& Reason)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("reason"),Reason);
        R->SetStringField(TEXT("weapon"),Weapon);R->SetArrayField(TEXT("samples"),Samples);
        R->SetBoolField(TEXT("visual_review_required"),true);
        FString Json;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json,*(Output/TEXT("runtime.json")));
        Finished=true;
        UE_LOG(LogTemp,Display,TEXT("HAMMER_REVIEW_FINISHED %s"),*Reason);
        FPlatformMisc::RequestExitWithStatus(false,Shot>=8?0:1);
    }

    void Capture(AFPSGAMECharacter* Pawn,const FString& Name)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("image"),Name);
        R->SetNumberField(TEXT("time"),FPlatformTime::Seconds()-Started);
        FFlameArmorAttachments Spans;FlameArmorAttachments::Gather(Pawn,Spans);
        R->SetNumberField(TEXT("attachments"),Spans.Num());
        TArray<TSharedPtr<FJsonValue>> Effects;
        TArray<UNiagaraComponent*> Components;Pawn->GetComponents(Components);
        for(auto* FX:Components)
        {
            if(!FX->GetAsset()||!FX->GetAsset()->GetPathName().Contains(TEXT("HammerSurface")))continue;
            bool ParameterValid=false;
            auto E=MakeShared<FJsonObject>();E->SetStringField(TEXT("asset"),FX->GetAsset()->GetPathName());
            E->SetBoolField(TEXT("active"),FX->IsActive());E->SetBoolField(TEXT("visible"),FX->IsVisible());
            E->SetBoolField(TEXT("paused"),FX->IsPaused());E->SetNumberField(TEXT("fade"),FX->GetVariableFloat(TEXT("User.Fade"),ParameterValid));
            E->SetStringField(TEXT("transform"),FX->GetComponentTransform().ToString());
            E->SetStringField(TEXT("triangle_a0"),FX->GetVariableVec3(TEXT("User.HammerA0"),ParameterValid).ToString());
            E->SetStringField(TEXT("triangle_b0"),FX->GetVariableVec3(TEXT("User.HammerB0"),ParameterValid).ToString());
            if(Spans.Num())
            {
                E->SetStringField(TEXT("mesh"),Spans[0].Geometry.IsValid()?Spans[0].Geometry->GetPathName():TEXT("none"));
                E->SetNumberField(TEXT("anchor_error_cm"),FVector::Dist(FX->GetComponentLocation(),Spans[0].Base));
            }
            TArray<TSharedPtr<FJsonValue>> Counts,Bounds;
            if(auto C=FX->GetSystemInstanceController())if(auto* I=C->GetSystemInstance_Unsafe())
            {
                E->SetNumberField(TEXT("system_age"),I->GetAge());
                for(const auto& Emit:I->GetEmitters())
                {
                    Counts.Add(MakeShared<FJsonValueNumber>(Emit->GetNumParticles()));
                    Bounds.Add(MakeShared<FJsonValueString>(Emit->GetBounds().ToString()));
                }
            }
            E->SetArrayField(TEXT("particles"),Counts);E->SetArrayField(TEXT("bounds"),Bounds);
            auto* Cache=UNiagaraSimCacheFunctionLibrary::CreateNiagaraSimCache(FX);UNiagaraSimCache* Captured=nullptr;
            if(UNiagaraSimCacheFunctionLibrary::CaptureNiagaraSimCacheImmediate(Cache,FNiagaraSimCacheCreateParameters(),FX,Captured))
            {
                TArray<TSharedPtr<FJsonValue>> ParticleRows;
                for(FName Emitter:Cache->GetEmitterNames())
                {
                    TArray<FVector> Positions,Anchors,Directions;TArray<FLinearColor> Colors;TArray<FVector2D> Sizes,UV;
                    Cache->ReadPositionAttribute(Positions,TEXT("Position"),Emitter,false);
                    Cache->ReadPositionAttribute(Anchors,TEXT("HammerAnchor"),Emitter,false);
                    Cache->ReadVectorAttribute(Directions,TEXT("SpriteAlignment"),Emitter);
                    Cache->ReadColorAttribute(Colors,TEXT("Color"),Emitter);Cache->ReadVector2Attribute(Sizes,TEXT("SpriteSize"),Emitter);
                    Cache->ReadVector2Attribute(UV,TEXT("UVScale"),Emitter);
                    for(int32 I=0;I<FMath::Min(Positions.Num(),6);++I)
                    {
                        auto P=MakeShared<FJsonObject>();P->SetStringField(TEXT("emitter"),Emitter.ToString());
                        P->SetStringField(TEXT("position"),Positions[I].ToString());
                        if(Anchors.IsValidIndex(I))P->SetStringField(TEXT("anchor"),Anchors[I].ToString());
                        if(Colors.IsValidIndex(I))P->SetStringField(TEXT("color"),Colors[I].ToString());
                        if(Sizes.IsValidIndex(I))P->SetStringField(TEXT("size"),Sizes[I].ToString());
                        if(UV.IsValidIndex(I))P->SetStringField(TEXT("uv"),UV[I].ToString());
                        if(Directions.IsValidIndex(I))P->SetStringField(TEXT("direction"),Directions[I].ToString());
                        ParticleRows.Add(MakeShared<FJsonValueObject>(P));
                    }
                }
                E->SetArrayField(TEXT("particle_samples"),ParticleRows);
            }
            Effects.Add(MakeShared<FJsonValueObject>(E));
        }
        R->SetArrayField(TEXT("effects"),Effects);Samples.Add(MakeShared<FJsonValueObject>(R));
        FScreenshotRequest::RequestScreenshot(Output/Name,false,false);
        UE_LOG(LogTemp,Display,TEXT("HAMMER_REVIEW_CAPTURE %s effects=%d"),*Name,Effects.Num());
    }

    void Tick(float Delta)
    {
        auto* W=World.Get();if(!W)return;
        const double Now=FPlatformTime::Seconds()-Started;
        if(Now>150.){Finish(TEXT("Timed out waiting for equipment or flame activation"));return;}
        auto* PC=W->GetFirstPlayerController();auto* Pawn=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
        auto* Model=W->GetGameInstance()?W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
        auto* Tool=Pawn?Pawn->FindComponentByClass<UProductionToolComponent>():nullptr;
        auto* Fire=Pawn?Pawn->FindComponentByClass<UFPSFireMagicComponent>():nullptr;
        if(!PC||!Pawn||!Model||!Tool||!Fire)
        {
            if(Now>=NextLog){NextLog=Now+5.;UE_LOG(LogTemp,Display,TEXT("HAMMER_REVIEW_SETUP pc=%d pawn=%d model=%d tool=%d fire=%d"),PC!=nullptr,Pawn!=nullptr,Model!=nullptr,Tool!=nullptr,Fire!=nullptr);}
            return;
        }
        if(auto* Loading=W->GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();Loading&&Loading->IsHoldingGameplayInput())Loading->ReleaseToGameplay();
        if(W->IsPaused())PC->SetPause(false);
        if(!Seeded)
        {
            if(!Model->IsAudit()||!Model->ProfileSlot().StartsWith(TEXT("ColdSteel_HammerFlameAudit_")))
            {Finish(TEXT("Requires isolated HammerFlameAudit profile"));return;}
            auto P=Model->Snapshot();P.Items.Reset();P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();P.DungeonRun={};
            auto Item=Model->CreateItem(Weapon);Item.Place=1;Item.Cell=6;P.Items.Add(Item);
            P.Skills.FindOrAdd(TEXT("flameArmor")).Level=1;P.FlameArmorCooldown=P.FlameArmorCooldownDuration=0;
            P.Attributes.FindOrAdd(TEXT("intt"))=100;P.Attributes.FindOrAdd(TEXT("wis"))=100;
            P.Mana=10000;P.Health=1000;P.Stamina=150;
            if(!Model->CommitState(P)){Finish(Model->ResultMessage());return;}
            Pawn->SetCanBeDamaged(false);PC->SetControlRotation(FRotator(-3,0,0));Seeded=true;
            UE_LOG(LogTemp,Display,TEXT("HAMMER_REVIEW_SEEDED %s"),*Model->ProfileSlot());
        }
        if(EquippedAt<0&&Tool->IsWarhammerEquipped()&&!Tool->IsBusy())EquippedAt=Now;
        if(!Triggered&&EquippedAt>=0&&Now-EquippedAt>4.)
        {
            Capture(Pawn,TEXT("00-before.png"));Fire->Trigger(TEXT("flameArmor"));Triggered=true;LastTrigger=Now;
            UE_LOG(LogTemp,Display,TEXT("HAMMER_REVIEW_TRIGGER %s"),*Fire->StatusText(TEXT("flameArmor")));
        }
        if(Triggered&&ActiveAt<0&&Fire->ArmorRemaining()<=0&&Now-LastTrigger>2.
            &&!Fire->HasQueuedAction()&&Fire->UnreleasedSkill().IsNone())
        {Fire->Trigger(TEXT("flameArmor"));LastTrigger=Now;}
        if(Triggered&&ActiveAt<0&&Fire->ArmorRemaining()>0)ActiveAt=Now;
        if(ActiveAt>=0)
        {
            const double Age=Now-ActiveAt;
            if(Age>=3.&&Age<5.)PC->SetControlRotation(FRotator(-3+12*FMath::Sin((Age-3.)*6.),65*FMath::Sin((Age-3.)*7.),0));
            else PC->SetControlRotation(FRotator(-3,0,0));
            if(Age>=5.5&&!Attack){Tool->BeginPrimaryAttack();Attack=true;}
            if(Age>=5.65&&!Released){Tool->ReleasePrimaryAttack();Released=true;}
            if(Age>=8.&&!Inspect){Inspect=Tool->BeginInspect(false);}
            const double Times[]={.6,1.3,2.3,3.2,3.8,5.7,6.,7.5,8.5,9.2,10.};
            if(Shot<UE_ARRAY_COUNT(Times)&&Age>=Times[Shot]&&!FScreenshotRequest::IsScreenshotRequested())
                Capture(Pawn,FString::Printf(TEXT("%02d-active.png"),++Shot));
            if(Motion&&Age>=NextMotion&&Age<7.5&&!FScreenshotRequest::IsScreenshotRequested())
            {
                Capture(Pawn,FString::Printf(TEXT("motion-%03d.png"),++MotionShot));
                NextMotion=Age+.05;
            }
            if(Age>11.){Finish(TEXT("Captured idle, rapid camera turn, hammer attack and inspect"));return;}
        }
        if(Now>=NextLog)
        {
            NextLog=Now+5.;UE_LOG(LogTemp,Display,TEXT("HAMMER_REVIEW_WAIT t=%.1f equipped=%d busy=%d armor=%.2f status=%s"),
                Now,Tool->IsWarhammerEquipped(),Tool->IsBusy(),Fire->ArmorRemaining(),*Fire->StatusText(TEXT("flameArmor")));
        }
    }
};
FAutoConsoleCommand HammerFlameReviewCommand(TEXT("fps.HammerFlameReview"),
    TEXT("Opt-in hammer flame screenshot review using an isolated audit profile."),
    FConsoleCommandDelegate::CreateLambda([]()
    {
        if(!FParse::Param(FCommandLine::Get(),TEXT("HammerFlameVisualAudit")))return;
        // Startup ExecCmds has no console world yet. Resolve the actual game
        // world on the next engine tick, rather than silently dropping it.
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([](float)
        {
        UWorld* World=nullptr;
        if(GEngine)for(const auto& Context:GEngine->GetWorldContexts())
            if(Context.World()&&Context.World()->IsGameWorld()&&Context.World()->GetFirstPlayerController()){World=Context.World();break;}
        if(!World)return true;
        auto Run=MakeShared<FHammerFlameVisualReview>();Run->World=World;
        Run->Output=FPaths::ProjectSavedDir()/TEXT("HammerFlameReview");
        FParse::Value(FCommandLine::Get(),TEXT("HammerReviewOutput="),Run->Output);
        FParse::Value(FCommandLine::Get(),TEXT("HammerReviewWeapon="),Run->Weapon);
        Run->Motion=FParse::Param(FCommandLine::Get(),TEXT("HammerReviewMotion"));
        IFileManager::Get().MakeDirectory(*Run->Output,true);
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Run](float Delta){Run->Tick(Delta);return !Run->Finished;}));
        UE_LOG(LogTemp,Display,TEXT("HAMMER_REVIEW_STARTED %s"),*Run->Output);
        return false;
        }));
    }));
}
#endif
