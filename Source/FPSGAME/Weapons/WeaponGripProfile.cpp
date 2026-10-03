#include "WeaponGripProfile.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

bool UWeaponGripProfile::SetSharedClipsFromJson(const FString& Json)
{
#if WITH_EDITOR
    TSharedPtr<FJsonObject> Root;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root)||!Root)return false;
    const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
    if(!Root->TryGetArrayField(TEXT("clips"),Rows))return false;
    TArray<FWeaponGripClip> Imported;
    for(const auto& Row:*Rows)
    {
        const auto Spec=Row->AsObject();if(!Spec)return false;
        FWeaponGripClip Clip;
        Clip.Base=LoadObject<UAnimSequence>(nullptr,*Spec->GetStringField(TEXT("base")));
        if(!Clip.Base)return false;
        Clip.Duration=Spec->GetNumberField(TEXT("duration"));
        for(const auto& Value:Spec->GetArrayField(TEXT("tracks")))
        {
            const auto TrackSpec=Value->AsObject();if(!TrackSpec)return false;
            FWeaponGripTrack Track;Track.Bone=*TrackSpec->GetStringField(TEXT("bone"));
            for(const auto& Time:TrackSpec->GetArrayField(TEXT("times")))Track.Times.Add(Time->AsNumber());
            for(const auto& Key:TrackSpec->GetArrayField(TEXT("values")))Track.Values.Add(Key->AsNumber());
            if(Track.Times.IsEmpty()||Track.Values.Num()!=Track.Times.Num()*10)return false;
            Clip.Tracks.Add(MoveTemp(Track));
        }
        Imported.Add(MoveTemp(Clip));
    }
    Modify();Family=*Root->GetStringField(TEXT("family"));Clips=MoveTemp(Imported);MarkPackageDirty();return true;
#else
    return false;
#endif
}

namespace
{
FTransform ReadKey(const FWeaponGripTrack& Track,int32 Index)
{
    const float* V=Track.Values.GetData()+Index*10;
    return FTransform(FQuat(V[3],V[4],V[5],V[6]).GetNormalized(),FVector(V[0],V[1],V[2]),FVector(V[7],V[8],V[9]));
}
FTransform Interpolate(const FTransform& A,const FTransform& B,float Alpha)
{
    return FTransform(FQuat::Slerp(A.GetRotation(),B.GetRotation(),Alpha).GetNormalized(),
        FMath::Lerp(A.GetTranslation(),B.GetTranslation(),Alpha),FMath::Lerp(A.GetScale3D(),B.GetScale3D(),Alpha));
}
}

FTransform FWeaponGripTrack::Sample(float Time) const
{
    if(Times.Num()==1||Time<=Times[0])return ReadKey(*this,0);
    if(Time>=Times.Last())return ReadKey(*this,Times.Num()-1);
    int32 Low=0,High=Times.Num()-1;
    while(High-Low>1){const int32 Mid=(Low+High)/2;if(Times[Mid]<=Time)Low=Mid;else High=Mid;}
    return Interpolate(ReadKey(*this,Low),ReadKey(*this,High),(Time-Times[Low])/(Times[High]-Times[Low]));
}

void FWeaponGripClip::ApplyLocal(FName Bone,float Time,FTransform& Local) const
{
    const auto* Track=Tracks.FindByPredicate([Bone](const FWeaponGripTrack& Item){return Item.Bone==Bone;});
    if(!Track)return;
    const FTransform Delta=Track->Sample(FMath::Clamp(Time,0.f,Duration));
    Local.SetTranslation(Local.GetTranslation()+Delta.GetTranslation());
    Local.SetRotation((Delta.GetRotation()*Local.GetRotation()).GetNormalized());
    Local.SetScale3D(Local.GetScale3D()+Delta.GetScale3D());
}

const FWeaponGripClip* UWeaponGripProfile::Find(const UAnimSequence* Base) const
{
    return Base?Clips.FindByPredicate([Base](const FWeaponGripClip& Clip){return Clip.Base==Base;}):nullptr;
}

const FWeaponGripClip* UWeaponGripProfile::FindAction(FName Action) const
{
    const FString Role=Action.ToString().ToLower();
    return Clips.FindByPredicate([&Role](const FWeaponGripClip& Clip)
    {
        if(!Clip.Base)return false;
        const FString Name=Clip.Base->GetName().ToLower();
        if(Role.StartsWith(TEXT("sprint_")))
            return Name.Contains(TEXT("sprint"))&&Name.EndsWith(Role.RightChop(7));
        if(Role==TEXT("quick_melee"))return Name.Contains(TEXT("quick_melee"))||Name.Contains(TEXT("quickcombat"));
        // Sword roles retain their existing names, including WhirlwindV5.
        return Name.EndsWith(TEXT("_")+Role)||(Role==TEXT("whirlwind")&&Name.EndsWith(TEXT("_whirlwindv5")));
    });
}

bool UWeaponGripProfile::BakeClip(UAnimSequence* Base,UAnimSequence* Authored)
{
#if WITH_EDITOR
    if(!Base||!Authored||Base->GetSkeleton()!=Authored->GetSkeleton()||!Base->GetSkeleton()
        ||!FMath::IsNearlyEqual(Base->GetPlayLength(),Authored->GetPlayLength(),.001f))return false;
    const FReferenceSkeleton& Ref=Base->GetSkeleton()->GetReferenceSkeleton();
    FWeaponGripClip Clip;Clip.Base=Base;Clip.Duration=Base->GetPlayLength();
    const int32 Steps=FMath::Max(1,FMath::RoundToInt(Clip.Duration*120.f));
    // Key reduction is part of data production. Tolerances are local bone units
    // and radians; no pose solver or motion retiming is introduced at runtime.
    const auto Error=[](const FTransform& A,const FTransform& B)
    {
        return FMath::Max3(FVector::Dist(A.GetTranslation(),B.GetTranslation())/.0001,
            A.GetRotation().AngularDistance(B.GetRotation())/FMath::DegreesToRadians(.01),
            FVector::Dist(A.GetScale3D(),B.GetScale3D())/.000001);
    };
    const FTransform Zero(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector);
    for(int32 Bone=0;Bone<Ref.GetNum();++Bone)
    {
        TArray<FTransform> Samples;Samples.Reserve(Steps+1);
        bool bDifferent=false;
        for(int32 Frame=0;Frame<=Steps;++Frame)
        {
            const double Time=double(Frame)*Clip.Duration/Steps;
            FTransform B,F;
            Base->GetBoneTransform(B,FSkeletonPoseBoneIndex(Bone),FAnimExtractContext(Time,false),false);
            Authored->GetBoneTransform(F,FSkeletonPoseBoneIndex(Bone),FAnimExtractContext(Time,false),false);
            const FTransform Delta((F.GetRotation()*B.GetRotation().Inverse()).GetNormalized(),
                F.GetTranslation()-B.GetTranslation(),F.GetScale3D()-B.GetScale3D());
            Samples.Add(Delta);bDifferent|=Error(Delta,Zero)>1.;
        }
        if(!bDifferent)continue;
        FWeaponGripTrack Track;Track.Bone=Ref.GetBoneName(Bone);
        TArray<int32> Keys;Keys.Add(0);
        bool bConstant=true;
        for(int32 I=1;I<=Steps;++I)if(Error(Samples[0],Samples[I])>1.){bConstant=false;break;}
        if(!bConstant)
        {
            Keys.Add(Steps);
            TArray<FIntPoint> Pending;Pending.Add(FIntPoint(0,Steps));
            while(!Pending.IsEmpty())
            {
                const FIntPoint Range=Pending.Pop(EAllowShrinking::No);
                double Maximum=1.;int32 Split=INDEX_NONE;
                for(int32 I=Range.X+1;I<Range.Y;++I)
                {
                    const double E=Error(Samples[I],Interpolate(Samples[Range.X],Samples[Range.Y],float(I-Range.X)/(Range.Y-Range.X)));
                    if(E>Maximum){Maximum=E;Split=I;}
                }
                if(Split!=INDEX_NONE){Keys.Add(Split);Pending.Add(FIntPoint(Range.X,Split));Pending.Add(FIntPoint(Split,Range.Y));}
            }
            Keys.Sort();
        }
        for(const int32 I:Keys)
        {
            Track.Times.Add(float(I)*Clip.Duration/Steps);
            const FTransform& D=Samples[I];const FVector P=D.GetTranslation(),S=D.GetScale3D();const FQuat Q=D.GetRotation();
            Track.Values.Append({float(P.X),float(P.Y),float(P.Z),float(Q.X),float(Q.Y),float(Q.Z),float(Q.W),float(S.X),float(S.Y),float(S.Z)});
        }
        Clip.Tracks.Add(MoveTemp(Track));
    }
    Clips.RemoveAll([Base](const FWeaponGripClip& Old){return Old.Base==Base;});
    Clips.Add(MoveTemp(Clip));MarkPackageDirty();return true;
#else
    return false;
#endif
}

void UWeaponGripProfile::KeepClip(UAnimSequence* Base,UAnimSequence* Authored)
{
#if WITH_EDITOR
    if(!Base||!Authored)return;
    FWeaponGripClip Clip;Clip.Base=Base;Clip.Duration=Base->GetPlayLength();Clip.Retained=Authored;
    Clips.RemoveAll([Base](const FWeaponGripClip& Old){return Old.Base==Base;});
    Clips.Add(MoveTemp(Clip));MarkPackageDirty();
#endif
}
