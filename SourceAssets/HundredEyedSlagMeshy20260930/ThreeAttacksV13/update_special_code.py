"""Apply the scoped laser-presentation replacement and retire jump execution."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=ROOT/'Source/FPSGAME/Monsters/HundredEyedSlagSpecialAttacks.cpp'
s=p.read_text(encoding='utf-8-sig')
for line in ('#include "Mutant3PounceCameraShake.h"\n',
    '#include "../Weapons/FPSImpactFXSubsystem.h"\n','#include "Camera/CameraComponent.h"\n',
    '#include "Engine/OverlapResult.h"\n'):
    s=s.replace(line,'')
s=s.replace('    return State == ESlagState::EyeLaserWindup || State == ESlagState::EyeLaserFire\n'
    '        || State == ESlagState::EyeLaserRecover || State == ESlagState::JumpWindup\n'
    '        || State == ESlagState::JumpAir || State == ESlagState::JumpImpact || State == ESlagState::JumpRecover;',
    '    return State == ESlagState::EyeLaserWindup || State == ESlagState::EyeLaserFire\n'
    '        || State == ESlagState::EyeLaserRecover;')
start=s.index('void AHundredEyedSlagMonster::UpdateLaserFX(')
end=s.index('void AHundredEyedSlagMonster::ReleaseEyeLaser()',start)
replacement=r'''void AHundredEyedSlagMonster::UpdateLaserFX(float Energy, bool Firing)
{
    if (GetNetMode() == NM_DedicatedServer || EyeLaserRenderers.Num() != 7) return;
    auto* PC = GetWorld()->GetFirstPlayerController();
    if (!PC || !PC->PlayerCameraManager
        || FVector::DistSquared(PC->PlayerCameraManager->GetCameraLocation(),GetActorLocation()) > FMath::Square(2600.f))
    { ClearLaserFX(); return; }
    if (EyeLaserMaterials.IsEmpty())
    {
        auto* Glow = EyeLaserRenderers[0]->CreateDynamicMaterialInstance(0);
        auto* Core = EyeLaserRenderers[5]->CreateDynamicMaterialInstance(0);
        if (!Glow || !Core) return;
        EyeLaserMaterials.Add(Glow); EyeLaserMaterials.Add(Core);
        Glow->SetVectorParameterValue(TEXT("Tint"),FLinearColor(1.f,.008f,.003f));
        Core->SetVectorParameterValue(TEXT("Tint"),FLinearColor(1.f,.65f,.25f));
        Glow->SetScalarParameterValue(TEXT("Opacity"),.55f);
        Core->SetScalarParameterValue(TEXT("Opacity"),.8f);
        for (int32 I : {0,1,4,6}) EyeLaserRenderers[I]->SetMaterial(0,Glow);
        EyeLaserRenderers[5]->SetMaterial(0,Core);
    }
    if (!EyeChargeMaterial)
    {
        EyeChargeMaterial = EyeChargeParticles->CreateDynamicMaterialInstance(0);
        if (EyeChargeMaterial)
        {
            EyeChargeMaterial->SetVectorParameterValue(TEXT("Tint"),FLinearColor(1.f,.006f,.002f));
            EyeChargeMaterial->SetScalarParameterValue(TEXT("Opacity"),.9f);
            EyeLaserRenderers[2]->SetMaterial(0,EyeChargeMaterial);
            EyeLaserRenderers[3]->SetMaterial(0,EyeChargeMaterial);
        }
    }
    Energy = FMath::Clamp(Energy,0.f,1.f);
    const float Pulse = 1.f+.07f*FMath::Sin(StateSeconds*22.f);
    EyeLaserMaterials[0]->SetScalarParameterValue(TEXT("Intensity"),Firing ? 22.f : (4.f+16.f*Energy)*Pulse);
    EyeLaserMaterials[1]->SetScalarParameterValue(TEXT("Intensity"),18.f);
    if (EyeChargeMaterial) EyeChargeMaterial->SetScalarParameterValue(TEXT("Intensity"),Firing ? 16.f : (8.f+24.f*Energy)*Pulse);
    const FVector View = PC->PlayerCameraManager->GetCameraLocation();
    const FVector Right = GetActorRightVector(), Up = GetActorUpVector(), Forward = GetActorForwardVector();
    if (!Firing && EyeChargeParticles->GetInstanceCount() == EyeChargeParticleCount)
    {
        for (int32 I = 0; I < EyeChargeParticleCount; ++I)
        {
            const float Life = FMath::Fmod(StateSeconds*1.2f+I*.618034f,1.f);
            const float Inward = 1.f-Life;
            const float Angle = I*2.399963f+Life*4.8f;
            const float Radius = (44.f+16.f*Energy)*Inward;
            // Push the sprites in front of the skin; the V12 small spheres
            // faded against the surface and were barely readable at range.
            const FVector Position = LaserEye(I%2)+Forward*(12.f+20.f*Inward)
                +(Right*FMath::Cos(Angle)+Up*FMath::Sin(Angle))*Radius;
            const float RadiusCM = (3.5f+3.f*Life)*FMath::Clamp(Energy*8.f,0.f,1.f);
            const FQuat Facing = FRotationMatrix::MakeFromZ(View-Position).ToQuat();
            EyeChargeParticles->UpdateInstanceTransform(I,FTransform(Facing,Position,FVector(RadiusCM/50.f)),
                true,I == EyeChargeParticleCount-1,true);
        }
        EyeChargeParticles->SetVisibility(Energy > .01f);
    }
    else EyeChargeParticles->SetVisibility(false);
    const FVector Focus = LaserFocus();
    for (int32 I = 0; I < 2; ++I)
    {
        const FVector Eye = LaserEye(I)+Forward*8.f;
        EyeLaserRenderers[I]->SetWorldLocation(Eye);
        EyeLaserRenderers[I]->SetWorldScale3D(FVector((3.f+5.f*Energy)/50.f));
        EyeLaserRenderers[I]->SetVisibility(Energy > .02f);
        const FVector Halo = Eye+Forward*4.f;
        const float RadiusCM = (10.f+8.f*Energy)*(I == 0 ? 1.f : .8f);
        EyeLaserRenderers[I+2]->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(View-Halo).ToQuat(),
            Halo,FVector(RadiusCM/50.f)));
        EyeLaserRenderers[I+2]->SetVisibility(Energy > .02f);
    }
    EyeLaserRenderers[4]->SetWorldLocation(Focus);
    EyeLaserRenderers[4]->SetWorldScale3D(FVector((1.5f+4.5f*Energy)/50.f));
    EyeLaserRenderers[4]->SetVisibility(Energy > .1f);
    const FVector Delta = LaserEnd-Focus;
    for (int32 I = 5; I < 7; ++I)
    {
        const float Radius = I == 5 ? 2.5f : 7.f;
        EyeLaserRenderers[I]->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(Delta).ToQuat(),
            (Focus+LaserEnd)*.5,FVector(Radius/50.f,Radius/50.f,Delta.Size()/100.f)));
        EyeLaserRenderers[I]->SetVisibility(Firing && Delta.SizeSquared() > 1.f);
    }
}

'''
s=s[:start]+replacement+s[end:]
start=s.index('void AHundredEyedSlagMonster::BeginJumpSlam()')
end=s.index('void AHundredEyedSlagMonster::TickSpecialAttack(',start)
s=s[:start]+s[end:]
s=s.replace('const bool Windup = State == ESlagState::EyeLaserWindup || State == ESlagState::JumpWindup;',
    'const bool Windup = State == ESlagState::EyeLaserWindup;')
start=s.index('    case ESlagState::JumpWindup:')
end=s.index('    default: break;',start)
s=s[:start]+s[end:]
p.write_text(s,encoding='utf-8')
# Keep deprecated reflected names and enum ordinals for old saved objects.
p=ROOT/'Source/FPSGAME/Monsters/HundredEyedSlagMonster.h'
s=p.read_text(encoding='utf-8-sig').replace('    virtual void Landed(const FHitResult& Hit) override;\n','')
import re
s=re.sub(r'UPROPERTY\(EditAnywhere, Category="Slag\|JumpSlam", meta=\([^\n]*?\)\)',
    'UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Jump attack retired; only Sweep, Slam and EyeLaser are active"))',s)
s=s.replace('Replaced by EyeLaser/JumpSlam','Replaced by EyeLaser; retired attack')
p.write_text(s,encoding='utf-8')
print('SLAG_V13_THREE_ATTACKS_AND_RED_EYE_FX_SOURCE_WRITTEN')
