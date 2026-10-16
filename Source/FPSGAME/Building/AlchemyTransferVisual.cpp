#include "PotionWorkbenchVisualComponent.h"
#include "AlchemyInteractionAssets.h"
#include "AlchemyBottlingMotion.h"
#include "AlchemyWorkbenchLayout.h"
#include "AlchemyManualComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SplineMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"

void UPotionWorkbenchVisualComponent::CreateInteractionParts()
{
    for(const TCHAR* Name:{TEXT("HeatControl"),TEXT("HeatKnob"),TEXT("ReagentTray"),TEXT("MortarHover"),TEXT("TransferRing")})
    {
        auto* C=NewObject<UStaticMeshComponent>(GetOwner());C->SetupAttachment(Original);
        C->SetStaticMesh(Cast<UStaticMesh>(AlchemyInteraction::Asset(*(FString(TEXT("SM_Alchemy"))+Name)).ResolveObject()));
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);C->SetCanEverAffectNavigation(false);
        C->SetMobility(EComponentMobility::Movable);C->RegisterComponent();Parts.Add(FName(Name),C);
    }
    Part(TEXT("HeatControl"))->SetRelativeLocation(AlchemyInteraction::HeatControl);
    Part(TEXT("HeatKnob"))->SetRelativeLocation(AlchemyInteraction::HeatControl+FVector(0,0,2.45));
    Part(TEXT("MortarHover"))->SetRelativeLocation(FVector(45,-50,95));
    Part(TEXT("MortarHover"))->SetRenderInMainPass(false);Part(TEXT("MortarHover"))->SetRenderInDepthPass(false);Part(TEXT("MortarHover"))->SetCastShadow(false);
    TransferMaterial=UMaterialInstanceDynamic::Create(Cast<UMaterialInterface>(AlchemyInteraction::Asset(TEXT("M_AlchemyTransferFluid")).ResolveObject()),this);
    BottlingMaterial=UMaterialInstanceDynamic::Create(Cast<UMaterialInterface>(AlchemyInteraction::BottlingAsset(TEXT("M_AlchemyBottlingFlow")).ResolveObject()),this);
    BottleMaterial=UMaterialInstanceDynamic::Create(Cast<UMaterialInterface>(AlchemyInteraction::BottlingAsset(TEXT("M_AlchemyVesselLiquid")).ResolveObject()),this);
    GrainMaterial=UMaterialInstanceDynamic::Create(Cast<UMaterialInterface>(AlchemyInteraction::Asset(TEXT("M_AlchemyTransferGrain")).ResolveObject()),this);
    Part(TEXT("DoseFill"))->SetMaterial(0,BottleMaterial);Part(TEXT("DoseFill"))->SetCastShadow(false);
    auto* LadleFill=NewObject<UStaticMeshComponent>(GetOwner());LadleFill->SetupAttachment(Part(TEXT("Ladle")));
    LadleFill->SetStaticMesh(Part(TEXT("DoseFill"))->GetStaticMesh());LadleFill->SetMaterial(0,BottleMaterial);
    LadleFill->SetMobility(EComponentMobility::Movable);LadleFill->SetCollisionEnabled(ECollisionEnabled::NoCollision);LadleFill->SetCastShadow(false);LadleFill->SetCanEverAffectNavigation(false);
    LadleFill->SetVisibility(false);LadleFill->RegisterComponent();Parts.Add(TEXT("LadleFill"),LadleFill);
    Part(TEXT("TransferRing"))->SetMaterial(0,TransferMaterial);Part(TEXT("TransferRing"))->SetCastShadow(false);
    Part(TEXT("TransferRing"))->SetVisibility(false);Part(TEXT("Stream"))->SetVisibility(false);
    for(int32 I=0;I<3;++I)
    {
        auto* C=NewObject<UStaticMeshComponent>(GetOwner());C->SetupAttachment(Original);C->SetMobility(EComponentMobility::Movable);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);C->SetCanEverAffectNavigation(false);C->RegisterComponent();C->SetVisibility(false);IngredientCaps.Add(C);
    }
    for(int32 I=0;I<8;++I)
    {
        auto* C=NewObject<USplineMeshComponent>(GetOwner());C->SetupAttachment(Original);C->SetMobility(EComponentMobility::Movable);
        C->SetStaticMesh(Part(TEXT("Stream"))->GetStaticMesh());C->SetForwardAxis(ESplineMeshAxis::Z,false);
        C->SetSplineUpDir(FVector::YAxisVector,false);C->SetMaterial(0,TransferMaterial);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);C->SetCanEverAffectNavigation(false);C->SetCastShadow(false);
        C->SetVisibility(false);C->RegisterComponent();FlowSegments.Add(C);
    }
    TransferDrops=NewObject<UInstancedStaticMeshComponent>(GetOwner());TransferDrops->SetupAttachment(Original);
    TransferDrops->SetCollisionEnabled(ECollisionEnabled::NoCollision);TransferDrops->SetCastShadow(false);TransferDrops->SetCanEverAffectNavigation(false);
    TransferDrops->RegisterComponent();TransferDrops->SetVisibility(false);
    // SetStaticMesh before AddInstance; switching between grain and water reuses the same bounded pool.
    TransferDrops->SetStaticMesh(Cast<UStaticMesh>(AlchemyInteraction::Asset(TEXT("SM_AlchemyTransferGrain")).ResolveObject()));
    for(int32 I=0;I<24;++I)TransferDrops->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector));
}
void UPotionWorkbenchVisualComponent::AnimateIngredients(float T,bool Pouring)
{
    for(int32 I=0;I<IngredientParts.Num();++I)
    {
        if(!IngredientRest.IsValidIndex(I)||!IngredientParts[I]->GetStaticMesh())continue;
        const FTransform& Rest=IngredientRest[I];FTransform Body=Rest,Cap=Rest;
        if(Pouring&&I==State.Ingredient)
        {
            // Open the selected original container first, then carry it by its body.
            const float Carry=AlchemyInteraction::Smooth((T-.38f)/.62f)*(1-AlchemyInteraction::Smooth((T-2.42f)/.68f));
            const float Tip=AlchemyInteraction::Smooth((T-.9f)/.25f)*(1-AlchemyInteraction::Smooth((T-2.16f)/.26f));
            const FQuat Q=FQuat(FVector::YAxisVector,FMath::DegreesToRadians(112.f)*Tip);
            const FVector MouthAtRest=Rest.TransformPosition(IngredientMouth[I]);
            FVector Mouth=FMath::Lerp(MouthAtRest,FVector(220,-103,131),Carry);
            Mouth.Z+=8.f*FMath::Sin(Carry*PI);
            Body=FTransform(Q,Mouth-Q.RotateVector(IngredientMouth[I]*Rest.GetScale3D()),Rest.GetScale3D());
            const float Open=AlchemyInteraction::Smooth(T/.24f)*(1-AlchemyInteraction::Smooth((T-3.1f)/.2f));
            const float Side=AlchemyInteraction::Smooth((T-.24f)/.14f)*(1-AlchemyInteraction::Smooth((T-2.9f)/.2f));
            const float Lift=FMath::Max(9.f,float(IngredientMouth[I].Z*Rest.GetScale3D().Z)+2.f);
            // The long extraction pipette clears the neck vertically before it moves aside.
            Cap=FTransform(FQuat(FVector::UpVector,Open*PI*1.5f),Rest.GetLocation()+FVector(-7*Side,-5*Side,Lift*Open),Rest.GetScale3D());
        }
        IngredientParts[I]->SetRelativeTransform(Body);IngredientCaps[I]->SetRelativeTransform(Cap);
    }
}
void UPotionWorkbenchVisualComponent::UpdateTransfer(float T,float SurfaceZ,bool Active)
{
    const bool Pouring=Active&&State.Tool==uint8(EAlchemyOp::Pour)&&IngredientParts.IsValidIndex(State.Ingredient)&&IngredientMouth.IsValidIndex(State.Ingredient);
    const bool Bottling=Active&&State.Tool==uint8(EAlchemyOp::Bottle);
    const bool Grain=Pouring&&IngredientGranular[State.Ingredient];
    const float Begin=Pouring?AlchemyInteraction::FlowStart:AlchemyBottling::FlowStart,EndTime=Pouring?AlchemyInteraction::FlowEnd:AlchemyBottling::FlowEnd;
    const float Flow=(Pouring||Bottling)?AlchemyInteraction::Smooth((T-Begin)/.18f)*(1-AlchemyInteraction::Smooth((T-(EndTime-.18f))/.18f)):0;
    FVector Start=FVector::ZeroVector,End=FVector::ZeroVector,Outlet(0,0,-1);
    if(Pouring)
    {
        const FTransform F=IngredientParts[State.Ingredient]->GetRelativeTransform();
        Start=F.TransformPosition(IngredientMouth[State.Ingredient]);Outlet=F.GetRotation().GetUpVector();
        End=FVector(225,-106,SurfaceZ+.04);
    }
    else if(Bottling)
    {
        Start=Part(TEXT("Ladle"))->GetRelativeTransform().TransformPosition(AlchemyBottling::Spout);
        End=Part(TEXT("Dose"))->GetRelativeTransform().TransformPosition(AlchemyBottling::Mouth-FVector(0,0,1.5));
        Outlet=FVector(0,0,-1);
    }
    const float Reach=AlchemyInteraction::Smooth((T-Begin)/.12f);
    const FVector ControlA=Start+Outlet*3,ControlB=End+FVector(0,0,FMath::Max(1.,(Start.Z-End.Z)*.35));
    auto Curve=[&](float U)
    {const float V=1-U;return V*V*V*Start+3*V*V*U*ControlA+3*V*U*U*ControlB+U*U*U*End+FVector(0,.08f*FMath::Square(FMath::Sin(PI*U))*FMath::Sin(T*12-U*4),0);};
    auto Tangent=[&](float U)
    {const float V=1-U,S=FMath::Sin(PI*U),C=FMath::Cos(PI*U);return 3*V*V*(ControlA-Start)+6*V*U*(ControlB-ControlA)+3*U*U*(End-ControlB)+FVector(0,.08f*(2*PI*S*C*FMath::Sin(T*12-U*4)-4*S*S*FMath::Cos(T*12-U*4)),0);};
    const bool Visible=Bottling?(T>Begin&&T<EndTime+AlchemyBottling::Flight):Flow>.002f;
    const bool Catalyst=Pouring&&IngredientParts[State.Ingredient]->GetStaticMesh()->GetFName()==FName(TEXT("SM_AlchemyCatalystOpen"));
    const FLinearColor Tint=Pouring?(State.Ingredient==0?FLinearColor(.2f,.47f,.62f):Catalyst?FLinearColor(.47f,.14f,.72f):Grain?FLinearColor(.13f,.53f,.76f):FLinearColor(.45f,.035f,.015f)):State.Color;
    TransferMaterial->SetVectorParameterValue(TEXT("PotionColor"),Tint);TransferMaterial->SetScalarParameterValue(TEXT("Flow"),FMath::Sqrt(Flow));
    BottlingMaterial->SetVectorParameterValue(TEXT("PotionColor"),State.Color);
    GrainMaterial->SetVectorParameterValue(TEXT("PotionColor"),Tint);BottleMaterial->SetVectorParameterValue(TEXT("PotionColor"),State.Color);
    for(int32 I=0;I<FlowSegments.Num();++I)
    {
        auto* C=FlowSegments[I].Get();auto* Material=Bottling?BottlingMaterial.Get():TransferMaterial.Get();
        if(C->GetMaterial(0)!=Material)C->SetMaterial(0,Material);
        const float Length=Bottling?1.f:Reach;
        const float A=Length*I/FlowSegments.Num(),B=Length*(I+1)/FlowSegments.Num(),Span=B-A;
        const float AtStart=Bottling?AlchemyBottling::Flow(T-A*AlchemyBottling::Flight):Flow;
        const float AtEnd=Bottling?AlchemyBottling::Flow(T-B*AlchemyBottling::Flight):Flow;
        const bool SegmentVisible=Visible&&!Grain&&FMath::Max(AtStart,AtEnd)>.002f;
        C->SetVisibility(SegmentVisible);if(!SegmentVisible)continue;
        // The stream starts at the lip and drains down to the mouth. Do not
        // fade the entire column at once, or hide the falling tail at cut-off.
        const float Radius=Bottling?1.6f:1.f;
        C->SetStartScale(FVector2D(Radius*FMath::Sqrt(FMath::Max(.0001f,AtStart))*(1-A*.22f)*(1+.06f*FMath::Sin(T*22-A*12))),false);
        C->SetEndScale(FVector2D(Radius*FMath::Sqrt(FMath::Max(.0001f,AtEnd))*(1-B*.22f)*(1+.06f*FMath::Sin(T*22-B*12))),false);
        C->SetStartAndEnd(Curve(A),Tangent(A)*Span,Curve(B),Tangent(B)*Span,true);
    }
    auto* DropMesh=Cast<UStaticMesh>((Grain?AlchemyInteraction::Asset(TEXT("SM_AlchemyTransferGrain")):FSoftObjectPath(TEXT("/Engine/BasicShapes/Sphere.Sphere"))).ResolveObject());
    if(TransferDrops->GetStaticMesh()!=DropMesh)TransferDrops->SetStaticMesh(DropMesh);
    TransferDrops->SetMaterial(0,Grain?GrainMaterial:Bottling?BottlingMaterial:TransferMaterial);TransferDrops->SetVisibility(Visible);
    if(Visible)for(int32 I=0;I<24;++I)
    {
        const float Phase=FMath::Frac((T-Begin)*(Grain?2.3f:3.2f)+I*.618034f);
        const float Angle=I*2.39996f;FVector P;FVector Size;
        if(Bottling)
        {
            P=End;Size=FVector::ZeroVector;
            if(I<4)
            {
                const float Age=(T-(EndTime-.12f+I*.04f))/AlchemyBottling::Flight;
                if(Age>=0&&Age<=1){P=Curve(Age*Age);Size=FVector(.0024,.0024,.0065);}
            }
            else if(I<12&&T>Begin+AlchemyBottling::Flight)
            {
                // Tiny impact beads stay inside the open neck, not outside the bottle.
                P=End+FVector(.28f*FMath::Cos(Angle),.28f*FMath::Sin(Angle),.35f*FMath::Sin(PI*Phase));
                Size=FVector(.0015f*AlchemyBottling::Flow(T-AlchemyBottling::Flight)*(1-Phase));
            }
        }
        else if(Grain)
        {P=Curve(Phase*Reach)+FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*(.12f+Phase*.8f);Size=FVector((.65f+(I%4)*.2f)*Flow);}
        else
        {const float R=Phase*(Bottling?.6f:2.f);P=End+FVector(R*FMath::Cos(Angle),R*FMath::Sin(Angle),FMath::Sin(PI*Phase)*(Bottling?.5f:1.5f));Size=FVector(.0025f*Flow*(1-Phase));}
        TransferDrops->UpdateInstanceTransform(I,FTransform(FRotator(T*80+I*21,I*57,T*100),P,Size),false,false,true);
    }
    if(Visible)TransferDrops->MarkRenderStateDirty();
    auto* Ring=Part(TEXT("TransferRing"));Ring->SetVisibility(Visible&&Pouring&&!Grain&&Reach>.95f);
    if(Visible)
    {
        const float Wave=FMath::Frac((T-Begin)*2.1f);Ring->SetRelativeLocation(End+FVector(0,0,.035));Ring->SetRelativeScale3D(FVector(.4f+Wave*2.6f,.4f+Wave*2.6f,.4f*(1-Wave)));
        if(Pouring&&Reach>.95f&&ImpactSerial!=State.ActionSerial&&WaterMaterial)
        {WaterMaterial->SetScalarParameterValue(TEXT("QuenchTime"),GetWorld()->GetTimeSeconds());WaterMaterial->SetVectorParameterValue(TEXT("QuenchPoint"),FLinearColor(End.X-225,End.Y+106,0));ImpactSerial=State.ActionSerial;}
    }
    // Scale from the vessel's fixed bottom; never pull the fill down through the glass base.
    const float Fill=Bottling?AlchemyBottling::Received(T):0.f;
    Part(TEXT("DoseFill"))->SetVisibility(Bottling&&Fill>.001f);
    Part(TEXT("DoseFill"))->SetRelativeScale3D(FVector(1,1,FMath::Max(.001f,Fill)));
    Part(TEXT("DoseFill"))->SetRelativeLocation(FVector(0,0,-4.4f*(1-Fill)));
    const float Scoop=Bottling?AlchemyInteraction::Smooth((T-AlchemyBottling::DipAt)/(AlchemyBottling::LiftAt-AlchemyBottling::DipAt))*(1-AlchemyBottling::Emitted(T)):0.f;
    auto* LadleFill=Part(TEXT("LadleFill"));LadleFill->SetVisibility(Scoop>.001f);
    const float Tip=Bottling?AlchemyBottling::Tilt(T):0.f;
    const FTransform Bowl=Part(TEXT("Ladle"))->GetRelativeTransform();
    FVector Level=Bowl.TransformPosition(FVector(-3.f*Tip,0,-19.3f-.6f*(1-Scoop)));
    Level.Z=FMath::Min(Level.Z,Bowl.TransformPosition(AlchemyBottling::Spout).Z-.08);
    // Keep the exposed liquid level while the bowl tilts; the shrinking pool
    // moves toward the outlet rather than rotating a solid disk with the spoon.
    LadleFill->SetRelativeLocationAndRotation(Bowl.InverseTransformPosition(Level),Bowl.GetRotation().Inverse());
    const float Radius=1.36f*FMath::Sqrt(Scoop);
    LadleFill->SetRelativeScale3D(FVector(Radius*(1-.78f*Tip),Radius*(1-.25f*Tip),.035));
}
void UPotionWorkbenchVisualComponent::SetHoverTarget(const FAlchemyTableHit& Hit,bool Enabled)
{
    HoverSources.Reset();
    auto Add=[this](UStaticMeshComponent* C){if(C&&C->IsVisible()&&C->GetStaticMesh())HoverSources.Add(C);};
    if(Enabled)switch(Hit.Object)
    {
        case EAlchemyTableObject::Ingredient:if(IngredientParts.IsValidIndex(Hit.Ingredient)){Add(IngredientParts[Hit.Ingredient]);Add(IngredientCaps[Hit.Ingredient]);}break;
        case EAlchemyTableObject::Book:if(Manual)for(const auto& C:Manual->Meshes())Add(C);break;
        case EAlchemyTableObject::Heater:Add(Part(TEXT("HeatControl")));Add(Part(TEXT("HeatKnob")));break;
        case EAlchemyTableObject::Mortar:Add(Part(TEXT("MortarHover")));Add(Part(TEXT("Pestle")));break;
        case EAlchemyTableObject::Liquid:Add(Part(TEXT("Liquid")));break;
        case EAlchemyTableObject::Stirrer:Add(Part(TEXT("Stirrer")));break;
        case EAlchemyTableObject::Hourglass:Add(Part(TEXT("Hourglass")));break;
        case EAlchemyTableObject::Bottle:Add(Part(TEXT("Dose")));Add(Part(TEXT("Ladle")));break;
        default:break;
    }
    UpdateHoverProxies();
}
void UPotionWorkbenchVisualComponent::UpdateHoverProxies()
{
    const int32 Count=FMath::Min(HoverSources.Num(),16);
    while(HoverProxies.Num()<Count)
    {
        auto* C=NewObject<UStaticMeshComponent>(GetOwner());C->SetupAttachment(Original);C->SetMobility(EComponentMobility::Movable);
        C->SetRenderInMainPass(false);C->SetRenderInDepthPass(false);C->SetCastShadow(false);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        C->SetGenerateOverlapEvents(false);C->SetCanEverAffectNavigation(false);C->SetCustomDepthStencilValue(AlchemyInteraction::HoverStencil);C->RegisterComponent();HoverProxies.Add(C);
    }
    auto* Opaque=Cast<UMaterialInterface>(FSoftObjectPath(TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")).ResolveObject());
    for(int32 I=0;I<HoverProxies.Num();++I)
    {
        auto* Proxy=HoverProxies[I].Get();auto* Source=I<Count?HoverSources[I].Get():nullptr;
        const bool Show=Source&&Source->IsVisible();Proxy->SetRenderCustomDepth(Show);Proxy->SetVisibility(Show);
        if(!Show)continue;
        if(Proxy->GetStaticMesh()!=Source->GetStaticMesh())
        {Proxy->SetStaticMesh(Source->GetStaticMesh());for(int32 J=0;J<Proxy->GetNumMaterials();++J)Proxy->SetMaterial(J,Opaque);}
        Proxy->SetWorldTransform(Source->GetComponentTransform());
    }
}
