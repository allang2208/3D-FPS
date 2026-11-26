#include "BowFlexMeshComponent.h"
#include "Engine/SkeletalMesh.h"

namespace
{
// Compound rigs author each moving control and its full-draw goal as siblings.
// Interpolate their local poses so the cams travel with the flexing limb tips,
// the cable ends follow the cams, and both player views share the same phase.
const FName CompoundDrawEnd(TEXT("compound_draw_end"));
const FName CompoundLimbControls[][2]={
    {TEXT("upper_01"),TEXT("draw_upper_01")},{TEXT("lower_01"),TEXT("draw_lower_01")},
    {TEXT("upper_02"),TEXT("draw_upper_02")},{TEXT("lower_02"),TEXT("draw_lower_02")}};
struct FCamControls
{
    FName Cam, DrawCam, Tip, DrawTip;
    FName Centre, RimU, RimV, Cable[2];
};
const FCamControls CompoundWheels[]={
    {TEXT("upper_cam"),TEXT("draw_upper_cam"),TEXT("upper_tip"),TEXT("draw_upper_tip"),
        TEXT("upper_rim_center"),TEXT("upper_rim_u"),TEXT("upper_rim_v"),{TEXT("upper_cable0"),TEXT("upper_cable1")}},
    {TEXT("lower_cam"),TEXT("draw_lower_cam"),TEXT("lower_tip"),TEXT("draw_lower_tip"),
        TEXT("lower_rim_center"),TEXT("lower_rim_u"),TEXT("lower_rim_v"),{TEXT("lower_cable0"),TEXT("lower_cable1")}}};
const FName CableGuides[]={TEXT("guide_0"),TEXT("guide_1")};

// FTransform::Blend snaps negative weights to rest. Permit a small signed
// follow-through on the same authored axis without introducing scale or shear.
void PoseCompoundControl(FTransform& Out,const FTransform& Rest,const FTransform& Full,float Phase)
{
    if(Phase>=0.f){Out.Blend(Rest,Full,Phase);return;}
    Out=FTransform(FQuat::Slerp(Rest.GetRotation(),Full.GetRotation(),Phase).GetNormalized(),
        FMath::Lerp(Rest.GetTranslation(),Full.GetTranslation(),Phase),Rest.GetScale3D());
}

// The track markers live on the animated wheel. The free strand leaves the
// rear silhouette towards the current hand or cable guide in component space.
FVector TrackExit(const FVector& Centre,const FVector& U,const FVector& V,const FVector& To)
{
    const FVector Delta=To-Centre;
    const double X=FVector::DotProduct(Delta,U)/FMath::Max(U.SizeSquared(),UE_DOUBLE_SMALL_NUMBER);
    const double Y=FVector::DotProduct(Delta,V)/FMath::Max(V.SizeSquared(),UE_DOUBLE_SMALL_NUMBER);
    const double D=FMath::Max(X*X+Y*Y,1.000001);
    const double H=FMath::Sqrt(D-1.);
    const FVector A=Centre+(U*(X-Y*H)+V*(Y+X*H))/D;
    const FVector B=Centre+(U*(X+Y*H)+V*(Y-X*H))/D;
    return A.X<B.X?A:B;
}
}

void UBowFlexMeshComponent::SetFlexMesh(USkeletalMesh* Mesh)
{
    SetSkeletalMesh(Mesh);SetComponentTickEnabled(false);SetBoundsScale(1.8f);
    bFlexReady=false;bStringReady=false;ReferenceCS.Reset();LastDistribution=-1.f;
    for(auto& Position:LastString)Position=FVector(BIG_NUMBER);
    if(!Mesh)return;
    const auto& Ref=Mesh->GetRefSkeleton();ReferenceCS=Ref.GetRefBonePose();BoneSpaceTransforms=ReferenceCS;
    for(int32 I=0;I<ReferenceCS.Num();++I)
        if(const int32 Parent=Ref.GetParentIndex(I);Parent!=INDEX_NONE)ReferenceCS[I]*=ReferenceCS[Parent];
    bool Valid=true;
    for(int32 S=0;S<2;++S)for(int32 I=0;I<5;++I)
    {
        const FString Name=FString(S==0?TEXT("upper"):TEXT("lower"))+(I==4?TEXT("_tip"):FString::Printf(TEXT("_%02d"),I+1));
        Chain[S][I]=Ref.FindBoneIndex(FName(Name));Valid&=Chain[S][I]!=INDEX_NONE;
    }
    bFlexReady=Valid||(Ref.FindBoneIndex(CompoundDrawEnd)!=INDEX_NONE
        &&Chain[0][4]!=INDEX_NONE&&Chain[1][4]!=INDEX_NONE);
    const FName Names[]={TEXT("string_upper"),TEXT("string_nock"),TEXT("string_lower")};
    bStringReady=true;
    for(int32 I=0;I<3;++I){StringBones[I]=Ref.FindBoneIndex(Names[I]);bStringReady&=StringBones[I]!=INDEX_NONE;}
    MarkRefreshTransformDirty();RefreshBoneTransforms();
}
bool UBowFlexMeshComponent::PoseString(const FVector& Upper,const FVector& Nock,const FVector& Lower,
    const FVector* FittingAxes)
{
    if(!bStringReady)return false;
    if(Upper.Equals(LastString[0],.0001)&&Nock.Equals(LastString[1],.0001)&&Lower.Equals(LastString[2],.0001))return true;
    LastString[0]=Upper;LastString[1]=Nock;LastString[2]=Lower;
    TArray<FTransform,TInlineAllocator<16>> Pose;Pose.Append(ReferenceCS);
    for(int32 I=0;I<3;++I)
    {
        FTransform& Fitting = Pose[StringBones[I]];
        Fitting.SetLocation(LastString[I]);
        if (FittingAxes && !FittingAxes[I].IsNearlyZero())
        {
            // The beam asset's eyes, ferrules and serving are authored along component +Z.
            const FQuat Turn = FQuat::FindBetweenNormals(FVector::UpVector, FittingAxes[I]);
            Fitting.SetRotation((Turn * Fitting.GetRotation()).GetNormalized());
        }
    }
    const auto& Ref=GetSkinnedAsset()->GetRefSkeleton();
    for(int32 I=0;I<Pose.Num();++I)
    {const int32 Parent=Ref.GetParentIndex(I);BoneSpaceTransforms[I]=Parent==INDEX_NONE?Pose[I]:Pose[I].GetRelativeTransform(Pose[Parent]);}
    MarkRefreshTransformDirty();RefreshBoneTransforms();return true;
}
FVector UBowFlexMeshComponent::TipPosition(int32 Side,float Angle,float Distribution) const
{
    FVector Position=ReferenceCS[Chain[Side][0]].GetLocation();
    for(int32 I=1;I<5;++I)
    {
        const float Weight=FMath::Pow(float(I)/4.f,Distribution);
        const FQuat Bend(FVector::YAxisVector,Angle*(Side==0?-1.f:1.f)*Weight);
        Position+=Bend.RotateVector(ReferenceCS[Chain[Side][I]].GetLocation()-ReferenceCS[Chain[Side][I-1]].GetLocation());
    }
    return Position;
}
void UBowFlexMeshComponent::ApplyStringLoad(const FVector& NockCM,const FVector& BraceCM,float Distribution,float RingDegrees)
{
    if(!bFlexReady)return;
    Distribution=FMath::Clamp(Distribution,.5f,2.f);
    if(NockCM.Equals(LastNock,.0001)&&BraceCM.Equals(LastBrace,.0001)&&FMath::IsNearlyEqual(Distribution,LastDistribution)&&FMath::IsNearlyEqual(RingDegrees,LastRing))return;
    LastNock=NockCM;LastBrace=BraceCM;LastDistribution=Distribution;LastRing=RingDegrees;
    const auto& Ref=GetSkinnedAsset()->GetRefSkeleton();
    if(const int32 End=Ref.FindBoneIndex(CompoundDrawEnd);End!=INDEX_NONE)
    {
        const FVector Travel=ReferenceCS[End].GetLocation()-BraceCM;
        const double Draw=FVector::DotProduct(NockCM-BraceCM,Travel)/FMath::Max(Travel.SizeSquared(),UE_DOUBLE_SMALL_NUMBER);
        const float Phase=FMath::Clamp(float(Draw)+RingDegrees*.008f,-.06f,1.f);
        const auto& Rest=Ref.GetRefBonePose();
        for(const auto& Pair:CompoundLimbControls)
        {
            const int32 Control=Ref.FindBoneIndex(Pair[0]),Goal=Ref.FindBoneIndex(Pair[1]);
            if(Control!=INDEX_NONE&&Goal!=INDEX_NONE)PoseCompoundControl(BoneSpaceTransforms[Control],Rest[Control],Rest[Goal],Phase);
        }
        // Ease the visible wheel rollout near either end of the draw. Both
        // wheels use the same clock, including when the player lets down.
        const float WheelPhase=Phase<0.f?Phase*.70f:FMath::Lerp(Phase,Phase*Phase*(3.f-2.f*Phase),.5f);
        for(const FCamControls& Wheel:CompoundWheels)
        {
            const int32 Cam=Ref.FindBoneIndex(Wheel.Cam),DrawCam=Ref.FindBoneIndex(Wheel.DrawCam);
            const int32 Tip=Ref.FindBoneIndex(Wheel.Tip),DrawTip=Ref.FindBoneIndex(Wheel.DrawTip);
            if(Cam==INDEX_NONE||DrawCam==INDEX_NONE||Tip==INDEX_NONE||DrawTip==INDEX_NONE)continue;
            PoseCompoundControl(BoneSpaceTransforms[Cam],Rest[Cam],Rest[DrawCam],WheelPhase);
            const int32 Centre=Ref.FindBoneIndex(Wheel.Centre),U=Ref.FindBoneIndex(Wheel.RimU),V=Ref.FindBoneIndex(Wheel.RimV);
            if(Centre!=INDEX_NONE && U!=INDEX_NONE && V!=INDEX_NONE)
            {
                FTransform Limb=FTransform::Identity;
                for(int32 P=Ref.GetParentIndex(Cam);P!=INDEX_NONE;P=Ref.GetParentIndex(P))
                    Limb*=BoneSpaceTransforms[P];
                const FTransform WheelCS=BoneSpaceTransforms[Cam]*Limb;
                const FVector CentreLocal=Rest[Centre].GetTranslation();
                const FVector AxisU=WheelCS.TransformVector(Rest[U].GetTranslation()-CentreLocal);
                const FVector AxisV=WheelCS.TransformVector(Rest[V].GetTranslation()-CentreLocal);
                const FVector Contact=TrackExit(WheelCS.TransformPosition(CentreLocal),AxisU,AxisV,NockCM);
                BoneSpaceTransforms[Tip].SetTranslation(Limb.InverseTransformPosition(Contact));
                const FVector Normal=FVector::CrossProduct(AxisU,AxisV).GetSafeNormal();
                for(int32 I=0;I<2;++I)
                {
                    const int32 Cable=Ref.FindBoneIndex(Wheel.Cable[I]),Guide=Ref.FindBoneIndex(CableGuides[I]);
                    if(Cable==INDEX_NONE || Guide==INDEX_NONE)continue;
                    const FVector Offset=WheelCS.TransformVector(Rest[Cable].GetTranslation());
                    const FVector Lateral=Normal*FVector::DotProduct(Offset,Normal);
                    const double Radius=(Offset-Lateral).Size();
                    const FVector Exit=TrackExit(WheelCS.GetTranslation()+Lateral,AxisU.GetSafeNormal()*Radius,
                        AxisV.GetSafeNormal()*Radius,ReferenceCS[Guide].GetTranslation());
                    BoneSpaceTransforms[Cable].SetTranslation(WheelCS.InverseTransformPosition(Exit));
                }
                continue;
            }
            // The string exit and axle share a parent. Move around the modeled
            // rim rather than cutting across the face of the wheel at half draw.
            const FVector Hub=Rest[Cam].GetTranslation();
            const FVector Start=Rest[Tip].GetTranslation()-Hub,EndOffset=Rest[DrawTip].GetTranslation()-Hub;
            const FQuat Arc=FQuat::FindBetweenNormals(Start.GetSafeNormal(),EndOffset.GetSafeNormal());
            const FVector Direction=FQuat::Slerp(FQuat::Identity,Arc,WheelPhase).RotateVector(Start.GetSafeNormal());
            BoneSpaceTransforms[Tip].SetTranslation(Hub+Direction*FMath::Lerp(Start.Size(),EndOffset.Size(),double(WheelPhase)));
        }
        MarkRefreshTransformDirty();RefreshBoneTransforms();return;
    }
    const double RestLength=FVector::Distance(ReferenceCS[Chain[0][4]].GetLocation(),BraceCM)+FVector::Distance(ReferenceCS[Chain[1][4]].GetLocation(),BraceCM);
    auto Length=[&](float A){return FVector::Distance(TipPosition(0,A,Distribution),NockCM)+FVector::Distance(TipPosition(1,A,Distribution),NockCM);};
    float Low=0.f,High=FMath::DegreesToRadians(38.f);
    if(Length(0.f)>RestLength+.0001)
    {
        // Bounded deterministic solve; bone segment lengths remain unchanged.
        for(int32 I=0;I<14;++I){const float Mid=(Low+High)*.5f;if(Length(Mid)>RestLength)Low=Mid;else High=Mid;}
    }
    else High=0.f;
    const float Angle=(Low+High)*.5f+FMath::DegreesToRadians(FMath::Clamp(RingDegrees,-1.5f,1.5f));
    TArray<FTransform,TInlineAllocator<16>> Pose;Pose.Append(ReferenceCS);
    for(int32 S=0;S<2;++S)
    {
        FVector Position=ReferenceCS[Chain[S][0]].GetLocation();
        for(int32 I=0;I<5;++I)
        {
            if(I>0)
            {
                const FQuat Previous(FVector::YAxisVector,Angle*(S==0?-1.f:1.f)*FMath::Pow(float(I)/4.f,Distribution));
                Position+=Previous.RotateVector(ReferenceCS[Chain[S][I]].GetLocation()-ReferenceCS[Chain[S][I-1]].GetLocation());
            }
            const FQuat Bend(FVector::YAxisVector,Angle*(S==0?-1.f:1.f)*FMath::Pow(float(FMath::Min(I+1,4))/4.f,Distribution));
            Pose[Chain[S][I]].SetLocation(Position);Pose[Chain[S][I]].SetRotation((Bend*ReferenceCS[Chain[S][I]].GetRotation()).GetNormalized());
        }
    }
    for(int32 I=0;I<Pose.Num();++I)
    {const int32 Parent=Ref.GetParentIndex(I);BoneSpaceTransforms[I]=Parent==INDEX_NONE?Pose[I]:Pose[I].GetRelativeTransform(Pose[Parent]);}
    MarkRefreshTransformDirty();RefreshBoneTransforms();
}
bool UBowFlexMeshComponent::Tips(FVector& Upper,FVector& Lower) const
{
    if(!bFlexReady)return false;
    const auto& Pose=GetComponentSpaceTransforms();
    if(!Pose.IsValidIndex(Chain[0][4])||!Pose.IsValidIndex(Chain[1][4]))return false;
    Upper=Pose[Chain[0][4]].GetLocation();Lower=Pose[Chain[1][4]].GetLocation();return true;
}
