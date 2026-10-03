#include "../FPSGAMECharacter.h"
#include "FPSGunplayAnimInstance.h"
#include "WeaponGripProfile.h"
#include "Components/SkeletalMeshComponent.h"

bool AFPSGAMECharacter::SampleRSH12Presentation(UAnimSequence* Clip)
{
    if(!IsRSH12Weapon() || !Clip || !AKMViewmodel)return false;
    AKMViewmodel->SetAnimationMode(EAnimationMode::AnimationBlueprint);
    AKMViewmodel->SetAnimInstanceClass(UFPSGunplayAnimInstance::StaticClass());
    auto* Pose=Cast<UFPSGunplayAnimInstance>(AKMViewmodel->GetAnimInstance());
    if(!Pose)return false;
    Pose->GripProfile=WeaponGripProfileFor(EM4SprintGrip::Base);
    Pose->IdleClip=Clip;Pose->AimClip=nullptr;Pose->ActionClip=nullptr;
    Pose->SprintClip=nullptr;Pose->SprintLoopClip=nullptr;
    Pose->BaseTime=0.f;Pose->AimAlpha=0.f;Pose->ActionAlpha=0.f;
    Pose->SprintAlpha=0.f;Pose->SprintLoopAlpha=0.f;
    Pose->bRevolver=true;Pose->RevolverLiveRounds=5;Pose->RevolverCartridges=5;
    return true;
}
