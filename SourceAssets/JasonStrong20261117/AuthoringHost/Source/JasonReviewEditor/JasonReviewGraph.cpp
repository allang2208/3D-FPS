#include "JasonReviewGraph.h"
#include "Modules/ModuleManager.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_LinkedInputPose.h"
#include "AnimGraphNode_BoneDrivenController.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "AssetCompilingManager.h"
#include "Animation/AnimCurveMetaData.h"
#include "EdGraph/EdGraphSchema.h"
#include "GameFramework/Actor.h"
IMPLEMENT_MODULE(FDefaultModuleImpl, JasonReviewEditor)

static UEdGraphPin* FirstPosePin(UEdGraphNode* Node, EEdGraphPinDirection Direction)
{
    for (auto* Pin : Node->Pins)
        if (Pin->Direction==Direction && Pin->PinType.PinCategory==TEXT("struct") && Pin->PinType.PinSubCategoryObject.IsValid() &&
            Pin->PinType.PinSubCategoryObject->GetName().Contains(TEXT("PoseLink"))) return Pin;
    return nullptr;
}

bool UJasonReviewGraph::AddDrivers(UAnimBlueprint* BP,const TArray<FName>& Bones,const TArray<FName>& Morphs,const TArray<int32>& Axes,const TArray<float>& Starts,const TArray<float>& Ends)
{
    if (!BP || !BP->GetPathName().Contains(TEXT("/R4_PoseRefined/")) || Bones.Num()!=4 || Morphs.Num()!=4 || Axes.Num()!=4 || Starts.Num()!=4 || Ends.Num()!=4) return false;
    UEdGraph* Graph=nullptr;
    for (UEdGraph* G:BP->FunctionGraphs) if (G->GetFName()==TEXT("AnimGraph")) Graph=G;
    if (!Graph) return false;
    TArray<UAnimGraphNode_Root*> Roots; Graph->GetNodesOfClass(Roots);
    if (Roots.Num()!=1) return false;
    UEdGraphPin* End=FirstPosePin(Roots[0],EGPD_Input);
    if (!End) return false;
    UEdGraphPin* Tail=End->LinkedTo.Num()==1?End->LinkedTo[0]:nullptr;
    if (!Tail)
    {
        TArray<UAnimGraphNode_LinkedInputPose*> Inputs;Graph->GetNodesOfClass(Inputs);
        if (!Inputs.Num())
        {
            FGraphNodeCreator<UAnimGraphNode_LinkedInputPose> Make(*Graph);
            auto* Node=Make.CreateNode();Node->NodePosX=-1600;Make.Finalize();Inputs.Add(Node);
        }
        Tail=FirstPosePin(Inputs[0],EGPD_Output);
    }
    if (!Tail) return false;
    End->BreakAllPinLinks();
    for (int32 Index=0;Index<4;++Index)
    {
        FGraphNodeCreator<UAnimGraphNode_BoneDrivenController> Make(*Graph);
        auto* Node=Make.CreateNode();
        Node->NodePosX=Roots[0]->NodePosX-1000+Index*220;
        Node->NodePosY=Roots[0]->NodePosY+260;
        auto& Driver=Node->Node;
        Driver.SourceBone.BoneName=Bones[Index];Driver.ParameterName=Morphs[Index];
        Driver.SourceComponent=static_cast<EComponentType::Type>(static_cast<int32>(EComponentType::RotationX)+Axes[Index]);
        Driver.DestinationMode=EDrivenDestinationMode::MorphTarget;
        Driver.bUseRange=true;Driver.RangeMin=Starts[Index];Driver.RangeMax=Ends[Index];
        Driver.RemappedMin=0;Driver.RemappedMax=1;Driver.Multiplier=1;
        Make.Finalize();
        auto* Input=FirstPosePin(Node,EGPD_Input);
        if (!Input || !Graph->GetSchema()->TryCreateConnection(Tail,Input)) return false;
        Tail=FirstPosePin(Node,EGPD_Output);if (!Tail) return false;
    }
    if (!Graph->GetSchema()->TryCreateConnection(Tail,End)) return false;
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
    FKismetEditorUtilities::CompileBlueprint(BP);
    return BP->Status!=BS_Error;
}

void UJasonReviewGraph::SetMeshMorphFlags(USkeletalMesh* Mesh,const TArray<FName>& Morphs)
{
    if (!Mesh || !Mesh->GetPathName().Contains(TEXT("/R4_PoseRefined/"))) return;
    auto* Meta=Mesh->GetAssetUserData<UAnimCurveMetaData>();
    if (!Meta) { Meta=NewObject<UAnimCurveMetaData>(Mesh); Mesh->AddAssetUserData(Meta); }
    for (auto Name:Morphs) { Meta->AddCurveMetaData(Name,false); Meta->SetCurveMetaDataMorphTarget(Name,true); }
    for (int32 LOD=1;LOD<Mesh->GetLODNum();++LOD)
        if (auto* Info=Mesh->GetLODInfo(LOD)) Info->ReductionSettings.bRemapMorphTargets=true;
    Mesh->MarkPackageDirty();
}

TArray<float> UJasonReviewGraph::SampleMorphs(USkeletalMesh* Mesh,UAnimSequence* Clip,float Time,const TArray<FName>& Morphs)
{
    TArray<float> Values;
    if (!Mesh||!Clip) return Values;
    FAssetCompilingManager::Get().FinishAllCompilation();
    auto Init=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateAISystem(false).CreateNavigation(false).ShouldSimulatePhysics(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Init);
    auto* Owner=World->SpawnActor<AActor>();
    auto* Body=NewObject<USkeletalMeshComponent>(Owner);Owner->AddInstanceComponent(Body);Owner->SetRootComponent(Body);
    Body->SetSkeletalMeshAsset(Mesh);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body->RegisterComponentWithWorld(World);Body->SetAnimationMode(EAnimationMode::AnimationSingleNode);
    Body->PlayAnimation(Clip,false);Body->SetPosition(Time,false);Body->TickAnimation(0,false);Body->RefreshBoneTransforms();
    if (auto* Post=Body->GetPostProcessInstance())
        for (auto Name:Morphs) Values.Add(Post->GetCurveValue(Name));
    for (auto Name:Morphs) {
        int32 Index=INDEX_NONE;Mesh->FindMorphTargetAndIndex(Name,Index);
        Values.Add(Body->MorphTargetWeights.IsValidIndex(Index)?Body->MorphTargetWeights[Index]:-1.f);
    }
    Owner->Destroy();World->DestroyWorld(false);return Values;
}
