// Jason's elbow skin is weighted to corrective branches on both sides of the
// hinge. Keeping their bind locals folds those surfaces even when the wrist
// and elbow positions are correct. Fit the weighted helpers to the achieved
// bend after contact IK; never change the main chain, fingers or food mount.
void FControls::CorrectConsumeElbows(FCSPose<FCompactPose>& Pose)
{
    if(!bConsumeFood||!bConsumeNativeArm)return;
    const auto& Bones=Pose.GetPose().GetBoneContainer();
    TArray<FBoneTransform,TInlineAllocator<6>> Changes;
    for(int32 Side=0;Side<2;++Side)
    {
        if((Side==0&&!bConsumeTwoHands)||!Hands[Side].IsValidToEvaluate(Bones))continue;
        const auto W=Hands[Side].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W),U=Bones.GetParentBoneIndex(E);
        const auto& Arm=ConsumeArms[Side];const auto Elbow=Pose.GetComponentSpaceTransform(E);
        const FQuat UpperDeform=Pose.GetComponentSpaceTransform(U).GetRotation()*Arm.InverseUpper;
        const FQuat LowerDeform=Elbow.GetRotation()*Arm.InverseLower;
        // Fitted against each side's actual Jason skin throughout all six foods.
        const float Shares[3]={Side==0?.1f:.3f,Side==0?.5f:bConsumeTwoHands?.8f:.35f,Side==0?.875f:bConsumeTwoHands?.75f:.85f};
        for(int32 H=0;H<3;++H)
        {
            const auto& Helper=Arm.Helpers[H];if(!Helper.Bone.IsValidToEvaluate(Bones))continue;
            const auto B=Helper.Bone.GetCompactPoseIndex(Bones);auto Target=Pose.GetComponentSpaceTransform(B);
            const FQuat Deform=FQuat::Slerp(UpperDeform,LowerDeform,Shares[H]).GetNormalized();
            Target.SetRotation((Deform*Helper.ReferenceRotation).GetNormalized());
            Target.SetLocation(Elbow.GetLocation()+Deform.RotateVector(Helper.ElbowOffset));Changes.Emplace(B,Target);
        }
    }
    Changes.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex.GetInt()<B.BoneIndex.GetInt();});
    if(!Changes.IsEmpty())Pose.LocalBlendCSBoneTransforms(Changes,ConsumeWeight);
}

// Independent native torso/arm takes. Feet retain locomotion and grounding;
// the large-rack take owns both arms, while single-hand food preserves equipment.
void FControls::BlendConsume(FPoseContext& Out,FCSPose<FCompactPose>& Pose)
{
    if(ConsumeWeight<=ZERO_ANIMWEIGHT_THRESH)return;
    const auto& Bones=Out.Pose.GetBoneContainer();
    const bool TwoHands=!bConsumeTwoHands&&State.Contacts.Consumable==TEXT("roasted_large_lamb")&&
        (State.Contacts.Wrists&3)==3&&Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones);
    FTransform RightFromLeft;
    if(TwoHands)RightFromLeft=Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones)).GetRelativeTransform(
        Pose.GetComponentSpaceTransform(Hands[1].GetCompactPoseIndex(Bones)));
    Out.Pose=Pose.GetPose();
    FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
    FPoseContext Authored(Out);Consume.Evaluate(Authored);
    const auto Hip=Pelvis.GetCompactPoseIndex(Bones),Chest=ChestBase.GetCompactPoseIndex(Bones);
    const FTransform BaseChest=Pose.GetComponentSpaceTransform(Chest);
    FCSPose<FCompactPose> Donor;Donor.InitPose(Authored.Pose);
    FTransform AuthoredChest=Donor.GetComponentSpaceTransform(Chest);
    const FVector AuthoredHip=Donor.GetComponentSpaceTransform(Hip).GetLocation();
    for(int32 I=0;I<ConsumeBones.Num();++I)if(ConsumeBones[I]||(bConsumeTwoHands&&(LibraryArmBones[I]&1)))
    {
        const FCompactPoseBoneIndex B(I);
        FTransform Mixed;Mixed.Blend(Out.Pose[B],Authored.Pose[B],ConsumeWeight);Out.Pose[B]=Mixed;
    }
    Pose.InitPose(Out.Pose);
    // Retain the native torso/arm frame while the gait supplies hip translation.
    // Mixing only local spine transforms inherits the unrelated gait pelvis
    // rotation and makes both the mouth and the held food/bottle shake.
    AuthoredChest.AddToTranslation(Pose.GetComponentSpaceTransform(Hip).GetLocation()-AuthoredHip);
    FTransform MixedChest;MixedChest.Blend(BaseChest,AuthoredChest,ConsumeWeight);
    TArray<FBoneTransform,TInlineAllocator<1>> Anchor;Anchor.Emplace(Chest,MixedChest);
    Pose.LocalBlendCSBoneTransforms(Anchor,1.f);
    if(bConsumeTwoHands)
    {
        // This clip owns both complete native arm chains, including the helper
        // bones, wrists and the real rack contacts. Re-applying single-hand
        // bread IK or the FPS right-from-left frame would break that fit.
        CorrectConsumeElbows(Pose);
        for(int32 Side=0;Side<2;++Side)if(Hands[Side].IsValidToEvaluate(Bones))
            LastHands[Side]=Pose.GetComponentSpaceTransform(Hands[Side].GetCompactPoseIndex(Bones));
        return;
    }
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
    if(TwoHands)
    {
        const auto R=Hands[0].GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(R),S=Bones.GetParentBoneIndex(E);
        const FTransform Target=RightFromLeft*LastHands[1];
        FLegReference Arm;Arm.Set(Pose.GetComponentSpaceTransform(S).GetLocation(),Pose.GetComponentSpaceTransform(E).GetLocation(),Pose.GetComponentSpaceTransform(R).GetLocation());
        Solve(Pose,Hands[0],Target,Arm.Pole(Arm.Hip,Target.GetLocation()),1.f);
        LastHands[0]=Pose.GetComponentSpaceTransform(R);
    }
    CorrectConsumeElbows(Pose);
}
