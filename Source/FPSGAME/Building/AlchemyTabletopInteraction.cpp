#include "PotionWorkbenchVisualComponent.h"
#include "AlchemySystem.h"
#include "AlchemyInteractionAssets.h"
#include "AlchemyManualComponent.h"
#include "AlchemyWorkbenchLayout.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

namespace
{
bool RayBox(const FVector& Origin,const FVector& Direction,const FBox& Box,double& Enter)
{
    Enter=0;double Exit=1000;
    for(int32 Axis=0;Axis<3;++Axis)
    {
        if(FMath::Abs(Direction[Axis])<1.e-8){if(Origin[Axis]<Box.Min[Axis]||Origin[Axis]>Box.Max[Axis])return false;continue;}
        double A=(Box.Min[Axis]-Origin[Axis])/Direction[Axis],B=(Box.Max[Axis]-Origin[Axis])/Direction[Axis];
        if(A>B)Swap(A,B);Enter=FMath::Max(Enter,A);Exit=FMath::Min(Exit,B);if(Exit<Enter)return false;
    }
    return Exit>=0&&Enter<1000;
}
}
void UPotionWorkbenchVisualComponent::UpdateIngredients()
{
    if(!bReady)return;
    if(!IsValid(State.Operator))
    {
        // A resumed/saved batch may share the recipe ID but have a different accepted snapshot.
        IngredientRecipe=NAME_None;IngredientJobId.Reset();
        for(const auto& C:IngredientParts)C->SetVisibility(false);
        for(const auto& C:IngredientCaps)C->SetVisibility(false);
        return;
    }
    if(IngredientRecipe!=State.Recipe||IngredientJobId!=State.JobId)
    {
        IngredientRecipe=State.Recipe;IngredientJobId=State.JobId;
        const auto* System=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelAlchemySystem>();
        const auto* Recipe=System?(System->Recipe()&&System->Recipe()->Id==State.Recipe?System->Recipe():System->Find(State.Recipe)):nullptr;
        UnitFill=0;if(Recipe){int32 Units=0;for(const auto& Input:Recipe->Inputs)Units+=Input.Count;UnitFill=.85f/FMath::Max(1,Units);}
        IngredientRest.SetNum(IngredientParts.Num());IngredientMouth.SetNum(IngredientParts.Num());IngredientGranular.SetNum(IngredientParts.Num());
        for(int32 I=0;I<IngredientParts.Num();++I)
        {
            auto* C=IngredientParts[I].Get();const auto* Path=Recipe&&Recipe->Inputs.IsValidIndex(I)?IngredientAssets.Find(Recipe->Inputs[I].Item):nullptr;
            auto* Mesh=Path?Cast<UStaticMesh>(Path->ResolveObject()):nullptr;C->SetStaticMesh(Mesh);
            const auto* Reagent=Recipe&&Recipe->Inputs.IsValidIndex(I)?AlchemyInteraction::Reagent(Recipe->Inputs[I].Item):nullptr;
            IngredientCaps[I]->SetStaticMesh(Reagent?Cast<UStaticMesh>(AlchemyInteraction::ReagentAsset(*Reagent,TEXT("Cap")).ResolveObject()):nullptr);if(!Mesh)continue;
            const FBox Box=Mesh->GetBoundingBox();const FVector Size=Box.GetSize();
            const double Scale=FMath::Min(15./FMath::Max(1.,Reagent?double(Reagent->Height):Size.Z),9./FMath::Max(1.,FMath::Max(Size.X,Size.Y)));
            const FVector Bottom=Reagent?FVector::ZeroVector:FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
            IngredientRest[I]=FTransform(FQuat::Identity,AlchemyTabletop::Ingredients[I]-Bottom*Scale,FVector(Scale));
            IngredientMouth[I]=FVector(0,0,Reagent?Reagent->Mouth:Box.Max.Z);IngredientGranular[I]=Reagent&&Reagent->Granular;
            C->SetRelativeTransform(IngredientRest[I]);IngredientCaps[I]->SetRelativeTransform(IngredientRest[I]);
        }
    }
    for(const auto& C:IngredientParts)C->SetVisibility(IsValid(State.Operator)&&C->GetStaticMesh()!=nullptr);
    for(const auto& C:IngredientCaps)C->SetVisibility(IsValid(State.Operator)&&C->GetStaticMesh()!=nullptr);
}
FTransform UPotionWorkbenchVisualComponent::StirFrame() const
{
    const auto* Water=Part(TEXT("Liquid"));return Water?Water->GetComponentTransform():FTransform::Identity;
}
bool UPotionWorkbenchVisualComponent::StirPoint(const FVector& RayOrigin,const FVector& RayDirection,FVector& LocalPoint) const
{
    const auto* Water=Part(TEXT("Liquid"));if(!bReady||!Original||!Water||!Water->IsVisible())return false;
    const FTransform Frame=Original->GetComponentTransform();const FVector Origin=Frame.InverseTransformPosition(RayOrigin),Direction=Frame.InverseTransformVector(RayDirection);
    if(Direction.Z>=-1.e-6)return false;const double T=(Water->GetRelativeLocation().Z-Origin.Z)/Direction.Z;if(T<0||T>1000)return false;
    LocalPoint=Origin+Direction*T;const FVector Center=Water->GetRelativeLocation();
    const double Radius=FMath::Min(21.,21.*Water->GetRelativeScale3D().X);
    return FVector::DistSquared2D(LocalPoint,Center)<=Radius*Radius;
}
FAlchemyTableHit UPotionWorkbenchVisualComponent::TraceTabletop(const FVector& RayOrigin,const FVector& RayDirection) const
{
    FAlchemyTableHit Hit;if(!bReady||!Original||!IsValid(State.Operator))return Hit;
    double Nearest=1000;
    auto Pick=[&](EAlchemyTableObject Object,int32 Index,const FTransform& Frame,const FBox& Box)
    {
        double T;if(!RayBox(Frame.InverseTransformPosition(RayOrigin),Frame.InverseTransformVector(RayDirection),Box,T)||T>=Nearest)return;
        Nearest=T;Hit={Object,Index,RayOrigin+RayDirection*T};
    };
    auto Mesh=[&](EAlchemyTableObject Object,const UStaticMeshComponent* C,int32 Index=INDEX_NONE)
    {if(C&&C->IsVisible()&&C->GetStaticMesh())Pick(Object,Index,C->GetComponentTransform(),C->GetStaticMesh()->GetBoundingBox());};
    for(int32 I=0;I<IngredientParts.Num();++I){Mesh(EAlchemyTableObject::Ingredient,IngredientParts[I],I);Mesh(EAlchemyTableObject::Ingredient,IngredientCaps[I],I);}
    Mesh(EAlchemyTableObject::Stirrer,Part(TEXT("Stirrer")));Mesh(EAlchemyTableObject::Hourglass,Part(TEXT("Hourglass")));
    Mesh(EAlchemyTableObject::Bottle,Part(TEXT("Dose")));Mesh(EAlchemyTableObject::Bottle,Part(TEXT("Ladle")));
    const FTransform Frame=Original->GetComponentTransform();
    if(Manual)for(const auto& C:Manual->Meshes())Mesh(EAlchemyTableObject::Book,C);
    Mesh(EAlchemyTableObject::Mortar,Part(TEXT("MortarHover")));Mesh(EAlchemyTableObject::Mortar,Part(TEXT("Pestle")));
    Mesh(EAlchemyTableObject::Heater,Part(TEXT("HeatControl")));Mesh(EAlchemyTableObject::Heater,Part(TEXT("HeatKnob")));
    Pick(EAlchemyTableObject::Decoration,INDEX_NONE,Frame,FBox(FVector(65,-19,99),FVector(190,-3,143)));
    FVector Point;if(StirPoint(RayOrigin,RayDirection,Point))
    {
        const FVector World=Frame.TransformPosition(Point);const double T=FVector::DotProduct(World-RayOrigin,RayDirection);
        if(T<Nearest)Hit={EAlchemyTableObject::Liquid,INDEX_NONE,World};
    }
    return Hit;
}
