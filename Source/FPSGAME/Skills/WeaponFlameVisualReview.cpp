// Opt-in visual diagnosis. Never runs outside an explicitly isolated audit profile.
#if WITH_EDITOR
#include "FPSFireMagicComponent.h"
#include "FlameArmorAttachments.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Components/InputComponent.h"
#include "Components/SceneComponent.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
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
#include "UObject/UObjectIterator.h"
#include "UnrealClient.h"

namespace
{
struct FWeaponFlameVisualReview
{
    TWeakObjectPtr<UWorld> World;
    FString Output,CaseOutput;
    TArray<TSharedPtr<FJsonValue>> Cases,Results,Samples;
    int32 Index=0,Shot=0;
    double Started=FPlatformTime::Seconds(),CaseAt=-1,ReadyAt=-1,ActiveAt=-1,LastTrigger=-10,NextLog=0;
    bool Finished=false,Pressed=false,Released=false,Aimed=false,UnAimed=false,Inspected=false;

    void Input(AFPSGAMECharacter* Pawn,FName Name,EInputEvent Event)
    {
        if(auto* Component=Pawn->InputComponent.Get())
            for(int32 I=0;I<Component->GetNumActionBindings();++I)
            {auto& B=Component->GetActionBinding(I);if(B.GetActionName()==Name&&B.KeyEvent==Event)B.ActionDelegate.Execute(EKeys::LeftMouseButton);}
    }
    void Write(const FString& Path,const TSharedRef<FJsonObject>& Data)
    {FString Json;FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*Path);}
    void EndCase(const FString& Reason)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("id"),Cases[Index]->AsObject()->GetStringField(TEXT("id")));
        R->SetObjectField(TEXT("case"),Cases[Index]->AsObject());R->SetStringField(TEXT("reason"),Reason);
        R->SetArrayField(TEXT("samples"),Samples);Write(CaseOutput/TEXT("runtime.json"),R);
        Results.Add(MakeShared<FJsonValueObject>(R));auto Summary=MakeShared<FJsonObject>();Summary->SetArrayField(TEXT("cases"),Results);Write(Output/TEXT("runtime.json"),Summary);
        UE_LOG(LogTemp,Display,TEXT("WEAPON_FLAME_CASE_END %d %s %s"),Index,*R->GetStringField(TEXT("id")),*Reason);
        ++Index;CaseAt=ReadyAt=ActiveAt=-1;Shot=0;Samples.Reset();Pressed=Released=Aimed=UnAimed=Inspected=false;LastTrigger=-10;
        if(Index>=Cases.Num()){Finished=true;FPlatformMisc::RequestExitWithStatus(false,0);}
    }
    void Capture(AFPSGAMECharacter* Pawn,const FString& Name)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("image"),Name);R->SetNumberField(TEXT("time"),FPlatformTime::Seconds()-Started);
        R->SetNumberField(TEXT("armor_remaining"),Pawn->FindComponentByClass<UFPSFireMagicComponent>()->ArmorRemaining());
        FFlameArmorAttachments Spans;FlameArmorAttachments::Gather(Pawn,Spans);
        TArray<TSharedPtr<FJsonValue>> Attachments,Effects;
        for(const auto& Span:Spans)
        {
            auto A=MakeShared<FJsonObject>();A->SetStringField(TEXT("section"),Span.Section.ToString());
            A->SetStringField(TEXT("mesh"),Span.Geometry.IsValid()?Span.Geometry->GetPathName():TEXT("none"));
            A->SetNumberField(TEXT("length"),(Span.Tip-Span.Base).Size());A->SetStringField(TEXT("base"),Span.Base.ToString());
            A->SetStringField(TEXT("tip"),Span.Tip.ToString());Attachments.Add(MakeShared<FJsonValueObject>(A));
        }
        for(TObjectIterator<UNiagaraComponent> It;It;++It)
        {
            auto* FX=*It;if(FX->GetWorld()!=Pawn->GetWorld()||!FX->GetAsset()||!FX->IsActive())continue;
            const FString Asset=FX->GetAsset()->GetPathName();
            if(!Asset.Contains(TEXT("NS_FlameArmorWeapon"))&&!Asset.Contains(TEXT("NS_FlameArmorSword"))&&!Asset.Contains(TEXT("NS_FlameArmorHammer"))&&!Asset.Contains(TEXT("NS_StarMarrowDenseBladeFire")))continue;
            auto E=MakeShared<FJsonObject>();E->SetStringField(TEXT("asset"),Asset);E->SetStringField(TEXT("owner"),FX->GetOwner()?FX->GetOwner()->GetName():TEXT("none"));
            E->SetBoolField(TEXT("visible"),FX->IsVisible());E->SetBoolField(TEXT("paused"),FX->IsPaused());
            bool Valid=false;E->SetNumberField(TEXT("fade"),FX->GetVariableFloat(TEXT("User.Fade"),Valid));
            E->SetStringField(TEXT("position"),FX->GetComponentLocation().ToString());
            double Distance=1.e20;const FFlameArmorAttachment* Match=nullptr;
            for(const auto& Span:Spans)if(FX->GetAttachParent()==Span.Source.Get()&&FX->GetAttachSocketName()==Span.Socket)
            {double D=FVector::Dist(FX->GetComponentLocation(),Span.Base);if(D<Distance){Distance=D;Match=&Span;}}
            if(Match){E->SetNumberField(TEXT("anchor_error_cm"),Distance);E->SetStringField(TEXT("section"),Match->Section.ToString());}
            TArray<TSharedPtr<FJsonValue>> Counts;
            if(auto Controller=FX->GetSystemInstanceController())if(auto* Instance=Controller->GetSystemInstance_Unsafe())
                for(const auto& Emitter:Instance->GetEmitters())Counts.Add(MakeShared<FJsonValueNumber>(Emitter->GetNumParticles()));
            E->SetArrayField(TEXT("particles"),Counts);
            auto* Cache=UNiagaraSimCacheFunctionLibrary::CreateNiagaraSimCache(FX);UNiagaraSimCache* Captured=nullptr;
            if(UNiagaraSimCacheFunctionLibrary::CaptureNiagaraSimCacheImmediate(Cache,FNiagaraSimCacheCreateParameters(),FX,Captured))
            {
                TArray<TSharedPtr<FJsonValue>> Rows;
                for(FName Emitter:Cache->GetEmitterNames())
                {
                    TArray<FVector> Positions;TArray<FLinearColor> Colors;TArray<FVector2D> Sizes;
                    Cache->ReadPositionAttribute(Positions,TEXT("Position"),Emitter,false);
                    Cache->ReadColorAttribute(Colors,TEXT("Color"),Emitter);Cache->ReadVector2Attribute(Sizes,TEXT("SpriteSize"),Emitter);
                    int32 Invalid=0;for(const FVector& P:Positions)Invalid+=P.ContainsNaN();
                    for(const auto& S:Sizes)Invalid+=!FMath::IsFinite(S.X)||!FMath::IsFinite(S.Y)||S.X<0||S.Y<0;
                    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("emitter"),Emitter.ToString());Row->SetNumberField(TEXT("invalid"),Invalid);
                    TArray<TSharedPtr<FJsonValue>> Points,Dimensions,ColorRows;
                    for(int32 I=0;I<FMath::Min(Positions.Num(),6);++I)
                    {
                        Points.Add(MakeShared<FJsonValueString>(Positions[I].ToString()));
                        if(Sizes.IsValidIndex(I))Dimensions.Add(MakeShared<FJsonValueString>(Sizes[I].ToString()));
                        if(Colors.IsValidIndex(I))ColorRows.Add(MakeShared<FJsonValueString>(Colors[I].ToString()));
                    }
                    Row->SetArrayField(TEXT("positions"),Points);Row->SetArrayField(TEXT("sizes"),Dimensions);Row->SetArrayField(TEXT("colors"),ColorRows);Rows.Add(MakeShared<FJsonValueObject>(Row));
                }
                E->SetArrayField(TEXT("particle_samples"),Rows);
            }
            Effects.Add(MakeShared<FJsonValueObject>(E));
        }
        R->SetArrayField(TEXT("attachments"),Attachments);R->SetArrayField(TEXT("effects"),Effects);Samples.Add(MakeShared<FJsonValueObject>(R));
        FScreenshotRequest::RequestScreenshot(CaseOutput/Name,false,false);
        UE_LOG(LogTemp,Display,TEXT("WEAPON_FLAME_CAPTURE %d %s spans=%d fx=%d"),Index,*Name,Spans.Num(),Effects.Num());
    }
    void Tick()
    {
        auto* W=World.Get();if(!W)return;auto* PC=W->GetFirstPlayerController();auto* Pawn=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
        auto* Model=W->GetGameInstance()?W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
        auto* Fire=Pawn?Pawn->FindComponentByClass<UFPSFireMagicComponent>():nullptr;if(!PC||!Pawn||!Model||!Fire)return;
        if(!Model->IsAudit()||!Model->ProfileSlot().StartsWith(TEXT("ColdSteel_WeaponFlameAudit_")))
        {Finished=true;FPlatformMisc::RequestExitWithStatus(false,2);return;}
        if(auto* Loading=W->GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();Loading&&Loading->IsHoldingGameplayInput())Loading->ReleaseToGameplay();
        if(W->IsPaused())PC->SetPause(false);
        const double Now=FPlatformTime::Seconds()-Started;
        if(CaseAt<0)
        {
            const auto& C=Cases[Index]->AsObject();CaseOutput=Output/C->GetStringField(TEXT("id"));IFileManager::Get().MakeDirectory(*CaseOutput,true);
            Input(Pawn,TEXT("Fire"),IE_Released);Input(Pawn,TEXT("Aim"),IE_Released);
            auto P=Model->Snapshot();P.Items.Reset();P.ActiveWeaponSlot=6;P.ActiveProductionTool.Reset();P.DungeonRun={};
            // Cast with a free left hand, then equip the requested offhand.
            // This follows the real spell restriction instead of bypassing it.
            for(const auto Pair:{TPair<const TCHAR*,int32>(TEXT("weapon"),6)})
            {
                FString Id;if(C->TryGetStringField(Pair.Key,Id)&&!Id.IsEmpty())
                {
                    auto Item=Model->CreateItem(Id);Item.Place=1;Item.Cell=Pair.Value;P.Items.Add(Item);
                    FString Family;C->TryGetStringField(TEXT("family"),Family);
                    if(Family==TEXT("bow")&&!Model->AddAmmoToState(P,Model->AmmoDefinitionFor(Item),12))
                    {EndCase(TEXT("Could not supply audit bow arrows"));return;}
                }
            }
            // Level 20 supplies a long enough visual window for the whole
            // sequence. Only this isolated profile is changed, never skill data.
            P.Skills.FindOrAdd(TEXT("flameArmor")).Level=20;P.FlameArmorCooldown=P.FlameArmorCooldownDuration=0;
            P.Attributes.FindOrAdd(TEXT("intt"))=100;P.Attributes.FindOrAdd(TEXT("wis"))=100;P.Mana=10000;P.Stamina=150;P.Health=1000;
            if(!Model->CommitState(P)){EndCase(TEXT("Commit failed: ")+Model->ResultMessage());return;}
            Pawn->SetCanBeDamaged(false);PC->SetControlRotation(FRotator(-3,0,0));CaseAt=Now;
            UE_LOG(LogTemp,Display,TEXT("WEAPON_FLAME_CASE_START %d %s"),Index,*C->GetStringField(TEXT("id")));
        }
        if(Now-CaseAt>100.){EndCase(TEXT("Timeout: ")+Fire->StatusText(TEXT("flameArmor")));return;}
        FFlameArmorAttachments Spans;FlameArmorAttachments::Gather(Pawn,Spans);
        if(ReadyAt<0&&Now-CaseAt>5.&&Spans.Num())ReadyAt=Now;
        if(ReadyAt>=0&&ActiveAt<0)
        {
            FString Offhand;Cases[Index]->AsObject()->TryGetStringField(TEXT("offhand"),Offhand);
            if(Fire->ArmorRemaining()>(Offhand.IsEmpty()?12.:16.)&&!Fire->HasQueuedAction()&&Fire->UnreleasedSkill().IsNone())
            {
                if(!Offhand.IsEmpty())
                {
                    auto P=Model->Snapshot();auto Item=Model->CreateItem(Offhand);Item.Place=1;Item.Cell=8;P.Items.Add(Item);
                    if(!Model->CommitState(P)){EndCase(TEXT("Offhand commit failed: ")+Model->ResultMessage());return;}
                }
                ActiveAt=Now+(Offhand.IsEmpty()?0.:3.);
            }
            else if(Now-LastTrigger>2.&&!Fire->HasQueuedAction()&&Fire->UnreleasedSkill().IsNone())
            {Fire->Trigger(TEXT("flameArmor"));LastTrigger=Now;}
        }
        if(ActiveAt>=0)
        {
            const double Age=Now-ActiveAt;
            FString Family;Cases[Index]->AsObject()->TryGetStringField(TEXT("family"),Family);
            const double ReleaseAt=Family==TEXT("bow")?6.:5.;
            PC->SetControlRotation(Age>=2.5&&Age<4.?FRotator(-3+12*FMath::Sin((Age-2.5)*6.),65*FMath::Sin((Age-2.5)*7.),0):FRotator(-3,0,0));
            if(Age>=4.2&&!Pressed){Input(Pawn,TEXT("Fire"),IE_Pressed);Pressed=true;}
            if(Age>=ReleaseAt&&!Released){Input(Pawn,TEXT("Fire"),IE_Released);Released=true;}
            if(Age>=7.&&!Aimed){Input(Pawn,TEXT("Aim"),IE_Pressed);Aimed=true;}
            if(Age>=8.&&!UnAimed){Input(Pawn,TEXT("Aim"),IE_Released);UnAimed=true;}
            if(Age>=8.4&&!Inspected){Input(Pawn,TEXT("InspectWeapon"),IE_Pressed);Inspected=true;}
            const double Times[]={.6,2.,3.3,4.8,5.05,5.6,6.2,7.5,9.3};
            if(Shot<UE_ARRAY_COUNT(Times)&&Age>=Times[Shot]&&!FScreenshotRequest::IsScreenshotRequested())Capture(Pawn,FString::Printf(TEXT("%02d.png"),++Shot));
            if(Age>10.3){EndCase(TEXT("Captured idle, camera turn, fire/attack, aim and inspect"));return;}
        }
        if(Now>=NextLog){NextLog=Now+8.;UE_LOG(LogTemp,Display,TEXT("WEAPON_FLAME_WAIT case=%d t=%.1f armor=%.2f spans=%d %s"),Index,Now,Fire->ArmorRemaining(),Spans.Num(),*Fire->StatusText(TEXT("flameArmor")));}
    }
};
FAutoConsoleCommand WeaponFlameReviewCommand(TEXT("fps.WeaponFlameReview"),TEXT("Explicit isolated-profile weapon flame review."),FConsoleCommandDelegate::CreateLambda([]()
{
    if(!FParse::Param(FCommandLine::Get(),TEXT("WeaponFlameVisualAudit")))return;
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([](float)
    {
        UWorld* World=nullptr;if(GEngine)for(const auto& C:GEngine->GetWorldContexts())if(C.World()&&C.World()->IsGameWorld()&&C.World()->GetFirstPlayerController()){World=C.World();break;}
        if(!World)return true;
        auto Run=MakeShared<FWeaponFlameVisualReview>();Run->World=World;FString CasesPath,Json;
        FParse::Value(FCommandLine::Get(),TEXT("WeaponReviewOutput="),Run->Output);FParse::Value(FCommandLine::Get(),TEXT("WeaponReviewCases="),CasesPath);
        if(Run->Output.IsEmpty()||!FFileHelper::LoadFileToString(Json,*CasesPath)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Run->Cases)||Run->Cases.IsEmpty())
        {FPlatformMisc::RequestExitWithStatus(false,3);return false;}
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Run](float){Run->Tick();return !Run->Finished;}));return false;
    }));
}));
}
#endif
