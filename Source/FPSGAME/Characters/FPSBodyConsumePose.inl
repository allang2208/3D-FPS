// Independent full-body donor, applied to the torso and consuming arm. Feet
// retain locomotion/grounding, and the right arm retains its equipment pose.
void FControls::BlendConsume(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    if(ConsumeWeight<=ZERO_ANIMWEIGHT_THRESH)return;
    const auto& Bones=Out.Pose.GetBoneContainer();
    Out.Pose=Pose.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    FPoseContext Authored(Out);Consume.Evaluate(Authored);
    for(int32 I=0;I<ConsumeBones.Num();++I)if(ConsumeBones[I])
    {
        const FCompactPoseBoneIndex B(I);
        FTransform Mixed;Mixed.Blend(Out.Pose[B],Authored.Pose[B],ConsumeWeight);Out.Pose[B]=Mixed;
    }
    Pose.InitPose(Out.Pose);
    if(!Hands[1].IsValidToEvaluate(Bones))return;
    const auto W=Hands[1].GetCompactPoseIndex(Bones);
    if(bHasConsumeProp&&ConsumeContactWeight>ZERO_ANIMWEIGHT_THRESH&&Head.IsValidToEvaluate(Bones))
    {
        auto Target=Pose.GetComponentSpaceTransform(W);
        const auto E=Bones.GetParentBoneIndex(W),S=Bones.GetParentBoneIndex(E);
        FLegReference Arm;
        Arm.Set(Pose.GetComponentSpaceTransform(S).GetLocation(),Pose.GetComponentSpaceTransform(E).GetLocation(),Target.GetLocation());
        const FVector Mouth=Pose.GetComponentSpaceTransform(Head.GetCompactPoseIndex(Bones)).TransformPosition(ConsumeMouthInHead);
        const FVector Rim=State.Contacts.Props[0].TransformPosition(ConsumePropContact);
        if(bConsumeNativeArm)
        {
            // Solve to the bottle rim as the end of a rigid forearm/hand/prop
            // lever. The authored local wrist stays intact, instead of being
            // counter-rotated after positional IK bends the forearm again.
            auto Root=Pose.GetComponentSpaceTransform(S),Joint=Pose.GetComponentSpaceTransform(E);
            const FTransform WristLocal=Target.GetRelativeTransform(Joint);
            const FVector CurrentRim=Target.TransformPosition(Rim);
            FTransform Tip(FQuat::Identity,CurrentRim);
            const double Upper=FVector::Distance(Root.GetLocation(),Joint.GetLocation());
            const double Lever=FVector::Distance(Joint.GetLocation(),CurrentRim);
            const FVector Wanted=FMath::Lerp(CurrentRim,Mouth,ConsumeContactWeight*ConsumeWeight);
            const FVector Reach=Wanted-Root.GetLocation();
            const double Length=FMath::Clamp(Reach.Size(),FMath::Abs(Upper-Lever)+.01,(Upper+Lever)*.97);
            const FVector Goal=Root.GetLocation()+Reach.GetSafeNormal()*Length;
            Arm.Set(Root.GetLocation(),Joint.GetLocation(),CurrentRim);
            AnimationCore::SolveTwoBoneIK(Root,Joint,Tip,Arm.Pole(Arm.Hip,Goal),Goal,Upper,Lever,false,1.,1.);
            TArray<FBoneTransform,TInlineAllocator<3>> Changes;
            Changes.Emplace(S,Root);Changes.Emplace(E,Joint);Changes.Emplace(W,WristLocal*Joint);
            Pose.LocalBlendCSBoneTransforms(Changes,1.f);
        }
        else
        {
            const FVector Contact=Mouth-Target.TransformVector(Rim);
            Target.SetLocation(FMath::Lerp(Target.GetLocation(),Contact,ConsumeContactWeight*ConsumeWeight));
            Solve(Pose,Hands[1],Target,Arm.Pole(Arm.Hip,Target.GetLocation()),1.f);
        }
    }
    LastHands[1]=Pose.GetComponentSpaceTransform(W);
}
