#include "ColdSteelHUDWidget.h"
#include "ColdSteelResourceMeter.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/Border.h"
#include "Components/TextBlock.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"

void UColdSteelHUDWidget::RunTopVitalsAudit()
{
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* Pawn=GetOwningPlayerPawn();auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!M||!M->IsAudit()||!M->ProfileSlot().Contains(TEXT("TopVitals_"))||!Health){UE_LOG(LogTemp,Error,TEXT("TopVitals: FAIL isolated profile or health unavailable"));GetOwningPlayer()->ConsoleCommand(TEXT("quit"));return;}
    struct FRun{int32 Phase=0,Checks=0,Failures=0;FTimerHandle Timer;FColdSteelProfile Original;float HP=0,MaxHP=0;};auto R=MakeShared<FRun>();R->Original=M->Snapshot();R->HP=Health->Health;R->MaxHP=Health->MaxHealth;
    auto Check=[R](bool Pass,const TCHAR* Name){++R->Checks;if(!Pass)++R->Failures;UE_LOG(LogTemp,Display,TEXT("TopVitals: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);};
    SetInventoryOpen(false);auto P=M->Snapshot();P.Level=7;P.Health=M->Derived(TEXT("maxHp"));P.Mana=M->Derived(TEXT("maxMp"))*.4f;Check(M->CommitState(P),TEXT("isolated vitals profile initialized"));Health->Health=Health->MaxHealth;
    GetWorld()->GetTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(this,[this,M,Health,R,Check](){
        const auto View=UWidgetLayoutLibrary::GetViewportSize(this);
        auto Capture=[&](const TCHAR* Name){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("TopVitals")/FString::Printf(TEXT("%s-%dx%d.png"),Name,int32(View.X),int32(View.Y)),true,false);};
        switch(R->Phase++){
        case 0:{
            Check(!IsInventoryOpen()&&TopHealthValue->GetText().ToString()==FString::Printf(TEXT("%.0f / %.0f"),Health->MaxHealth,Health->MaxHealth)&&TopHealthMeter->Ratio()==1,TEXT("full health updates while drawer closed"));
            Check(FMath::IsNearlyEqual(TopManaMeter->Ratio(),.4f)&&TopLevelValue->GetText().ToString()==TEXT("7"),TEXT("mana and level read live profile"));
            const auto& G=TopVitalsSurface->GetCachedGeometry();const auto Top=GetCachedGeometry().AbsoluteToLocal(G.LocalToAbsolute(FVector2D::ZeroVector));const auto End=GetCachedGeometry().AbsoluteToLocal(G.LocalToAbsolute(G.GetLocalSize()));
            const auto TimelineTop=GetCachedGeometry().AbsoluteToLocal(TimelinePanel->GetCachedGeometry().LocalToAbsolute(FVector2D::ZeroVector));
            Check(Top.X>=0&&End.X<=GetCachedGeometry().GetLocalSize().X&&Top.Y>=0&&End.Y<=TimelineTop.Y,TEXT("top panel fits viewport above timeline"));
            Check(TopVitalsSurface->GetVisibility()==ESlateVisibility::HitTestInvisible,TEXT("display does not capture gameplay input"));Capture(TEXT("full"));break;}
        case 1:{auto P=M->Snapshot();P.Level=8;P.Mana=0;Check(M->CommitState(P),TEXT("live profile change committed"));Health->MaxHealth=100;Health->Health=25;break;}
        case 2:Check(TopHealthValue->GetText().ToString()==TEXT("25 / 100")&&FMath::IsNearlyEqual(TopHealthMeter->Ratio(),.25f),TEXT("damage updates number and fill"));Check(TopHealthValue->GetColorAndOpacity().GetSpecifiedColor().Equals(ColdSteelUI::Danger),TEXT("quarter health has static danger cue"));Check(TopManaMeter->Ratio()==0&&TopLevelValue->GetText().ToString()==TEXT("8"),TEXT("empty mana and level change update"));Capture(TEXT("low"));break;
        case 3:{auto P=M->Snapshot();P.Mana=M->Derived(TEXT("maxMp"));Check(M->CommitState(P),TEXT("mana recovery committed"));Health->MaxHealth=100;Health->Health=0;break;}
        case 4:Check(TopHealthMeter->Ratio()==0&&TopHealthValue->GetText().ToString()==TEXT("0 / 100")&&TopManaMeter->Ratio()==1,TEXT("zero health has no fill and mana recovery is full"));Capture(TEXT("empty"));break;
        case 5:Health->Health=150;break;
        case 6:Check(TopHealthMeter->Ratio()==1&&TopHealthValue->GetText().ToString()==TEXT("100 / 100"),TEXT("over-cap value clamps to visible maximum"));Check(M->CommitState(R->Original),TEXT("isolated profile restored"));Health->MaxHealth=R->MaxHP;Health->Health=R->HP;GetWorld()->GetTimerManager().ClearTimer(R->Timer);UE_LOG(LogTemp,Display,TEXT("TopVitals: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));break;
        }
    }),.7f,true);
}
