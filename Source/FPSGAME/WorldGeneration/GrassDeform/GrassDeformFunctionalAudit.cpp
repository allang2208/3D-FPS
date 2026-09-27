#include "GrassDeformSubsystem.h"
#include "GrassDeformSettings.h"

#if !UE_BUILD_SHIPPING
#include "GrassDeformTestField.h"
#include "GrassFootstepFeedbackComponent.h"
#include "../../SceneTestPortal.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/Material.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "UObject/Package.h"

namespace GrassFunctionalAudit
{
    struct FState
    {
        int32 Phase = 0, Failed = 0, Checks = 0, MaxDecals = 0, MaxPuffs = 0;
        double Next = 0, Start = 0, LastStamp = 0;
        float Peak = 0, GameTime = 0;
        FVector WalkStart = FVector::ZeroVector;
        TArray<FString> Lines;
        FString Dir;
        TWeakObjectPtr<ACameraActor> Camera;
        TWeakObjectPtr<UWorld> ObservedWorld;
    };
    void Record(FState& S, const FString& Line)
    {
        S.Lines.Add(Line);
        UE_LOG(LogTemp, Display, TEXT("GRASS_FUNCTIONAL %s"), *Line);
        IFileManager::Get().MakeDirectory(*S.Dir, true);
        FFileHelper::SaveStringArrayToFile(S.Lines, *(S.Dir / TEXT("results.txt")));
    }
    void Check(FState& S, const TCHAR* Name, bool Pass, const FString& Detail = FString())
    {
        ++S.Checks; if (!Pass) ++S.Failed;
        Record(S, FString::Printf(TEXT("%s %s %s"), Pass ? TEXT("PASS") : TEXT("FAIL"), Name, *Detail));
    }
    void Shot(const FState& S, const TCHAR* Name)
    {
        FScreenshotRequest::RequestScreenshot(S.Dir / (FString(Name) + TEXT(".png")), false, false);
    }
    void Finish(FState& S)
    {
        Record(S, FString::Printf(TEXT("COMPLETE checks=%d failed=%d"), S.Checks, S.Failed));
        FPlatformMisc::RequestExitWithStatus(false, S.Failed ? 1 : 0);
        S.Phase = 999;
    }
}

void UGrassDeformSubsystem::RunGrassFunctionalAudit(float DeltaTime)
{
    using namespace GrassFunctionalAudit;
    static const bool Functional = FParse::Param(FCommandLine::Get(), TEXT("GrassFunctionalAudit"));
    static const bool Portal = FParse::Param(FCommandLine::Get(), TEXT("GrassPortalAudit"));
    if (!Functional && !Portal) return;
    UWorld* World = GetWorld();
    if (!World || World->WorldType != EWorldType::Game || !World->HasBegunPlay()) return;
    static FState S;
    if (S.Dir.IsEmpty())
    {
        FString Label = Portal ? TEXT("portals") : TEXT("functional");
        FParse::Value(FCommandLine::Get(), TEXT("GrassAuditLabel="), Label);
        S.Dir = FPaths::ProjectSavedDir() / TEXT("GrassDenseValidation20260926") / Label;
        S.Start = FPlatformTime::Seconds();
        if(Portal && FParse::Param(FCommandLine::Get(),TEXT("GrassPortalFromHills")))S.Phase=3;
    }
    if (S.Phase == 999) return;
    const double Now = FPlatformTime::Seconds();
    if (Now - S.Start > (Portal ? 600 : 180))
    {
        Check(S, TEXT("watchdog"), false, FString::Printf(TEXT("phase=%d"), S.Phase)); Finish(S); return;
    }
    if (Now < S.Next) return;
    APlayerController* PC = World->GetFirstPlayerController();
    ACharacter* Pawn = PC ? Cast<ACharacter>(PC->GetPawn()) : nullptr;
    if (!Pawn) return;
    auto Next = [&](int32 Phase, double Delay) { S.Phase = Phase; S.Next = Now + Delay; };
    if (Portal)
    {
        const FString Map = UGameplayStatics::GetCurrentLevelName(World, true);
        if(S.ObservedWorld.Get()!=World)
        {
            S.ObservedWorld=World;S.Next=Now+8;
            Record(S,TEXT("WORLD_READY_WAIT ")+Map);return;
        }
        const TCHAR* Expected[] = {TEXT("DayNight_Lighting"), TEXT("L_GrassDeformDenseTest"),
            TEXT("DayNight_Lighting"), TEXT("L_TemperateHills_Initial"),
            TEXT("L_GrassDeformDenseTest"), TEXT("L_TemperateHills_Initial")};
        if (Map != Expected[S.Phase]) return;
        if (S.Phase == 5)
        {
            Check(S, TEXT("hills_grass_round_trip"), World->URL.HasOption(TEXT("HillsContinue")), Map);
            Shot(S, TEXT("05_hills_return")); Next(999, 0); Finish(S); return;
        }
        ASceneTestPortal* Door = nullptr;
        const FName Tag(S.Phase == 2 ? TEXT("ScenePortal.HillsLink") : TEXT("ScenePortal.GrassLink"));
        for (TActorIterator<ASceneTestPortal> It(World); It; ++It)
            if (It->ActorHasTag(Tag)) { Door = *It; break; }
        if (!Door) return;
        if (S.Phase == 1) Check(S, TEXT("hub_to_grass"), true, Map);
        if (S.Phase == 2) Check(S, TEXT("grass_to_hub"), true, Map);
        if (S.Phase == 3) Check(S, TEXT("hub_to_hills"), true, Map);
        if (S.Phase == 4) Check(S, TEXT("hills_to_grass_origin_option"), World->URL.HasOption(TEXT("GrassReturnHills")), Map);
        const FVector Forward = Door->GetActorForwardVector();
        Pawn->SetActorLocation(Door->GetActorLocation() + Forward * 300 + FVector(0,0,100), false);
        Check(S, TEXT("portal_rejects_outside_2m"), !Door->IsWithinInteractionRange(Pawn), Map);
        Pawn->SetActorLocation(Door->GetActorLocation() + Forward * 130 + FVector(0,0,100), false);
        Check(S, TEXT("portal_accepts_within_2m"), Door->IsWithinInteractionRange(Pawn), Map);
        PC->SetControlRotation((-Forward).Rotation());
        PC->bShowMouseCursor = false;
        PC->SetInputMode(FInputModeGameOnly());
        Shot(S, *FString::Printf(TEXT("%02d_portal"), S.Phase));
        Record(S, FString::Printf(TEXT("PRESS_E phase=%d map=%s door=%s"), S.Phase, *Map, *Door->GetName()));
        if (UPackage* HubPackage=FindPackage(nullptr,TEXT("/Game/GameMaps/DayNight_Lighting")))
            Record(S,FString::Printf(TEXT("HUB_PACKAGE_BEFORE_TRAVEL world=%s fully_loaded=%d"),
                *GetNameSafe(UWorld::FindWorldInPackage(HubPackage)),HubPackage->IsFullyLoaded()));
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E, IE_Pressed, 1.f));
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E, IE_Released, 0.f));
        Next(S.Phase + 1, 4.0);
        return;
    }

    auto* Movement = Pawn->GetCharacterMovement();
    auto* Feedback = Pawn->FindComponentByClass<UGrassFootstepFeedbackComponent>();
    auto* MPC = CollectionAsset ? World->GetParameterCollectionInstance(CollectionAsset) : nullptr;
    auto Scalar = [&](const TCHAR* Name) { float Value=-999; if (MPC) MPC->GetScalarParameterValue(Name,Value); return Value; };
    auto Cvar = [&](const TCHAR* Name, int32 Value) { IConsoleManager::Get().FindConsoleVariable(Name)->Set(Value, ECVF_SetByConsole); };
    TArray<FFloat16Color> Pixels;
    auto Read = [&]()
    {
        Pixels.Reset();
        auto* RT = GetReadTarget();
        if (!RT || !RT->GameThread_GetRenderTargetResource()->ReadFloat16Pixels(Pixels)) return false;
        TArray<FLinearColor> ContactTimes;
        auto* TimeRT = ContactTimeTargets[ReadIndex].Get();
        FReadSurfaceDataFlags Flags(RCM_MinMax);
        Flags.SetLinearToGamma(false);
        if (!TimeRT || !TimeRT->GameThread_GetRenderTargetResource()->ReadLinearColorPixels(ContactTimes, Flags)
            || ContactTimes.Num() != Pixels.Num()) { Pixels.Reset(); return false; }
        // Raw R stores a peak in v12, not the current pose. Existing lifetime assertions
        // must consume the evaluated response. This readback remains explicit-audit-only.
        for (int32 I = 0; I < Pixels.Num(); ++I)
        {
            const float T = FMath::Clamp((World->GetTimeSeconds() - ContactTimes[I].R - Response->HoldSeconds)
                / FMath::Max(Response->RecoverSeconds, 0.05f), 0.f, 1.f);
            Pixels[I].R = Pixels[I].R.GetFloat() * (1.f - T*T*(3.f-2.f*T));
        }
        return true;
    };
    auto PeakAt = [&](FVector Position)
    {
        if (Pixels.IsEmpty()) return -1.f;
        const FVector2D UV = (FVector2D(Position)-WindowCenter)/GrassDeformTuning::WindowSizeCm+FVector2D(.5,.5);
        const int32 X = FMath::FloorToInt(UV.X*ActiveRTSize), Y = FMath::FloorToInt(UV.Y*ActiveRTSize);
        float Peak = 0;
        for (int32 DY=-2;DY<=2;++DY) for (int32 DX=-2;DX<=2;++DX)
            if (X+DX>=0 && X+DX<ActiveRTSize && Y+DY>=0 && Y+DY<ActiveRTSize)
                Peak=FMath::Max(Peak,Pixels[(Y+DY)*ActiveRTSize+X+DX].R.GetFloat());
        return Peak;
    };
    auto Maximum = [&]() { float Peak=0; for (const auto& P:Pixels) Peak=FMath::Max(Peak,P.R.GetFloat()); return Peak; };
    const FVector A(-1800, 0, 0), B(-1200, 0, 0);
    const float GroundZ = Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3.f;
    switch (S.Phase)
    {
    case 0:
        Record(S,TEXT("START isolated GPU grass functional audit"));
        Cvar(TEXT("r.GrassDeform"),1); Cvar(TEXT("sg.FoliageQuality"),3);
        Next(1,5); break;
    case 1:
    {
        Check(S,TEXT("subsystem_assets_enabled"),IsEnabled() && bAssetsReady && MPC);
        Check(S,TEXT("spawn_grounded"),Movement->IsMovingOnGround(),Pawn->GetActorLocation().ToString());
        int32 Count=0,Components=0; bool Materials=true;
        for(TActorIterator<AGrassDeformTestField> It(World);It;++It)
            for(auto* C:{It->TallGrassA.Get(),It->TallGrassB.Get()})
            { Count+=C->GetInstanceCount(); ++Components;
              Materials &= C->GetMaterial(0) && C->GetMaterial(0)->GetMaterial()->GetName()==TEXT("M_TemperateMeadow"); }
        Check(S,TEXT("dense_field_instances_materials"),Count==25494 && Components==2 && Materials,FString::FromInt(Count));
        Check(S,TEXT("footstep_component"),Feedback!=nullptr);
        Pawn->SetActorLocation(FVector(-2200,-600,GroundZ),false);
        Movement->StopMovementImmediately(); Movement->DisableMovement();
        Pawn->SetActorHiddenInGame(true);
        if(Feedback)Feedback->ResetTrail();
        const FVector Eye(-2250,-900,550);
        auto* Cam=World->SpawnActor<ACameraActor>(Eye,(A+FVector(0,0,60)-Eye).Rotation());
        S.Camera=Cam; Cam->GetCameraComponent()->SetFieldOfView(70); PC->SetViewTarget(Cam);
        World->GetWorldSettings()->SetTimeDilation(.0001f);
        DiscardInteractionState(); Next(2,2); break;
    }
    case 2:
        Check(S,TEXT("initial_clear_RT"),Read() && Maximum()<.001f);
        Shot(S,TEXT("01_before")); Next(3,.4); break;
    case 3:
        StampTrample(A,250,1); Next(4,.5); break;
    case 4:
        Read();
        Check(S,TEXT("stamp_GPU_mask"),PeakAt(A)>.9f,FString::Printf(TEXT("peak=%.4f"),PeakAt(A)));
        Check(S,TEXT("stamp_locality"),PeakAt(B)<.001f);
        S.Peak=PeakAt(A); Shot(S,TEXT("02_stamped"));
        Pawn->SetActorLocation(Pawn->GetActorLocation()+FVector(450,0,0),false);
        Next(5,.5); break;
    case 5:
        Read();
        Check(S,TEXT("recenter_preserves_world_mask"),!Pixels.IsEmpty() && FMath::Abs(PeakAt(A)-S.Peak)<.06f,FString::Printf(TEXT("peak=%.4f center=%s"),PeakAt(A),*WindowCenter.ToString()));
        DiscardInteractionState(); StampTrample(A,150,1); StampTrample(B,150,1);
        Pawn->SetActorLocation(Pawn->GetActorLocation()+FVector(450,0,0),false);
        Next(6,.5); break;
    case 6:
        Read();
        Check(S,TEXT("queued_stamps_across_recenter"),PeakAt(A)>.9f && PeakAt(B)>.9f,FString::Printf(TEXT("A=%.4f B=%.4f"),PeakAt(A),PeakAt(B)));
        DiscardInteractionState(); World->GetWorldSettings()->SetTimeDilation(1);
        AddImpulse(A,650,.9f,500); Next(7,.4); break;
    case 7:
        Check(S,TEXT("impulse_mask"),Read() && PeakAt(A)>.8f);
        Check(S,TEXT("impulse_wave_parameters"),FMath::IsNearlyEqual(Scalar(TEXT("GrassWaveRadius")),650) && FMath::IsNearlyEqual(Scalar(TEXT("GrassWaveStrength")),.9f) && Scalar(TEXT("WorldTime"))-Scalar(TEXT("GrassWaveStartTime"))<2,
            FString::Printf(TEXT("radius=%.0f strength=%.2f age=%.3f"),Scalar(TEXT("GrassWaveRadius")),Scalar(TEXT("GrassWaveStrength")),Scalar(TEXT("WorldTime"))-Scalar(TEXT("GrassWaveStartTime"))));
        Shot(S,TEXT("03_impulse")); S.Peak=PeakAt(A); S.GameTime=World->GetTimeSeconds(); Next(8,0); break;
    case 8:
        if(World->GetTimeSeconds()-S.GameTime<Response->HoldSeconds+Response->RecoverSeconds+0.2f)break;
        Read(); Check(S,TEXT("regrowth_elapsed_time"),!Pixels.IsEmpty() && PeakAt(A)<.02f,
            FString::Printf(TEXT("initial=%.4f now=%.4f seconds=%.3f"),S.Peak,PeakAt(A),World->GetTimeSeconds()-S.GameTime));
        Next(9,0); break;
    case 9:
        if(Now-S.LastStamp>.25){StampTrample(B,100,1);S.LastStamp=Now;}
        if(World->GetTimeSeconds()-S.GameTime<Response->HoldSeconds+Response->RecoverSeconds+1.f)break;
        Read();
        Check(S,TEXT("old_grass_recovers_while_new_stamps_continue"),!Pixels.IsEmpty() && PeakAt(A)<.02f && PeakAt(B)>.8f,FString::Printf(TEXT("old=%.4f new=%.4f"),PeakAt(A),PeakAt(B)));
        Shot(S,TEXT("04_regrown")); Cvar(TEXT("r.GrassDeform"),0);Next(10,.3);break;
    case 10:
        Check(S,TEXT("console_disable_clears_state"),!IsEnabled() && Scalar(TEXT("bEnabled"))==0 && Read() && Maximum()<.001f);
        Cvar(TEXT("r.GrassDeform"),1);Next(11,.3);break;
    case 11:
        Check(S,TEXT("console_reenable"),IsEnabled()); StampTrample(A,150,1);SetEnabled(false);Next(12,.3);break;
    case 12:
        Check(S,TEXT("API_disable_clears_state"),!IsEnabled() && Read() && Maximum()<.001f && Pending.IsEmpty());
        SetEnabled(true);Cvar(TEXT("sg.FoliageQuality"),0);Next(13,.3);break;
    case 13:
        Check(S,TEXT("low_foliage_disables"),!IsEnabled() && Scalar(TEXT("bEnabled"))==0);
        Cvar(TEXT("sg.FoliageQuality"),3);Next(14,.5);break;
    case 14:
        Check(S,TEXT("quality_reenable_no_stale_mask"),IsEnabled() && Read() && Maximum()<.001f);
        Pawn->SetActorHiddenInGame(false);
        Pawn->SetActorLocation(FVector(-2100,500,GroundZ),false);Movement->SetMovementMode(MOVE_Walking);
        PC->SetControlRotation(FRotator::ZeroRotator);S.WalkStart=Pawn->GetActorLocation();S.GameTime=World->GetTimeSeconds();Next(15,0);break;
    case 15:
        Pawn->AddMovementInput(FVector(1,0,0),1,true);
        if(Feedback){S.MaxDecals=FMath::Max(S.MaxDecals,Feedback->GetActiveDecalCount());S.MaxPuffs=FMath::Max(S.MaxPuffs,Feedback->GetActivePuffCount());}
        if(FVector::Dist2D(Pawn->GetActorLocation(),S.WalkStart)<650 && World->GetTimeSeconds()-S.GameTime<5)break;
        Movement->StopMovementImmediately();
        Check(S,TEXT("walk_collision_and_motion"),FVector::Dist2D(Pawn->GetActorLocation(),S.WalkStart)>400 && Movement->IsMovingOnGround(),Pawn->GetActorLocation().ToString());
        Check(S,TEXT("walk_creates_GPU_trail"),Read() && Maximum()>.1f);
        Check(S,TEXT("footstep_decal_and_puff_active"),S.MaxDecals>0 && S.MaxDecals<=12 && S.MaxPuffs>0 && S.MaxPuffs<=64,FString::Printf(TEXT("decals=%d puffs=%d"),S.MaxDecals,S.MaxPuffs));
        PC->SetViewTarget(Pawn); PC->SetControlRotation(FRotator(-60,180,0));
        Next(150,.5);break;
    case 150:
        Shot(S,TEXT("05_walk"));Next(151,.5);break;
    case 151:
        Pawn->SetActorLocation(FVector(-1000,1000,600),false);Movement->GravityScale=0;Movement->SetMovementMode(MOVE_Falling);
        if(Feedback)Feedback->ResetTrail();DiscardInteractionState();Next(16,.3);break;
    case 16:
        DiscardInteractionState();S.GameTime=World->GetTimeSeconds();Next(17,0);break;
    case 17:
        Pawn->AddMovementInput(FVector(1,0,0),1,true);
        if(World->GetTimeSeconds()-S.GameTime<1)break;
        Check(S,TEXT("airborne_motion_no_trample"),!Movement->IsMovingOnGround() && Read() && Maximum()<.001f);
        Movement->GravityScale=1;Movement->StopMovementImmediately();Movement->DisableMovement();Next(18,7);break;
    case 18:
        Check(S,TEXT("footstep_pool_released"),Feedback && Feedback->GetActiveDecalCount()==0 && Feedback->GetActivePuffCount()==0);
        { int32 Decals=0;bool Domain=true;TInlineComponentArray<UDecalComponent*> Items(Pawn);
          for(auto* D:Items)if(D->GetDecalMaterial() && D->GetDecalMaterial()->GetName().Contains(TEXT("GrassTrample")))
          {++Decals;Domain &= D->GetDecalMaterial()->GetMaterial()->MaterialDomain==MD_DeferredDecal;}
          Check(S,TEXT("decal_material_domain_and_bounded_pool"),Domain && Decals>0 && Decals<=12,FString::FromInt(Decals)); }
        Next(19,2);break;
    case 19: Finish(S);break;
    }
}
#endif
