#pragma once
#include "CoreMinimal.h"
#include "KukriRhythm.h"
#include "KukriHeavyRhythm.h"
#include "KukriOffhandDraw.h"
#include "OffhandBladeDraw.h"
#include "SwiftFalconHeavy.h"
namespace KukriWeaponPrivate
{
    inline const TCHAR* KukriPommelHitPath=TEXT("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick");
    inline const TCHAR* KukriWallPath=TEXT("/Game/Audio/MeleeBlock20260927/S_MeleeBlock_02.S_MeleeBlock_02");
    inline const FName KukriIdle(TEXT("Idle")),KukriWalk(TEXT("Walk")),KukriRun(TEXT("Run")),KukriEquip(TEXT("Equip"));
    inline const FName KukriDualIdle(TEXT("DualIdle")),KukriDualWalk(TEXT("DualWalk")),KukriDualRun(TEXT("DualRun"));
    // Dual draw: the single toss-and-catch on the right, its mirror on the left a beat later, into the dual hold.
    inline const FName KukriDualEquip(TEXT("DualEquip"));
    // Single hatchet draw: a straight vertical toss without spin, caught by the handle (HatchetDrawRhythm.h).
    inline const FName KukriHatchetEquip(TEXT("HatchetEquip"));
    // ...and its last combo hit: an overhead chop instead of the kukri's stab (HatchetChopRhythm.h).
    inline const FName KukriHatchetAttack3(TEXT("HatchetAttack3"));
    inline const FName KukriHatchetDualAttack3(TEXT("HatchetDualAttack3"));
    // Dual hatchets' sprint-ready run set: enter (from the idle hand gesture) / loop (raised) / exit (HatchetReadyRhythm.h).
    inline const FName KukriHatchetReadyEnter(TEXT("HatchetDualSprintEnter")),
        KukriHatchetReadyRun(TEXT("HatchetDualSprintReady")), KukriHatchetReadyExit(TEXT("HatchetDualSprintExit"));
    // Hatchet pairs (HatchetPairRhythm.h): two hatchets draw with the hatchet's own toss; a hatchet + kukri pair plays each
    // hand's own weapon in the draw and on combo stage 3 (HK = hatchet right / kukri left, KH = kukri right / hatchet left).
    inline const FName KukriHatchetDualEquip(TEXT("HatchetDualEquip")),KukriPairEquipHK(TEXT("HatchetPairEquipHK")),
        KukriPairEquipKH(TEXT("HatchetPairEquipKH")),KukriPairAttack3HK(TEXT("HatchetPairAttack3HK")),
        KukriPairAttack3KH(TEXT("HatchetPairAttack3KH"));
    // The pair's sprint attack: both hands chop down (KukriDualDashRhythm.h, played by KukriDashAttack.cpp).
    inline const FName KukriDualDash(TEXT("DualSprintAttack"));
    // ShadowStepSlash (瞬步掠影斩): Stage 1 dash-through slash + Stage 2 reverse backhand follow-up (single & dual).
    inline const FName KukriShadowStep(TEXT("ShadowStep")), KukriShadowStepFollow(TEXT("ShadowStepFollow"));
    inline const FName KukriDualShadowStep(TEXT("DualShadowStep")), KukriDualShadowStepFollow(TEXT("DualShadowStepFollow"));
    inline bool IsDualEquipClip(FName Clip)
    {
        return Clip==KukriDualEquip||Clip==KukriHatchetDualEquip||Clip==KukriPairEquipHK||Clip==KukriPairEquipKH||OffhandBladeDraw::IsClip(Clip);
    }
    // The draw clips whose right / left hand tosses a hatchet (the others toss a kukri).
    inline bool IsRightHatchetDraw(FName Clip){return Clip==KukriHatchetEquip||Clip==KukriHatchetDualEquip||Clip==KukriPairEquipHK;}
    inline bool IsLeftHatchetDraw(FName Clip){return Clip==KukriHatchetDualEquip||Clip==KukriPairEquipKH||Clip==OffhandBladeDraw::Hatchet;}
    inline const FName KukriWeaponSocket(TEXT("WPN_root")),KukriOffhandSocket(TEXT("hand_l"));
    inline constexpr float KukriWalkReferenceSpeed=360.f;
    // The left arm travels between the single stance (hanging below the frame) and the dual hold.
    inline constexpr float KukriDualArmBlendSeconds=.25f;
    // Dual run (reference sprint, R4): the right kukri sits reversed in the fist, turned 180 deg about its grip-frame Y
    // (edge to the wrist, blade straight ahead), as authored in A_Kukri_DualRun (run_keys.json flip 'y'); the left keeps
    // the forward grip.  R5 (user 2026-10-26: no twirl, just a natural change): the half turn rides the arm's own blend into
    // and out of the run -- same time, same curve as the local-space entry blend (KukriArmsMeshComponent::CaptureEntry), so
    // the blade turns over the fingers while the fist travels up into the corner, and back on the way down.
    inline constexpr float KukriDualRunBlendSeconds=.24f, KukriDualFlipAngle=PI;
    inline const FVector KukriRunFlipAxis(0.f,1.f,0.f);
    // Dual sweeps: combo stages 1 and 2 with two kukris (right blade, then the mirrored left blade).
    inline const FName KukriDualAttacks[KukriRhythm::DualSweepStages]={FName(KukriRhythm::DualSweepClips[0]),FName(KukriRhythm::DualSweepClips[1])};
    // ...and stage 3: both blades thrust together.
    inline const FName KukriDualThrust(KukriRhythm::DualThrustClip);
    inline bool IsDualClip(FName Clip)
    {
        return Clip==KukriDualIdle||Clip==KukriDualWalk||Clip==KukriDualRun||Clip==KukriDualAttacks[0]||Clip==KukriDualAttacks[1]||
            Clip==KukriDualThrust||Clip==KukriHeavyRhythm::DualChargeClip||Clip==KukriHeavyRhythm::DualReleaseClip||
            IsDualEquipClip(Clip)||Clip==KukriPairAttack3HK||Clip==KukriPairAttack3KH||Clip==KukriDualDash||
            Clip==KukriDualShadowStep||Clip==KukriDualShadowStepFollow||
            Clip==SwiftFalconHeavy::DualCharge||Clip==SwiftFalconHeavy::DualRelease;
    }
    inline bool IsRunClip(FName Clip){return Clip==KukriRun||Clip==KukriDualRun||Clip==KukriHatchetReadyEnter||
        Clip==KukriHatchetReadyRun||Clip==KukriHatchetReadyExit;}
    inline bool IsWalkClip(FName Clip){return Clip==KukriWalk||Clip==KukriDualWalk;}
    // Off-hand SM_Kukri on hand_l: the mirror of the accepted right grip (SourceAssets/DualKukriIdle20261025/
    // left_kukri.json; hand_l carries the rig's 100x import scale like WPN_root, the mesh is in centimetres).
    inline FTransform OffhandHandToBlade()
    {
        return KukriOffhandDraw::Grip();
    }
    // ...and through the dual draw: the off-hand kukri's mirrored toss on hand_l (KukriDualEquipBlade.h, generated by
    // SourceAssets/DualKukriIdle20261025/author_dual_equip.py), the constant grip again from the catch on.
    inline FTransform OffhandDrawBlade(float Time)
    {
        return KukriOffhandDraw::Sample(Time);
    }
}
