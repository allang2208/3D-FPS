#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

// Opt-in 实机取证（独立 -game 进程）：装 M4 → 触发步枪快速进战 → 逐帧记录
// 枪托/枪口在屏幕上的投影与相机距离，并按 30Hz 截图。只取证不判定：
// "枪托有没有像参考一样往前扫"以这里的屏幕轨迹与帧图为准。
void AFPSGAMECharacter::RunQuickCombatAcceptance(float DeltaSeconds)
{
    struct FRun
    {
        int32 Phase = 0, LastFrame = -1;
        float Start = 0.f;
        FString Out, CSV, ClipPath, MeshPath;
        bool bLoggedIdle = false;
    };
    static FRun Run;
    auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* PC = Cast<APlayerController>(Controller);
    const float Now = GetWorld()->GetTimeSeconds();
    if (Now < 1.f) return;
    if (!Profile || !Profile->IsAudit() || !Profile->ProfileSlot().Contains(TEXT("QuickCombatAudit")) || !PC)
    {
        UE_LOG(LogTemp, Error, TEXT("QUICKCOMBAT_AUDIT unsafe or missing fixture"));
        FPlatformMisc::RequestExitWithStatus(false, 1); return;
    }
    const auto Record = [&](const FString& Line)
    {
        UE_LOG(LogTemp, Display, TEXT("%s"), *Line);
        FFileHelper::SaveStringToFile(Line + TEXT("\n"), *(Run.Out / TEXT("results.log")),
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
    };
    if (Run.Out.IsEmpty())
    {
        FString Label; FParse::Value(FCommandLine::Get(), TEXT("GunplayLabel="), Label);
        Run.Out = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("QuickCombatAudit") / FPaths::MakeValidFileName(Label));
        IFileManager::Get().MakeDirectory(*Run.Out, true);
        auto State = Profile->Snapshot(); State.Items.Reset(); State.Hotbar.Init(TEXT(""), 4); State.HotbarDefinitions.Init(TEXT(""), 4);
        auto Item = Profile->CreateItem(TEXT("ue_m4a1")); Item.Place = 1; Item.Cell = 9; Item.Magazine = 17;
        State.Items.Add(Item); State.ActiveWeaponSlot = 9; State.Stamina = Profile->MaxStamina();
        Record(FString::Printf(TEXT("QUICKCOMBAT_FIXTURE commit=%d"), Profile->CommitState(State) ? 1 : 0));
        Run.Start = Now + 1.0f;
        Run.CSV = TEXT("time,butt_u,butt_v,butt_in,muzzle_u,muzzle_v,muzzle_in,butt_dist_cm,muzzle_dist_cm,\n");
        Run.CSV.Append(TEXT("cam_x,cam_y,cam_z,cam_pitch,cam_yaw,cam_roll,root_x,root_y,root_z,root_pitch,root_yaw,root_roll,butt_x,butt_y,butt_z,muzzle_x,muzzle_y,muzzle_z\n"));
    }
    if (Run.Phase == 0)
    {
        if (Now < Run.Start || IsWeaponBusy() || !AKMViewmodel || !AKMViewmodel->GetSkeletalMeshAsset()) return;
        UAnimSequence* Clip = RifleQuickCombatClip(ResolveRifleGripProfile());
        Run.ClipPath = GetPathNameSafe(Clip);
        Run.MeshPath = GetNameSafe(AKMViewmodel->GetSkeletalMeshAsset());
        Record(FString::Printf(TEXT("QUICKCOMBAT_CLIP mesh=%s clip=%s length=%.4f"),
            *Run.MeshPath, *Run.ClipPath, Clip ? Clip->GetPlayLength() : -1.f));
        TriggerRifleStockMelee();
        Run.Phase = 1; Run.Start = Now;
    }
    const float T = Now - Run.Start;
    AKMViewmodel->TickAnimation(0.f, false); AKMViewmodel->RefreshBoneTransforms(); AKMViewmodel->UpdateChildTransforms();
    const FTransform Root = AKMViewmodel->GetSocketTransform(TEXT("WPN_root"));
    // 骨架导入带 0.01 缩放：socket 局部单位是"导入单位"，26cm 世界 = 局部 0.26。
    // M4 臂架 +Y 为**前**：枪托底在局部 −Y（g4 实测 +0.26 落在枪口侧——探针方向曾反）。
    const FVector Butt = Root.TransformPosition(FVector(0.f, -0.26f, 0.f));   // 枪托底≈枪根局部 −Y（向后）
    const FVector Muzzle = AKMViewmodel->GetSocketLocation(TEXT("WPN_SOCKET_Muzzle"));
    if (!Run.bLoggedIdle)
    {
        Run.bLoggedIdle = true;
        Record(FString::Printf(TEXT("QUICKCOMBAT_SANITY root_to_butt_cm=%.1f root_to_muzzle_cm=%.1f"),
            FVector::Dist(Butt, Root.GetLocation()), FVector::Dist(Muzzle, Root.GetLocation())));
    }
    int32 Width, Height; PC->GetViewportSize(Width, Height);
    const auto Project = [&](const FVector& World, double& U, double& V, int32& In)
    {
        FVector2D Screen;
        if (PC->ProjectWorldLocationToScreen(World, Screen) && Screen.X > -20000.f && Screen.X < 20000.f)
        { U = Screen.X / Width; V = Screen.Y / Height; In = 1; }
        else { U = V = -99; In = 0; }   // 相机身后/出画标记
    };
    double BU = 0, BV = 0, MU = 0, MV = 0; int32 BI = 0, MI = 0;
    Project(Butt, BU, BV, BI); Project(Muzzle, MU, MV, MI);
    const FTransform Camera = FirstPersonCamera->GetComponentTransform();
    const float ButtDist = FVector::Dist(Butt, Camera.GetLocation()), MuzzleDist = FVector::Dist(Muzzle, Camera.GetLocation());
    Run.CSV += FString::Printf(TEXT("%.4f,%.3f,%.3f,%d,%.3f,%.3f,%d,%.1f,%.1f,%.1f,%.1f,%.1f,%.2f,%.2f,%.2f,%.1f,%.1f,%.1f,%.2f,%.2f,%.2f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f\n"),
        T, BU, BV, BI, MU, MV, MI, ButtDist, MuzzleDist,
        Camera.GetLocation().X, Camera.GetLocation().Y, Camera.GetLocation().Z, Camera.Rotator().Pitch, Camera.Rotator().Yaw, Camera.Rotator().Roll,
        Root.GetLocation().X, Root.GetLocation().Y, Root.GetLocation().Z, Root.Rotator().Pitch, Root.Rotator().Yaw, Root.Rotator().Roll,
        Butt.X, Butt.Y, Butt.Z, Muzzle.X, Muzzle.Y, Muzzle.Z);
    if (FParse::Param(FCommandLine::Get(), TEXT("GunplayCaptureFrames")))
    {
        const int32 Frame = FMath::FloorToInt(T * 30.f);
        if (Frame >= 0 && Frame != Run.LastFrame && !FScreenshotRequest::IsScreenshotRequested())
        {
            Run.LastFrame = Frame;
            FScreenshotRequest::RequestScreenshot(Run.Out / FString::Printf(TEXT("Frame_%04d.png"), Frame), false, false);
        }
    }
    if (T >= 2.6f)   // 1.5s 后仍留 1.1s,让最后的截图异步回读落盘再退
    {
        FFileHelper::SaveStringToFile(Run.CSV, *(Run.Out / TEXT("screens.csv")));
        TArray<FString> Found; IFileManager::Get().FindFiles(Found, *(Run.Out / TEXT("Frame_*.png")), true, false);
        Record(FString::Printf(TEXT("QUICKCOMBAT_AUDIT_COMPLETE clip=%s frames_seen=%d png_on_disk=%d"),
            *Run.ClipPath, Run.LastFrame + 1, Found.Num()));
        bRunGunplayAcceptance = false;
        FPlatformMisc::RequestExitWithStatus(false, 0);
    }
}
