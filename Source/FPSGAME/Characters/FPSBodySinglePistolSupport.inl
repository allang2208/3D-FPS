// Fit the native arm around a real palm contact, retaining its bone lengths and
// sampled helper rotations. Both palms move as a rigid group when reach requires.
struct FSinglePistolSupportFit
{
    struct FHelper {FCompactPoseBoneIndex Bone;bool Lower=false;float Roll=0.f;};
    TArray<FHelper> Helpers[2];
    FTransform Torso=FTransform::Identity;
    FVector2D Radius=FVector2D(18.,12.);
    double Bottom=-45.,Top=25.;
    bool bReload=false;
    bool bLongGrip=false;
    float ReloadPostureWeight=1.f;
    float Delta=1.f/60.f;
    FVector LastBend[2],LastAxis[2];
    bool HasAngle[2]={false,false};
    void Reset(){HasAngle[0]=HasAngle[1]=false;}
    void Configure(const FTransform& Chest,const FQuat& ChestBind,const FVector& Hip,const FVector& RightShoulder,const FVector& LeftShoulder)
    {
        Torso=FTransform((Chest.GetRotation()*ChestBind.Inverse()).GetNormalized(),Chest.GetLocation());
        const double HalfWidth=FVector::Distance(RightShoulder,LeftShoulder)*.5;
        Radius=FVector2D(HalfWidth*1.25,HalfWidth*.80);
        Bottom=Torso.InverseTransformPosition(Hip).Z-10.;
        Top=FMath::Min(Torso.InverseTransformPosition(RightShoulder).Z,Torso.InverseTransformPosition(LeftShoulder).Z)-5.;
    }
    double Inside(const FVector& Point,double Padding) const
    {
        const FVector P=Torso.InverseTransformPosition(Point);
        const double CapPadding=bLongGrip?Padding:0.;
        if(P.Z<Bottom-CapPadding||P.Z>Top+CapPadding)return 0.;
        const double X=Radius.X+Padding,Y=Radius.Y+Padding;
        const double Radial=FMath::Max(0.,1.-FMath::Sqrt(FMath::Square(P.X/X)+FMath::Square(P.Y/Y)))*FMath::Min(X,Y);
        return bLongGrip?FMath::Min(Radial,FMath::Min(P.Z-Bottom+Padding,Top+Padding-P.Z)):Radial;
    }
    FTransform ClearFreeHand(FTransform Goal) const
    {
        FVector P=Torso.InverseTransformPosition(Goal.GetLocation());
        if(P.Z<Bottom||P.Z>Top)return Goal;
        const double X=Radius.X+11.,Y=Radius.Y+11.;
        const double R=FMath::Sqrt(FMath::Square(P.X/X)+FMath::Square(P.Y/Y));
        if(R>.001&&R<1.){P.X/=R;P.Y/=R;Goal.SetLocation(Torso.TransformPosition(P));}
        return Goal;
    }
    double FrontShift(const FVector& Point) const
    {
        const FVector P=Torso.InverseTransformPosition(Point);
        if(P.Z<Bottom||P.Z>Top||FMath::Abs(P.X)>Radius.X+9.)return 0.;
        return FMath::Max(0.,(Radius.Y+9.)*FMath::Sqrt(FMath::Max(0.,1.-FMath::Square(P.X/(Radius.X+9.))))-P.Y);
    }
    void Initialize(const FBoneContainer& Bones)
    {
        const auto& Ref=Bones.GetReferenceSkeleton();
        auto Bind=Ref.GetRefBonePose();
        for(int32 I=0;I<Bind.Num();++I)if(Ref.GetParentIndex(I)>=0)Bind[I]=Bind[I]*Bind[Ref.GetParentIndex(I)];
        for(int32 Side=0;Side<2;++Side)
        {
            Helpers[Side].Reset();const FString Suffix=Side==0?TEXT("_r"):TEXT("_l");
            const int32 U=Ref.FindBoneIndex(FName(TEXT("upperarm")+Suffix));
            const int32 E=Ref.FindBoneIndex(FName(TEXT("lowerarm")+Suffix));
            const int32 W=Ref.FindBoneIndex(FName(TEXT("hand")+Suffix));
            if(U==INDEX_NONE||E==INDEX_NONE||W==INDEX_NONE)continue;
            const FVector Span=Bind[W].GetLocation()-Bind[E].GetLocation();
            for(int32 I=0;I<Bones.GetCompactPoseNumBones();++I)
            {
                const FCompactPoseBoneIndex B(I);const int32 M=Bones.MakeMeshPoseIndex(B).GetInt();
                const FString Name=Ref.GetBoneName(M).ToString();
                if(M==U||M==E||M==W||Ref.BoneIsChildOf(M,W)||!Name.EndsWith(Suffix))continue;
                if(!Ref.BoneIsChildOf(M,U)&&!Name.StartsWith(TEXT("upperarm"))&&!Name.StartsWith(TEXT("lowerarm")))continue;
                FHelper H;H.Bone=B;H.Lower=Ref.BoneIsChildOf(M,E)||Name.StartsWith(TEXT("lowerarm"));
                H.Roll=FMath::Clamp(float(FVector::DotProduct(Bind[M].GetLocation()-Bind[E].GetLocation(),Span)/FMath::Max(Span.SizeSquared(),.001)),0.f,1.f);
                Helpers[Side].Add(H);
            }
        }
    }
    void Apply(FCSPose<FCompactPose>& Pose,const FBoneReference& Hand,int32 Side,const FTransform& Contact,float Weight)
    {
        const auto& Bones=Pose.GetPose().GetBoneContainer();
        if(Weight<=ZERO_ANIMWEIGHT_THRESH||!Hand.IsValidToEvaluate(Bones))return;
        const auto W=Hand.GetCompactPoseIndex(Bones),E=Bones.GetParentBoneIndex(W);
        if(E==INDEX_NONE)return;const auto U=Bones.GetParentBoneIndex(E);if(U==INDEX_NONE)return;
        const auto Upper=Pose.GetComponentSpaceTransform(U),Lower=Pose.GetComponentSpaceTransform(E),Wrist=Pose.GetComponentSpaceTransform(W);
        const FVector H=Upper.GetLocation(),J=Lower.GetLocation(),P=Wrist.GetLocation();
        FTransform Goal;Goal.Blend(Wrist,Contact,FMath::Clamp(Weight,0.f,1.f));
        const double A=FVector::Distance(H,J),B=FVector::Distance(J,P);
        const FVector OldAxis=(P-H).GetSafeNormal(),Axis=(Goal.GetLocation()-H).GetSafeNormal();
        if(A<.01||B<.01||Axis.IsNearlyZero())return;
        FVector Bend=J-H-OldAxis*FVector::DotProduct(J-H,OldAxis);
        if(!Bend.Normalize())return;
        Bend=FQuat::FindBetweenNormals(OldAxis,Axis).RotateVector(Bend);
        const double Reach=FMath::Clamp(FVector::Distance(H,Goal.GetLocation()),FMath::Abs(A-B)+.01,(A+B)*.985);
        const double Along=(A*A-B*B+Reach*Reach)/(2.*Reach);
        const double CircleRadius=FMath::Sqrt(FMath::Max(0.,A*A-Along*Along));
        const FVector Center=H+Axis*Along,NewWrist=H+Axis*Reach;
        const auto& HandRef=Bones.GetRefPoseTransform(W);
        const FVector PalmAxis=(Goal.GetRotation()*HandRef.GetRotation().Inverse()).RotateVector(HandRef.GetLocation().GetSafeNormal());
        // Once a palm is fitted, its original elbow plane may fold the wrist
        // back through the torso. Select the nearest viable point on the SAME
        // two-bone circle: wrist, shoulder and both bone lengths stay fixed.
        const auto Loss=[&](const FVector& Direction)
        {
            const FVector Joint=Center+Direction*CircleRadius;
            const double Angle=FMath::Acos(FMath::Clamp(FVector::DotProduct((NewWrist-Joint).GetSafeNormal(),PalmAxis),-1.,1.));
            const double Excess=FMath::Max(0.,Angle-FMath::DegreesToRadians(55.));
            double Cost=6000.*Excess*Excess+4.*(1.-FVector::DotProduct(Direction,Bend));
            const FVector Local=Torso.InverseTransformPosition(Joint),Shoulder=Torso.InverseTransformPosition(H);
            // Each elbow remains on its own side in ready AND reload poses.
            // Checking only the forearm below the chest cap allowed an elbow
            // just above that cap to cross the upper chest with its skinned arm.
            if(bLongGrip)Cost+=80.*FMath::Square(FMath::Max(0.,Radius.X*.35-Local.X*(Side?1.:-1.)));
            if(bReload)
            {
                Cost+=40.*ReloadPostureWeight*FMath::Square(FMath::Max(0.,Local.Z-Shoulder.Z+10.));
                if(!bLongGrip)Cost+=40.*ReloadPostureWeight*FMath::Square(FMath::Max(0.,Radius.X*.65-Local.X*(Side?1.:-1.)));
            }
            for(int32 I=0;I<=5;++I)
            {
                Cost+=200.*FMath::Square(Inside(FMath::Lerp(Joint,NewWrist,I/5.),5.5));
                if(bLongGrip)Cost+=200.*FMath::Square(Inside(FMath::Lerp(H,Joint,I/5.),4.5));
            }
            return Cost;
        };
        FVector Best=Bend;double BestLoss=Loss(Best);
        // Bounded scalar search, followed by local refinement. No fixed pole,
        // rest-pose reset, wrist-only rotation, or bone stretching.
        for(int32 I=-36;I<=36;++I)
        {
            const FVector Candidate=FQuat(Axis,FMath::DegreesToRadians(I*5.)).RotateVector(Bend);
            const double Cost=Loss(Candidate);if(Cost<BestLoss){Best=Candidate;BestLoss=Cost;}
        }
        for(const double Step:{2.,.5,.125})
        {
            const FVector Seed=Best;
            for(const double Sign:{-1.,1.})
            {
                const FVector Candidate=FQuat(Axis,FMath::DegreesToRadians(Step*Sign)).RotateVector(Seed);
                const double Cost=Loss(Candidate);if(Cost<BestLoss){Best=Candidate;BestLoss=Cost;}
            }
        }
        if(HasAngle[Side])
        {
            // The donor elbow plane changes as the grip group moves. A scalar
            // angle relative to that changing plane is not temporal history:
            // reusing it can sweep the elbow across the ribs. Transport the
            // previously displayed bend in the moving torso's frame instead.
            const FVector PreviousAxis=Torso.TransformVectorNoScale(LastAxis[Side]).GetSafeNormal();
            FVector Previous=FQuat::FindBetweenNormals(PreviousAxis,Axis).RotateVector(Torso.TransformVectorNoScale(LastBend[Side]));
            Previous=FVector::VectorPlaneProject(Previous,Axis).GetSafeNormal();
            const double Change=FMath::Atan2(FVector::DotProduct(Axis,FVector::CrossProduct(Previous,Best)),FVector::DotProduct(Previous,Best));
            Best=FQuat(Axis,FMath::Clamp(Change,-FMath::DegreesToRadians(360.*Delta),FMath::DegreesToRadians(360.*Delta))).RotateVector(Previous);
        }
        HasAngle[Side]=true;LastBend[Side]=Torso.InverseTransformVectorNoScale(Best);LastAxis[Side]=Torso.InverseTransformVectorNoScale(Axis);
        const FVector NewJoint=Center+Best*CircleRadius,Forearm=(NewWrist-NewJoint).GetSafeNormal();
        const FQuat UpperSwing=FQuat::FindBetweenNormals((J-H).GetSafeNormal(),(NewJoint-H).GetSafeNormal());
        const FQuat LowerSwing=FQuat::FindBetweenNormals((P-J).GetSafeNormal(),Forearm);
        // Share axial palm rotation with the forearm. Keep the remaining wrist
        // bend independent, and carry all skin helpers from the sampled donor.
        FQuat Residual=(Goal.GetRotation()*(LowerSwing*Wrist.GetRotation()).Inverse()).GetNormalized();
        if(Residual.W<0.f)Residual=Residual*-1.f;
        const FVector V(Residual.X,Residual.Y,Residual.Z);
        const double Twist=FMath::Clamp(2.*FMath::Atan2(FVector::DotProduct(V,Forearm),double(Residual.W))*.65,
            -FMath::DegreesToRadians(65.),FMath::DegreesToRadians(65.));
        const FQuat Roll(Forearm,Twist);
        FTransform NewUpper=Upper,NewLower=Lower,NewHand=Wrist;
        NewUpper.SetRotation((UpperSwing*Upper.GetRotation()).GetNormalized());
        NewLower.SetLocation(NewJoint);NewLower.SetRotation((Roll*LowerSwing*Lower.GetRotation()).GetNormalized());
        NewHand.SetLocation(NewWrist);NewHand.SetRotation(Goal.GetRotation());
        TArray<FBoneTransform,TInlineAllocator<32>> Changes;
        Changes.Emplace(U,NewUpper);Changes.Emplace(E,NewLower);Changes.Emplace(W,NewHand);
        for(const auto& Helper:Helpers[Side])
        {
            FTransform Value=Pose.GetComponentSpaceTransform(Helper.Bone);
            const FQuat Rotation=Helper.Lower?FQuat(Forearm,Twist*Helper.Roll)*LowerSwing:UpperSwing;
            Value.SetLocation((Helper.Lower?NewJoint:H)+Rotation.RotateVector(Value.GetLocation()-(Helper.Lower?J:H)));
            Value.SetRotation((Rotation*Value.GetRotation()).GetNormalized());Changes.Emplace(Helper.Bone,Value);
        }
        Changes.Sort([](const FBoneTransform& L,const FBoneTransform& R){return L.BoneIndex<R.BoneIndex;});
        Pose.LocalBlendCSBoneTransforms(Changes,1.f);
    }
};
