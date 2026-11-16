#include "FPSBodyGunAim.h"
#include "../Weapons/AKMSovietCalibration.h"
#include "../Weapons/Saiga12KWeaponAssets.h"
#include "../Weapons/SVCHWeaponAssets.h"
#include "../Weapons/M24WeaponAssets.h"
#include "../Weapons/M870WeaponAssets.h"
#include "Components/SkinnedMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Math/RotationMatrix.h"
#include "TwoBoneIK.h"

FFPSBodyGunAimFrame FPSBodyGunAim::FromMuzzle(const FTransform& MuzzleInMesh,const FTransform& Mount)
{
    FFPSBodyGunAimFrame Result;
    Result.Muzzle=Mount.TransformPosition(MuzzleInMesh.GetLocation());
    Result.Forward=Mount.TransformVectorNoScale(MuzzleInMesh.GetRotation().GetForwardVector()).GetSafeNormal();
    Result.bValid=!Result.Forward.IsNearlyZero();
    return Result;
}

bool FPSBodyGunAim::SightFrame(const USkinnedMeshComponent& Weapon,FTransform& Frame)
{
    const auto* Asset=Weapon.GetSkinnedAsset();
    if(!Asset||!Weapon.DoesSocketExist(TEXT("WPN_root"))||
        !Weapon.DoesSocketExist(TEXT("WPN_FrontSight"))||!Weapon.DoesSocketExist(TEXT("WPN_RearSight")))return false;
    const FString Path=Asset->GetPathName();
    const bool SVCH=Path.StartsWith(TEXT("/Game/Weapons/SVCH/"));
    const bool Saiga=Path.StartsWith(TEXT("/Game/Weapons/Saiga12K/"));
    const bool AKM=Path.Contains(TEXT("/AKMIntegration/SovietFab/"));
    const FTransform Root=Weapon.GetSocketTransform(TEXT("WPN_root"),RTS_Component);
    const FVector Front=SVCH?Root.TransformPosition(SVCHWeaponAssets::FrontSight):Saiga?Root.TransformPosition(Saiga12KWeaponAssets::Front):
        AKM?Root.TransformPosition(AKMSoviet::Front):Weapon.GetSocketTransform(TEXT("WPN_FrontSight"),RTS_Component).GetLocation();
    const FVector Rear=SVCH?Root.TransformPosition(SVCHWeaponAssets::RearSight):Saiga?Root.TransformPosition(Saiga12KWeaponAssets::Rear):
        AKM?Root.TransformPosition(AKMSoviet::Rear):Weapon.GetSocketTransform(TEXT("WPN_RearSight"),RTS_Component).GetLocation();
    const FVector Forward=(Front-Rear).GetSafeNormal();
    if(Forward.IsNearlyZero())return false;
    const FVector Up=Path==M24WeaponAssets::MeshPath?Root.TransformVectorNoScale(M24WeaponAssets::SightUp):
        SVCH?Root.TransformVectorNoScale(SVCHWeaponAssets::SightUp):
        Path==M870WeaponAssets::MeshPath?Root.TransformVectorNoScale(FVector(0,-.9999901840,-.0044230472)):
        Root.GetRotation().GetUpVector();
    // Preserve the measured sight-line slope. Projecting it onto a guessed
    // donor "up" plane changes the very barrel direction we are trying to fit.
    Frame=FTransform(FRotationMatrix::MakeFromXZ(Forward,Up).ToQuat(),Rear);
    return true;
}

FFPSBodyGunAimFrame FPSBodyGunAim::FromWeapon(const USkinnedMeshComponent& Weapon)
{
    FFPSBodyGunAimFrame Result; FTransform Sight;
    if(!SightFrame(Weapon,Sight))return Result;
    const FTransform Mount=Weapon.GetRelativeTransform();
    Result.Forward=Mount.TransformVectorNoScale(Sight.GetRotation().GetForwardVector()).GetSafeNormal();
    Result.Muzzle=Mount.TransformPosition(Weapon.DoesSocketExist(TEXT("WPN_SOCKET_Muzzle"))?
        Weapon.GetSocketTransform(TEXT("WPN_SOCKET_Muzzle"),RTS_Component).GetLocation():Sight.GetLocation());
    Result.bValid=true;
    return Result;
}

void FFPSBodyGunAimNode::Reset()
{
    SupportWeight=0.f;
    for(int32 Side=0;Side<2;++Side){Weight[Side]=0.f;LastCorrection[Side]=FQuat::Identity;}
}
void FFPSBodyGunAimNode::Initialize_AnyThread(const FAnimationInitializeContext& Context)
{ Reset(); Source.Initialize(Context); }
void FFPSBodyGunAimNode::CacheBones_AnyThread(const FAnimationCacheBonesContext& Context)
{
    Reset(); Source.CacheBones(Context);
    const auto& Bones=Context.AnimInstanceProxy->GetRequiredBones();
    for(auto& Hand:Hands)Hand.Initialize(Bones);
    Spine.Initialize(Bones);
}
void FFPSBodyGunAimNode::Update_AnyThread(const FAnimationUpdateContext& Context)
{
    Delta=Context.GetDeltaTime();
    SupportWeight=FMath::FInterpConstantTo(SupportWeight,bFitSupport?1.f:0.f,Delta,10.f);
    for(int32 Side=0;Side<2;++Side)
        Weight[Side]=Guns[Side].bValid?FMath::FInterpConstantTo(Weight[Side],Enabled[Side]?1.f:0.f,Delta,10.f):0.f;
    Source.Update(Context);
}
void FFPSBodyGunAimNode::Evaluate_AnyThread(FPoseContext& Output)
{
    Source.Evaluate(Output);
    if(Weight[0]<=ZERO_ANIMWEIGHT_THRESH&&Weight[1]<=ZERO_ANIMWEIGHT_THRESH&&SupportWeight<=ZERO_ANIMWEIGHT_THRESH)return;
    FCSPose<FCompactPose> Pose; Pose.InitPose(Output.Pose);
    const auto& Bones=Output.Pose.GetBoneContainer();
    bool Changed=false;
    if(SupportWeight>ZERO_ANIMWEIGHT_THRESH&&Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones))
    {
        FTransform Goals[2]={Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones)),FTransform::Identity};
        Goals[1]=SupportFromRight*Goals[0];
        FVector Centers[2];double Radii[2];
        for(int32 Side=0;Side<2;++Side)
        {
            const auto W=Hands[Side].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
            const FVector H=Pose.GetComponentSpaceTransform(S).GetLocation(),J=Pose.GetComponentSpaceTransform(E).GetLocation();
            Radii[Side]=(FVector::Distance(H,J)+FVector::Distance(J,Pose.GetComponentSpaceTransform(W).GetLocation()))*.98;
            Centers[Side]=H-Goals[Side].GetLocation();
        }
        const auto Inside=[&](FVector P,int32 Side){return FVector::DistSquared(P,Centers[Side])<=FMath::Square(Radii[Side])+.0001;};
        FVector Shift=FVector::ZeroVector;
        if(!Inside(Shift,0)||!Inside(Shift,1))
        {
            const FVector A=Centers[0]+(-Centers[0]).GetClampedToMaxSize(Radii[0]);
            const FVector B=Centers[1]+(-Centers[1]).GetClampedToMaxSize(Radii[1]);
            if(Inside(A,1)||Inside(B,0))Shift=Inside(A,1)&&(!Inside(B,0)||A.SizeSquared()<B.SizeSquared())?A:B;
            else
            {
                const FVector Between=Centers[1]-Centers[0];const double Distance=Between.Size();
                if(Distance>UE_SMALL_NUMBER&&Distance<=Radii[0]+Radii[1])
                {
                    const FVector Axis=Between/Distance;
                    const double Along=(FMath::Square(Radii[0])-FMath::Square(Radii[1])+Distance*Distance)/(2.*Distance);
                    const FVector Center=Centers[0]+Axis*Along;
                    FVector Toward=FVector::VectorPlaneProject(-Center,Axis).GetSafeNormal();
                    if(Toward.IsNearlyZero()){FVector Other;Axis.FindBestAxisVectors(Toward,Other);}
                    Shift=Center+Toward*FMath::Sqrt(FMath::Max(0.,Radii[0]*Radii[0]-Along*Along));
                }
            }
        }
        // Translate the pair together into both arms' reachable space. Do not
        // clamp only the support wrist and leave it short of the foregrip.
        for(int32 Side=0;Side<2;++Side)
        {
            const auto W=Hands[Side].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
            FTransform Root=Pose.GetComponentSpaceTransform(S),Joint=Pose.GetComponentSpaceTransform(E),Tip=Pose.GetComponentSpaceTransform(W);
            Goals[Side].AddToTranslation(Shift);
            const FVector H=Root.GetLocation(),J=Joint.GetLocation(),P=Tip.GetLocation();
            const FVector Old=(P-H).GetSafeNormal(),Next=(Goals[Side].GetLocation()-H).GetSafeNormal();
            FVector Bend=J-H-Old*FVector::DotProduct(J-H,Old);
            Bend=FQuat::FindBetweenNormals(Old,Next).RotateVector(Bend).GetSafeNormal();
            AnimationCore::SolveTwoBoneIK(Root,Joint,Tip,H+Bend*80.f,Goals[Side].GetLocation(),
                FVector::Distance(H,J),FVector::Distance(J,P),false,1.,1.);
            Tip.SetRotation(Goals[Side].GetRotation());
            TArray<FBoneTransform,TInlineAllocator<3>> Changes;
            Changes.Emplace(S,Root);Changes.Emplace(E,Joint);Changes.Emplace(W,Tip);
            Pose.LocalBlendCSBoneTransforms(Changes,SupportWeight);
        }
        Changed=true;
    }
    for(int32 Side=0;Side<2;++Side)
    {
        if(Weight[Side]<=ZERO_ANIMWEIGHT_THRESH||!Hands[Side].IsValidToEvaluate(Bones))continue;
        const auto Wrist=Hands[Side].GetCompactPoseIndex(Bones);
        const auto Elbow=Bones.GetParentBoneIndex(Wrist);
        const auto Shoulder=Elbow!=INDEX_NONE?Bones.GetParentBoneIndex(Elbow):FCompactPoseBoneIndex(INDEX_NONE);
        if(Shoulder==INDEX_NONE||(bPaired&&Spine.Chain.IsEmpty()))continue;
        const auto Apply=[&](const FQuat& Correction)
        {
            // Divide the angular change over the native spine, not one waist
            // joint. Independent pistols move only their complete owning arm.
            const int32 Count=bPaired?Spine.Chain.Num():1;
            const FQuat Step=FQuat::Slerp(FQuat::Identity,Correction,1.f/Count).GetNormalized();
            for(int32 I=0;I<Count;++I)
            {
                const auto Bone=bPaired?Spine.Chain[I]:Shoulder;
                auto Transform=Pose.GetComponentSpaceTransform(Bone);
                Transform.SetRotation((Step*Transform.GetRotation()).GetNormalized());
                TArray<FBoneTransform,TInlineAllocator<1>> Change; Change.Emplace(Bone,Transform);
                Pose.LocalBlendCSBoneTransforms(Change,1.f);
            }
        };
        if(Enabled[Side])
        {
            FQuat Total=FQuat::Identity;
            // Recompute convergence after the upper chain moves the muzzle.
            // Direction-only player aim needs one pass; a nearby AI target two.
            for(int32 Pass=0;Pass<(bUseTarget?2:1);++Pass)
            {
                const auto Palm=Pose.GetComponentSpaceTransform(Wrist);
                const FVector Forward=Palm.TransformVectorNoScale(Guns[Side].Forward).GetSafeNormal();
                const FVector ToTarget=Target-Palm.TransformPosition(Guns[Side].Muzzle);
                // A sight ray can hit a wall behind an extended muzzle. Keep
                // facing forward while the existing shot obstruction test blocks
                // the shot, rather than twisting the arms back into the chest.
                FVector Aim=bUseTarget&&FVector::DotProduct(ToTarget,Direction)>10.f?ToTarget.GetSafeNormal():Direction.GetSafeNormal();
                if(Aim.IsNearlyZero())break;
                const FVector PitchAxis=FVector::CrossProduct(Aim,FVector::UpVector).GetSafeNormal();
                Aim=FQuat(PitchAxis,FMath::DegreesToRadians(Recoil[Side])).RotateVector(Aim);
                const FQuat Correction=FQuat::FindBetweenNormals(Forward,Aim);
                const FQuat Weighted=FQuat::Slerp(FQuat::Identity,Correction,Weight[Side]).GetNormalized();
                Apply(Weighted); Total=(Weighted*Total).GetNormalized();
            }
            LastCorrection[Side]=Total;
        }
        else
        {
            // Releasing aim must fade the last alignment, not chase the gun
            // through the new reload/equip animation back toward the target.
            const float Previous=FMath::Min(1.f,Weight[Side]+Delta*10.f);
            LastCorrection[Side]=FQuat::Slerp(FQuat::Identity,LastCorrection[Side],Weight[Side]/Previous).GetNormalized();
            Apply(LastCorrection[Side]);
        }
        Changed=true;
    }
    if(Changed)FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Output.Pose);
}
