#pragma once
#include "CoreMinimal.h"

// Presentation-only profiles; ballistic pattern, attachment indices and fire
// cadence stay in WeaponHandling. Axes use the existing gun spring convention:
// position Z is rearward travel, rotation X is muzzle rise.
namespace FPSVisualRecoil
{
    struct FProfile
    {
        FVector Position = FVector(.72f,.75f,1.16f);
        FVector Rotation = FVector(.80f,.58f,.42f);
        float Flip = .72f, Jitter = .70f;
        float PositionStiffness = 300.f, PositionDamping = 24.f;
        float RotationStiffness = 320.f, RotationDamping = 25.f;
        // What the weapon's own fire animation does not carry, in the shared gun
        // convention: position is metres (Z rearward, X right, Y up), rotation is
        // radians (X muzzle rise, Y yaw, Z roll). The M4 reference fire clip
        // moves the gun 1.93 cm and 3.04 degrees on its own, so it needs none;
        // a weapon whose clip is a stub gets that motion here instead.
        FVector ClipPosition = FVector::ZeroVector;
        FVector ClipRotation = FVector::ZeroVector;
        // Armed aiming uses its own authored clip, and the reference one is a
        // straight rearward push with almost no rotation (2.32 cm, 0.48 deg) so
        // the sights stay on the eye line. Keep both sets apart: feeding the hip
        // values into ADS rotates the gun off the sights.
        FVector ClipADSPosition = FVector::ZeroVector;
        FVector ClipADSRotation = FVector::ZeroVector;
        // How much the gun itself may rotate while aiming down iron sights.
        // Rotating about the receiver swings the front post across the rear
        // notch by angle x sight radius: the AKM's Soviet sights are 38.7 cm
        // apart, so even one degree leaves a several millimetre notch. Long
        // radius sights therefore need this well below 1, or the post leaves the
        // notch and the sight picture cannot be used after the first shot.
        float ADSRotationScale = 1.f;
    };
    // Fire clip motion shape: the reference punches inside one 30 Hz frame and
    // settles over a few tenths of a second. Presentation only, no aim effect.
    inline float ClipWave(float Seconds)
    {
        constexpr float Attack = .033f;
        constexpr float Decay = .11f;
        if (Seconds < 0.f) return 0.f;
        if (Seconds < Attack)
        {
            const float Alpha = Seconds / Attack;
            return Alpha * Alpha * (3.f - 2.f * Alpha);
        }
        return FMath::Exp(-(Seconds - Attack) / Decay);
    }
    // Measured on each weapon's fire FBX weapon root; see
    // Docs/Weapons/rifle-fire-clip-recoil-20260917.md for the raw numbers.
    inline FVector ReferenceClipPosition() { return FVector(.00205f, 0.f, .01934f); }
    inline FVector ReferenceClipRotation() { return FVector(.05306f, .01663f, .01753f); }
    inline FVector ReferenceADSClipPosition() { return FVector(0.f, 0.f, .02323f); }
    inline FVector ReferenceADSClipRotation() { return FVector(.00838f, .00262f, 0.f); }
    // Dual wield fires two independent triggers from one unsupported hand pair.
    // Each shot keeps the single-pistol profile and adds an explicit one-hand
    // gain; the revolver (source 155 recoil / 125 camera shake against the
    // M1911's 110 / 95) is the heavier of the two hands.
    struct FDualWield
    {
        float HandGain = 1.f;
        float CameraGain = 1.f;
    };
    inline FDualWield ForDualWield(bool Revolver)
    {
        return Revolver ? FDualWield{1.35f,1.60f} : FDualWield{1.10f,1.25f};
    }
    inline FProfile ForWeapon(bool Pistol,bool Revolver,bool QBZ,bool M4)
    {
        FProfile P;
        if(Pistol)
        {
            P.Position=FVector(.50f,.9f,.72f);
            P.Rotation=FVector(Revolver?1.48f:1.28f,.46f,.36f);
            P.Flip=Revolver?1.26f:1.10f;P.Jitter=.52f;
            P.PositionStiffness=380.f;P.PositionDamping=29.f;
            P.RotationStiffness=Revolver?310.f:390.f;P.RotationDamping=Revolver?24.f:28.f;
        }
        else if(QBZ)
        {
            P.Position.Z=1.04f;P.Rotation.X=.72f;P.Flip=.64f;
            P.PositionStiffness=345.f;P.PositionDamping=27.f;
            P.RotationStiffness=360.f;P.RotationDamping=28.f;
            // QBZ fire clip: .49 cm and .73 deg measured against the reference.
            P.ClipPosition=ReferenceClipPosition()-FVector(0.f,0.f,.0049f);
            P.ClipRotation=ReferenceClipRotation()-FVector(.0128f,0.f,0.f);
            // Its aimed clip is the same pulse, so only the rearward travel is
            // short. Rotation stays out of ADS: it moves the post off the notch.
            P.ClipADSPosition=FVector(0.f,0.f,.010f);
            P.ClipADSRotation=FVector::ZeroVector;
        }
        else if(!M4)
        {
            // AKM retains a heavier pulse than the M4/QBZ.
            P.Position.Z=1.22f;P.Rotation.X=.94f;P.Flip=.86f;
            P.PositionStiffness=275.f;P.PositionDamping=22.f;
            P.RotationStiffness=285.f;P.RotationDamping=23.f;
            // The AKM fire clip is a six frame stub with a static weapon root,
            // so the whole reference motion has to come from here.
            P.ClipPosition=ReferenceClipPosition();
            P.ClipRotation=ReferenceClipRotation();
            // Its Soviet sights sit 38.7 cm apart: a .48 deg rise is enough to
            // swing the front post out of the notch, so ADS keeps the push only.
            P.ClipADSPosition=FVector(0.f,0.f,.012f);
            P.ClipADSRotation=FVector::ZeroVector;
            P.ADSRotationScale=.4f;
        }
        return P;
    }
}
