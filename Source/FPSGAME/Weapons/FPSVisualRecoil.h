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
    };
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
        }
        else if(!M4)
        {
            // AKM retains a heavier pulse than the M4/QBZ.
            P.Position.Z=1.22f;P.Rotation.X=.94f;P.Flip=.86f;
            P.PositionStiffness=275.f;P.PositionDamping=22.f;
            P.RotationStiffness=285.f;P.RotationDamping=23.f;
        }
        return P;
    }
}
