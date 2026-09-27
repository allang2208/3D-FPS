#include "GrassDeformSubsystem.h"

#if !UE_BUILD_SHIPPING
#include "GrassDeformSettings.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

// Explicit opt-in, isolated -game fixture. It uses real CharacterMovement and production
// materials. Capture/readback and forced camera/speed changes never run in normal play.
void UGrassDeformSubsystem::RunGrassResponseAudit(float DeltaTime)
{
    static const bool Active = FParse::Param(FCommandLine::Get(), TEXT("GrassResponseAudit"));
    if (!Active) return;
    UWorld* World = GetWorld();
    if (!World || World->WorldType != EWorldType::Game || !World->HasBegunPlay()) return;
    struct FState
    {
        int32 Phase = 0, Frame = 0, Checks = 0, Failed = 0, RecoverySample = 0;
        double StartWall = 0, PhaseStart = 0, CaptureStart = 0, NextCapture = 0;
        float ContactTime = 0;
        FVector StopPosition = FVector::ZeroVector;
        FString Dir;
        TArray<FString> Report, Frames;
    };
    static FState S;
    const double Now = World->GetTimeSeconds();
    if (S.Dir.IsEmpty())
    {
        FString Label = TEXT("v12");
        FParse::Value(FCommandLine::Get(), TEXT("GrassAuditLabel="), Label);
        S.Dir = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("GrassResponseAudit20260927") / Label);
        IFileManager::Get().MakeDirectory(*(S.Dir / TEXT("frames")), true);
        S.StartWall = FPlatformTime::Seconds();
        S.PhaseStart = Now;
        S.Frames.Add(TEXT("frame,game_seconds,phase,phase_seconds,pawn_x,pawn_y"));
    }
    auto Record = [&](const FString& Line)
    {
        S.Report.Add(Line);
        UE_LOG(LogTemp, Display, TEXT("GRASS_RESPONSE %s"), *Line);
        FFileHelper::SaveStringArrayToFile(S.Report, *(S.Dir / TEXT("results.txt")));
    };
    auto Check = [&](const TCHAR* Name, bool Pass, const FString& Detail = FString())
    {
        ++S.Checks;
        if (!Pass) ++S.Failed;
        Record(FString::Printf(TEXT("%s %s %s"), Pass ? TEXT("PASS") : TEXT("FAIL"), Name, *Detail));
    };
    if (S.Phase == 99) return;
    if (FPlatformTime::Seconds() - S.StartWall > 240)
    {
        Check(TEXT("watchdog"), false, FString::FromInt(S.Phase));
        FPlatformMisc::RequestExitWithStatus(false, 1);
        S.Phase = 99;
        return;
    }
    APlayerController* PC = World->GetFirstPlayerController();
    ACharacter* Pawn = PC ? Cast<ACharacter>(PC->GetPawn()) : nullptr;
    if (!Pawn) return;
    auto* Move = Pawn->GetCharacterMovement();
    auto Next = [&](int32 Phase)
    {
        S.Phase = Phase;
        S.PhaseStart = Now;
        Record(FString::Printf(TEXT("PHASE %d time=%.3f location=%s"), Phase, Now, *Pawn->GetActorLocation().ToString()));
    };
    auto Probe = [&](const FVector& Position, float& Peak, float& Time, float& Amount)
    {
        TArray<FFloat16Color> Mask;
        TArray<FLinearColor> Times;
        auto* RT = GetReadTarget();
        auto* TimeRT = ContactTimeTargets[ReadIndex].Get();
        FReadSurfaceDataFlags Flags(RCM_MinMax);
        Flags.SetLinearToGamma(false);
        if (!RT || !TimeRT || !RT->GameThread_GetRenderTargetResource()->ReadFloat16Pixels(Mask)
            || !TimeRT->GameThread_GetRenderTargetResource()->ReadLinearColorPixels(Times, Flags)) return false;
        const FVector2D UV = (FVector2D(Position.X, Position.Y) - WindowCenter) / GrassDeformTuning::WindowSizeCm + FVector2D(.5,.5);
        const int32 X = FMath::FloorToInt(UV.X * ActiveRTSize), Y = FMath::FloorToInt(UV.Y * ActiveRTSize);
        const int32 I = Y * ActiveRTSize + X;
        if (X < 0 || Y < 0 || X >= ActiveRTSize || Y >= ActiveRTSize || !Mask.IsValidIndex(I) || !Times.IsValidIndex(I)) return false;
        Peak = Mask[I].R.GetFloat();
        Time = Times[I].R;
        const float T = FMath::Clamp((float(Now) - Time - Response->HoldSeconds) / FMath::Max(Response->RecoverSeconds, .05f), 0.f, 1.f);
        Amount = Peak * (1.f - T*T*(3.f-2.f*T));
        return true;
    };
    float Peak = 0, Contact = 0, Amount = 0;
    switch (S.Phase)
    {
    case 0:
        if (Now - S.PhaseStart < 8) break;
        Record(FString::Printf(TEXT("SETTINGS hold=%.3f recover=%.3f"),Response->HoldSeconds,Response->RecoverSeconds));
        Check(TEXT("enabled_and_v12_time_targets"), IsEnabled() && ContactTimeTargets[0] && ContactTimeTargets[1]);
        Move->StopMovementImmediately();
        Move->DisableMovement();
        Pawn->SetActorLocation(FVector(-2150,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2), false);
        Pawn->SetActorHiddenInGame(true);
        PC->SetControlRotation(FRotator::ZeroRotator);
        {
            const FVector Eye(-1950,-510,360), Focus(-1575,0,65);
            auto* Camera = World->SpawnActor<ACameraActor>(Eye, (Focus-Eye).Rotation());
            Camera->GetCameraComponent()->SetFieldOfView(66.f);
            PC->SetViewTarget(Camera);
        }
        DiscardInteractionState();
        Next(1);
        break;
    case 1:
        if (Now-S.PhaseStart < 2) break; // settle camera/exposure before recording
        S.CaptureStart = Now;
        S.NextCapture = Now;
        Next(2);
        break;
    case 2:
        if (Now-S.PhaseStart < 1) break;
        Move->SetMovementMode(MOVE_Walking);
        Next(3);
        break;
    case 3:
        Move->MaxWalkSpeed = 260.f;
        Pawn->AddMovementInput(FVector::ForwardVector, 1.f, true);
        if (Pawn->GetActorLocation().X < -1450) break;
        Move->StopMovementImmediately();
        S.StopPosition = Pawn->GetActorLocation();
        Check(TEXT("real_walk_7m_grounded"), Move->IsMovingOnGround() && S.StopPosition.X > -1470, S.StopPosition.ToString());
        Next(4);
        break;
    case 4:
        Move->StopMovementImmediately();
        if (Now-S.PhaseStart < 10) break;
        Check(TEXT("standing_10s_remains_pressed"), Probe(S.StopPosition,Peak,Contact,Amount) && Amount>.88f && Now-Contact<.25,
            FString::Printf(TEXT("elapsed=%.3f"),Now-S.PhaseStart));
        Record(FString::Printf(TEXT("STANDING peak=%.4f amount=%.4f contact_age=%.3f"),Peak,Amount,Now-Contact));
        Check(TEXT("core_width_at_50cm"), Probe(S.StopPosition+FVector(0,50,0),Peak,Contact,Amount) && Amount>.84f);
        Check(TEXT("outside_at_100cm_untouched"), Probe(S.StopPosition+FVector(0,100,0),Peak,Contact,Amount) && Amount<.01f);
        Next(5);
        break;
    case 5:
        Move->MaxWalkSpeed = 260.f;
        Pawn->AddMovementInput(FVector::ForwardVector,1.f,true);
        // Stop just beyond contact so short hold presets can still be sampled.
        if (Pawn->GetActorLocation().X < S.StopPosition.X+FMath::Max(Response->BodyRadiusCm,
            Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius()*GrassDeformTuning::TrampleRadiusScale)+40.f) break;
        Move->StopMovementImmediately();
        Check(TEXT("departed_contact_time_read"), Probe(S.StopPosition,Peak,Contact,Amount) && Contact>0);
        S.ContactTime = Contact;
        Record(FString::Printf(TEXT("RELEASE last_contact=%.4f now=%.4f peak=%.4f"),Contact,Now,Peak));
        Next(6);
        break;
    case 6:
    {
        const float Age = float(Now) - S.ContactTime;
        const float Targets[] = {Response->HoldSeconds*.5f,
            Response->HoldSeconds+Response->RecoverSeconds*.5f,
            Response->HoldSeconds+Response->RecoverSeconds+.25f};
        if (S.RecoverySample < 3 && Age >= Targets[S.RecoverySample])
        {
            const bool ReadOK = Probe(S.StopPosition,Peak,Contact,Amount);
            const bool Pass = S.RecoverySample == 0 ? Amount>.88f : (S.RecoverySample == 1 ? Amount>.2f && Amount<.75f : Amount<.01f);
            const TCHAR* Names[] = {TEXT("hold_phase"), TEXT("recovery_midpoint"), TEXT("recovered_after_duration")};
            Check(Names[S.RecoverySample], ReadOK && Pass,
                FString::Printf(TEXT("age=%.3f peak=%.4f amount=%.4f"),Age,Peak,Amount));
            ++S.RecoverySample;
        }
        if (Age > Response->HoldSeconds+Response->RecoverSeconds+1.5f) Next(7);
        break;
    }
    case 7:
        if (Now-S.PhaseStart < 1.5) break;
        {
            TArray<FString> Files;
            IFileManager::Get().FindFiles(Files, *(S.Dir / TEXT("frames/*.png")), true, false);
            Check(TEXT("frames_saved"), Files.Num()>100 && Files.Num()==S.Frame,
                FString::Printf(TEXT("requested=%d saved=%d"),S.Frame,Files.Num()));
            Record(FString::Printf(TEXT("COMPLETE checks=%d failed=%d frames=%d"), S.Checks,S.Failed,Files.Num()));
            S.Phase = 99;
            FPlatformMisc::RequestExitWithStatus(false,S.Failed?1:0);
        }
        break;
    }
    if (S.Phase>=2 && S.Phase<=6 && Now>=S.NextCapture && !FScreenshotRequest::IsScreenshotRequested())
    {
        const FVector P = Pawn->GetActorLocation();
        FScreenshotRequest::RequestScreenshot(S.Dir / FString::Printf(TEXT("frames/frame_%04d.png"),S.Frame),false,false);
        S.Frames.Add(FString::Printf(TEXT("%d,%.6f,%d,%.6f,%.4f,%.4f"),S.Frame,Now-S.CaptureStart,S.Phase,Now-S.PhaseStart,P.X,P.Y));
        FFileHelper::SaveStringArrayToFile(S.Frames,*(S.Dir / TEXT("frames.csv")));
        ++S.Frame;
        S.NextCapture = Now + .1; // 10 Hz actual game timestamps recorded for GIF timing.
    }
}
#endif
