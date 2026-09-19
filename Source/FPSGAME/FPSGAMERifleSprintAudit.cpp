#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/GunsmithSystem.h"
#include "Weapons/FPSGunplayAnimInstance.h"
#include "Weapons/M4TacticalSprintComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

// Opt-in, isolated-profile runtime coverage of the actual equipped meshes,
// attachment selection, controller inputs, animation blend and rendered camera.
void AFPSGAMECharacter::RunRifleSprintAcceptance(float DeltaSeconds)
{
    struct FRun
    {
        int32 Case = -1, Event = 0, LastFrame = -1, Failures = 0, Samples = 0, Visible = 0;
        float Start = 0.f, ReadyAt = 0.f, MaxRightDrift = 0.f, RecoveryError = 0.f;
        FVector Origin, RightContact, LeftContact;
        bool bStarted = false, bConfigured = false, bSawSprint = false, bRecovered = false;
        FString Out, Name, CSV;
    };
    static FRun Run;
    auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* Gunsmith = GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    auto* PC = Cast<APlayerController>(Controller);
    const float Now = GetWorld()->GetTimeSeconds();
    if (Now < 2.f) return;
    if (!Profile || !Profile->IsAudit() || !Profile->ProfileSlot().Contains(TEXT("RifleSprintAudit")) || !Gunsmith || !PC)
    {
        UE_LOG(LogTemp, Error, TEXT("RIFLE_SPRINT_AUDIT unsafe or missing fixture"));
        FPlatformMisc::RequestExitWithStatus(false, 1); return;
    }
    const auto Key = [&](const FKey& K, bool Press)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(K, Press ? IE_Pressed : IE_Released, Press ? 1.f : 0.f));
    };
    const auto Record = [&](const FString& Line)
    {
        UE_LOG(LogTemp, Display, TEXT("%s"), *Line);
        FFileHelper::SaveStringToFile(Line + TEXT("\n"), *(Run.Out / TEXT("results.log")),
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
    };
    const auto Check = [&](bool OK, const FString& Label)
    {
        if (!OK) ++Run.Failures;
        Record(FString::Printf(TEXT("RIFLE_SPRINT_ASSERT %s %s %s"), OK ? TEXT("PASS") : TEXT("FAIL"), *Run.Name, *Label));
    };
    if (Run.Out.IsEmpty())
    {
        FString Label; FParse::Value(FCommandLine::Get(), TEXT("GunplayLabel="), Label);
        Run.Out = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("RifleSprintAudit") / FPaths::MakeValidFileName(Label));
        IFileManager::Get().MakeDirectory(*Run.Out, true);
        Run.Origin = GetActorLocation();
    }
    if (Run.Case < 0 || (Run.bStarted && Now - Run.Start >= 4.3f))
    {
        if (Run.Case >= 0)
        {
            Check(Run.bSawSprint, TEXT("entered actual sprint with loaded clips"));
            Check(Run.Samples > 15 && Run.Visible == 0, FString::Printf(TEXT("left hand outside view samples=%d visible=%d"), Run.Samples, Run.Visible));
            Check(Run.bRecovered && Run.RecoveryError < .5f, FString::Printf(TEXT("returned to installed grip error_cm=%.5f"), Run.RecoveryError));
            Check(Run.MaxRightDrift < .5f, FString::Printf(TEXT("right hand stays on weapon drift_cm=%.5f"), Run.MaxRightDrift));
            FFileHelper::SaveStringToFile(Run.CSV, *(Run.Out / Run.Name / TEXT("poses.csv")));
        }
        Key(EKeys::W, false); Key(EKeys::LeftShift, false);
        if (++Run.Case >= 18)
        {
            Record(FString::Printf(TEXT("RIFLE_SPRINT_AUDIT_COMPLETE cases=18 failures=%d"), Run.Failures));
            bRunGunplayAcceptance = false;
            FPlatformMisc::RequestExitWithStatus(false, Run.Failures ? 1 : 0); return;
        }
        const TCHAR* Weapons[] = {TEXT("ue_m4a1"), TEXT("ue_akm"), TEXT("ue_qbz191")};
        const TCHAR* Names[] = {TEXT("M4"), TEXT("AKM"), TEXT("QBZ191")};
        const TCHAR* Grips[] = {TEXT("Base"), TEXT("Drum"), TEXT("Angled"), TEXT("Vertical"), TEXT("Canted"), TEXT("Prism")};
        const int32 Weapon = Run.Case / 6, Grip = Run.Case % 6;
        Run.Name = FString(Names[Weapon]) + TEXT("_") + Grips[Grip];
        IFileManager::Get().MakeDirectory(*(Run.Out / Run.Name), true);
        SetActorLocation(Run.Origin, false, nullptr, ETeleportType::TeleportPhysics);
        GetCharacterMovement()->StopMovementImmediately(); PC->SetControlRotation(FRotator::ZeroRotator);
        auto State = Profile->Snapshot(); State.Items.Reset(); State.Hotbar.Init(TEXT(""), 4); State.HotbarDefinitions.Init(TEXT(""), 4);
        auto Item = Profile->CreateItem(Weapons[Weapon]); Item.Place = 1; Item.Cell = 9; Item.Magazine = 17;
        State.Items.Add(Item); State.ActiveWeaponSlot = 9; State.Stamina = Profile->MaxStamina(); State.bSprintExhausted = false;
        Check(Profile->CommitState(State), TEXT("isolated equipped weapon fixture"));
        Run.ReadyAt = Now + 1.2f; Run.bStarted = Run.bConfigured = false; Run.Event = 0; Run.LastFrame = -1;
        Run.Samples = Run.Visible = 0; Run.MaxRightDrift = Run.RecoveryError = 0.f;
        Run.bSawSprint = Run.bRecovered = false;
        Run.CSV = TEXT("time,sprint,progress,loop_alpha,speed,left_x,left_y,left_z,right_x,right_y,right_z,gun_x,gun_y,gun_z,hand_visible\n");
        return;
    }
    if (!Run.bStarted)
    {
        if (Now < Run.ReadyAt || IsWeaponBusy()) return;
        if (!Run.bConfigured)
        {
            const int32 Grip = Run.Case % 6;
            const TCHAR* Options[] = {TEXT("false"), TEXT("false"), TEXT("angled_foregrip"), TEXT("vertical_foregrip"), TEXT("canted_foregrip"), TEXT("prism_handstop")};
            if (Grip > 0)
            {
                const bool OK = Gunsmith->Begin(Profile->Equipped()->InstanceId)
                    && Gunsmith->Select(Grip == 1 ? TEXT("magazine") : TEXT("underbarrel"), Grip == 1 ? TEXT("large_drum") : Options[Grip])
                    && Gunsmith->Apply();
                Check(OK, TEXT("installed configuration through gunsmith: ") + Gunsmith->Message());
                Gunsmith->Close();
            }
            Run.bConfigured = true; Run.ReadyAt = Now + .4f; return;
        }
        Run.Start = Now; Run.bStarted = true;
        Record(FString::Printf(TEXT("RIFLE_SPRINT_ASSETS %s mesh=%s idle=%s sprint=%s"), *Run.Name,
            *GetNameSafe(AKMViewmodel->GetSkeletalMeshAsset()), *GetPathNameSafe(GunplayAnimation->IdleClip), *GetPathNameSafe(GunplayAnimation->SprintClip)));
    }
    const float Time = Now - Run.Start;
    // Hold > 0.2 s before releasing Shift so interrupted entry exercises sprint,
    // rather than invoking the independent short-tap dodge binding.
    const float At[] = {0.f, .45f, 1.85f, 2.40f, 2.64f, 2.72f, 3.03f, 3.80f};
    while (Run.Event < UE_ARRAY_COUNT(At) && Time >= At[Run.Event])
    {
        const int32 E = Run.Event++;
        Key(E == 0 || E == 7 ? EKeys::W : EKeys::LeftShift, E == 0 || E == 1 || E == 3 || E == 5);
    }
    AKMViewmodel->TickAnimation(0.f, false); AKMViewmodel->RefreshBoneTransforms(); AKMViewmodel->UpdateChildTransforms();
    const FTransform Root = AKMViewmodel->GetSocketTransform(TEXT("WPN_root"));
    const FVector Left = AKMViewmodel->GetSocketLocation(TEXT("hand_l"));
    const FVector Right = AKMViewmodel->GetSocketLocation(TEXT("hand_r"));
    const FVector RContact = Root.InverseTransformPosition(Right), LContact = Root.InverseTransformPosition(Left);
    if (Time < .03f) { Run.RightContact = RContact; Run.LeftContact = LContact; }
    // Convert local contact error back to centimetres; some imported rigs have scaled roots.
    Run.MaxRightDrift = FMath::Max(Run.MaxRightDrift, Root.TransformVector(RContact - Run.RightContact).Size());
    auto* Sprint = FindComponentByClass<UM4TacticalSprintComponent>();
    const float Progress = Sprint ? Sprint->PoseProgress() : 0.f;
    const bool Steady = Time > .95f && Time < 1.80f;
    bool Visible = false;
    int32 Width, Height; PC->GetViewportSize(Width, Height);
    for (const FName Bone : {FName(TEXT("hand_l")), FName(TEXT("thumb_03_l")), FName(TEXT("index_03_l")), FName(TEXT("middle_03_l")), FName(TEXT("ring_03_l")), FName(TEXT("pinky_03_l"))})
    {
        FVector2D Screen;
        if (PC->ProjectWorldLocationToScreen(AKMViewmodel->GetSocketLocation(Bone), Screen)
            && Screen.X >= -12.f && Screen.X <= Width + 12.f && Screen.Y >= -12.f && Screen.Y <= Height + 12.f) Visible = true;
    }
    if (Steady)
    {
        ++Run.Samples; if (Visible) ++Run.Visible;
        Run.bSawSprint |= bIsSprinting && Progress > .99f && Sprint->OwnsPose();
    }
    if (Time > 3.55f && Time < 3.75f)
    {
        Run.bRecovered |= !bIsSprinting && Progress < .001f;
        Run.RecoveryError = FMath::Max(Run.RecoveryError, Root.TransformVector(LContact - Run.LeftContact).Size());
    }
    const FTransform Camera = FirstPersonCamera->GetComponentTransform();
    const FVector L = Camera.InverseTransformPosition(Left), R = Camera.InverseTransformPosition(Right), W = Camera.InverseTransformPosition(Root.GetLocation());
    Run.CSV += FString::Printf(TEXT("%.6f,%d,%.6f,%.6f,%.3f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%d\n"),
        Time, bIsSprinting, Progress, GunplayAnimation->SprintLoopAlpha, HorizontalSpeed(), L.X,L.Y,L.Z,R.X,R.Y,R.Z,W.X,W.Y,W.Z,Visible);
    if (FParse::Param(FCommandLine::Get(), TEXT("GunplayCaptureFrames")))
    {
        const int32 Frame = FMath::FloorToInt(Time * 20.f);
        if (Frame != Run.LastFrame && !FScreenshotRequest::IsScreenshotRequested())
        {
            Run.LastFrame = Frame;
            FScreenshotRequest::RequestScreenshot(Run.Out / Run.Name / FString::Printf(TEXT("Frame_%04d.png"), Frame), false, false);
        }
    }
}
