#include "SpiralPillarM14.h"
#include "MonsterCorpseRagdollComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#if WITH_EDITOR
#include "MeshDescription.h"
#include "SkeletalMeshAttributes.h"
#endif

void ASpiralPillarM14::ApplySoftDeath(float Seconds)
{
    if(!SoftDeathMorphTargets.IsEmpty()&&SoftDeathMorphTimes.Num()==SoftDeathMorphTargets.Num())
    {
        int32 Upper=0;
        while(Upper<SoftDeathMorphTimes.Num()&&Seconds>SoftDeathMorphTimes[Upper])++Upper;
        const int32 Lower=Upper-1;
        const float Start=Lower>=0?SoftDeathMorphTimes[Lower]:0.f;
        const float Alpha=Upper<SoftDeathMorphTimes.Num()?
            FMath::Clamp((Seconds-Start)/FMath::Max(UE_SMALL_NUMBER,SoftDeathMorphTimes[Upper]-Start),0.f,1.f):0.f;
        // Acceleration, contact and recoil are baked into the samples. Easing
        // every interval again stops the whole creature at each intermediate pose.
        for(int32 I=0;I<SoftDeathMorphTargets.Num();++I)
            GetMesh()->SetMorphTarget(SoftDeathMorphTargets[I],I==Upper?Alpha:I==Lower?1.f-Alpha:0.f);
        return;
    }
    // Retain playback for older saved three-shape assets until they are replaced.
    if(SoftDeathMorphTargets.Num()!=3)return;
    auto Ease=[](float X){X=FMath::Clamp(X,0.f,1.f);return X*X*(3.f-2.f*X);};
    float Weights[3]={0.f,0.f,0.f};
    if(Seconds<=.75f)Weights[0]=Ease(Seconds/.75f);
    else if(Seconds<=1.60f){Weights[1]=Ease((Seconds-.75f)/.85f);Weights[0]=1.f-Weights[1];}
    else if(Seconds<=2.70f){Weights[2]=Ease((Seconds-1.60f)/1.10f);Weights[1]=1.f-Weights[2];}
    else Weights[2]=1.f;
    // Component override curves survive the shared corpse pose snapshot and
    // animation-instance replacement. Do not let the body reinflate on sleep.
    for(int32 I=0;I<3;++I)GetMesh()->SetMorphTarget(SoftDeathMorphTargets[I],Weights[I]);
}

bool ASpiralPillarM14::StartCorpsePhysics()
{
    // Only after the tissue is spread may its final low collision footprint
    // replace the standing query asset. Earlier replacement would hold an
    // unrelated upright shell or prevent the authored collapse from completing.
    if(!SoftDeathMorphTargets.IsEmpty()&&CorpsePhysicsAsset)GetMesh()->SetPhysicsAsset(CorpsePhysicsAsset);
    return CorpseRagdoll->Start(GetMesh());
}

bool ASpiralPillarM14::BuildSoftDeathMorphs(USkeletalMesh* SourceMesh)
{
#if WITH_EDITOR
    if(!SourceMesh)return false;
    FMeshDescription* Description=SourceMesh->GetMeshDescription(0);
    if(!Description)return false;
    const auto& Ref=SourceMesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    const int32 Base=Ref.FindBoneIndex(TEXT("base")),XB=Ref.FindBoneIndex(TEXT("roottoe_00")),YB=Ref.FindBoneIndex(TEXT("roottoe_02"));
    const int32 MouthBone=Ref.FindBoneIndex(TEXT("maw")),SacL=Ref.FindBoneIndex(TEXT("sac_L")),SacR=Ref.FindBoneIndex(TEXT("sac_R"));
    if(Base==INDEX_NONE||XB==INDEX_NONE||YB==INDEX_NONE||MouthBone==INDEX_NONE||SacL==INDEX_NONE||SacR==INDEX_NONE)return false;
    const FVector X=(Frames[XB].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    const FVector Y=(Frames[YB].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    auto ToBlender=[&](const FVector& P){return FVector(P.Dot(X),P.Dot(Y),P.Z)*.01;};
    auto ToMesh=[&](const FVector& P){return (X*P.X+Y*P.Y+FVector::UpVector*P.Z)*100.;};
    auto Ease=[](double T){T=FMath::Clamp(T,0.,1.);return T*T*(3.-2.*T);};
    const FVector Mouth=ToBlender(Frames[MouthBone].GetLocation());
    const FVector MouthAt(.20*FMath::Sin(Mouth.Z*1.45),Mouth.Y*1.2+.65*Mouth.Z+.12*FMath::Sin(Mouth.Z*2.),.23);
    const FVector Band(0.,0.,2.03),BandAt(.20*FMath::Sin(2.03*1.45),.65*2.03+.12*FMath::Sin(2.03*2.),.18);
    const FVector Sacs[2]={ToBlender(Frames[SacL].GetLocation())-FVector(0,0,.18),ToBlender(Frames[SacR].GetLocation())-FVector(0,0,.18)};
    const double Angle=FMath::DegreesToRadians(-76.),C=FMath::Cos(Angle),S=FMath::Sin(Angle);
    SourceMesh->Modify();FSkeletalMeshAttributes Attributes(*Description);
    const FName Names[3]={TEXT("M14_DeathSag"),TEXT("M14_DeathFold"),TEXT("M14_DeathSpread")};
    TArray<TVertexAttributesRef<FVector3f>> Deltas;
    for(const FName Name:Names)
    {
        // Store editable source deltas so reloads/DDC rebuilds retain the shapes.
        // UE derives normals from each deformed surface during mesh building.
        Attributes.RegisterMorphTargetAttribute(Name,false);
        Deltas.Add(Attributes.GetVertexMorphPositionDelta(Name));
    }
    const auto Positions=Attributes.GetVertexPositions();
    const double Times[3]={.75,1.60,2.70};
    for(const FVertexID Vertex:Description->Vertices().GetElementIDs())
    {
        const FVector Original(Positions[Vertex]),P=ToBlender(Original);
        FVector Final(P.X*(1.32+.10*FMath::Sin(P.Z*1.7))+.20*FMath::Sin(P.Z*1.45),
            P.Y*1.20+.65*P.Z+.12*FMath::Sin(P.Z*2.),.014+.080*P.Z+.025*FMath::Square(FMath::Sin(P.Z*3.)));
        const FVector MD=P-Mouth;
        const double MR=FMath::Sqrt(FMath::Square(MD.X/.30)+FMath::Square(MD.Y/.22)+FMath::Square(MD.Z/.28));
        Final=FMath::Lerp(Final,MouthAt+FVector(MD.X,C*MD.Y-S*MD.Z,S*MD.Y+C*MD.Z),1.-Ease((MR-.72)/.78));
        const FVector BD=P-Band;
        const double BR=FMath::Sqrt(FMath::Square(BD.X/.42)+FMath::Square(BD.Y/.37)+FMath::Square(BD.Z/.15));
        Final=FMath::Lerp(Final,BD+BandAt,1.-Ease((BR-.88)/.72));
        for(const FVector& Sac:Sacs)
        {
            const FVector D=P-Sac;
            Final.Z+=.11*FMath::Exp(-2.*(FMath::Square(D.X/.23)+FMath::Square(D.Y/.21)+FMath::Square(D.Z/.30)));
        }
        Final.Z=FMath::Max(.012,Final.Z);
        const double Height=FMath::Clamp(P.Z,0.,3.),Delay=.07+.16*Height+.08*Ease(P.X+.5);
        for(int32 I=0;I<3;++I)
        {
            const double Phase=I==2?1.:Ease((Times[I]-Delay)/(1.55+.12*Height));
            FVector Target=FMath::Lerp(P,Final,Phase);
            if(I<2){const double Sway=FMath::Sin(PI*Phase)*.13;Target.X+=Sway*FMath::Sin(P.Z*1.8);Target.Y-=Sway*.35;}
            Deltas[I][Vertex]=FVector3f(ToMesh(Target)-Original);
        }
    }
    // This is the same spatial field as author_soft_death_v06.py, applied to
    // the existing imported topology without a second high-density FBX parse.
    if(!SourceMesh->CommitMeshDescription(0))return false;
    SourceMesh->PostEditChange();SourceMesh->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}

bool ASpiralPillarM14::BuildSoftCorpsePhysics(USkeletalMesh* SourceMesh,UPhysicsAsset* CorpseAsset,
    const TArray<FVector>& BlenderPointsCm,const TArray<int32>& HullSizes)
{
#if WITH_EDITOR
    if(!SourceMesh||!CorpseAsset||HullSizes.IsEmpty())return false;
    const auto& Ref=SourceMesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    const int32 Base=Ref.FindBoneIndex(TEXT("base")),XBone=Ref.FindBoneIndex(TEXT("roottoe_00")),YBone=Ref.FindBoneIndex(TEXT("roottoe_02"));
    if(Base==INDEX_NONE||XBone==INDEX_NONE||YBone==INDEX_NONE)return false;
    const FVector X=(Frames[XBone].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    const FVector Y=(Frames[YBone].GetLocation()-Frames[Base].GetLocation()).GetSafeNormal2D();
    auto* Body=NewObject<USkeletalBodySetup>(CorpseAsset,NAME_None,RF_Transactional);
    Body->BoneName=TEXT("base");Body->PhysicsType=PhysType_Default;Body->CollisionTraceFlag=CTF_UseSimpleAsComplex;
    int32 Cursor=0;
    for(const int32 Count:HullSizes)
    {
        if(Count<4||Cursor+Count>BlenderPointsCm.Num())return false;
        FKConvexElem Hull;
        for(int32 I=0;I<Count;++I)
        {
            const FVector P=BlenderPointsCm[Cursor++];
            Hull.VertexData.Add(Frames[Base].InverseTransformPosition(X*P.X+Y*P.Y+FVector::UpVector*P.Z));
        }
        Hull.UpdateElemBox();Body->AggGeom.ConvexElems.Add(MoveTemp(Hull));
    }
    if(Cursor!=BlenderPointsCm.Num())return false;
    Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));Body->DefaultInstance.SetMassOverride(240.f);
    Body->DefaultInstance.LinearDamping=.25f;Body->DefaultInstance.AngularDamping=.9f;
    Body->DefaultInstance.bUseCCD=true;Body->DefaultInstance.PositionSolverIterationCount=12;Body->DefaultInstance.VelocitySolverIterationCount=4;
    Body->InvalidatePhysicsData();Body->CreatePhysicsMeshes();
    CorpseAsset->Modify();CorpseAsset->SkeletalBodySetups.Reset();CorpseAsset->ConstraintSetup.Reset();CorpseAsset->CollisionDisableTable.Reset();
    CorpseAsset->SkeletalBodySetups.Add(Body);CorpseAsset->UpdateBodySetupIndexMap();CorpseAsset->UpdateBoundsBodiesArray();CorpseAsset->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
