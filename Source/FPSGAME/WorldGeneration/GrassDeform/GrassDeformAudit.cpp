// GrassDeformAudit: development-only self-driven fixture for the "grass never reacts" backlog
// item (Docs/Backlog.md G1). Member functions of UGrassDeformSubsystem live here so the runtime
// file stays free of diagnostics code; everything in this translation unit is stripped from
// shipping builds.
//
// Launch:
//   UnrealEditor.exe FPSGAME.uproject <map> -game -windowed -ResX=1280 -ResY=720 -GrassDeformAudit
//
// Stages (world-time driven; every step logs one GRASS_AUDIT line and lands in
// Saved/GrassDeform/audit_report.txt):
//   0  arm: force r.GrassDeform 1 / sg.FoliageQuality 4, wait for the hills streaming layers,
//      inventory every grass ISM near the pawn (component / instance count / material chain) and
//      pick the nearest clump as the target. The inventory answers "does the rendered grass
//      actually derive from MA_Grass" without opening an editor: if it does not, MF_GrassDeform
//      is never in the shader and no amount of RT work can show up.
//   1  camera: park the player camera above the target; two stills 0.25 s apart. The pair is the
//      wind-sway control: world position offset is alive on this grass iff the two frames differ.
//   2  stamp: StampTrample strength 1, radius 150 cm, right on the clump.
//   3  readback: ReadPixels on BOTH sides of the RT pair (mask presence, extent, direction
//      encoding) plus every MPC parameter the shader consumes (bEnabled / ReadIsB / Center /
//      WindowSize / WorldTime), so a dead uniform is caught without a GPU capture.
//   4  camera again: two stills with the same POV as stage 1.
//   5  walk: teleport next to the clump and drive ~3 s of 300 cm/s movement with a matching
//      velocity, so the 10 Hz trample source's speed gate passes. Read the mask again after.
//   6  report + quit (2.5 s tail so the async screenshots flush to disk first).
//
// Verdict reading (mirrors the G1 diagnostic ladder):
//   - masked texels = 0            -> pass side (DrawMaterial / parameters / window UV maths).
//   - mask present, stills unchanged -> material side (MF chain, MA_Grass wiring, MI overrides).
//   - before_1 == before_2         -> WPO itself is dead for this grass (wind control pair).

#include "GrassDeformSubsystem.h"

#if !UE_BUILD_SHIPPING

#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "UnrealClient.h"
#include "UObject/UObjectIterator.h"

namespace
{
    TArray<FString>& GrassAuditReport()
    {
        static TArray<FString> Lines;
        return Lines;
    }

    void GrassAuditLog(const FString& Line)
    {
        GrassAuditReport().Add(Line);
        UE_LOG(LogTemp, Display, TEXT("GRASS_AUDIT: %s"), *Line);
    }

    void GrassAuditShot(UWorld* World, const FString& Name)
    {
        const FString Dir = FPaths::ProjectSavedDir() / GrassDeformTuning::DumpDirectory / TEXT("Audit");
        IFileManager::Get().MakeDirectory(*Dir, true);
        FScreenshotRequest::RequestScreenshot(Dir / (Name + TEXT(".png")), false, false);
        GrassAuditLog(FString::Printf(TEXT("screenshot requested: %s"), *Name));
    }

    void GrassAuditWriteReport()
    {
        const FString Dir = FPaths::ProjectSavedDir() / GrassDeformTuning::DumpDirectory;
        IFileManager::Get().MakeDirectory(*Dir, true);
        FFileHelper::SaveStringArrayToFile(GrassAuditReport(), *(Dir / TEXT("audit_report.txt")));
    }
}

bool UGrassDeformSubsystem::AuditReadRenderTarget(UTextureRenderTarget2D* RT, TArray<FColor>& OutPixels)
{
    OutPixels.Reset();
    if (!RT) return false;
    FRenderTarget* Resource = RT->GameThread_GetRenderTargetResource();
    return Resource && Resource->ReadPixels(OutPixels);
}

void UGrassDeformSubsystem::AuditLogRenderTargetStats(const TCHAR* Side, UTextureRenderTarget2D* RT, int64& OutMaskedTexels)
{
    OutMaskedTexels = -1;
    GrassAuditLog(FString::Printf(TEXT("window: center=(%.0f,%.0f) readIndex=%d initialized=%d"),
        WindowCenter.X, WindowCenter.Y, ReadIndex, bWindowInitialized ? 1 : 0));
    if (!RT)
    {
        GrassAuditLog(FString::Printf(TEXT("RT%c: <null>"), *Side));
        return;
    }
    if (UWorld* World = GetWorld())
    {
        // PNG ground truth alongside the numeric stats: catches "the numbers say zero and the
        // pixels really are zero" vs "the readback lies".
        const FString Dir = FPaths::ProjectSavedDir() / GrassDeformTuning::DumpDirectory / TEXT("Audit");
        IFileManager::Get().MakeDirectory(*Dir, true);
        const FString Png = FString::Printf(TEXT("rt_%s_%03d.png"), Side, AuditPngCounter++);
        UKismetRenderingLibrary::ExportRenderTarget(World, RT, Dir, Png);
    }
    TArray<FColor> Pixels;
    if (!AuditReadRenderTarget(RT, Pixels))
    {
        GrassAuditLog(FString::Printf(TEXT("RT%c: readback FAILED (no render resource)"), *Side));
        return;
    }
    int64 Masked = 0;
    int32 MaxR = 0;
    double SumG = 0.0, SumB = 0.0;
    for (const FColor& P : Pixels)
    {
        if (P.R > 12) // ~0.05 of the 0..1 flatten range
        {
            ++Masked;
            SumG += P.G;
            SumB += P.B;
        }
        MaxR = FMath::Max(MaxR, (int32)P.R);
    }
    OutMaskedTexels = Masked;
    const int64 Total = (int64)RT->SizeX * RT->SizeY;
    GrassAuditLog(FString::Printf(TEXT("RT%c: %dx%d maskedTexels=%lld (%.4f%%) maxR=%d gAvg=%d bAvg=%d"),
        *Side, RT->SizeX, RT->SizeY, Masked,
        Total > 0 ? 100.0 * double(Masked) / double(Total) : 0.0,
        MaxR,
        Masked > 0 ? int32(SumG / Masked) : 0,
        Masked > 0 ? int32(SumB / Masked) : 0));
}

void UGrassDeformSubsystem::RunGrassDeformAudit(float DeltaTime)
{
    static bool bFlagChecked = false;
    static bool bFlagPresent = false;
    if (!bFlagChecked)
    {
        bFlagChecked = true;
        bFlagPresent = FParse::Param(FCommandLine::Get(), TEXT("GrassDeformAudit"));
        if (!bFlagPresent) return;
        AuditStage = -1;
    }
    if (!bFlagPresent) return;

    UWorld* World = GetWorld();
    if (!World || World->WorldType != EWorldType::Game) return;
    // Wall clock, not world time: the frozen-wind phases run under 'slomo 0', where world time
    // stops advancing and a world-time schedule would deadlock the audit.
    const double Now = FPlatformTime::Seconds();
    if (Now < AuditNextAction) return;

    auto Next = [this](double Delay) { AuditNextAction = FPlatformTime::Seconds() + Delay; };

    if (AuditStage == -1)
    {
        // Arm once a pawn exists; the hills streaming needs a few seconds after that.
        APlayerController* PC = World->GetFirstPlayerController();
        if (!PC || !PC->GetPawn()) return;

        GrassAuditLog(FString::Printf(TEXT("map=%s time=%.1f"), *World->GetMapName(), World->GetTimeSeconds()));
        GEngine->Exec(World, TEXT("r.GrassDeform 1"));
        GEngine->Exec(World, TEXT("sg.FoliageQuality 4"));
        int32 Cvar = -1, Foliage = -1;
        if (const IConsoleVariable* C = IConsoleManager::Get().FindConsoleVariable(TEXT("r.GrassDeform"))) Cvar = C->GetInt();
        if (const IConsoleVariable* C = IConsoleManager::Get().FindConsoleVariable(TEXT("sg.FoliageQuality"))) Foliage = C->GetInt();
        GrassAuditLog(FString::Printf(TEXT("gates: r.GrassDeform=%d sg.FoliageQuality=%d"), Cvar, Foliage));
        GEngine->Exec(World, TEXT("GrassDeform.Status"));
        AuditStage = 0;
        Next(4.0);
        return;
    }

    if (AuditStage == 0)
    {
        // Inventory the grass ISMs and pick the clump nearest the pawn.
        ACharacter* Pawn = nullptr;
        if (APlayerController* PC = World->GetFirstPlayerController()) Pawn = Cast<ACharacter>(PC->GetPawn());
        if (!Pawn) return;
        const FVector Origin = Pawn->GetActorLocation();

        UInstancedStaticMeshComponent* Best = nullptr;
        int32 BestIndex = 0;
        double BestDist = TNumericLimits<double>::Max();
        int32 GrassComponents = 0;
        for (TObjectIterator<UInstancedStaticMeshComponent> It; It; ++It)
        {
            UInstancedStaticMeshComponent* Comp = *It;
            if (!Comp || Comp->GetWorld() != World || Comp->GetInstanceCount() <= 0) continue;
            const UMaterialInterface* Mat = Comp->GetMaterial(0);
            if (!Mat) continue;
            const FString Path = Mat->GetPathName();
            const UMaterial* Base = Mat->GetMaterial();
            const bool bGrassMaterial = Path.Contains(TEXT("grass"), ESearchCase::IgnoreCase)
                || (Base && Base->GetName().Contains(TEXT("MA_Grass"), ESearchCase::IgnoreCase));
            if (!bGrassMaterial) continue;
            ++GrassComponents;
            if (GrassComponents <= 6)
            {
                // Runtime ground truth for the RT-default binding: if the material instance does
                // not resolve GrassDeformRTA/B to the RT assets, the shader samples black no
                // matter what the subsystem draws into them.
                UTexture* RTA = nullptr;
                UTexture* RTB = nullptr;
                const bool bHasA = Mat->GetTextureParameterValue(FName(TEXT("GrassDeformRTA")), RTA);
                const bool bHasB = Mat->GetTextureParameterValue(FName(TEXT("GrassDeformRTB")), RTB);
                GrassAuditLog(FString::Printf(TEXT("grass ISM: %s instances=%d material=%s base=%s compDist=%.0fm RTA=%s RTB=%s"),
                    *Comp->GetName(), Comp->GetInstanceCount(), *Path,
                    Base ? *Base->GetPathName() : TEXT("<none>"),
                    FVector::Distance(Comp->GetComponentTransform().GetLocation(), Origin) / 100.0,
                    bHasA ? (RTA ? *RTA->GetName() : TEXT("<null>")) : TEXT("<unset>"),
                    bHasB ? (RTB ? *RTB->GetName() : TEXT("<null>")) : TEXT("<unset>")));
            }

            // Nearest instance of this component to the pawn (sampled: 2048 probes max).
            const int32 Count = Comp->GetInstanceCount();
            const int32 Step = FMath::Max(1, Count / 2048);
            FTransform InstanceXf;
            for (int32 Index = 0; Index < Count; Index += Step)
            {
                if (!Comp->GetInstanceTransform(Index, InstanceXf, true)) continue;
                const double Dist = FVector::DistSquared2D(InstanceXf.GetLocation(), Origin);
                if (Dist < BestDist)
                {
                    BestDist = Dist;
                    Best = Comp;
                    BestIndex = Index;
                }
            }
        }

        if (!Best || BestDist > FMath::Square(15000.0))
        {
            // The hills grass streams in asynchronously around the pawn; on a cold load it can
            // take well over a minute to appear. Poll instead of aborting on the first miss.
            if (++AuditFindRetries < 24)
            {
                if (AuditFindRetries == 1)
                {
                    GrassAuditLog(FString::Printf(TEXT("no grass ISM yet (grassComponents=%d) - polling, the hills stream generates asynchronously"), GrassComponents));
                }
                Next(5.0);
                return;
            }
            GrassAuditLog(FString::Printf(TEXT("ABORT: no grass ISM within 150 m after 2 minutes (grassComponents=%d)"), GrassComponents));
            GrassAuditWriteReport();
            AuditStage = 100;
            GEngine->Exec(World, TEXT("QUIT"));
            return;
        }

        FTransform TargetXf;
        Best->GetInstanceTransform(BestIndex, TargetXf, true);
        AuditTarget = TargetXf.GetLocation();
        GrassAuditLog(FString::Printf(TEXT("target clump at (%.0f, %.0f, %.0f), %.1f m from pawn, on %s"),
            AuditTarget.X, AuditTarget.Y, AuditTarget.Z,
            FMath::Sqrt(BestDist) / 100.0, *Best->GetName()));

        GEngine->Exec(World, TEXT("GrassDeform.Status"));
        AuditStage = 1;
        Next(0.5);
        return;
    }

    if (AuditStage == 1)
    {
        // Park a spawned camera actor straight above the clump and make it the view target. A
        // SetCameraCachePOV alone is overwritten by the next view-target update, so the stills
        // would silently show the first-person view instead of the grass. The screen projection
        // is logged so the stills can be read against the actual clump position.
        APlayerController* PC = World->GetFirstPlayerController();
        if (PC && PC->PlayerCameraManager && PC->GetPawn())
        {
            const FVector Eye = AuditTarget + FVector(0, 0, 320);
            const FRotator LookAt(-90.f, 0.f, 0.f);
            if (ACameraActor* Cam = World->SpawnActor<ACameraActor>(Eye, LookAt))
            {
                Cam->GetCameraComponent()->SetFieldOfView(90.f);
                Cam->GetCameraComponent()->SetProjectionMode(ECameraProjectionMode::Perspective);
                PC->SetViewTargetWithBlend(Cam, 0.f);
            }
            // Freeze world time: the pack wind animates from the world clock, so with dilation 0
            // the before/after pairs share the exact same wind phase and any pixel delta between
            // them is attributable to the deform mask alone (the stamp pass is event driven, not
            // DeltaTime driven, so it still lands while frozen). SetTimeDilation is used because
            // 'slomo' is a cheat command and -game rejects it silently.
            if (World->GetWorldSettings()) World->GetWorldSettings()->SetTimeDilation(0.f);
            FVector2D Screen;
            const bool bProjected = PC->ProjectWorldLocationToScreen(AuditTarget, Screen);
            GrassAuditLog(FString::Printf(TEXT("camera parked straight above clump; screen=(%.0f,%.0f) projected=%d time frozen"),
                Screen.X, Screen.Y, bProjected ? 1 : 0));
            // Stand the pawn beside the clump so the trample source has a real capsule nearby.
            PC->GetPawn()->SetActorLocation(AuditTarget + FVector(120, 120, 0), false, nullptr, ETeleportType::TeleportPhysics);
        }
        AuditStage = 2;
        Next(1.5); // let the view target actually adopt the parked camera before any capture
        return;
    }

    if (AuditStage == 2)
    {
        // Verify the clump is actually in frame before capturing (the projection in stage 1 read
        // the camera manager's PRE-switch POV and reported the clump off screen).
        if (APlayerController* PC = World->GetFirstPlayerController())
        {
            FVector2D Screen;
            const bool bProjected = PC->ProjectWorldLocationToScreen(AuditTarget, Screen);
            GrassAuditLog(FString::Printf(TEXT("clump on screen now: (%.0f, %.0f) projected=%d (expect near centre 640,360)"),
                Screen.X, Screen.Y, bProjected ? 1 : 0));
        }
        GrassAuditShot(World, TEXT("grass_before_1"));
        AuditStage = 3;
        Next(0.5);
        return;
    }

    if (AuditStage == 3)
    {
        GrassAuditShot(World, TEXT("grass_before_2")); // frozen-wind control pair
        AuditStage = 4;
        Next(0.3);
        return;
    }

    if (AuditStage == 31)
    {
        // Isolated recenter test while the world is still frozen (no fade, no trample): teleport
        // the pawn across one 4 m snap cell and probe both RT sides around the single recenter
        // pass it triggers. This separates "the window move destroys the mask" from everything
        // the walk phase does.
        int64 MaskedA = 0, MaskedB = 0;
        AuditLogRenderTargetStats(TEXT("A(rec-pre)"), RenderTargets[0], MaskedA);
        AuditLogRenderTargetStats(TEXT("B(rec-pre)"), RenderTargets[1], MaskedB);
        AuditMaskedTexelsBeforeWalk = FMath::Max(MaskedA, MaskedB);
        if (APlayerController* PC = World->GetFirstPlayerController(); PC && PC->GetPawn())
        {
            const FVector Here = PC->GetPawn()->GetActorLocation();
            PC->GetPawn()->SetActorLocation(Here + FVector(450, 0, 0), false, nullptr, ETeleportType::TeleportPhysics);
            GrassAuditLog(FString::Printf(TEXT("recenter test: pawn teleported +450 X from (%.0f,%.0f)"), Here.X, Here.Y));
        }
        AuditStage = 32;
        Next(0.5);
        return;
    }

    if (AuditStage == 32)
    {
        int64 MaskedA = 0, MaskedB = 0;
        AuditLogRenderTargetStats(TEXT("A(rec-post)"), RenderTargets[0], MaskedA);
        AuditLogRenderTargetStats(TEXT("B(rec-post)"), RenderTargets[1], MaskedB);
        const int64 After = FMath::Max(MaskedA, MaskedB);
        GrassAuditLog(FString::Printf(TEXT("RECENTER VERDICT: before=%lld after=%lld (%s)"),
            AuditMaskedTexelsBeforeWalk, After,
            After > 0 ? TEXT("mask survived the window move") : TEXT("RECENTER DESTROYS THE MASK")));
        AuditStage = 7;
        Next(0.2);
        return;
    }

    if (AuditStage == 4)
    {
        StampTrample(AuditTarget + FVector(0, 0, 30), 250.f, 1.f);
        GrassAuditLog(FString::Printf(TEXT("stamped target: strength=1.0 radius=250 at (%.0f,%.0f,%.0f)"),
            AuditTarget.X, AuditTarget.Y, AuditTarget.Z + 30));
        GEngine->Exec(World, TEXT("GrassDeform.Status"));
        AuditStage = 5;
        Next(1.0); // let DrainPendingStamps run and ReadIsB settle
        return;
    }

    if (AuditStage == 5)
    {
        int64 MaskedA = 0, MaskedB = 0;
        AuditLogRenderTargetStats(TEXT("A"), RenderTargets[0], MaskedA);
        AuditLogRenderTargetStats(TEXT("B"), RenderTargets[1], MaskedB);
        GrassAuditLog(FString::Printf(TEXT("read side: ReadIndex=%d (0=A, 1=B)"), ReadIndex));

        if (CollectionAsset)
        {
            if (UMaterialParameterCollectionInstance* Inst = World->GetParameterCollectionInstance(CollectionAsset))
            {
                // Names duplicated from GrassDeformParams in the runtime .cpp (file-local there);
                // keep in sync when the collection contract changes.
                float Enabled = -1.f, ReadIsB = -1.f, WorldTime = -1.f, WindowSize = -1.f;
                FLinearColor Center = FLinearColor::Black;
                Inst->GetScalarParameterValue(FName(TEXT("bEnabled")), Enabled);
                Inst->GetScalarParameterValue(FName(TEXT("ReadIsB")), ReadIsB);
                Inst->GetScalarParameterValue(FName(TEXT("WorldTime")), WorldTime);
                Inst->GetScalarParameterValue(FName(TEXT("WindowSize")), WindowSize);
                Inst->GetVectorParameterValue(FName(TEXT("Center")), Center);
                GrassAuditLog(FString::Printf(TEXT("MPC: bEnabled=%.1f ReadIsB=%.1f WorldTime=%.2f WindowSize=%.0f Center=(%.0f,%.0f)"),
                    Enabled, ReadIsB, WorldTime, WindowSize, Center.R, Center.G));
            }
        }
        AuditStage = 6;
        Next(0.2);
        return;
    }

    if (AuditStage == 6)
    {
        GrassAuditShot(World, TEXT("grass_after_1"));
        AuditStage = 61;
        Next(0.25);
        return;
    }

    if (AuditStage == 61)
    {
        GrassAuditShot(World, TEXT("grass_after_2"));
        AuditStage = 31; // isolated recenter test with a full mask, still frozen
        Next(0.3);
        return;
    }

    if (AuditStage == 7)
    {
        // Simulated walk through the real movement pipeline: AddMovementInput keeps the character
        // movement component driving velocity (setting Velocity directly is zeroed again by the
        // CMC's own tick before the subsystem's 10 Hz sample, which reads GetVelocity()).
        APlayerController* PC = World->GetFirstPlayerController();
        ACharacter* Pawn = PC ? Cast<ACharacter>(PC->GetPawn()) : nullptr;
        if (!Pawn)
        {
            AuditStage = 8;
            Next(1.0);
            return;
        }
        if (AuditWalkTicks == 0)
        {
            // Restore world time first: the movement pipeline needs it, and the trample source
            // reads the pawn's live velocity. Also take the pre-walk mask baseline here, after
            // the frozen-phase stamp has had its say, so the verdict measures the WALK delta and
            // not the big console stamp decaying.
            if (World->GetWorldSettings()) World->GetWorldSettings()->SetTimeDilation(1.f);
            if (PC) PC->SetControlRotation(FRotator(0.f, 0.f, 0.f)); // undo the -90 look-down
            AuditWalkDir = FVector(1, 0, 0);
            Pawn->SetActorLocation(AuditTarget - AuditWalkDir * 200, false, nullptr, ETeleportType::TeleportPhysics);
            int64 MaskedA = 0, MaskedB = 0;
            AuditLogRenderTargetStats(TEXT("A(pre-walk)"), RenderTargets[0], MaskedA);
            AuditLogRenderTargetStats(TEXT("B(pre-walk)"), RenderTargets[1], MaskedB);
            AuditMaskedTexelsBeforeWalk = FMath::Max(MaskedA, MaskedB);
            GrassAuditLog(FString::Printf(TEXT("walk phase: driving movement input across the clump (speed=%.0f)"),
                Pawn->GetCharacterMovement() ? Pawn->GetCharacterMovement()->MaxWalkSpeed : 0.f));
        }
        // Hold the input every tick; the CMC integrates it into real velocity + position.
        // bForce: without it the direction is rotated by the control rotation, which the camera
        // park set to -90 pitch - the pawn then tried to walk into the ground and slid sideways.
        Pawn->AddMovementInput(AuditWalkDir, 1.f, true);
        ++AuditWalkTicks;
        const double Walked = FVector::Dist(Pawn->GetActorLocation(), AuditTarget - AuditWalkDir * 200);
        if (AuditWalkTicks % 30 == 0)
        {
            int64 MaskedProbe = 0;
            AuditLogRenderTargetStats(TEXT("A(walk)"), RenderTargets[0], MaskedProbe);
            AuditLogRenderTargetStats(TEXT("B(walk)"), RenderTargets[1], MaskedProbe);
            GrassAuditLog(FString::Printf(TEXT("walk probe: ticks=%d walked=%.0f pos=(%.0f,%.0f) pawnSpeed=%.0f"),
                AuditWalkTicks, Walked, Pawn->GetActorLocation().X, Pawn->GetActorLocation().Y, Pawn->GetVelocity().Size()));
        }
        if (Walked >= 500.f || AuditWalkTicks >= 240) // stop before running out of the window / off a cliff
        {
            PC->StopMovement();
            GrassAuditLog(FString::Printf(TEXT("walk phase finished: walked=%.0f cm lastSpeed=%.0f"),
                Walked, Pawn->GetVelocity().Size()));
            AuditStage = 8;
            Next(1.0);
        }
        else
        {
            AuditNextAction = 0.0; // keep pressing input every tick
        }
        return;
    }

    if (AuditStage == 8)
    {
        int64 MaskedA = 0, MaskedB = 0;
        AuditLogRenderTargetStats(TEXT("A"), RenderTargets[0], MaskedA);
        AuditLogRenderTargetStats(TEXT("B"), RenderTargets[1], MaskedB);
        const int64 AfterWalk = FMath::Max(MaskedA, MaskedB);
        GrassAuditLog(FString::Printf(TEXT("walk verdict: masked before=%lld after=%lld delta=%lld (%s)"),
            AuditMaskedTexelsBeforeWalk, AfterWalk, AfterWalk - AuditMaskedTexelsBeforeWalk,
            AfterWalk > AuditMaskedTexelsBeforeWalk ? TEXT("trail grew - trample source works") : TEXT("NO GROWTH - trample source dead")));
        GEngine->Exec(World, TEXT("GrassDeform.Status"));
        AuditStage = 9;
        Next(2.5); // let the last screenshots flush to disk
        return;
    }

    if (AuditStage == 9)
    {
        GrassAuditWriteReport();
        GrassAuditLog(TEXT("done - quitting"));
        AuditStage = 10;
        GEngine->Exec(World, TEXT("QUIT"));
        return;
    }
}

#endif // !UE_BUILD_SHIPPING
