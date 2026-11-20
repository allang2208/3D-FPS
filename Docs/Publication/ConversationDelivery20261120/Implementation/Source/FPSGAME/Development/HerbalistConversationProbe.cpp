// Explicitly requested, isolated, headless standalone run on the production hills map.
#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
#include "HillsContinuitySupport.h"
#include "VillageNetworkAudit.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../NPC/ResidentConversation.h"
#include "../NPC/VillageHerbalist.h"
#include "../UI/ColdSteelNpcDialogueArtisans.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../WorldGeneration/HillsHerbalistWorkshop.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Containers/Ticker.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/DefaultPawn.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Layout/Children.h"
#include "Widgets/SViewport.h"
#include "Widgets/Text/STextBlock.h"

namespace HerbalistConversationProbe
{
using ColdSteelMerchantDialogue::Herbalist;

void ReadText(const TSharedRef<SWidget>& Widget, TArray<FString>& Out)
{
    if (!Widget->GetVisibility().IsVisible() || Widget->GetRenderOpacity() <= 0.f) return;
    if (Widget->GetType() == STextBlock::StaticWidgetClass().GetWidgetType())
    {
        Out.Add(StaticCastSharedRef<STextBlock>(Widget)->GetText().ToString());
        return;
    }
    FChildren* Children = Widget->GetChildren();
    if (Children)
        for (int32 Index = 0; Index < Children->Num(); ++Index)
            ReadText(Children->GetChildAt(Index), Out);
}

void MenuKey(FKey Key)
{
    const FKeyEvent Event(Key, FModifierKeysState(), 0, false, 0, 0);
    FSlateApplication::Get().ProcessKeyDownEvent(Event);
    FSlateApplication::Get().ProcessKeyUpEvent(Event);
}

struct FRun
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<AVillageHerbalist> Resident;
    TWeakObjectPtr<APlayerController> SecondController;
    TWeakObjectPtr<ADefaultPawn> SecondPawn;
    FString Output, Detail;
    TArray<TSharedPtr<FJsonValue>> Checks;
    double Started = FPlatformTime::Seconds(), LastLog = 0., Since = 0.;
    int32 Step = 0;
    bool Passed = true;
    FVector SpawnPoint, StoppedPoint;
    double WalkBeforeOpen = 0.;

    void Check(const FString& Name, bool OK, const FString& Evidence = {})
    {
        auto Row = MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("case"), Name);
        Row->SetBoolField(TEXT("passed"), OK);
        Row->SetStringField(TEXT("detail"), Evidence);
        Checks.Add(MakeShared<FJsonValueObject>(Row));
        Passed &= OK;
        UE_LOG(LogTemp, Display, TEXT("HERBALIST_DIALOGUE %s %d %s"), *Name, OK, *Evidence);
    }

    bool Finish()
    {
        auto Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("passed"), Passed);
        Result->SetArrayField(TEXT("checks"), Checks);
        FString Json;
        FJsonSerializer::Serialize(Result, TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json, *Output, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        FPlatformMisc::RequestExit(false);
        return false;
    }

    TArray<FString> ScreenText() const
    {
        TArray<FString> Text;
        if (auto* Client = World->GetGameViewport())
            if (auto View = Client->GetGameViewportWidget()) ReadText(View.ToSharedRef(), Text);
        return Text;
    }

    bool HasMainMenu() const
    {
        const auto Text = ScreenText();
        if (!Text.Contains(Herbalist.Name) || !Text.Contains(Herbalist.Workshop) ||
            !Text.Contains(TEXT("对话")) || !Text.Contains(TEXT("交易")) || !Text.Contains(TEXT("学习技能"))) return false;
        for (const auto& Topic : Herbalist.Topics)
            if (Text.Contains(Topic.Title)) return false;
        return true;
    }

    bool HasTopicsMenu() const
    {
        const auto Text = ScreenText();
        if (!Text.Contains(TEXT("闲聊"))) return false;
        for (const auto& Topic : Herbalist.Topics)
            if (!Text.Contains(Topic.Title)) return false;
        return true;
    }

    // Space completes the visible line, then advances it. Compare the accumulated
    // spoken text with the authored passage, excluding the invisible sizing copy.
    bool ReadPassage(const TCHAR* Expected) const
    {
        FString Remaining(Expected);
        for (int32 Press = 0; Press < 128 && !Remaining.IsEmpty(); ++Press)
        {
            MenuKey(EKeys::SpaceBar);
            const auto Text = ScreenText();
            for (const FString& Line : Text)
            {
                if (!Line.IsEmpty() && Remaining.StartsWith(Line) &&
                    (Remaining.Len() == Line.Len() || FCString::Strchr(TEXT("。！？!?；;.”’」』）)】"), Line[Line.Len()-1])))
                {
                    Remaining.RightChopInline(Line.Len());
                    Remaining.TrimStartInline();
                    break;
                }
            }
        }
        return Remaining.IsEmpty();
    }

    void Topics()
    {
        const FKey Keys[] = {EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four};
        Check(TEXT("menu.greeting-and-services"), HasMainMenu() && ReadPassage(Herbalist.Greeting));
        if (!Passed) return;
        MenuKey(EKeys::Three);
        Check(TEXT("menu.lesson-placeholder-stays-on-main"), HasMainMenu());
        if (!Passed) return;
        MenuKey(EKeys::One);
        Check(TEXT("menu.talk-opens-topics"), HasTopicsMenu());
        for (int32 I = 0; I < UE_ARRAY_COUNT(Keys) && Passed; ++I)
        {
            const auto& T = Herbalist.Topics[I];
            MenuKey(Keys[I]);
            const auto Story = ScreenText();
            Check(FString::Printf(TEXT("topic.%d.story"), I+1),
                Story.Contains(T.Title) && Story.Contains(T.FollowUp) && ReadPassage(T.Reply), T.Title);
            if (!Passed) break;
            MenuKey(EKeys::One);
            const auto Follow = ScreenText();
            Check(FString::Printf(TEXT("topic.%d.followup"), I+1),
                Follow.Contains(T.FollowUp) && Follow.Contains(TEXT("返回上一问")) && ReadPassage(T.FollowUpReply), T.FollowUp);
            if (!Passed) break;
            MenuKey(EKeys::Escape);
            const auto Back = ScreenText();
            const bool BackToStory = Back.Contains(T.Title) && Back.Contains(T.FollowUp);
            MenuKey(EKeys::Escape);
            Check(FString::Printf(TEXT("topic.%d.back-to-story-and-topics"), I+1), BackToStory && HasTopicsMenu());
        }
        if (!Passed) return;
        MenuKey(EKeys::Escape);
        Check(TEXT("menu.topics-back-to-main"), HasMainMenu());
    }

    bool Approach(AFPSGAMEPlayerController& PC, AFPSGAMECharacter& Pawn, AVillageHerbalist& NPC)
    {
        const FVector Base = NPC.GetActorLocation();
        const FVector Aim = Base + FVector(0, 0, 126);
        const auto* Capsule = Pawn.GetCapsuleComponent();
        FCollisionQueryParams Query(SCENE_QUERY_STAT(HerbalistApproach), false, &Pawn);
        for (const double Distance : {120., 165., 90.})
        {
            for (const double Angle : {0., 45., -45., 90., -90., 135., -135., 180.})
            {
                const FVector Near = Base + NPC.GetActorForwardVector().RotateAngleAxis(Angle, FVector::UpVector)*Distance;
                FHitResult Floor;
                if (!World->LineTraceSingleByChannel(Floor, Near + FVector(0,0,28), Near - FVector(0,0,35), ECC_Visibility, Query)
                    || Floor.ImpactNormal.Z < .7) continue;
                const FVector Center = Floor.ImpactPoint + FVector(0,0,Capsule->GetScaledCapsuleHalfHeight()+3);
                if (World->OverlapBlockingTestByChannel(Center, FQuat::Identity, ECC_Pawn, Capsule->GetCollisionShape(), Query)) continue;
                VillageNetAudit::Place(&PC, Center, Aim);
                for (int32 Turn = 0; Turn < 4; ++Turn)
                {
                    FVector Eye; FRotator Look;
                    ColdSteelWorldInteraction::GetReachViewPoint(&PC, Eye, Look);
                    PC.SetControlRotation((Aim-Eye).Rotation());
                    if (PC.PlayerCameraManager) PC.PlayerCameraManager->UpdateCamera(0.f);
                }
                if (ColdSteelWorldInteraction::TraceUseTargets(&PC).Target == &NPC && PC.GetChapelDialogue()->CanStartConversation(&NPC))
                {
                    Detail = HillsContinuity::InteractionTrace(&PC, Aim);
                    return true;
                }
            }
        }
        Detail = HillsContinuity::InteractionTrace(&PC, Aim);
        return false;
    }

    void Advance() { ++Step; Since = World->GetTimeSeconds(); }

    // A second server-side session without another local viewport. This exercises
    // concurrent ownership and controller teardown, independently of UDP transport.
    bool OpenFixtureSession()
    {
        auto* Controller = World->SpawnActor<APlayerController>();
        FActorSpawnParameters Spawn;
        Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        const FVector TalkPoint = Resident->GetActorLocation()+FVector(0,0,95);
        auto* Pawn = World->SpawnActor<ADefaultPawn>(ADefaultPawn::StaticClass(), TalkPoint, FRotator::ZeroRotator, Spawn);
        if (!Controller || !Pawn) return false;
        SecondController=Controller;
        SecondPawn=Pawn;
        Pawn->SetActorEnableCollision(false);
        auto* Health = NewObject<UFPSCombatHealthComponent>(Pawn);
        Health->RegisterComponent();
        Controller->Possess(Pawn);
        if (Controller->PlayerCameraManager) Controller->PlayerCameraManager->UpdateCamera(0.f);
        if (!ResidentConversation::CanReach(Pawn, Resident.Get())) return false;
        auto* Dialogue = NewObject<UChapelDialogueComponent>(Controller);
        Dialogue->RegisterComponent();
        struct { uint32 Session; AActor* Merchant; APawn* Initiator; } Args{1, Resident.Get(), Pawn};
        Dialogue->ProcessEvent(Dialogue->FindFunctionChecked(TEXT("ServerOpenMerchant")), &Args);
        return true;
    }

    bool Tick(float)
    {
        if (!World.IsValid()) { Check(TEXT("world.active"), false); return Finish(); }
        const double Now = FPlatformTime::Seconds();
        const double Age = World->GetTimeSeconds()-Since;
        if (Now - Started > 600. || (Step > 1 && Age > 125.))
        {
            Check(FString::Printf(TEXT("stage.%d.timeout"), Step), false, Detail);
            return Finish();
        }
        if (Now - LastLog > 15.)
        {
            const FString Location = Resident.IsValid() ? Resident->GetActorLocation().ToCompactString() : TEXT("unavailable");
            UE_LOG(LogTemp, Display, TEXT("HERBALIST_WAIT stage=%d age=%.1f npc=%s %s"), Step, Age, *Location, *Detail);
            LastLog = Now;
        }
        auto* PC = Cast<AFPSGAMEPlayerController>(World->GetFirstPlayerController());
        auto* Pawn = PC ? Cast<AFPSGAMECharacter>(PC->GetPawn()) : nullptr;
        if (!Pawn || !World->HasBegunPlay()) return true;
        auto* D = PC->GetChapelDialogue();
        if (!D) return true;
        if (Step == 0)
        {
            auto* Hills = VillageNetAudit::FindHills(World.Get());
            if (!Hills || !Hills->GetVillageSite().bPlaced || !PC->CanOpenGameMenu()) return true;
            FText Reason;
            if (!Hills->UnlockVillagePlan(TEXT("herbalist"), Reason)) { Detail=Reason.ToString(); return true; }
            Pawn->SetCanBeDamaged(false);
            Advance();
        }
        if (Step == 1)
        {
            for (TActorIterator<AVillageHerbalist> It(World.Get()); It; ++It)
                if (Cast<AHillsHerbalistWorkshop>(It->GetOwner())) { Resident = *It; break; }
            if (!Resident.IsValid()) return true;
            Check(TEXT("repaired-shop.resident"), true, Resident->GetPathName());
            SpawnPoint = Resident->GetActorLocation();
            Advance();
            return true;
        }
        if (!Resident.IsValid()) { Check(TEXT("shop.resident-alive"), false); return Finish(); }
        const FVector Position = Resident->GetActorLocation();
        if (Step == 2)
        {
            WalkBeforeOpen = FVector::Dist2D(SpawnPoint, Position);
            // Prefer an active walk. A stuck patrol should still exercise all the dialogue pages.
            if (WalkBeforeOpen < 7. && Age < 40.) return true;
            if (!PC->CanOpenGameMenu() || !Approach(*PC,*Pawn,*Resident)) return true;
            const auto Hint = ColdSteelWorldInteraction::ResolveInteractionHint(Resident.Get(), Pawn);
            Check(TEXT("walking.focus-and-prompt"), Hint.bAction && Hint.Text.Contains(Herbalist.Name), Detail+TEXT(" ")+Hint.Text);
            HillsContinuity::KeyE(PC);
            Check(TEXT("E.open-and-lock-input"), D->IsOpen() && D->IsHerbalist() && PC->IsMoveInputIgnored() && PC->IsLookInputIgnored());
            if (!Passed) return Finish();
            StoppedPoint = Resident->GetActorLocation();
            Topics();
            if (!Passed) return Finish();
            Check(TEXT("patrol.moved-before-E"), WalkBeforeOpen >= 7., FString::Printf(TEXT("travel_cm=%.2f"), WalkBeforeOpen));
            Advance();
        }
        else if (Step == 3)
        {
            const double Drift = FVector::Distance(StoppedPoint, Position);
            if (Drift > 1. || !D->IsOpen() || Age >= 6.)
            {
                Check(TEXT("conversation.stays-still"), Drift <= 1. && D->IsOpen(), FString::Printf(TEXT("drift_cm=%.2f seconds=%.2f"), Drift, Age));
                MenuKey(EKeys::Escape);
                Check(TEXT("Esc.close-and-restore-input"), !D->IsOpen() && !PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored() && !PC->bShowMouseCursor);
                if (D->IsOpen()) return Finish();
                // Free the narrow service aisle while observing the next leg.
                VillageNetAudit::Place(PC, Pawn->GetActorLocation()+FVector(0,0,650), Position);
                Advance();
            }
        }
        else if (Step == 4 && FVector::Dist2D(StoppedPoint,Position) >= 12.)
        {
            if (!Approach(*PC,*Pawn,*Resident)) return true;
            Check(TEXT("closed.walk-resumes"), true, FString::Printf(TEXT("travel_cm=%.2f seconds=%.2f"), FVector::Dist2D(StoppedPoint,Position), Age));
            HillsContinuity::KeyE(PC);
            Check(TEXT("E.reopen"), D->IsOpen() && HasMainMenu());
            if (!D->IsOpen()) return Finish();
            Check(TEXT("concurrent.authority-fixture-open"), OpenFixtureSession());
            if (!SecondController.IsValid()) return Finish();
            StoppedPoint = Resident->GetActorLocation();
            VillageNetAudit::Place(PC, Pawn->GetActorLocation()+FVector(0,0,650), Position);
            Advance();
        }
        else if (Step == 5 && Age > 1.)
        {
            Check(TEXT("out-of-reach.auto-close"), !D->IsOpen() && !PC->IsMoveInputIgnored() && !D->CanStartConversation(Resident.Get()));
            Advance();
        }
        else if (Step == 6 && Age >= 10.)
        {
            const double Drift = FVector::Distance(StoppedPoint, Position);
            Check(TEXT("concurrent.one-session-still-holds"), Drift <= 1., FString::Printf(TEXT("drift_cm=%.2f"),Drift));
            if (SecondController.IsValid()) SecondController->Destroy();
            if (SecondPawn.IsValid()) SecondPawn->Destroy();
            StoppedPoint = Position;
            Advance();
        }
        else if (Step == 7 && FVector::Dist2D(StoppedPoint,Position) >= 12.)
        {
            Check(TEXT("concurrent.controller-teardown-resumes-walk"), true,
                FString::Printf(TEXT("travel_cm=%.2f seconds=%.2f"),FVector::Dist2D(StoppedPoint,Position), Age));
            return Finish();
        }
        return true;
    }
};

FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.HerbalistConversation"),TEXT("Run the isolated herbalist dialogue check."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
    {
        auto Run = MakeShared<FRun>();
        if (!World || World->GetNetMode() != NM_Standalone ||
            !FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("HerbalistConversation")) ||
            !FParse::Value(FCommandLine::Get(),TEXT("HerbalistDialogueResult="),Run->Output)) return;
        Run->World = World;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Run](float Dt){ return Run->Tick(Dt); }), .1f);
    }));
}
#endif
