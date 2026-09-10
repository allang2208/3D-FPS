#include "FPSGAMECharacter.h"
#include "Weapons/GunsmithSystem.h"
#include "UI/ColdSteelStatusModel.h"
#include "UI/ColdSteelItemTooltipData.h"
#include "UI/M4GunsmithWidget.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "TimerManager.h"
#include "UnrealClient.h"

// Explicitly opt-in, isolated save only. Integration uses real catalog selection,
// save/restore and pawn binding; deterministic feedback probes are separate from
// the existing controller-input gunplay acceptance suite.
void AFPSGAMECharacter::RunWeaponHandlingAudit()
{
    static bool Done=false;
    if(Done||GetWorld()->GetTimeSeconds()<6.f)return;
    Done=true;
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    auto* PC=Cast<APlayerController>(Controller);
    if(!P||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("WeaponHandlingAudit"))||!G||!PC)
    {UE_LOG(LogTemp,Error,TEXT("HANDLING: isolated profile required"));FPlatformMisc::RequestExitWithStatus(false,2);return;}
    int32 Checks=0,Failures=0;
    FString Report=TEXT("case,pass\n");
    auto Check=[&](bool Pass,const TCHAR* Name){++Checks;if(!Pass)++Failures;Report+=FString::Printf(TEXT("%s,%d\n"),Name,Pass);UE_LOG(LogTemp,Display,TEXT("HANDLING: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);};
    const auto Near=[](double A,double B){return FMath::Abs(A-B)<.0001;};
    auto* W=const_cast<FGunsmithWeapon*>(G->Weapon(TEXT("ue_m4a1")));
    if(!W||!P->Equipped()){Check(false,TEXT("live equipped M4 exists"));FPlatformMisc::RequestExitWithStatus(false,2);return;}
    const auto OriginalOptions=W->Options;
    const auto OriginalBase=W->Base;
    const FString Instance=P->Equipped()->InstanceId;
    auto* Drum=const_cast<FGunsmithOption*>(G->Option(W->Id,TEXT("magazine"),TEXT("large_drum")));
    auto* Optic=const_cast<FGunsmithOption*>(G->Option(W->Id,TEXT("optic"),TEXT("holographic")));
    if(!Drum||!Optic){FPlatformMisc::RequestExitWithStatus(false,2);return;}
    // These values never modify the catalog on disk or a player's save.
    Drum->Recoil=.8;Drum->Shake=.64;Optic->Recoil=.9;Optic->Shake=.81;
    Drum->Effects.Add({TEXT("验收样本：后坐力降低20%，抖动降低36%"),1});
    Optic->Effects.Add({TEXT("验收样本：后坐力降低10%，抖动降低19%"),1});
    Check(G->Begin(Instance),TEXT("open equipped instance"));
    Check(G->Select(TEXT("magazine"),TEXT("large_drum")),TEXT("select recoil stability fixture"));
    auto Draft=G->Calculate(W->Id,G->Draft());
    Check(Near(Draft.Recoil,80)&&Near(Draft.Shake,64),TEXT("draft computes physical indices"));
    Check(Near(WeaponHandling.RecoilIndex,100)&&Near(WeaponHandling.ShakeIndex,100),TEXT("draft does not change live shooting"));
    G->Undo();Check(G->Pending()==0,TEXT("undo restores original"));
    G->Select(TEXT("magazine"),TEXT("large_drum"));G->Select(TEXT("optic"),TEXT("holographic"));
    Draft=G->Calculate(W->Id,G->Draft());
    Check(Near(Draft.Recoil,72)&&Near(Draft.Shake,51.84),TEXT("multiplicative stacking 20 and 10 percent gives 28 percent"));
    Check(Draft.Handling.Stability>50&&Draft.Handling.Stability<100,TEXT("less shake gives higher bounded stability"));
    P->AuditFailNextSave=true;
    Check(!G->Apply()&&Near(WeaponHandling.RecoilIndex,100),TEXT("failed save leaves shooting unchanged"));
    Check(G->Apply(),TEXT("apply saves installed modifiers"));
    Check(Near(WeaponHandling.RecoilIndex,72)&&Near(WeaponHandling.ShakeIndex,51.84),TEXT("installed modifiers reach live pawn"));
    for(int32 I=0;I<3;++I)ApplyColdSteelProfile(P);
    Check(Near(BallisticRecoilScale,.504),TEXT("profile rebind never compounds recoil"));
    Check(P->ReloadProfile()&&Near(WeaponHandling.ShakeIndex,51.84),TEXT("saved instance restores handling"));
    const auto Tooltip=BuildColdSteelItemTooltip(*P->Equipped(),P,G);
    bool TooltipStability=false;
    for(const auto& Card:Tooltip.Cards)for(const auto& Row:Card.Rows)
        if(Row.Label.Contains(TEXT("枪械稳定性")))TooltipStability=true;
    Check(TooltipStability,TEXT("equipment tooltip exposes stability"));
    W->Base.Recoil=150;W->Base.Shake=144;
    const auto NonDefault=G->Calculate(W->Id,{});
    Check(Near(NonDefault.Handling.RecoilScale,1.5)&&Near(NonDefault.Handling.ShakeScale,1.44),TEXT("weapon base indices also drive handling"));
    W->Base=OriginalBase;

    auto Reset=[&](double Recoil,double Shake){
        WeaponHandling=FWeaponHandling::FromIndices(Recoil,Shake);
        BallisticRecoilScale=FWeaponHandling::ReferenceBallisticScale*WeaponHandling.RecoilScale;
        PC->SetControlRotation(FRotator::ZeroRotator);RecoilPatternIndex=0;
        CurrentSpread=MoveSpread=AirSpread=0;FireTrauma=FOVPunch=0;
        GunKickPosition=GunKickPositionVelocity=GunKickRotation=GunKickRotationVelocity=FVector::ZeroVector;
        GunJitterPosition=GunJitterPositionVelocity=GunJitterRotation=GunJitterRotationVelocity=FVector::ZeroVector;
        CameraJitterPosition=CameraJitterPositionVelocity=CameraJitterRotation=CameraJitterRotationVelocity=FVector::ZeroVector;
        GunFlip=GunFlipVelocity=CameraKickPitch=CameraKickPitchVelocity=CameraKickYaw=CameraKickYawVelocity=0;
        CameraADSFactor=WeaponADSFactor=1;TimeSinceLastShot=0;PatternRecoveryAccumulator=0;
        FMath::RandInit(81723);
    };
    Reset(100,100);ApplyShotFeedback();
    const float BasePitch=PC->GetControlRotation().Pitch;
    const FVector BaseJitter=GunJitterRotationVelocity;
    const float BaseCamera=CameraKickPitchVelocity;
    Check(Near(BasePitch,WeaponHandling.FirstShotDegrees()),TEXT("UI first-shot degrees equal actual control impulse"));
    Reset(80,100);ApplyShotFeedback();
    Check(Near(PC->GetControlRotation().Pitch,BasePitch*.8),TEXT("recoil reduction changes actual aim by 20 percent"));
    Check(GunJitterRotationVelocity.Equals(BaseJitter,.0001),TEXT("recoil does not double-scale independent jitter"));
    Reset(100,64);ApplyShotFeedback();
    Check(Near(PC->GetControlRotation().Pitch,BasePitch),TEXT("stability does not grant extra recoil compensation"));
    Check(GunJitterRotationVelocity.Equals(BaseJitter*.64,.0001)&&Near(CameraKickPitchVelocity,BaseCamera*.64),TEXT("stability scales gun and camera impulses once"));
    const FRotator ControlBeforeRecovery=PC->GetControlRotation();
    UpdateWeaponFeedback(.6f);
    Check(PC->GetControlRotation().Equals(ControlBeforeRecovery,.0001),TEXT("settling never auto aims back to pre-shot position"));
    Reset(100,100);
    float Previous=0;
    for(int32 I=0;I<12;++I){ApplyShotFeedback();const float Current=PC->GetControlRotation().Pitch;
        if(I>=8)Check(Near(Current-Previous,WeaponHandling.MaxVerticalDegrees()),TEXT("sustained shot upper limit matches UI"));Previous=Current;}
    Reset(0,0);ApplyShotFeedback();
    Check(Near(PC->GetControlRotation().Pitch,0)&&GunJitterRotationVelocity.IsNearlyZero()&&Near(CameraKickPitchVelocity,0),TEXT("zero indices remove their respective impulses"));
    Check(Near(WeaponHandling.Stability,100)&&Near(WeaponHandling.ADSRecoveryMilliseconds(),0),TEXT("zero shake has full stability and no shake recovery"));
    Check(Near(FWeaponHandling::FromIndices(-10,900).RecoilIndex,0)&&Near(FWeaponHandling::FromIndices(-10,900).ShakeIndex,400),TEXT("invalid range is bounded before UI and runtime"));

    // Measure actual analytic spring response at multiple frame rates and a hitch.
    // The time at 10% envelope is independent of frame partitioning.
    FString Curve=TEXT("shake,hz,time_ms,camera_pitch_deg,envelope_deg\n");
    for(float Shake:{100.f,64.f}){
        const auto H=FWeaponHandling::FromIndices(100,Shake);
        float Reference=0;
        for(int32 Hz:{30,60,144}){
            Reset(100,Shake);ApplyShotFeedback();
            const float InitialVelocity=CameraKickPitchVelocity;
            const float Omega=FMath::Sqrt(FWeaponHandling::CameraStiffness-FMath::Square(11.5f));
            const float InitialEnvelope=FMath::Abs(InitialVelocity)/Omega;
            const float End=H.ADSRecoveryMilliseconds()/1000.f;
            float T=0;
            while(T<End-.000001f){const float Dt=FMath::Min(1.f/Hz,End-T);UpdateWeaponFeedback(Dt);T+=Dt;
                const float Envelope=InitialEnvelope*FMath::Exp(-11.5f*T*H.RecoveryRate());
                Curve+=FString::Printf(TEXT("%.0f,%d,%.3f,%.8f,%.8f\n"),Shake,Hz,T*1000,FMath::RadiansToDegrees(CameraKickPitch),FMath::RadiansToDegrees(Envelope));}
            Check(FMath::Abs(CameraKickPitch)<=InitialEnvelope*.1001f,TEXT("90 percent envelope settling bound holds"));
            if(Hz==30)Reference=CameraKickPitch;else Check(Near(CameraKickPitch,Reference),TEXT("30 60 144 Hz spring partition invariance"));
        }
        Reset(100,Shake);ApplyShotFeedback();UpdateWeaponFeedback(H.ADSRecoveryMilliseconds()/1000.f);
        Check(Near(CameraKickPitch,Reference),TEXT("single hitch equals multi-frame settling"));
    }
    Reset(100,100);ApplyColdSteelProfile(P);
    G->Begin(Instance);G->Select(TEXT("magazine"),TEXT("false"));G->Select(TEXT("optic"),TEXT("false"));
    Check(G->Apply()&&Near(WeaponHandling.RecoilIndex,100)&&Near(WeaponHandling.ShakeIndex,100),TEXT("removing parts restores factory shooting"));
    Check(P->ReloadProfile()&&G->Installed(*P->Equipped()).IsEmpty(),TEXT("removal persists"));
    G->Begin(Instance);G->Select(TEXT("magazine"),TEXT("large_drum"));G->Select(TEXT("optic"),TEXT("holographic"));
    auto* Panel=CreateWidget<UM4GunsmithWidget>(PC,UM4GunsmithWidget::StaticClass());
    Panel->AddToViewport(100);Panel->Choose(true);Panel->ChooseDrum(true);Panel->SetCompareFactory(true);Panel->RefreshPresentation();
    bool RowsOK=false;
    for(const auto& Row:Panel->GetOverviewRows())if(Row.Label==TEXT("枪械稳定性 ↑"))RowsOK=Row.Benefit==1;
    Check(RowsOK,TEXT("actual workbench highlights improved stability green"));
    const FString Directory=FPaths::ProjectSavedDir()/TEXT("WeaponHandlingAudit");
    IFileManager::Get().MakeDirectory(*Directory,true);
    FFileHelper::SaveStringToFile(Report,*(Directory/TEXT("assertions.csv")));
    FFileHelper::SaveStringToFile(Curve,*(Directory/TEXT("settling.csv")));
    UE_LOG(LogTemp,Display,TEXT("HANDLING_COMPLETE checks=%d failures=%d"),Checks,Failures);
    FTimerHandle CaptureTimer;GetWorldTimerManager().SetTimer(CaptureTimer,[Directory](){FScreenshotRequest::RequestScreenshot(Directory/TEXT("handling-panel.png"),true,false);},1.f,false);
    FTimerHandle ExitTimer;GetWorldTimerManager().SetTimer(ExitTimer,[G,W,OriginalOptions,Panel,Failures](){Panel->RemoveFromParent();G->Close();W->Options=OriginalOptions;FPlatformMisc::RequestExitWithStatus(false,Failures?1:0);},2.5f,false);
}
