#include "FPSGAMECharacter.h"
#include "BallisticAuditTarget.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/FPSBallisticsComponent.h"
#include "Weapons/FPSWeaponFXComponent.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "UnrealClient.h"

void AFPSGAMECharacter::RunBallisticPresentationAudit()
{
    static bool InputIsolated=false;
    if(!InputIsolated){
        if(auto* PC=Cast<APlayerController>(Controller)){PC->SetIgnoreLookInput(true);PC->SetIgnoreMoveInput(true);InputIsolated=true;}
    }
    static int32 Stage=0,Failures=0,Checks=0,InitialImpacts=0,InitialTracers=0;
    static double Next=5;
    static FString Report;
    static ABallisticAuditTarget* HitTarget=nullptr;
    static AStaticMeshActor* BurstWall=nullptr;
    const double Now=GetWorld()->GetTimeSeconds();
    const FString Dir=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("BallisticPresentationAudit"));
    static int32 Frame=0;
    if(Stage>=1&&Stage<=8&&FParse::Param(FCommandLine::Get(),TEXT("BallisticCaptureFrames")))
        FScreenshotRequest::RequestScreenshot(FPaths::Combine(Dir,FString::Printf(TEXT("Frames/%04d.png"),Frame++)),true,false);
    if(Now<Next)return;
    auto Check=[&](bool OK,const TCHAR* Name){++Checks;if(!OK)++Failures;
        const FString Line=FString::Printf(TEXT("BALLISTIC %s %s\n"),OK?TEXT("PASS"):TEXT("FAIL"),Name);
        Report+=Line;UE_LOG(LogTemp,Display,TEXT("%s"),*Line);};
    auto Capture=[&](const TCHAR* Name){FScreenshotRequest::RequestScreenshot(FPaths::Combine(Dir,Name),true,false);};
    if(Stage==0)
    {
        IFileManager::Get().MakeDirectory(*Dir,true);
        IFileManager::Get().MakeDirectory(*FPaths::Combine(Dir,TEXT("Strafe")),true);
        IFileManager::Get().MakeDirectory(*FPaths::Combine(Dir,TEXT("Frames")),true);
        auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if(!Profile||!Profile->IsAudit()){FPlatformMisc::RequestExitWithStatus(false,2);return;}
        Check(bInventoryWeaponReady,TEXT("isolated profile has weapon"));
        Check(WeaponFX->HasEpicGunFX(),TEXT("Epic Niagara muzzle and smoke assets loaded"));
        bIsAiming=false;WeaponADSFactor=0;CurrentSpread=MoveSpread=AirSpread=0;HipSpreadMultiplier=1;
        Check(FMath::IsNearlyEqual(GetHipSpread(),.035f),TEXT("standing hip spread reaches 35 cm per axis at 10 m"));
        auto* ProjectionPC=Cast<APlayerController>(Controller);
        int32 ViewWidth=0,ViewHeight=0;ProjectionPC->GetViewportSize(ViewWidth,ViewHeight);
        const FVector2D LocalSize(ViewWidth,ViewHeight);
        const FVector2D RestExtent=GetCrosshairHalfExtent(LocalSize);
        const FVector Forward=FirstPersonCamera->GetForwardVector(),Right=FirstPersonCamera->GetRightVector(),Up=FirstPersonCamera->GetUpVector();
        bool Bounded=true,Varied=false;const FVector First=ComputeShotDirection();
        for(int32 I=0;I<512;++I){const FVector D=ComputeShotDirection();const double F=FVector::DotProduct(D,Forward);
            Bounded &= FMath::Abs(FVector::DotProduct(D,Right)/F)<=.035001 && FMath::Abs(FVector::DotProduct(D,Up)/F)<=.035001;
            Varied |= !D.Equals(First,1.e-6);}
        Check(Bounded&&Varied,TEXT("512 hip shots random inside tuned angular bounds"));
        bool ScreenBounded=true;FVector2D MaxObserved=FVector2D::ZeroVector;
        FVector2D ProjectedCenter;const FVector Eye=FirstPersonCamera->GetComponentLocation();
        ProjectionPC->ProjectWorldLocationToScreen(Eye+Forward*1000.f,ProjectedCenter,true);
        for(int32 I=0;I<2048;++I){const FVector D=ComputeShotDirection();FVector2D Pixel;
            ProjectionPC->ProjectWorldLocationToScreen(Eye+D*(1000.f/FVector::DotProduct(D,Forward)),Pixel,true);
            const FVector2D Offset=Pixel-ProjectedCenter;
            MaxObserved.X=FMath::Max(MaxObserved.X,FMath::Abs(Offset.X));MaxObserved.Y=FMath::Max(MaxObserved.Y,FMath::Abs(Offset.Y));
            ScreenBounded &= FMath::Abs(Offset.X)<=RestExtent.X+.02 && FMath::Abs(Offset.Y)<=RestExtent.Y+.02;}
        Check(ScreenBounded&&MaxObserved.X>RestExtent.X*.98&&MaxObserved.Y>RestExtent.Y*.98,
            TEXT("2048 projected impacts fill and stay inside crosshair inner edges"));
        Check(GetCrosshairHalfExtent(LocalSize*.5).Equals(RestExtent*.5,.001),TEXT("HUD DPI scaling preserves physical spread boundary"));
        FMath::RandInit(4901);const FVector Full=ComputeShotDirection();HipSpreadMultiplier=.5f;FMath::RandInit(4901);const FVector Half=ComputeShotDirection();
        Check(FMath::IsNearlyEqual(FVector::DotProduct(Half,Right)/FVector::DotProduct(Half,Forward),
            .5*FVector::DotProduct(Full,Right)/FVector::DotProduct(Full,Forward),1.e-7),TEXT("attachment halves hip angular spread"));
        HipSpreadMultiplier=1;
        CurrentSpread=.018f;MoveSpread=.020f;AirSpread=.025f;
        Check(GetCrosshairHalfExtent(LocalSize).Equals(RestExtent*(GetHipSpread()/.035f),.02),TEXT("moving airborne crosshair tracks full spread without clamp"));
        bIsAiming=true;WeaponADSFactor=1;
        const FVector Aim=ComputeShotDirection();bool Exact=true;
        for(int32 I=0;I<512;++I)Exact &= ComputeShotDirection().Equals(Aim,1.e-10);
        Check(Exact,TEXT("512 ADS shots identical despite max movement and bloom"));
        FMath::RandInit(719);ComputeShotDirection();const float After=FMath::FRand();FMath::RandInit(719);
        Check(After==FMath::FRand(),TEXT("ADS consumes no scatter RNG"));
        const FTransform Before=AKMViewmodel->GetRelativeTransform();
        AKMViewmodel->AddLocalRotation(FRotator(2,1,0));
        const FVector Displaced=ComputeShotDirection();
        Check(!Displaced.Equals(Aim,1.e-5),TEXT("shot follows displaced animated sight"));
        AKMViewmodel->SetRelativeTransform(Before);
        bIsAiming=false;WeaponADSFactor=0;CurrentSpread=MoveSpread=AirSpread=0;
        auto* PC=Cast<APlayerController>(Controller);PC->SetControlRotation(FRotator(0,PC->GetControlRotation().Yaw,0));
        auto* Wall=GetWorld()->SpawnActor<AStaticMeshActor>();
        BurstWall=Wall;
        Wall->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
        Wall->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
        Wall->SetActorLocation(FirstPersonCamera->GetComponentLocation()+PC->GetControlRotation().Vector()*1800.f);
        Wall->SetActorRotation(PC->GetControlRotation());Wall->SetActorScale3D(FVector(.2,20,12));
        Wall->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
        InitialImpacts=Ballistics->ImpactCount;InitialTracers=WeaponFX->TracerSegments;
        Stage=1;Next=Now+.5;return;
    }
    if(Stage==1){Capture(TEXT("01-hip.png"));Stage=2;Next=Now+.2;return;}
    if(Stage==2){FirePressed();Stage=3;Next=Now+.035;return;}
    if(Stage==3){Capture(TEXT("02-hip-tracer.png"));Stage=4;Next=Now+.5;return;}
    if(Stage==4){Check(CurrentSpread>=.009f,TEXT("held hip fire accumulates visible bloom"));FireReleased();AimPressed();Stage=5;Next=Now+.7;return;}
    if(Stage==5){Capture(TEXT("03-ads.png"));Check(bIsAiming&&WeaponADSFactor>.98f,TEXT("actual ADS settled"));FirePressed();Stage=6;Next=Now+.16;return;}
    if(Stage==6){Capture(TEXT("04-ads-tracer.png"));Stage=7;Next=Now+.4;return;}
    if(Stage==7){FireReleased();Stage=8;Next=Now+.7;return;}
    if(Stage==8){
        Check(WeaponFX->TracerSegments>InitialTracers,TEXT("real shots emit depth-tested tracer segments"));
        Check(Ballistics->ImpactCount>InitialImpacts,TEXT("real rounds impact fixture"));
        Check(Ballistics->ActiveCount()==0,TEXT("rounds stop after impact"));
        Check(GetHitMarkerOpacity()==0.f,TEXT("wall impacts never trigger target hit marker"));
        HitTarget=GetWorld()->SpawnActor<ABallisticAuditTarget>();
        const FVector Eye=FirstPersonCamera->GetComponentLocation();
        HitTarget->SetActorLocation(Eye+FirstPersonCamera->GetForwardVector()*300.f);
        NotifyConfirmedWeaponHit(HitTarget,0.f);
        Check(GetHitMarkerOpacity()==0.f,TEXT("zero damage does not trigger marker"));
        AimReleased();
        Stage=9;Next=Now+.7;return;
    }
    if(Stage==9){
        const FVector Target=HitTarget->GetActorLocation();
        Ballistics->Launch(Target-FVector(50,0,0),FVector::ForwardVector,10000.f,100.f,1.f,WeaponFX,nullptr);
        Stage=10;Next=Now+.035;return;
    }
    if(Stage==10){
        Check(HitTarget->Received>0.f&&GetHitMarkerOpacity()>.6f,TEXT("actual projectile damage triggers translucent marker"));
        Capture(TEXT("05-hip-hitmarker.png"));Stage=11;Next=Now+.10;return;
    }
    if(Stage==11){
        Check(GetHitMarkerOpacity()>0.f&&GetHitMarkerOpacity()<.6f,TEXT("marker fades after hold"));
        NotifyConfirmedWeaponHit(HitTarget,1.f);
        Check(FMath::IsNearlyEqual(GetHitMarkerOpacity(),.65f),TEXT("repeated hits refresh without stacking opacity"));
        AimPressed();Stage=12;Next=Now+.7;return;
    }
    if(Stage==12){
        Check(GetHitMarkerOpacity()==0.f,TEXT("marker expires"));
        const FVector Target=HitTarget->GetActorLocation();
        Ballistics->Launch(Target-FVector(50,0,0),FVector::ForwardVector,10000.f,100.f,1.f,WeaponFX,nullptr);
        Stage=13;Next=Now+.035;return;
    }
    if(Stage==13){
        Check(bIsAiming&&GetHitMarkerOpacity()>.6f,TEXT("ADS confirmed hit marker visible"));
        Capture(TEXT("06-ads-hitmarker.png"));Stage=14;Next=Now+.3;return;
    }
    static int32 BurstShots=0,BeforeImpact=0;
    static FVector ExpectedImpact;
    static double MaxImpactError=0;
    static bool KickedLeft=false,KickedRight=false;
    if(Stage==14){
        HitTarget->Destroy();
        BurstWall->SetActorLocation(FirstPersonCamera->GetComponentLocation()+FirstPersonCamera->GetForwardVector()*600.f);
        RecoilPatternIndex=ADSHorizontalRecoilIndex=0;
        Stage=15;Next=Now+.3;return;
    }
    if(Stage==15){
        if(BurstShots>0){
            const double Error=FVector::Distance(ExpectedImpact,Ballistics->LastImpactPoint);
            MaxImpactError=FMath::Max(MaxImpactError,Error);
            Check(Ballistics->ImpactCount==BeforeImpact+1&&Error<.1,
                TEXT("ADS recoil burst actual impact matches pre-shot sight ray within 1 mm"));
        }
        if(BurstShots==9){
            Check(KickedLeft&&KickedRight,TEXT("tested both horizontal recoil directions"));
            Report+=FString::Printf(TEXT("ADS_RECOIL_BURST shots=%d max_error_cm=%.6f\n"),BurstShots,MaxImpactError);
            Stage=16;Next=Now+.1;return;
        }
        const FVector Eye=FirstPersonCamera->GetComponentLocation();
        // Independently sample the visible sight, not ComputeShotDirection's return value.
        const FVector Sight=bHolographicOptic?HolographicAimPoint():AKMViewmodel->GetSocketLocation(TEXT("WPN_FrontSight"));
        FHitResult Expected;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(ADSBurstAcceptance),true,this);
        Check(GetWorld()->LineTraceSingleByChannel(Expected,Eye,Eye+(Sight-Eye).GetSafeNormal()*TraceDistance,ECC_Visibility,Query),
            TEXT("visible sight ray reaches test surface"));
        ExpectedImpact=Expected.ImpactPoint;BeforeImpact=Ballistics->ImpactCount;
        const float Yaw=Controller->GetControlRotation().Yaw;
        const int32 BeforeShots=ShotsFired;
        NextAllowedShotTime=Now;FireShot();
        Check(ShotsFired==BeforeShots+1&&!bLastShotMuzzleBlocked,TEXT("ADS burst fires through clear muzzle"));
        const float DeltaYaw=FRotator::NormalizeAxis(Controller->GetControlRotation().Yaw-Yaw);
        KickedLeft|=DeltaYaw<-.01f;KickedRight|=DeltaYaw>.01f;
        ++BurstShots;Next=Now+FireInterval;return;
    }
    static int32 MuzzleCase=0;
    static FVector SampledMuzzle;
    static const TCHAR* MuzzleCases[]={TEXT("true"),TEXT("brake"),TEXT("titanium_brake"),TEXT("false")};
    if(Stage==16){
        AimReleased();
        SetGunsmithMuzzle(MuzzleCases[MuzzleCase]);
        Stage=17;Next=Now+.5;return;
    }
    if(Stage==17){
        SampledMuzzle=GetEffectiveMuzzleLocation();
        const FVector Stock=AKMViewmodel->GetSocketLocation(TEXT("WPN_SOCKET_Muzzle"));
        const FVector Forward=GetEffectiveMuzzleForward();
        if(MuzzleCase<3){
            const auto B=MuzzleAttachment->GetStaticMesh()->GetBounds();
            const FVector Local=MuzzleAttachment->GetComponentTransform().InverseTransformPosition(SampledMuzzle);
            const double Surface=FVector::DotProduct(B.Origin,MuzzleLocalAxis)+FVector::DotProduct(B.BoxExtent,MuzzleLocalAxis.GetAbs());
            Check(FMath::Abs(FVector::DotProduct(Local,MuzzleLocalAxis)-Surface)<.001,
                TEXT("attachment launch point lies on front exit plane"));
            const double Extension=FVector::DotProduct(SampledMuzzle-Stock,Forward);
            Check(Extension>1.f,TEXT("modified muzzle extends beyond original muzzle"));
            Report+=FString::Printf(TEXT("MUZZLE_ORIGIN variant=%s extension_cm=%.4f\n"),MuzzleCases[MuzzleCase],Extension);
        }else Check(SampledMuzzle.Equals(Stock,.001),TEXT("removal restores original muzzle origin"));
        MagazineAmmo=MagazineCapacity;NextAllowedShotTime=Now;
        const int32 Before=ShotsFired;FireShot();
        Check(ShotsFired==Before+1&&!bLastShotMuzzleBlocked&&Ballistics->LastLaunchStart.Equals(SampledMuzzle+Forward.GetSafeNormal()*2.f,.001),
            TEXT("actual projectile starts 2 cm beyond pre-animation muzzle exit"));
        Capture(*FString::Printf(TEXT("07-muzzle-%s.png"),MuzzleCases[MuzzleCase]));
        Stage=18;Next=Now+.35;return;
    }
    if(Stage==18){
        ++MuzzleCase;Stage=MuzzleCase<4?16:19;Next=Now+.1;return;
    }
    if(Stage==19){
        Check(WeaponFX->EpicMuzzleBursts==ShotsFired&&WeaponFX->EpicMuzzleBursts>20&&WeaponFX->EpicSmokeBursts>0,TEXT("real fire drives Epic flash and heat smoke"));
        Stage=22;Next=Now+.5f;return;
    }
    static double StrafeStart=0;
    static FVector StrafeOrigin;
    static int32 StrafeFrame=0,PeakTracers=0;
    if(Stage==22){
        StrafeStart=Now;StrafeOrigin=GetActorLocation();
        MagazineAmmo=MagazineCapacity;FirePressed();Stage=23;Next=Now;return;
    }
    if(Stage==23){
        const double Elapsed=Now-StrafeStart;
        const double Offset=Elapsed<1.0?Elapsed*180.0:(2.0-Elapsed)*180.0;
        SetActorLocation(StrafeOrigin+FVector(0,Offset,0));
        PeakTracers=FMath::Max(PeakTracers,WeaponFX->GetActiveTracerCount());
        if(FParse::Param(FCommandLine::Get(),TEXT("BallisticCaptureFrames")))
            Capture(*FString::Printf(TEXT("Strafe/%04d.png"),StrafeFrame++));
        if(Elapsed>=2.0){
            FireReleased();
            Check(PeakTracers>0&&PeakTracers<=2,TEXT("lateral fire has bounded current flight segments without accumulated trails"));
            Check(WeaponFX->ExpiredTracerSegments>20,TEXT("previous frame tracer segments are retired"));
            Stage=21;Next=Now+6.f;
        }
        return;
    }
    if(Stage==21){
        Check(WeaponFX->GetActiveTracerCount()==0&&Ballistics->ActiveCount()==0,TEXT("no tracer remains after projectiles stop"));
        Check(WeaponFX->GetActiveEpicFXCount()==0,TEXT("Epic flashes and smoke finish after cooling without looping"));
        Report+=FString::Printf(TEXT("BALLISTIC_COMPLETE checks=%d failures=%d tracers=%d\n"),Checks,Failures,WeaponFX->TracerSegments-InitialTracers);
        FFileHelper::SaveStringToFile(Report,*FPaths::Combine(Dir,TEXT("assertions.log")));
        UE_LOG(LogTemp,Display,TEXT("%s"),*Report);Stage=20;
        FPlatformMisc::RequestExitWithStatus(false,Failures?1:0);
    }
}
