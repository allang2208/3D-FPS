#include "KukriWeaponComponent.h"
#include "KukriArmsMeshComponent.h"
#include "KukriRhythm.h"
#include "KukriRiftRibbons.h"
#include "KukriDualRiftRibbons.h"
#include "HatchetChopRhythm.h"
#include "HatchetDualChopRhythm.h"
#include "SwiftFalconHeavy.h"
#include "SwiftFalconRibbons.h"
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMECharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

// Swing rift (2026-10-23, user: "a space distortion like the two-handed sword, like sword qi").  The rune sword's normal
// slash rift (URuneSwordComponent::StartRift/TickRift): a crescent baked from the blade's authored contact path, frozen
// in world space at the viewmodel's transform, revealed along U (SweepProgress) and dissolved while it drifts forward.
// Here the reveal follows the swing's author clock (it stops with the hit-stop) and the dissolve runs in real time.

namespace
{
    using FRibbon=const float (*)[2][3];
    static_assert(SwiftFalconRibbons::Stations==KukriRiftRibbons::Stations);
    constexpr KukriRhythm::FRift FalconTrails[2]={
        {SwiftFalconHeavy::ChopTrail,SwiftFalconHeavy::ChopOut,.11f,.13f,22.f},
        {SwiftFalconHeavy::PullTrail,SwiftFalconHeavy::PullOut,.09f,.14f,-8.f}};

    static_assert(KukriDualRiftRibbons::Stations==KukriRiftRibbons::Stations,"one station count for all rift ribbons");
    static_assert(HatchetChopRhythm::Stations==KukriRiftRibbons::Stations,"one station count for all rift ribbons");
    static_assert(HatchetDualChopRhythm::Stations==KukriRiftRibbons::Stations,"one station count for all rift ribbons");

    /** Ribbons of one stage: the slashes have one crescent, the stab two crossed narrow ribbons, the dual heavy's X one
     *  crescent per blade (bDual). */
    int32 StageRibbons(int32 Stage,bool bDual,bool bChop,FRibbon Out[2],uint8 ChopSides,int8 FalconPhase)
    {
        if(FalconPhase>=0)
        {
            if(!bDual){Out[0]=FalconPhase?SwiftFalconRibbons::Pull:SwiftFalconRibbons::Chop;return 1;}
            Out[0]=FalconPhase?SwiftFalconRibbons::DualPullRight:SwiftFalconRibbons::DualChopRight;
            Out[1]=FalconPhase?SwiftFalconRibbons::DualPullLeft:SwiftFalconRibbons::DualChopLeft;
            return 2;
        }
        if(bDual&&bChop)   // hatchets on the double thrust: one crescent per chopping head (ChopSides 1 right, 2 left)
        {
            int32 N=0;
            if(ChopSides&1)Out[N++]=HatchetDualChopRhythm::RibbonRight;
            if(ChopSides&2)Out[N++]=HatchetDualChopRhythm::RibbonLeft;
            return N;
        }
        if(bDual){Out[0]=KukriDualRiftRibbons::HeavyRight;Out[1]=KukriDualRiftRibbons::HeavyLeft;return 2;}
        if(bChop){Out[0]=HatchetChopRhythm::Ribbon;return 1;}         // the hatchet chop: one crescent swept by its head
        if(Stage==0){Out[0]=KukriRiftRibbons::Sweep;return 1;}
        if(Stage==1){Out[0]=KukriRiftRibbons::Diag;return 1;}
        if(Stage==KukriRhythm::UppercutStage){Out[0]=KukriRiftRibbons::Upper;return 1;}
        if(Stage==KukriRhythm::HeavyStage){Out[0]=KukriRiftRibbons::Heavy;return 1;}
        Out[0]=KukriRiftRibbons::StabEdge;Out[1]=KukriRiftRibbons::StabFlat;return 2;
    }

    /** bMirror: the ribbon mirrored left-right about the view (mesh X = camera right) -- the dual sweep's left blade cuts
     *  the mirror image of the first stage (SourceAssets/DualKukriIdle20261025/author_dual_attack.py). */
    UE::Geometry::FDynamicMesh3 BuildRibbons(int32 Stage,bool bMirror,bool bDual,bool bChop,uint8 ChopSides,int8 FalconPhase)
    {
        using namespace UE::Geometry;
        FDynamicMesh3 Mesh;Mesh.EnableAttributes();
        FDynamicMeshUVOverlay* UV=Mesh.Attributes()->PrimaryUV();
        FDynamicMeshNormalOverlay* Normals=Mesh.Attributes()->PrimaryNormals();
        FRibbon Ribbons[2]={};
        const int32 Count=StageRibbons(Stage,bDual,bChop,Ribbons,ChopSides,FalconPhase);
        constexpr int32 N=KukriRiftRibbons::Stations;
        for(int32 R=0;R<Count;++R)
        {
            const int32 Base=Mesh.MaxVertexID();
            for(int32 S=0;S<N;++S)
                for(int32 E=0;E<2;++E)
                {
                    const float* P=Ribbons[R][S][E];
                    Mesh.AppendVertex(FVector3d(bMirror?-P[0]:P[0],P[1],P[2]));
                    UV->AppendElement(FVector2f(float(S)/(N-1),float(E)));
                    Normals->AppendElement(FVector3f(0.f,0.f,1.f));   // unlit two-sided material: the normal is unused
                }
            for(int32 S=0;S<N-1;++S)
            {
                const int32 A=Base+S*2;
                for(const FIndex3i T:{FIndex3i(A,A+2,A+1),FIndex3i(A+1,A+2,A+3)})
                {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
            }
        }
        return Mesh;
    }
}

void UKukriWeaponComponent::StartRift()
{
    auto* P=Pawn();
    if(!P||!Viewmodel||!Camera)return;
    if(!RiftVisual)
    {
        auto* Material=LoadObject<UMaterialInterface>(nullptr,KukriRhythm::RiftMaterial);
        if(!Material)return;
        RiftVisual=NewObject<UDynamicMeshComponent>(P,TEXT("KukriRift"));
        P->AddInstanceComponent(RiftVisual);
        RiftVisual->SetMobility(EComponentMobility::Movable);
        RiftVisual->SetCollisionEnabled(ECollisionEnabled::NoCollision);RiftVisual->SetGenerateOverlapEvents(false);
        RiftVisual->SetCanEverAffectNavigation(false);RiftVisual->SetCastShadow(false);RiftVisual->SetReceivesDecals(false);
        RiftVisual->SetOnlyOwnerSee(true);RiftVisual->bVisibleInRayTracing=false;RiftVisual->bAffectDistanceFieldLighting=false;
        RiftVisual->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
        RiftVisual->RegisterComponent();
        RiftMID=UMaterialInstanceDynamic::Create(Material,this);
        RiftVisual->SetMaterial(0,RiftMID);
        RiftStage=INDEX_NONE;
    }
    // Two hatchets' chop: one crescent per head (bDual and bChop together); a hatchet + kukri pair only the hatchet's.
    const bool bDualChopRift=bAttacking&&IsHatchetDualChop();
    const bool bDualRift=(bDualHeavy&&bHeavyAttack)||bDualChopRift, bChopRift=IsHatchetChop()||bDualChopRift;
    const uint8 ChopSides=bDualChopRift?uint8((bChopRight?1:0)|(bChopLeft?2:0)):3;
    // Mirrored for the dual sweep's left blade and for the lone off-hand blade's mirrored moveset.
    const bool bMirror=bOffhandSwing!=bLoneOffhand;
    const int8 FalconPhase=bHeavyAttack&&bFalconHeavy?int8(Shot.MeleeDamagePhase):-1;
    if(RiftStage!=Stage||bRiftMirrored!=bMirror||bRiftDual!=bDualRift||bRiftChop!=bChopRift||RiftChopSides!=ChopSides||RiftFalconPhase!=FalconPhase)
    {
        RiftVisual->SetMesh(BuildRibbons(Stage,bMirror,bDualRift,bChopRift,ChopSides,FalconPhase));RiftVisual->SetMaterial(0,RiftMID);
        RiftFalconPhase=FalconPhase;
        RiftStage=Stage;bRiftMirrored=bMirror;bRiftDual=bDualRift;bRiftChop=bChopRift;RiftChopSides=ChopSides;
    }
    // The dual sweep's left blade reveals its ribbon on the same window, its stage's DualSweepOffset later.
    RiftTimeOffset=bOffhandSwing?KukriRhythm::DualSweepOffset(Stage):0.f;
    // Freeze the authored crescent where the viewmodel is now, so it stays in the world while the view moves on.
    RiftOrigin=Viewmodel->GetComponentTransform();RiftDirection=Camera->GetForwardVector();
    RiftAge=0.f;RiftFadeAge=-1.f;bRiftActive=true;
    const auto& R=RiftFalconPhase>=0?FalconTrails[RiftFalconPhase]:bRiftDual&&bRiftChop?HatchetDualChopRhythm::Rift:bRiftDual?KukriRhythm::DualHeavyRift:
        bRiftChop?HatchetChopRhythm::Rift:KukriRhythm::Rifts[Stage];
    RiftMID->SetScalarParameterValue(TEXT("RiftStrength"),R.Strength);
    RiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f);
    RiftMID->SetScalarParameterValue(TEXT("SweepProgress"),0.f);
    RiftVisual->SetWorldTransform(RiftOrigin);
    RiftVisual->SetVisibility(true);
}

void UKukriWeaponComponent::TickRift(float Delta)
{
    if(!bRiftActive||!RiftVisual||!RiftMID)return;
    const auto& R=RiftFalconPhase>=0?FalconTrails[RiftFalconPhase]:bRiftDual&&bRiftChop?HatchetDualChopRhythm::Rift:bRiftDual?KukriRhythm::DualHeavyRift:
        bRiftChop?HatchetChopRhythm::Rift:KukriRhythm::Rifts[RiftStage==INDEX_NONE?Stage:RiftStage];
    RiftAge+=Delta;
    // Reveal on the swing's author clock while it plays (frozen through a hit-stop); the fade is real time.
    const float Reveal=(bAttacking||bUppercut||bHeavyAttack)&&Stage==RiftStage?
        FMath::Clamp((Elapsed-RiftTimeOffset-R.Start)/FMath::Max(.01f,R.End-R.Start),0.f,1.f):1.f;
    if(Reveal>=1.f&&RiftFadeAge<0.f)RiftFadeAge=0.f;
    else if(RiftFadeAge>=0.f)RiftFadeAge+=Delta;
    const float Recovery=RiftFadeAge<0.f?0.f:FMath::Clamp(RiftFadeAge/R.Dissolve,0.f,1.f);
    if(Recovery>=1.f){StopRift();return;}
    RiftMID->SetScalarParameterValue(TEXT("SweepProgress"),Reveal*1.06f);
    RiftMID->SetScalarParameterValue(TEXT("RiftFade"),1.f-Recovery*Recovery*(3.f-2.f*Recovery));
    const float DriftAge=RiftStage==KukriRhythm::UppercutStage?FMath::Max(0.f,RiftFadeAge):RiftAge;
    FTransform Pose=RiftOrigin;Pose.AddToTranslation(RiftDirection*(DriftAge*R.DriftCM));
    RiftVisual->SetWorldTransform(Pose);
}

void UKukriWeaponComponent::StopRift()
{
    bRiftActive=false;RiftAge=0.f;RiftFadeAge=-1.f;
    if(RiftVisual)RiftVisual->SetVisibility(false);
}
