#include "EnhancementDisplayAuditCommandlet.h"
#include "ColdSteelPickup.h"
#include "ColdSteelPickupStudio.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "../Weapons/GunsmithSystem.h"
#include "../FPSGAMECharacter.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"

int32 UEnhancementDisplayAuditCommandlet::Main(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Profile=TEXT("DisplayAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("EnhancementDisplayAudit -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("EnhancementDisplayAuditWorld"));
    FCommandLine::Set(*Original);
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    auto* Enhancement=GI->GetSubsystem<UColdSteelEnhancementSystem>();auto* Gunsmith=GI->GetSubsystem<UGunsmithSystem>();
    ON_SCOPE_EXIT {GI->Shutdown();if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}GI->RemoveFromRoot();};
    if(!World||!Model||!Enhancement||!Gunsmith||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 2;
    // A commandlet has no frame loop to dispatch the normal next-frame stream
    // delegates. Run them immediately in this isolated process, and restore it.
    auto* DelegateDelay=IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"));
    const int32 PreviousDelay=DelegateDelay?DelegateDelay->GetInt():1;
    if(DelegateDelay)DelegateDelay->Set(0,ECVF_SetByCode);
    ON_SCOPE_EXIT {if(DelegateDelay)DelegateDelay->Set(PreviousDelay,ECVF_SetByCode);};
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0,Definitions=0,Variants=0;
    const auto Inspect=[&](const FColdSteelItem& Item,const FString& Case)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("definition"),Item.Definition);Row->SetStringField(TEXT("case"),Case);
        TArray<TSharedPtr<FJsonValue>> Errors;
        const auto Check=[&](bool Pass,const TCHAR* Message){if(!Pass)Errors.Add(MakeShared<FJsonValueString>(Message));};
        FActorSpawnParameters Spawn;Spawn.ObjectFlags=RF_Transient;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
#if WITH_EDITOR
        Spawn.bTemporaryEditorActor=true;
#endif
        auto* Display=World->SpawnActor<AColdSteelPickup>(Spawn);Check(Display!=nullptr,TEXT("spawn failed"));
        if(Display)
        {
            Check(Display->InitializeWorkbenchDisplay(Item),TEXT("unsupported or failed display assembly"));
            // Offline audit only; never add a synchronous wait to the runtime path.
            if(Display->StaffLoad)Check(Display->StaffLoad->WaitUntilComplete(30.f)==EAsyncPackageState::Complete,TEXT("staff/bow stream timed out"));
            if(Display->ProductionToolLoad)Check(Display->ProductionToolLoad->WaitUntilComplete(30.f)==EAsyncPackageState::Complete,TEXT("tool stream timed out"));
            Check(Display->IsWorkbenchDisplayReady(),TEXT("display is not ready"));
            Check(!Display->GetActorEnableCollision()&&!Display->Body->IsSimulatingPhysics(),TEXT("display owns collision/physics"));
            const FVector Extent=Display->Body->GetUnscaledBoxExtent();
            Check(!Extent.ContainsNaN()&&Extent.GetMin()>0&&Extent.GetMax()<10000,TEXT("invalid display envelope"));
            Row->SetStringField(TEXT("extent_cm"),Extent.ToString());
            FBox Geometry(ForceInit);int32 VisibleParts=0;double PoseError=0;
            TInlineComponentArray<UMeshComponent*> Components(Display);
            for(auto* C:Components)
            {
                if(!C->IsVisible())continue;
                const FTransform Local=C->GetComponentTransform().GetRelativeTransform(Display->GetActorTransform());
                Check(!Local.ContainsNaN(),TEXT("non-finite component transform"));
                if(auto* Static=Cast<UStaticMeshComponent>(C);Static&&Static->GetStaticMesh())
                {++VisibleParts;Geometry+=Static->GetStaticMesh()->GetBoundingBox().TransformBy(Local);}
                else if(auto* Skin=Cast<USkinnedMeshComponent>(C);Skin&&Skin->GetSkinnedAsset())
                {
                    ++VisibleParts;
                    if(Skin!=Display->Weapon){Geometry+=Skin->CalcBounds(Local).GetBox();continue;}
                    bool Created=false;auto* Rig=GI->GetSubsystem<UColdSteelPickupStudio>()->Acquire(Item.Definition,Created);
                    auto* Source=Rig?Rig->AKMViewmodel.Get():nullptr;Check(Source&&!Created,TEXT("source rig missing"));
                    if(Source)
                    {
                        const auto& A=Skin->GetComponentSpaceTransforms();const auto& B=Source->GetComponentSpaceTransforms();
                        Check(A.Num()==B.Num(),TEXT("bone count differs"));
                        bool PoseMatches=A.Num()==B.Num();
                        for(int32 N=0;N<FMath::Min(A.Num(),B.Num());++N)
                        {PoseError=FMath::Max(PoseError,FVector::Distance(A[N].GetLocation(),B[N].GetLocation()));PoseMatches&=A[N].Equals(B[N],.001f);}
                        Check(PoseMatches,TEXT("frozen pose differs from sampled source"));
                        Check(Skin->BoundsScale>=Source->BoundsScale,TEXT("source culling bounds lost"));
                        Check(!Skin->IsComponentTickEnabled(),TEXT("frozen gun still ticks"));
                        const auto* Render=Source->GetSkeletalMeshAsset()->GetResourceForRendering();
                        if(Render&&!Render->LODRenderData.IsEmpty())if(auto* Weights=Source->GetSkinWeightBuffer(0))
                        {
                            const auto& LOD=Render->LODRenderData[0];TArray<FMatrix44f> Matrices;Source->GetCurrentRefToLocalMatrices(Matrices,0);
                            for(const auto& Section:LOD.RenderSections)if(Source->IsMaterialSectionShown(Section.MaterialIndex,0))
                                for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V)
                                    Geometry+=Local.TransformPosition(FVector(USkinnedMeshComponent::GetSkinnedVertexPosition(Source,V,LOD,*Weights,Matrices)));
                        }
                    }
                }
            }
            Row->SetNumberField(TEXT("visible_components"),VisibleParts);Row->SetNumberField(TEXT("max_bone_position_error_cm"),PoseError);
            Check(VisibleParts>0&&Geometry.IsValid,TEXT("empty visible geometry"));
            if(Geometry.IsValid)
            {
                Row->SetStringField(TEXT("geometry_center_cm"),Geometry.GetCenter().ToString());
                const FVector MaxAbs=Geometry.Min.GetAbs().ComponentMax(Geometry.Max.GetAbs());
                Check(MaxAbs.X<=Extent.X+1&&MaxAbs.Y<=Extent.Y+1&&MaxAbs.Z<=Extent.Z+1,TEXT("geometry escapes display envelope"));
            }
            TArray<FTransform> Before;for(auto* C:Components)Before.Add(C->GetComponentTransform().GetRelativeTransform(Display->GetActorTransform()));
            for(const FTransform Pose:{FTransform(FRotator(0,90,90),FVector(300,-200,100),FVector(.4)),FTransform::Identity})
            {
                Display->SetActorTransform(Pose);
                for(int32 N=0;N<Components.Num();++N)if(Components[N]->IsVisible())
                    Check(Components[N]->GetComponentTransform().GetRelativeTransform(Pose).Equals(Before[N],.01f),TEXT("component detached on rotation/scale"));
            }
            Display->Destroy();
        }
        const bool Pass=Errors.IsEmpty();Failures+=!Pass;Row->SetBoolField(TEXT("pass"),Pass);Row->SetArrayField(TEXT("errors"),Errors);Rows.Add(MakeShared<FJsonValueObject>(Row));
        UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_DISPLAY %s %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Item.Definition,*Case);
    };
    TArray<FString> Ids;Model->ItemDefinitions().GetKeys(Ids);Ids.Sort();
    for(const auto& Id:Ids)
    {
        auto Item=Model->CreateItem(Id);Item.Place=0;Item.Count=1;if(!Enhancement->Supports(Item))continue;
        ++Definitions;Inspect(Item,TEXT("factory"));
        // All definitions, then every Viper single-slot option plus factory reset.
        // Cross-slot combinations and rendered appearance need separate review.
        if(Id!=TEXT("ue_pit_viper2011"))continue;
        const auto* W=Gunsmith->Weapon(Id);if(!W)continue;
        for(const auto& Slot:W->Options)for(const auto& Option:Slot.Value)
        {
            auto Variant=Item;TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
            auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(Slot.Key,Option.Id);Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
            Variant.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Variant.Data));
            ++Variants;Inspect(Variant,Slot.Key+TEXT("=")+Option.Id);
        }
        Inspect(Item,TEXT("factory_after_variants"));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("definitions"),Definitions);Report->SetNumberField(TEXT("viper_option_cases"),Variants);
    Report->SetNumberField(TEXT("cases"),Rows.Num());Report->SetNumberField(TEXT("failures"),Failures);Report->SetArrayField(TEXT("results"),Rows);
    Report->SetStringField(TEXT("scope"),TEXT("All enhancement-eligible factory definitions and Viper individual options. Structural pose, bounds, transforms only; not rendered or mouse-input certification."));
    const FString Directory=FPaths::ProjectSavedDir()/TEXT("EnhancementDisplayAudit20261109");IFileManager::Get().MakeDirectory(*Directory,true);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    if(!FFileHelper::SaveStringToFile(Json,*(Directory/TEXT("report.json"))))return 2;
    UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_DISPLAY COMPLETE definitions=%d variants=%d cases=%d failures=%d"),Definitions,Variants,Rows.Num(),Failures);
    return Failures?1:0;
}
