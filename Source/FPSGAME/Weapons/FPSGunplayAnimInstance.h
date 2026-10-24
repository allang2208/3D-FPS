#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "FPSGunplayAnimInstance.generated.h"

class UAnimSequence;
class UWeaponGripProfile;

// Local first-person presentation. Gameplay owns the clock; the graph only blends poses.
UCLASS(Transient)
class FPSGAME_API UFPSGunplayAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> AimClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ActionClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> SprintClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> SprintLoopClip;
    float SprintTime = 0.0f;
    float SprintAlpha = 0.0f;
    float SprintLoopTime = 0.0f;
    float SprintLoopAlpha = 0.0f;
    float BaseTime = 0.0f;
    float AimAlpha = 0.0f;
    float ActionTime = 0.0f;
    float ActionAlpha = 0.0f;
    bool bRevolver = false;
    int32 RevolverLiveRounds = 6;
    int32 RevolverCartridges = 6;
    bool bDualPistolAim=false;
    int32 DualPistolSide=0;
    float DualPistolAimAlpha=0.f;
    FVector DualPistolAimTargetWorld=FVector::ZeroVector;
    // Align the evaluated neutral left-hand pose; apply the same rigid delta
    // to the action pose so firing keeps its authored recoil and contacts.
    float LonePistolADSAlpha=0.f;
    float LonePistolEyeDistance=30.f;
    FName LonePistolSightBone;
    FTransform LonePistolOpticMount=FTransform::Identity;
    FVector LonePistolSightRear=FVector::ZeroVector;
    FVector LonePistolSightFront=FVector::ForwardVector;
    FVector LonePistolSightUp=FVector::UpVector;
    // 副手手枪单持：整段姿态绕相机竖直面反射成左手，组件保持正缩放，枪身贴图不翻面。
    bool bMirrorLeftHand=false;
    // 镜面法线在网格物体空间的方向（单位向量）；角色每帧按当前机位/开镜旋转换算。
    FVector LeftHandMirrorPlane=FVector::RightVector;
    // 骨架是否具备镜像条件（有 WPN_root）；否则由角色退回镜像场景节点。
    bool bLeftHandMirrorReady=false;
    // GripLayer56 (GripPoseLayer.h): per-channel grip layer and its reference pairs.
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> GripIdleBase;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> GripIdleFamily;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> GripAimBase;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> GripAimFamily;
    bool bGripIdle=false,bGripAim=false,bGripSprint=false,bGripAction=false,bGripActionAim=false;
    // Compact authored corrections; one attachment family shared by all source channels.
    UPROPERTY(Transient) TObjectPtr<UWeaponGripProfile> GripProfile;
    // Action-specific registration can retain its contact while idle/ADS use another grip.
    UPROPERTY(Transient) TObjectPtr<UWeaponGripProfile> ActionGripProfile;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
