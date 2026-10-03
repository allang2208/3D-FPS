#include "FPSBodyMotionSample.h"
#include "Engine/NetSerialization.h"
namespace
{
void Rotation(FArchive& Ar,FQuat& Q)
{
    FRotator R=Ar.IsSaving()?Q.Rotator():FRotator::ZeroRotator;
    R.SerializeCompressedShort(Ar);if(Ar.IsLoading())Q=R.Quaternion();
}
void Transform(FArchive& Ar,FTransform& T)
{
    FVector P=T.GetLocation(),S=T.GetScale3D();FQuat Q=T.GetRotation();
    SerializePackedVector<100,24>(P,Ar);Rotation(Ar,Q);
    bool Unit=Ar.IsSaving()&&S.Equals(FVector::OneVector,.001);Ar.SerializeBits(&Unit,1);
    if(Unit)S=FVector::OneVector;else SerializePackedVector<1000,24>(S,Ar);
    if(Ar.IsLoading())T=FTransform(Q,P,S);
}
bool Good(const FTransform& T)
{return !T.ContainsNaN()&&T.GetLocation().GetAbsMax()<5000.&&T.GetScale3D().GetAbsMax()<=1000.;}
}
bool FFPSBodyMotionSample::NetSerialize(FArchive& Ar,UPackageMap*,bool& Success)
{
    Ar<<Channel;Ar<<Fingers;Ar<<Wrists;
    Ar.SerializeBits(&CoupledWrists,1);Ar.SerializeBits(&DroppedBottle,1);
    Ar.SerializeBits(&HasSupportGrip,1);if(HasSupportGrip)Transform(Ar,SupportGrip);
    for(int32 Side=0;Side<2;++Side)
    {
        if(Wrists&(1<<Side))Transform(Ar,Hands[Side].Wrist);
        if(Fingers&(1<<Side))for(auto& Q:Hands[Side].Fingers)Rotation(Ar,Q);
    }
    uint8 Count=Ar.IsSaving()?FMath::Min(Rigs.Num(),2):0;Ar<<Count;
    if(Count>2){Success=false;return true;}if(Ar.IsLoading())Rigs.SetNum(Count);
    for(auto& Rig:Rigs)
    {
        Ar.SerializeBits(&Rig.Valid,1);if(!Rig.Valid){if(Ar.IsLoading()){Rig.Bones.Reset();Rig.Parts.Reset();Rig.VisibleParts.Reset();}continue;}
        Ar<<Rig.Schema;Transform(Ar,Rig.Root);Ar<<Rig.Sections;Ar.SerializeBits(&Rig.Visible,1);
        for(int32 Kind=0;Kind<2;++Kind)
        {
            auto& Array=Kind==0?Rig.Bones:Rig.Parts;
            uint16 N=Ar.IsSaving()?FMath::Min(Array.Num(),Kind==0?512:64):0;Ar<<N;
            if(N>(Kind==0?512:64)){Success=false;return true;}if(Ar.IsLoading())Array.SetNum(N);
            if(Kind==1&&Ar.IsLoading())Rig.VisibleParts.SetNum(N);
            for(int32 I=0;I<N;++I){Transform(Ar,Array[I]);if(Kind==1)Ar<<Rig.VisibleParts[I];}
        }
    }
    Ar<<Consumable;Ar<<ConsumableSerial;Ar<<DiscardFlags;Ar<<PropVisibility;
    if(!Consumable.IsNone()){for(auto& P:Props)Transform(Ar,P);Ar<<LiquidLevel;}
    Ar<<Light;Success=!Ar.IsError();return true;
}
bool FFPSBodyMotionSample::IsSane() const
{
    if(Fingers>3||Wrists>3||Rigs.Num()>2||!FMath::IsFinite(LiquidLevel)||!FMath::IsFinite(Light)||!Good(SupportGrip))return false;
    for(const auto& H:Hands){if(!Good(H.Wrist))return false;for(const auto& Q:H.Fingers)if(Q.ContainsNaN())return false;}
    for(const auto& R:Rigs)
    {
        if(!Good(R.Root)||R.Bones.Num()>512||R.Parts.Num()>64||R.Parts.Num()!=R.VisibleParts.Num())return false;
        for(const auto& B:R.Bones)if(!Good(B))return false;for(const auto& P:R.Parts)if(!Good(P))return false;
    }
    for(const auto& P:Props)if(!Good(P))return false;
    return true;
}
bool FFPSBodyMotionSample::Identical(const FFPSBodyMotionSample* Other,uint32) const
{
    if(!Other)return false;const auto& B=*Other;
    if(Channel!=B.Channel||Consumable!=B.Consumable||ConsumableSerial!=B.ConsumableSerial||Fingers!=B.Fingers||Wrists!=B.Wrists
        ||PropVisibility!=B.PropVisibility||DiscardFlags!=B.DiscardFlags||CoupledWrists!=B.CoupledWrists||DroppedBottle!=B.DroppedBottle
        ||HasSupportGrip!=B.HasSupportGrip||(HasSupportGrip&&!SupportGrip.Equals(B.SupportGrip))
        ||Light!=B.Light||LiquidLevel!=B.LiquidLevel||Rigs.Num()!=B.Rigs.Num())return false;
    for(int32 S=0;S<2;++S)
    {
        if((Wrists&(1<<S))&&!Hands[S].Wrist.Equals(B.Hands[S].Wrist))return false;
        if(Fingers&(1<<S))for(int32 J=0;J<15;++J)if(!Hands[S].Fingers[J].Equals(B.Hands[S].Fingers[J]))return false;
    }
    for(int32 I=0;I<Rigs.Num();++I)
    {
        const auto& A=Rigs[I];const auto& R=B.Rigs[I];if(A.Valid!=R.Valid)return false;if(!A.Valid)continue;
        if(A.Schema!=R.Schema||A.Sections!=R.Sections||A.Visible!=R.Visible||!A.Root.Equals(R.Root)||A.Bones.Num()!=R.Bones.Num()
            ||A.Parts.Num()!=R.Parts.Num()||A.VisibleParts!=R.VisibleParts)return false;
        for(int32 J=0;J<A.Bones.Num();++J)if(!A.Bones[J].Equals(R.Bones[J]))return false;
        for(int32 J=0;J<A.Parts.Num();++J)if(!A.Parts[J].Equals(R.Parts[J]))return false;
    }
    if(!Consumable.IsNone())for(int32 I=0;I<3;++I)if(!Props[I].Equals(B.Props[I]))return false;
    return true;
}
