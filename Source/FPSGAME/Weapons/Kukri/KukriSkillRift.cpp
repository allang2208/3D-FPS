#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriDashRhythm.h"
#include "KukriSkillRiftRibbons.h"
#include "KukriDualDashRhythm.h"
#include "ShadowStepRiftRibbons.h"
#include "../RuneSwordWhirlwindFeel.h"
#include "../../FPSGAMECharacter.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

// Skill rifts (2026-10-24, user: the combo's space distortion on the whirlwind and the sprint attack too).  Same material
// and life cycle as the combo rift (KukriRift.cpp: M_RuneRift, SweepProgress reveal, real-time dissolve), on a separate
// owner-only dynamic mesh so the combo / uppercut / heavy rifts keep their own state.
//  * Sprint attack: the chop's crescent (KukriSkillRiftRibbons::Dash, baked from the clip like the combo's), frozen at
//    the viewmodel when the blade comes over the top, revealed on the dash clock, carried along with the dash momentum
//    while it unfolds, then dissolved while it drifts forward.
//  * Whirlwind: a short trailing arc follows the held blade around the player. Older sections leave through its soft
//    tail while the head follows the visible blade turn. It never accumulates a complete ring, and fades quickly after braking.

namespace
{
/** Keep only the most recent third-turn, at approximately the previous mesh's angular resolution. */
constexpr float KukriWhirlRingDegrees=120.f;
constexpr int32 KukriWhirlRingStations=32;
constexpr float KukriWhirlRingInner=.40f, KukriWhirlRingOuter=1.35f;     // along the grip->tip vector, as the crescents
/** RiftStrength over the first / second turn, the dissolve (real s) and the radial widening while it dissolves. */
constexpr float KukriWhirlRingStrength=.085f, KukriWhirlRingSecondStrength=.11f, KukriWhirlRingDissolve=.12f, KukriWhirlRingSpread=.14f;

float KukriWhirlTrailU(float Fraction)
{
    // M_RuneRift fades U=0..0.045. Spread that fade over 60% of this arc so old
    // sections progressively vanish, retaining the existing shared material.
    constexpr float Tail=.60f, FadeU=.045f;
    return Fraction<Tail?FadeU*Fraction/Tail:FadeU+(1.f-FadeU)*(Fraction-Tail)/(1.f-Tail);
}

/** One more strip in a ribbon mesh (the pair's second crescent); same UV / normal layout as KukriRibbonMesh. */
void AppendRibbon(UE::Geometry::FDynamicMesh3& Mesh,int32 Stations,TFunctionRef<void(int32,FVector&,FVector&)> Station,bool bSoftTrail=false)
{
    using namespace UE::Geometry;
    FDynamicMeshUVOverlay* UV=Mesh.Attributes()->PrimaryUV();
    FDynamicMeshNormalOverlay* Normals=Mesh.Attributes()->PrimaryNormals();
    const int32 Base=Mesh.MaxVertexID();
    for(int32 S=0;S<Stations;++S)
    {
        FVector Inner,Outer;Station(S,Inner,Outer);
        for(int32 E=0;E<2;++E)
        {
            Mesh.AppendVertex(FVector3d(E?Outer:Inner));
            const float Along=float(S)/(Stations-1);
            UV->AppendElement(FVector2f(bSoftTrail?KukriWhirlTrailU(Along):Along,float(E)));
            Normals->AppendElement(FVector3f(0.f,0.f,1.f));   // unlit two-sided material: the normal is unused
        }
    }
    for(int32 S=0;S<Stations-1;++S)
    {
        const int32 A=Base+S*2;
        for(const FIndex3i T:{FIndex3i(A,A+2,A+1),FIndex3i(A+1,A+2,A+3)})
        {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
    }
}

UE::Geometry::FDynamicMesh3 KukriRibbonMesh(int32 Stations,TFunctionRef<void(int32,FVector&,FVector&)> Station,bool bSoftTrail=false)
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    AppendRibbon(Mesh,Stations,Station,bSoftTrail);
    return Mesh;
}
}

bool UKukriWeaponComponent::PrepareSkillRift()
{
    auto* P=Pawn();
    if(!P||!Viewmodel||!Camera)return false;
    if(!SkillRiftVisual)
    {
        auto* Material=LoadObject<UMaterialInterface>(nullptr,KukriRhythm::RiftMaterial);
        if(!Material)return false;
        SkillRiftVisual=NewObject<UDynamicMeshComponent>(P,TEXT("KukriSkillRift"));
        P->AddInstanceComponent(SkillRiftVisual);
        SkillRiftVisual->SetMobility(EComponentMobility::Movable);
        SkillRiftVisual->SetCollisionEnabled(ECollisionEnabled::NoCollision);SkillRiftVisual->SetGenerateOverlapEvents(false);
        SkillRiftVisual->SetCanEverAffectNavigation(false);SkillRiftVisual->SetCastShadow(false);SkillRiftVisual->SetReceivesDecals(false);
        SkillRiftVisual->SetOnlyOwnerSee(true);SkillRiftVisual->bVisibleInRayTracing=false;SkillRiftVisual->bAffectDistanceFieldLighting=false;
        SkillRiftVisual->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
        SkillRiftVisual->RegisterComponent();
        SkillRiftMID=UMaterialInstanceDynamic::Create(Material,this);
        SkillRiftVisual->SetMaterial(0,SkillRiftMID);
    }
    return SkillRiftMID!=nullptr;
}

void UKukriWeaponComponent::StartDashRift()
{
    auto* P=Pawn();
    if(!PrepareSkillRift())return;
    // The lone off-hand blade chops the mirrored clip: its crescent is the mirror image (mesh X = camera right).  A pair
    // chops with both blades: one crescent per blade (KukriDualDashRhythm, the same reveal window).
    if(SkillRiftMesh!=EKukriSkillRift::Dash||bSkillRiftMirrored!=bLoneOffhand||bSkillRiftDual!=bDualDash)
    {
        const float Side=bLoneOffhand?-1.f:1.f;
        auto Mesh=bDualDash?KukriRibbonMesh(KukriDualDashRhythm::Stations,[](int32 S,FVector& Inner,FVector& Outer)
        {
            const float* A=KukriDualDashRhythm::RibbonRight[S][0];const float* B=KukriDualDashRhythm::RibbonRight[S][1];
            Inner=FVector(A[0],A[1],A[2]);Outer=FVector(B[0],B[1],B[2]);
        }):KukriRibbonMesh(KukriSkillRiftRibbons::Stations,[Side](int32 S,FVector& Inner,FVector& Outer)
        {
            const float* A=KukriSkillRiftRibbons::Dash[S][0];const float* B=KukriSkillRiftRibbons::Dash[S][1];
            Inner=FVector(A[0]*Side,A[1],A[2]);Outer=FVector(B[0]*Side,B[1],B[2]);
        });
        if(bDualDash)AppendRibbon(Mesh,KukriDualDashRhythm::Stations,[](int32 S,FVector& Inner,FVector& Outer)
        {
            const float* A=KukriDualDashRhythm::RibbonLeft[S][0];const float* B=KukriDualDashRhythm::RibbonLeft[S][1];
            Inner=FVector(A[0],A[1],A[2]);Outer=FVector(B[0],B[1],B[2]);
        });
        SkillRiftVisual->SetMesh(MoveTemp(Mesh));
        SkillRiftVisual->SetMaterial(0,SkillRiftMID);SkillRiftMesh=EKukriSkillRift::Dash;
        bSkillRiftMirrored=bLoneOffhand;bSkillRiftDual=bDualDash;
    }
    // Freeze the authored crescent where the viewmodel is now; it rides with the dash momentum while it unfolds.
    SkillRiftOrigin=Viewmodel->GetComponentTransform();SkillRiftDirection=Camera->GetForwardVector();
    SkillRiftPawnLocation=P->GetActorLocation();
    SkillRift=EKukriSkillRift::Dash;SkillRiftAge=0.f;SkillRiftFadeAge=-1.f;
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftStrength"),KukriDashRhythm::RiftStrength);
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f);
    SkillRiftMID->SetScalarParameterValue(TEXT("SweepProgress"),0.f);
    SkillRiftVisual->SetWorldTransform(SkillRiftOrigin);
    SkillRiftVisual->SetVisibility(true);
}

void UKukriWeaponComponent::StartShadowStepRift(bool bStage2,bool bDualCast)
{
    auto* P=Pawn();
    if(!PrepareSkillRift())return;
    const EKukriSkillRift Kind=bStage2?EKukriSkillRift::ShadowStep2:EKukriSkillRift::ShadowStep1;
    if(SkillRiftMesh!=Kind||bSkillRiftMirrored!=bLoneOffhand||bSkillRiftDual!=bDualCast)
    {
        const float Side=bLoneOffhand?-1.f:1.f;
        const auto& RightTbl=bStage2?(bDualCast?ShadowStepRiftRibbons::DualStage2Right:ShadowStepRiftRibbons::Stage2):
            (bDualCast?ShadowStepRiftRibbons::DualStage1Right:ShadowStepRiftRibbons::Stage1);
        auto Mesh=KukriRibbonMesh(ShadowStepRiftRibbons::Stations,[&RightTbl,Side,bDualCast](int32 S,FVector& Inner,FVector& Outer)
        {
            const float* A=RightTbl[S][0];const float* B=RightTbl[S][1];
            const float XScale=bDualCast?1.f:Side;
            Inner=FVector(A[0]*XScale,A[1],A[2]);Outer=FVector(B[0]*XScale,B[1],B[2]);
        });
        if(bDualCast)
        {
            const auto& LeftTbl=bStage2?ShadowStepRiftRibbons::DualStage2Left:ShadowStepRiftRibbons::DualStage1Left;
            AppendRibbon(Mesh,ShadowStepRiftRibbons::Stations,[&LeftTbl](int32 S,FVector& Inner,FVector& Outer)
            {
                const float* A=LeftTbl[S][0];const float* B=LeftTbl[S][1];
                Inner=FVector(A[0],A[1],A[2]);Outer=FVector(B[0],B[1],B[2]);
            });
        }
        SkillRiftVisual->SetMesh(MoveTemp(Mesh));
        SkillRiftVisual->SetMaterial(0,SkillRiftMID);SkillRiftMesh=Kind;
        bSkillRiftMirrored=bLoneOffhand;bSkillRiftDual=bDualCast;
    }
    SkillRiftOrigin=Viewmodel->GetComponentTransform();SkillRiftDirection=Camera->GetForwardVector();
    SkillRiftPawnLocation=P->GetActorLocation();
    SkillRift=Kind;SkillRiftAge=0.f;SkillRiftFadeAge=-1.f;
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftStrength"),(bStage2?ShadowStepRiftRibbons::StrengthStage2:ShadowStepRiftRibbons::StrengthStage1)*1.25f);
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f);
    SkillRiftMID->SetScalarParameterValue(TEXT("SweepProgress"),0.f);
    SkillRiftVisual->SetWorldTransform(SkillRiftOrigin);
    SkillRiftVisual->SetVisibility(true);
}

void UKukriWeaponComponent::StartWhirlwindRift()
{
    if(!PrepareSkillRift())return;
    // Build the fixed topology once. Both views fill it from their actual blade
    // after pose evaluation; never freeze a first-person sample at camera height.
    if(SkillRiftMesh!=EKukriSkillRift::Whirlwind)
    {
        SkillRiftVisual->SetMesh(KukriRibbonMesh(KukriWhirlRingStations,[](int32 S,FVector& In,FVector& Out)
        {In=FVector(S,0,0);Out=FVector(S,1,0);},true));
    }
    SkillRiftVisual->SetMaterial(0,SkillRiftMID);SkillRiftMesh=EKukriSkillRift::Whirlwind;
    SkillRiftOrigin=FTransform::Identity;SkillRiftDirection=FVector::ZeroVector;
    SkillRift=EKukriSkillRift::Whirlwind;SkillRiftAge=0.f;SkillRiftFadeAge=-1.f;
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftStrength"),KukriWhirlRingStrength);
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f);
    SkillRiftMID->SetScalarParameterValue(TEXT("SweepProgress"),0.f);
    SkillRiftVisual->SetWorldTransform(SkillRiftOrigin);
    SkillRiftVisual->SetVisibility(false);
}

void UKukriWeaponComponent::UpdateWhirlwindRiftPose(const FTransform& Knife)
{
    auto* P=Pawn();
    if(!P||!bWhirlwind||SkillRift!=EKukriSkillRift::Whirlwind||!SkillRiftVisual||!SkillRiftMID||SkillRiftFadeAge>=0.f)return;
    const float Turned=FMath::Abs(WhirlwindTuning.TurnDegrees*WhirlwindFeel::Phase(Elapsed,WhirlwindTuning));
    const float Span=FMath::Min(Turned,KukriWhirlRingDegrees);
    if(Span<=UE_KINDA_SMALL_NUMBER)return;
    const FVector Center(P->GetActorLocation().X,P->GetActorLocation().Y,Knife.GetLocation().Z);
    const FVector Inner=Knife.TransformPosition(KukriRhythm::BladeTip*KukriWhirlRingInner)-Center;
    const FVector Outer=Knife.TransformPosition(KukriRhythm::BladeTip*KukriWhirlRingOuter)-Center;
    const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();
    // Single-blade first person presents -theta through the camera/arms yaw
    // correction. Its tail must therefore trail -theta, not the +theta world
    // body/damage sweep. Match GetWhirlwindCameraMotion's view selection.
    const bool ReverseOwnerTurn=!IsDual()&&(!Body||!Body->IsThirdPersonViewEnabled());
    const float ViewTurn=ReverseOwnerTurn?-WhirlwindTuning.TurnDegrees:WhirlwindTuning.TurnDegrees;
    const float Direction=ViewTurn<0.f?-1.f:1.f;
    SkillRiftVisual->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& Mesh)
    {
        for(int32 S=0;S<KukriWhirlRingStations;++S)
        {
            const float U=float(S)/(KukriWhirlRingStations-1);
            const FRotator Back(0.f,-Direction*Span*(1.f-U),0.f);
            Mesh.SetVertex(S*2,FVector3d(Back.RotateVector(Inner)));
            Mesh.SetVertex(S*2+1,FVector3d(Back.RotateVector(Outer)));
        }
    },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions);
    SkillRiftOrigin=FTransform(Center);
    SkillRiftVisual->SetWorldTransform(SkillRiftOrigin);
    SkillRiftVisual->SetVisibility(true);
    // The head is always the current blade. Initial growth is in the geometry,
    // so reveal must not hide that head while the shortened arc is growing.
    SkillRiftMID->SetScalarParameterValue(TEXT("SweepProgress"),1.06f);
}

void UKukriWeaponComponent::TickSkillRift(float Delta)
{
    if(SkillRift==EKukriSkillRift::None||!SkillRiftVisual||!SkillRiftMID)return;
    SkillRiftAge+=Delta;
    float Reveal=1.f,Dissolve=KukriDashRhythm::RiftDissolve;
    if(SkillRift==EKukriSkillRift::Dash)
    {
        // Reveal on the dash clock (it stops with the hit-stop); ride along with the dash momentum until it has unfolded.
        if(bDashAttack)
        {
            Reveal=FMath::Clamp((Elapsed-KukriDashRhythm::RiftStart)/(KukriDashRhythm::RiftEnd-KukriDashRhythm::RiftStart),0.f,1.f);
            if(const auto* P=Pawn();P&&Reveal<1.f)
            {
                const FVector Location=P->GetActorLocation();
                SkillRiftOrigin.AddToTranslation(Location-SkillRiftPawnLocation);SkillRiftPawnLocation=Location;
            }
        }
    }
    else if(SkillRift==EKukriSkillRift::ShadowStep1||SkillRift==EKukriSkillRift::ShadowStep2)
    {
        const bool bS2=SkillRift==EKukriSkillRift::ShadowStep2;
        Dissolve=bS2?ShadowStepRiftRibbons::DissolveStage2:ShadowStepRiftRibbons::DissolveStage1;
        if(bShadowStep&&bShadowStepStage2==bS2)
        {
            const float Start=bS2?ShadowStepRiftRibbons::Stage2Start:ShadowStepRiftRibbons::Stage1Start;
            const float End=bS2?(bSkillRiftDual?ShadowStepRiftRibbons::Dual2LeftEnd:ShadowStepRiftRibbons::Stage2End):
                (bSkillRiftDual?ShadowStepRiftRibbons::Dual1LeftEnd:ShadowStepRiftRibbons::Stage1End);
            Reveal=FMath::Clamp((Elapsed-Start)/FMath::Max(.01f,End-Start),0.f,1.f);
            // Hold crescent frozen in place while 卡肉 (hit-stop) is active at the final slash pose!
            if(HitStop>0.f)Reveal=FMath::Min(Reveal,.999f);
            if(const auto* P=Pawn();P&&!bS2&&Reveal<1.f)
            {
                const FVector Location=P->GetActorLocation();
                SkillRiftOrigin.AddToTranslation(Location-SkillRiftPawnLocation);SkillRiftPawnLocation=Location;
            }
        }
    }
    else
    {
        // Grow the first short arc, then move its head with the turned angle.
        // The tail continuously fades old sections instead of keeping a ring.
        Dissolve=KukriWhirlRingDissolve;
        if(bWhirlwind)
        {
            const float Turned=FMath::Abs(WhirlwindTuning.TurnDegrees*WhirlwindFeel::Phase(Elapsed,WhirlwindTuning));
            Reveal=FMath::Clamp(Turned/KukriWhirlRingDegrees,0.f,1.f);
            const float Second=FMath::Clamp((Turned-360.f)/360.f,0.f,1.f);
            SkillRiftMID->SetScalarParameterValue(TEXT("RiftStrength"),FMath::Lerp(KukriWhirlRingStrength,KukriWhirlRingSecondStrength,Second));
            // Keep emitting the moving arc while spinning; stop emission and
            // finish the short real-time fade once the spin ends or cancels.
            if(Elapsed<WhirlwindTuning.ReadySeconds+WhirlwindTuning.SpinSeconds)Reveal=FMath::Min(Reveal,.999f);
        }
    }
    if(Reveal>=1.f&&SkillRiftFadeAge<0.f)SkillRiftFadeAge=0.f;
    else if(SkillRiftFadeAge>=0.f)SkillRiftFadeAge+=Delta;
    const float Recovery=SkillRiftFadeAge<0.f?0.f:FMath::Clamp(SkillRiftFadeAge/Dissolve,0.f,1.f);
    if(Recovery>=1.f){StopSkillRift();return;}
    const float Progress=SkillRift==EKukriSkillRift::Whirlwind?1.f:Reveal;
    SkillRiftMID->SetScalarParameterValue(TEXT("SweepProgress"),Progress*1.06f);
    SkillRiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f-Recovery*Recovery*(3.f-2.f*Recovery));
    FTransform Pose=SkillRiftOrigin;
    if(SkillRift==EKukriSkillRift::Dash)
        Pose.AddToTranslation(SkillRiftDirection*(FMath::Max(0.f,SkillRiftFadeAge)*KukriDashRhythm::RiftDriftCM));
    else if(SkillRift==EKukriSkillRift::ShadowStep1||SkillRift==EKukriSkillRift::ShadowStep2)
        Pose.AddToTranslation(SkillRiftDirection*(FMath::Max(0.f,SkillRiftFadeAge)*ShadowStepRiftRibbons::DriftCM));
    else
    {
        const float Spread=1.f+KukriWhirlRingSpread*FMath::SmoothStep(0.f,1.f,Recovery);
        Pose.SetScale3D(FVector(Spread,Spread,1.f));
    }
    SkillRiftVisual->SetWorldTransform(Pose);
}

void UKukriWeaponComponent::StopSkillRift()
{
    SkillRift=EKukriSkillRift::None;SkillRiftAge=0.f;SkillRiftFadeAge=-1.f;
    if(SkillRiftVisual)SkillRiftVisual->SetVisibility(false);
}
