#include "ProductionToolComponent.h"
#include "ProductionBluntCombo.h"
#include "WarhammerUppercutMotion.h"
#include "WarhammerQuickCombatMotion.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace
{
UE::Geometry::FDynamicMesh3 MakeWarhammerRiftRibbon()
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    auto* UV=Mesh.Attributes()->PrimaryUV();auto* Normals=Mesh.Attributes()->PrimaryNormals();
    for(int32 Band=0;Band<2;++Band)
    {
        const int32 Base=Band*WarhammerRift::Stations*2;
        for(int32 I=0;I<WarhammerRift::Stations;++I)for(int32 Side=0;Side<2;++Side)
        {
            Mesh.AppendVertex(FVector3d(0,0,0));UV->AppendElement(FVector2f(float(I)/(WarhammerRift::Stations-1),float(Side)));
            Normals->AppendElement(FVector3f(0,0,1));
        }
        for(int32 I=0;I<WarhammerRift::Stations-1;++I)
        {
            const int32 V=Base+I*2;
            for(const FIndex3i T:{FIndex3i(V,V+2,V+1),FIndex3i(V+1,V+2,V+3)})
            {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
        }
    }
    return Mesh;
}
}

void UProductionToolComponent::FeedWarhammerRift(FName Clip,float SourceSeconds)
{
    if(Kind!=TEXT("warhammer")||!Character.IsValid()||!Character->IsLocallyControlled()||!CanPresent())return;
    auto* Head=WarhammerRiftHead.Get();
    if(!Viewmodel||!Viewmodel->IsVisible()||Viewmodel->bHiddenInGame)return;
    const bool ModularHead=Head&&Head->GetStaticMesh()&&Head->IsVisible()&&!Head->bHiddenInGame;
    if(ModularHead)Head->UpdateComponentToWorld();
    FTransform Frame=ModularHead?Head->GetComponentTransform():Viewmodel->GetSocketTransform(TEXT("WPN_root"));
    // Native WPN_root coordinates are metres with the imported 100x scale.
    if(!ModularHead)Frame.SetScale3D(Frame.GetScale3D()/100.f);
    int32 Key=INDEX_NONE;float Start=0.f,End=0.f,Clock=SourceSeconds,Strength=.095f;bool Crossed=false;
    if(Clip==TEXT("Uppercut")&&bBluntUppercut)
    {Key=10;Start=1.f;End=1.125f;Strength=.13f;}
    else if(Clip==TEXT("Whirlwind")&&bBluntWhirlwind)
    {
        Clock=BluntWhirlwindTime;Start=BluntWhirlwindTuning.ReadySeconds;
        End=Start+BluntWhirlwindTuning.SpinSeconds;Strength=.105f;
        const float Turn=(Clock-Start)/FMath::Max(.01f,BluntWhirlwindTuning.SpinSeconds)*BluntWhirlwindTuning.TurnDegrees/360.f;
        Key=20+FMath::Max(0,FMath::FloorToInt(Turn));
    }
    else if(Clip==TEXT("QuickCombat")&&IsQuickCombatActive())
    {Key=30;Start=.09f;End=.175f;Strength=.085f;Crossed=true;}
    else if(Clip==TEXT("ActiveHitRecover")&&!bBluntHeavy&&bHitConfirmed&&Elapsed>=0.f)
    {Key=BluntStage;Clock=ProductionBluntCombo::ContactSeconds+SourceSeconds;Start=ProductionBluntCombo::ContactSeconds;End=Start+.04f;}
    else if(Clip==TEXT("ActiveSwing")&&Elapsed>=0.f)
    {
        if(UsesFinalTollHeavy())
        {
            const bool Up=SourceSeconds>=FinalTollHeavy::SecondStart;
            Key=Up?41:40;Start=Up?FinalTollHeavy::SecondStart:0.f;End=Up?FinalTollHeavy::FollowEnd:.15f;Strength=.14f;
        }
        else if(bBluntHeavy){Key=bBluntSprintAttack?51:50;Start=0.f;End=WarhammerHeavy::Contact+.065f;Strength=.15f;}
        else {Key=BluntStage;Start=ProductionBluntCombo::Apex(BluntStage);End=ProductionBluntCombo::Turn(BluntStage);}
    }
    const bool ContactHandoff=Clip==TEXT("ActiveHitRecover")&&WarhammerRiftKey==Key;
    const bool Same=(WarhammerRiftPreviousMotion.Get()==CurrentMotion||ContactHandoff)&&Clock>=WarhammerRiftPreviousSeconds;
    const bool CrossedEnd=Same&&WarhammerRiftPreviousSeconds<End&&Clock>End;
    const bool Emit=Key!=INDEX_NONE&&Clock>=Start&&(Clock<=End||CrossedEnd);
    if(!Emit)
    {
        if(WarhammerRiftActive!=INDEX_NONE)WarhammerRiftTrails[WarhammerRiftActive].FadeAge=0.f;
        WarhammerRiftActive=INDEX_NONE;WarhammerRiftKey=INDEX_NONE;
    }
    else
    {
        auto* Material=Cast<UMaterialInterface>(FSoftObjectPath(WarhammerRift::Material).ResolveObject());
        if(!Material)return;
        if(WarhammerRiftMeshes.IsEmpty())
        {
            for(int32 I=0;I<WarhammerRift::PoolSize;++I)
            {
                auto* Mesh=NewObject<UDynamicMeshComponent>(GetOwner());
                Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetGenerateOverlapEvents(false);
                Mesh->SetCanEverAffectNavigation(false);Mesh->SetCastShadow(false);Mesh->SetReceivesDecals(false);
                Mesh->SetOnlyOwnerSee(true);Mesh->bVisibleInRayTracing=false;Mesh->bAffectDistanceFieldLighting=false;
                Mesh->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);Mesh->RegisterComponent();
                Mesh->SetMesh(MakeWarhammerRiftRibbon());Mesh->SetVisibility(false);
                auto* MID=UMaterialInstanceDynamic::Create(Material,this);Mesh->SetMaterial(0,MID);
                WarhammerRiftMeshes.Add(Mesh);WarhammerRiftMIDs.Add(MID);
            }
        }
        if(WarhammerRiftActive==INDEX_NONE||WarhammerRiftKey!=Key||!Same)
        {
            if(WarhammerRiftActive!=INDEX_NONE)WarhammerRiftTrails[WarhammerRiftActive].FadeAge=0.f;
            WarhammerRiftActive=WarhammerRiftNext;WarhammerRiftNext=(WarhammerRiftNext+1)%WarhammerRift::PoolSize;
            auto& T=WarhammerRiftTrails[WarhammerRiftActive];T.Reset();T.Strength=Strength;T.bCrossed=Crossed;
            T.Drift=Camera?Camera->GetForwardVector()*85.f:FVector::ZeroVector;
            WarhammerRiftKey=Key;
        }
        auto& Trail=WarhammerRiftTrails[WarhammerRiftActive];
        const FBox Bounds=ModularHead?Head->GetStaticMesh()->GetBoundingBox():FBox(FVector(-17,-6,84),FVector(17,6,106));
        const FVector C=Bounds.GetCenter(),E=Bounds.GetExtent();
        const float Span=FMath::Max(8.f,E.Z+3.f);
        const FVector Inner=C-FVector(0,0,Span),Outer=C+FVector(0,0,Span);
        const FVector Across=FVector(FMath::Max(6.f,E.X*.65f),0,0);
        const float Step=Same?FMath::Clamp(Clock-WarhammerRiftPreviousSeconds,.00001f,10.f):1.f;
        const float From=Same?FMath::Clamp((Start-WarhammerRiftPreviousSeconds)/Step,0.f,1.f):1.f;
        const float To=Same?FMath::Clamp((End-WarhammerRiftPreviousSeconds)/Step,0.f,1.f):1.f;
        const int32 Divisions=Same?FMath::Clamp(FMath::CeilToInt(FVector::Distance(Frame.GetLocation(),WarhammerRiftPreviousFrame.GetLocation())/4.f),1,12):1;
        for(int32 I=0;I<=Divisions;++I)
        {
            FTransform Pose=Frame;if(Same)Pose.Blend(WarhammerRiftPreviousFrame,Frame,FMath::Lerp(From,To,float(I)/Divisions));
            const FVector A=Pose.TransformPosition(Inner),B=Pose.TransformPosition(Outer);
            if(!Trail.Inner.IsEmpty()&&FVector::DistSquared(B,Trail.Outer.Last())<4.f&&FVector::DistSquared(A,Trail.Inner.Last())<4.f)continue;
            if(!Trail.Inner.IsEmpty()&&FVector::DistSquared(B,Trail.Outer.Last())>FMath::Square(250.f))Trail.Reset();
            if(Trail.Inner.Num()==WarhammerRift::Stations)
            {
                for(auto* Points:{&Trail.Inner,&Trail.Outer,&Trail.CrossInner,&Trail.CrossOuter})
                {for(int32 J=0;J<WarhammerRift::Stations/2;++J)(*Points)[J]=(*Points)[J*2];Points->SetNum(WarhammerRift::Stations/2,EAllowShrinking::No);}
            }
            Trail.Inner.Add(A);Trail.Outer.Add(B);Trail.CrossInner.Add(Pose.TransformPosition(C-Across));Trail.CrossOuter.Add(Pose.TransformPosition(C+Across));Trail.bDirty=true;
        }
        if(Clock>End){Trail.FadeAge=0.f;WarhammerRiftActive=INDEX_NONE;WarhammerRiftKey=INDEX_NONE;}
    }
    WarhammerRiftPreviousMotion=CurrentMotion;WarhammerRiftPreviousSeconds=Clock;WarhammerRiftPreviousFrame=Frame;
}

void UProductionToolComponent::TickWarhammerRifts(float Delta,bool Present)
{
    if(!Present||Kind!=TEXT("warhammer")){ClearWarhammerRifts();return;}
    WarhammerRiftHeadRefresh-=Delta;
    if(WarhammerRiftHeadRefresh<=0.f||!WarhammerRiftHead.IsValid())
    {
        WarhammerRiftHeadRefresh=.25f;WarhammerRiftHead.Reset();
        TInlineComponentArray<UStaticMeshComponent*> Parts(GetOwner());
        for(auto* Part:Parts)if(Part->ComponentHasTag(TEXT("SwordSlot=hammer_heads"))&&Part->GetStaticMesh()&&Part->IsVisible()&&!Part->bHiddenInGame&&!Part->bOwnerNoSee)
            {WarhammerRiftHead=Part;break;}
    }
    for(int32 Slot=0;Slot<WarhammerRiftMeshes.Num();++Slot)
    {
        auto& Trail=WarhammerRiftTrails[Slot];auto* Mesh=WarhammerRiftMeshes[Slot].Get();auto* MID=WarhammerRiftMIDs[Slot].Get();
        if(Trail.FadeAge>=0.f)Trail.FadeAge+=Delta;
        const bool Visible=Trail.Inner.Num()>1&&Trail.FadeAge<.25f;Mesh->SetVisibility(Visible);if(!Visible)continue;
        if(Trail.bDirty)
        {
            Mesh->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& Data)
            {
                auto* UV=Data.Attributes()->PrimaryUV();const int32 Last=Trail.Inner.Num()-1;
                for(int32 Band=0;Band<2;++Band)for(int32 I=0;I<WarhammerRift::Stations;++I)
                {
                    const int32 P=FMath::Min(I,Last),Base=(Band*WarhammerRift::Stations+I)*2;
                    const FVector A=Band&&Trail.bCrossed?Trail.CrossInner[P]:Trail.Inner[P];
                    const FVector B=Band?(Trail.bCrossed?Trail.CrossOuter[P]:A):Trail.Outer[P];
                    Data.SetVertex(Base,FVector3d(A));Data.SetVertex(Base+1,FVector3d(B));
                    UV->SetElement(Base,FVector2f(float(P)/Last,0));UV->SetElement(Base+1,FVector2f(float(P)/Last,1));
                }
            },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions|EDynamicMeshAttributeChangeFlags::UVs);
            Trail.bDirty=false;
        }
        const float Fade=1.f-FMath::SmoothStep(0.f,.25f,FMath::Max(0.f,Trail.FadeAge));
        MID->SetScalarParameterValue(TEXT("RiftStrength"),Trail.Strength);MID->SetScalarParameterValue(TEXT("RiftFade"),Fade);
        MID->SetScalarParameterValue(TEXT("SweepProgress"),1.06f);
        Mesh->SetWorldLocation(Trail.Drift*FMath::Max(0.f,Trail.FadeAge));
    }
}

void UProductionToolComponent::ClearWarhammerRifts(bool Destroy)
{
    for(const auto& Mesh:WarhammerRiftMeshes)if(Mesh){Mesh->SetVisibility(false);if(Destroy)Mesh->DestroyComponent();}
    for(auto& Trail:WarhammerRiftTrails)Trail.Reset();
    WarhammerRiftActive=WarhammerRiftKey=INDEX_NONE;WarhammerRiftPreviousMotion.Reset();WarhammerRiftPreviousSeconds=-1.f;
    if(Destroy){WarhammerRiftMeshes.Reset();WarhammerRiftMIDs.Reset();WarhammerRiftHead.Reset();}
}
