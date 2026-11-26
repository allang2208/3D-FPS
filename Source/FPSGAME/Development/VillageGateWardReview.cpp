#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING
#include "../FPSGAMEPlayerController.h"
#include "../FPSWeatherManager.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/DamageEvents.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Containers/Ticker.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/HUD.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

// The opt-in runner uses a copy of the Hills save. All coordinates are local
// to the generated gate so the same photographs work across village seeds.
namespace VillageGateWardReview
{
enum class EProbe { None, IdleGrille, Raise, Lower, Repair };
struct FView
{
    const TCHAR* Name;
    FVector Eye,Target;
    float FOV;
    EProbe Probe=EProbe::None;
};
const FView Views[]={
    {TEXT("courtyard"),{-650,2270,390},{0,0,571},65.f},
    {TEXT("operating-wall"),{-72,280,156},{150,95,151},76.f},
    {TEXT("inner-walk"),{-307,-144,620},{121,-360,735},85.f},
    {TEXT("lookout"),{-300,-509,1235},{143,95,1090},82.f},
    {TEXT("gate-at-rest"),{0,180,160},{0,0,155},78.f,EProbe::IdleGrille},
    {TEXT("release-up"),{41,202,151},{240,155,112},68.f,EProbe::Raise},
    {TEXT("open-passage"),{105,604,168},{-31,-470,170},74.f},
    {TEXT("release-down"),{41,202,151},{240,155,112},68.f,EProbe::Lower},
    {TEXT("repaired-grille"),{0,180,160},{0,0,155},78.f,EProbe::Repair}
};
struct FReview
{
    FString Out,Report;
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<AHighVillageGate> Gate;
    TWeakObjectPtr<ACameraActor> Camera;
    int32 Index=-1;
    int32 Phase=0;
    double Start=FPlatformTime::Seconds(),After=0.;
    bool bOK=true;
    bool bRepairSandbox=false;
    bool bCourtyardOnly=false;
    int64 WalletBefore=0;

    bool Finish(const TCHAR* Reason)
    {
        Report+=FString::Printf(TEXT("result=%s reason=%s\n"),bOK?TEXT("pass"):TEXT("incomplete"),Reason);
        FFileHelper::SaveStringToFile(Report,*(Out/TEXT("review.txt")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        FPlatformMisc::RequestExitWithStatus(false,bOK?0:1);
        return false;
    }
    bool Tick(float)
    {
        const double Now=FPlatformTime::Seconds();
        if(Now-Start>260.){bOK=false;return Finish(TEXT("capture timeout"));}
        UWorld* W=World.Get();
        if(!W||Now<After)return true;
        auto* PC=Cast<AFPSGAMEPlayerController>(W->GetFirstPlayerController());
        auto* Pawn=PC?Cast<ACharacter>(PC->GetPawn()):nullptr;
        if(!Pawn)return true;
        if(!Camera.IsValid())
        {
            if(PC->IsMoveInputIgnored())return true;
            for(TActorIterator<AHighVillageGate> It(W);It;++It)
                if(It->GetSectionId()==50001 && It->GetStonePortal()->GetStaticMesh()) {Gate=*It;break;}
            if(!Gate.IsValid())return true;
            for(TActorIterator<AFPSWeatherManager> It(W);It;++It)
            {
                It->SetWeatherState(EFPSWeatherState::Clear);
                It->RealSecondsPerGameDay=864000.f;
                It->AdvanceGameTime(FMath::Fmod(10.5f-It->NormalizedDayTime*24.f+24.f,24.f)+.0001f);
            }
            Pawn->SetCanBeDamaged(false);
            Pawn->SetActorEnableCollision(false);
            Pawn->SetActorHiddenInGame(true);
            Pawn->GetCharacterMovement()->StopMovementImmediately();
            Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Flying);
            Pawn->SetActorLocation(Gate->GetActorTransform().TransformPosition({0,310,150}));
            Camera=W->SpawnActor<ACameraActor>();
            if(!Camera.IsValid()){bOK=false;return Finish(TEXT("no camera"));}
            if(auto* HUD=PC->GetHUD())HUD->bShowHUD=false;
            PC->ConsoleCommand(TEXT("showflag.HUD 0"),false);
        }
        if(!Gate.IsValid()){bOK=false;return Finish(TEXT("gate removed"));}
        if(Phase==0)
        {
            if(++Index>=UE_ARRAY_COUNT(Views))return Finish(TEXT("finished"));
            const FView& V=Views[Index];
            if(V.Probe==EProbe::Repair)
            {
                if(!bRepairSandbox)return Finish(TEXT("finished"));
                auto* Status=PC->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
                const int32 Cost=Gate->GetRepairSoulCost();
                if(!Status || (Status->SoulBalance()<Cost && !Status->GrantSouls(Cost-Status->SoulBalance())))
                {bOK=false;return Finish(TEXT("review wallet unavailable"));}
                WalletBefore=Status->SoulBalance();
                Gate->TakeDamage(300.f,FDamageEvent(),PC,Pawn);
                Report+=FString::Printf(TEXT("before-repair health=%.1f wallet=%lld\n"),Gate->GetHealth(),WalletBefore);
            }
            const FTransform Pose=Gate->GetActorTransform();
            const FVector Eye=Pose.TransformPosition(V.Eye),Target=Pose.TransformPosition(V.Target);
            const FRotator Aim=(Target-Eye).Rotation();
            Camera->SetActorLocationAndRotation(Eye,Aim);
            Camera->GetCameraComponent()->SetFieldOfView(V.FOV);
            PC->SetControlRotation(Aim);
            PC->SetViewTarget(Camera.Get());
            Phase=1;After=Now+(Index==0?12.:2.8);
            return true;
        }
        const FView& V=Views[Index];
        const FString Path=Out/(FString(V.Name)+TEXT(".png"));
        if(Phase==1 && V.Probe!=EProbe::None)
        {
            const auto Focus=ColdSteelWorldInteraction::TraceUseTargets(PC);
            const EHighGateUse Expected=(V.Probe==EProbe::Raise || V.Probe==EProbe::Lower)?EHighGateUse::Release:EHighGateUse::Repair;
            const bool bFocus=Focus.Target==Gate.Get() && Focus.GateUse==Expected;
            if(bFocus)
            {
                static_cast<APlayerController*>(PC)->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E,IE_Pressed,1.f));
                static_cast<APlayerController*>(PC)->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E,IE_Released,0.f));
            }
            bOK&=bFocus;
            Report+=FString::Printf(TEXT("%s correct_focus=%d health=%.1f\n"),V.Name,bFocus,Gate->GetHealth());
            Phase=2;After=Now+4.5;
            return true;
        }
        if(Phase<=2)
        {
            if(V.Probe!=EProbe::None)
            {
                const double Height=Gate->GetMasonry()->GetRelativeLocation().Z;
                const bool bPose=V.Probe==EProbe::Raise?Height>470.:Height<1.;
                bOK&=bPose;
                if(V.Probe==EProbe::Repair)
                {
                    auto* Status=PC->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
                    const int64 Paid=WalletBefore-Status->SoulBalance();
                    const bool bPaid=Paid==Gate->GetRepairSoulCost() && Gate->GetHealth()==Gate->GetMaximumHealth();
                    bOK&=bPaid;
                    Report+=FString::Printf(TEXT("after-repair health=%.1f souls_paid=%lld correct_payment=%d\n"),Gate->GetHealth(),Paid,bPaid);
                }
                Report+=FString::Printf(TEXT("%s height_cm=%.1f correct_pose=%d\n"),V.Name,Height,bPose);
            }
            FScreenshotRequest::RequestScreenshot(Path,false,false);
            Phase=3;After=Now+.4;return true;
        }
        if(IFileManager::Get().FileSize(*Path)>0)
        {
            if(bCourtyardOnly)return Finish(TEXT("courtyard captured"));
            Phase=0;
        }
        return true;
    }
};
static FAutoConsoleCommandWithWorld Command(TEXT("fps.Review.VillageGateWard"),TEXT("Capture the generated high gate and its E interactions in an isolated review host."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
    {
        FString Out;
        if(!World || !World->IsGameWorld() || !FParse::Value(FCommandLine::Get(),TEXT("GateWardReviewOutput="),Out) || Out.IsEmpty())return;
        IFileManager::Get().MakeDirectory(*Out,true);
        auto Review=MakeShared<FReview>();Review->World=World;Review->Out=Out;
        Review->bCourtyardOnly=FParse::Param(FCommandLine::Get(),TEXT("GateWardCourtyardOnly"));
        // Only change a wallet and a defense save inside an explicitly named review copy.
        FString Profile;
        Review->bRepairSandbox=FParse::Param(FCommandLine::Get(),TEXT("GateWardRepairSandbox"))
            && FParse::Value(FCommandLine::Get(),TEXT("ColdSteelProfile="),Profile) && Profile==TEXT("GateWardReview")
            && FPaths::IsUnderDirectory(FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()),FPaths::GetPath(Out));
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Review](float Dt){return Review->Tick(Dt);}),.15f);
    }));
}
#endif
