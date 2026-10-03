#include "M10FootPlantNode.h"
#include "TwoBoneIK.h"

FM10FootPlantNode::FM10FootPlantNode()
{
    // Run with alpha one so a disabled frame can clear worker-owned locks.
    Alpha=1.f;
    const float Offsets[]={0.f,.5f,.25f,.75f};
    const TCHAR* Parents[]={TEXT("body_front"),TEXT("body_center"),TEXT("body_rear"),TEXT("rump")};
    for(int32 I=0;I<8;++I)
    {
        auto& L=Legs[I];const FString Stem=FString::Printf(TEXT("leg_%02d_%s"),I%4+1,I<4?TEXT("L"):TEXT("R"));
        L.Upper.BoneName=FName(Stem+TEXT("_upper"));L.Lower.BoneName=FName(Stem+TEXT("_lower"));L.Foot.BoneName=FName(Stem+TEXT("_foot"));
        L.Body.BoneName=Parents[I%4];
        L.Offset=Offsets[I%4]+(I<4?0.f:.5f);
    }
}
void FM10FootPlantNode::InitializeBoneReferences(const FBoneContainer& Bones)
{
    auto RefCS=[&Bones](FCompactPoseBoneIndex Index)
    {
        FTransform T=Bones.GetRefPoseTransform(Index);
        for(auto Parent=Bones.GetParentBoneIndex(Index);Parent!=INDEX_NONE;Parent=Bones.GetParentBoneIndex(Parent))T*=Bones.GetRefPoseTransform(Parent);
        return T;
    };
    for(auto& L:Legs)
    {
        L.Upper.Initialize(Bones);L.Lower.Initialize(Bones);L.Foot.Initialize(Bones);L.Body.Initialize(Bones);L.Locked=L.Emergency=L.UsedEarlyStep=false;
        if(!L.Upper.IsValidToEvaluate(Bones)||!L.Lower.IsValidToEvaluate(Bones)||!L.Foot.IsValidToEvaluate(Bones)||!L.Body.IsValidToEvaluate(Bones))continue;
        const FVector Root=RefCS(L.Upper.GetCompactPoseIndex(Bones)).GetLocation(),Knee=RefCS(L.Lower.GetCompactPoseIndex(Bones)).GetLocation();
        const FVector Direction=(RefCS(L.Foot.GetCompactPoseIndex(Bones)).GetLocation()-Root).GetSafeNormal();
        const FVector Bend=(Knee-Root)-Direction*FVector::DotProduct(Knee-Root,Direction);
        const FTransform Body=RefCS(L.Body.GetCompactPoseIndex(Bones));
        L.PoleInBody=Body.InverseTransformVectorNoScale(Bend.GetSafeNormal());
        L.NeutralInBody=Body.InverseTransformPosition(RefCS(L.Foot.GetCompactPoseIndex(Bones)).GetLocation());
        L.OutwardInBody=Body.InverseTransformVectorNoScale((Root-Body.GetLocation()).GetSafeNormal2D());
        const FMeshPoseBoneIndex FrontMesh(Bones.GetReferenceSkeleton().FindBoneIndex(TEXT("body_front")));
        const FMeshPoseBoneIndex RearMesh(Bones.GetReferenceSkeleton().FindBoneIndex(TEXT("body_rear")));
        const auto Front=Bones.MakeCompactPoseIndex(FrontMesh),Rear=Bones.MakeCompactPoseIndex(RearMesh);
        if(Front!=INDEX_NONE&&Rear!=INDEX_NONE)
            L.ForwardInBody=Body.InverseTransformVectorNoScale((RefCS(Front).GetLocation()-RefCS(Rear).GetLocation()).GetSafeNormal2D());
    }
    WasEnabled=false;
}
bool FM10FootPlantNode::IsValidToEvaluate(const USkeleton*,const FBoneContainer& Bones)
{
    for(const auto& L:Legs)if(!L.Upper.IsValidToEvaluate(Bones)||!L.Lower.IsValidToEvaluate(Bones)||!L.Foot.IsValidToEvaluate(Bones)||!L.Body.IsValidToEvaluate(Bones))return false;
    return true;
}
void FM10FootPlantNode::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out)
{
    const bool NewFrame=Serial!=LastEvaluated;LastEvaluated=Serial;
    const bool Discontinuous=!WasEnabled||FVector::DistSquared(Frame.GetLocation(),PreviousFrame.GetLocation())>FMath::Square(80.)||
        Frame.GetRotation().AngularDistance(PreviousFrame.GetRotation())>FMath::DegreesToRadians(45.);
    PreviousFrame=Frame;WasEnabled=Enabled;
    if(!Enabled||Discontinuous)for(auto& L:Legs){L.Locked=L.Emergency=L.UsedEarlyStep=false;L.LastPhase=1.f;}
    if(GroundEnabled)Out.Emplace(FCompactPoseBoneIndex(0),Grounded(Output.Pose.GetComponentSpaceTransform(FCompactPoseBoneIndex(0))));
    if(!Enabled)return;
    const auto& Bones=Output.Pose.GetPose().GetBoneContainer();
    int32 Airborne=0;
    for(const auto& L:Legs)if((Walking&&FMath::Frac(CyclePhase+L.Offset)>=StanceFraction)||L.Emergency)++Airborne;
    for(int32 I=0;I<8;++I)
    {
        auto& L=Legs[I];const auto& Support=Supports[I];
        const auto U=L.Upper.GetCompactPoseIndex(Bones),K=L.Lower.GetCompactPoseIndex(Bones),F=L.Foot.GetCompactPoseIndex(Bones);
        const FTransform OriginalFoot=Output.Pose.GetComponentSpaceTransform(F);
        FTransform Upper=Grounded(Output.Pose.GetComponentSpaceTransform(U)),Lower=Grounded(Output.Pose.GetComponentSpaceTransform(K)),Foot=Grounded(OriginalFoot);
        const FTransform Body=Grounded(Output.Pose.GetComponentSpaceTransform(L.Body.GetCompactPoseIndex(Bones)));
        const float Phase=FMath::Frac(CyclePhase+L.Offset);
        const bool Stance=!Walking||Phase<StanceFraction;
        const FVector Animated=Frame.TransformPosition(Foot.GetLocation());
        const FQuat AnimatedRotation=Frame.GetRotation()*Foot.GetRotation();
        if(!Support.Valid){L.Locked=L.Emergency=false;L.LastPhase=Phase;continue;}
        // Correct the real foot contact hull, not just the ankle joint height.
        const FQuat SurfaceRotation=(FQuat::FindBetweenNormals(GroundRotation.RotateVector(FVector::UpVector),Support.Normal)*AnimatedRotation).GetNormalized();
        auto Land=[&](FVector Position,const FQuat& Rotation,float Lift)
        {
            const FTransform WorldFoot(Rotation,Position,Foot.GetScale3D()*Frame.GetScale3D());
            double Gap=TNumericLimits<double>::Max();
            for(const FVector& Sample:Support.Sole)Gap=FMath::Min(Gap,FVector::DotProduct(WorldFoot.TransformPosition(Sample)-Support.Point,Support.Normal));
            if(Gap!=TNumericLimits<double>::Max())Position.Z+=(.7-Gap)/FMath::Max(.5,Support.Normal.Z)+Lift;
            return Position;
        };
        float Lift=0.f;
        if(!Stance||PoseLiftAllowed)
        {
            double Bottom=TNumericLimits<double>::Max();
            for(const FVector& Sample:Support.Sole)Bottom=FMath::Min(Bottom,Frame.TransformPosition(OriginalFoot.TransformPosition(Sample)).Z);
            Lift=FMath::Max(0.f,float(Bottom-Frame.TransformPosition(FVector(0,0,BaseFloorZ)).Z));
            if(Walking&&!Stance)
            {const float Swing=(Phase-StanceFraction)/(1.f-StanceFraction);Lift=FMath::Max(Lift,12.f*FMath::Square(FMath::Sin(PI*Swing)));}
        }
        const FVector Landing=Land(Animated,SurfaceRotation,Lift);
        // Reset skipped swing contacts too; a wrap must never retain last cycle's lock.
        if((NewFrame&&Walking&&Phase<L.LastPhase)||!Stance||PoseLiftAllowed)
        {L.Locked=false;L.UsedEarlyStep=false;if(!Stance||PoseLiftAllowed)L.Emergency=false;}
        if(Stance&&!L.Locked&&!L.Emergency&&!PoseLiftAllowed)
        {L.Locked=true;L.LockPosition=Landing;L.LockRotation=SurfaceRotation;}
        const float Reach=FVector::Distance(Upper.GetLocation(),Lower.GetLocation())+FVector::Distance(Lower.GetLocation(),Foot.GetLocation());
        const FVector LockLocal=Frame.InverseTransformPosition(L.LockPosition);
        // A leg that runs out of reach gets one short corrective step. The
        // remaining support group stays planted instead of stretching the skin.
        if(NewFrame&&L.Locked&&!L.Emergency&&!L.UsedEarlyStep&&Airborne<3&&
            FVector::Distance(Upper.GetLocation(),LockLocal)>.94f*Reach&&FVector::DistSquared(Landing,L.LockPosition)>FMath::Square(6.f))
        {
            L.Emergency=true;L.UsedEarlyStep=true;L.EmergencyTime=0.f;L.EarlyStart=L.LockPosition;
            L.EarlyEnd=Land(Frame.TransformPosition(Body.TransformPosition(L.NeutralInBody)),SurfaceRotation,0.f);
            L.Locked=false;++Airborne;
        }
        FVector Goal=Landing;FQuat GoalRotation=SurfaceRotation;
        if(L.Emergency)
        {
            if(NewFrame)L.EmergencyTime+=Dt;
            const float T=FMath::Clamp(L.EmergencyTime/StepSeconds,0.f,1.f),S=T*T*(3.f-2.f*T);
            Goal=FMath::Lerp(L.EarlyStart,L.EarlyEnd,S)+FVector::UpVector*(12.f*FMath::Square(FMath::Sin(PI*T)));
            if(T>=1.f){L.Emergency=false;L.Locked=Stance;L.LockPosition=L.EarlyEnd;L.LockRotation=SurfaceRotation;}
        }
        else if(L.Locked)
        {
            const float Edge=Walking?FMath::Clamp(FMath::Min(Phase/.07f,(StanceFraction-Phase)/.09f),0.f,1.f):1.f;
            const float LockWeight=Walking?PlantWeight*Edge:1.f;
            GoalRotation=FQuat::Slerp(SurfaceRotation,L.LockRotation,LockWeight).GetNormalized();
            const float Twist=SurfaceRotation.AngularDistance(GoalRotation),Limit=FMath::DegreesToRadians(35.f);
            if(Twist>Limit)GoalRotation=FQuat::Slerp(SurfaceRotation,GoalRotation,Limit/Twist).GetNormalized();
            Goal=Land(FMath::Lerp(Landing,L.LockPosition,LockWeight),GoalRotation,0.f);
        }
        FVector Target=Frame.InverseTransformPosition(Goal);
        const FVector Outward=Body.TransformVectorNoScale(L.OutwardInBody).GetSafeNormal();
        const FVector Forward=Body.TransformVectorNoScale(L.ForwardInBody).GetSafeNormal();
        const FVector Neutral=Body.TransformPosition(L.NeutralInBody);
        const float Along=FVector::DotProduct(Target-Neutral,Forward);
        Target+=Forward*(FMath::Clamp(Along,-35.f,35.f)-Along);
        Target+=Outward*FMath::Max(0.f,.10f*Reach-float(FVector::DotProduct(Target-Upper.GetLocation(),Outward)));
        const FVector ToTarget=Target-Upper.GetLocation();
        const float Minimum=FMath::Abs(FVector::Distance(Upper.GetLocation(),Lower.GetLocation())-FVector::Distance(Lower.GetLocation(),Foot.GetLocation()))+.05f*Reach;
        Target=Upper.GetLocation()+ToTarget.GetSafeNormal()*FMath::Clamp(float(ToTarget.Size()),Minimum,.965f*Reach);
        const FQuat Rotation=(Frame.GetRotation().Inverse()*GoalRotation).GetNormalized();
        // A body-local pole remains stable when the planted leg approaches its
        // reach limit. Deriving it from a nearly straight current knee flips it.
        FVector Bend=Body.TransformVectorNoScale(L.PoleInBody);const FVector Direction=(Target-Upper.GetLocation()).GetSafeNormal();
        Bend-=Direction*FVector::DotProduct(Bend,Direction);
        if(Bend.SizeSquared()<.01){Bend=Outward+FVector::UpVector;Bend-=Direction*FVector::DotProduct(Bend,Direction);}
        const FVector Pole=Upper.GetLocation()+Bend.GetSafeNormal()*Reach;
        AnimationCore::SolveTwoBoneIK(Upper,Lower,Foot,Pole,Target,false,1.,1.);
        Foot.SetRotation(Rotation);
        Out.Emplace(U,Upper);Out.Emplace(K,Lower);Out.Emplace(F,Foot);L.LastPhase=Phase;
    }
    Out.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex.GetInt()<B.BoneIndex.GetInt();});
}
