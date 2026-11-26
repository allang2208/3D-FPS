#include "../FPSGAMECharacter.h"
#include "FPSVisualRecoil.h"
#include "M24Recoil.h"
#include "WeaponBipodDeploymentComponent.h"
#include "ColdSteelEnchantmentCombat.h"
#include "LMGStabilityGrip.h"

float AFPSGAMECharacter::StabilityGripFireAlpha(double Now) const
{
    if (!bStabilityGripInstalled || !bFireHeld || TriggerFirstShotWorldTime < 0.)
        return 0.f;
    return static_cast<float>(FMath::Clamp((Now - TriggerFirstShotWorldTime) / LMGStabilityGrip::FullBonusSeconds, 0., 1.));
}

FWeaponHandling AFPSGAMECharacter::FeedbackHandlingAt(float GripAlpha)
{
    auto Handling = ColdSteelCombat::ComposureHandling(this, WeaponHandling);
    if (BipodDeployment)
        Handling = BipodDeployment->ApplyStability(Handling);
    if (GripAlpha > 0.f)
        Handling = Handling.WithStabilityPoints(GripAlpha * LMGStabilityGrip::MaxBonusStabilityPoints);
    return Handling;
}

void AFPSGAMECharacter::AdvanceVisualWeaponRecoil(double Now)
{
    if(VisualRecoilUpdatedAt<0.){VisualRecoilUpdatedAt=Now;return;}
    const double Previous=VisualRecoilUpdatedAt;
    const float Elapsed=static_cast<float>(FMath::Max(0.,Now-Previous));
    VisualRecoilUpdatedAt=Now;
    if(Elapsed<=0.f)return;
    const auto Profile=IsM24Weapon()?M24Recoil::VisualProfile():FPSVisualRecoil::ForWeapon(IsPistolWeapon(),bUseDanWesson715,bUseQBZ191,bUseM4Infima || bUseM16);
    const float AttackDelta=FMath::Clamp(static_cast<float>(VisualRecoverAt-Previous),0.f,Elapsed);
    const FWeaponHandling FeedbackHandling = FeedbackHandlingAt(StabilityGripFireAlpha(Now));
    // Integrate across the event boundary exactly once. Multiple shots in one
    // frame add impulses at their actual time; Tick never ages a newborn impulse
    // using the interval before it was fired.
    auto Integrate=[&](float Seconds,bool Recovering)
    {
        if(Seconds<=0.f)return;
        const float Dt=Seconds*FeedbackHandling.RecoveryRate();
        const float PositionDamping=Recovering?1.94f*FMath::Sqrt(Profile.PositionStiffness):Profile.PositionDamping;
        const float RotationDamping=Recovering?1.94f*FMath::Sqrt(Profile.RotationStiffness):Profile.RotationDamping;
        AdvanceSpring(GunKickPosition,GunKickPositionVelocity,Profile.PositionStiffness,PositionDamping,Dt);
        AdvanceSpring(GunKickRotation,GunKickRotationVelocity,Profile.RotationStiffness,RotationDamping,Dt);
        AdvanceSpring(GunFlip,GunFlipVelocity,Profile.RotationStiffness,RotationDamping,Dt);
        AdvanceSpring(GunJitterPosition,GunJitterPositionVelocity,7000.f,Recovering?70.f:54.f,Dt);
        AdvanceSpring(GunJitterRotation,GunJitterRotationVelocity,7000.f,Recovering?70.f:54.f,Dt);
    };
    Integrate(AttackDelta,false);
    Integrate(Elapsed-AttackDelta,true);
}
