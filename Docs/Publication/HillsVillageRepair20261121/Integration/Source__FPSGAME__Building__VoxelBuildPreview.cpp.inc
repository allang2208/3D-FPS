// Source/FPSGAME/Building/VoxelBuildPreview.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 14-14 | file scope
#include "../WorldGeneration/HighVillageDefense.h"

// Lines 60-104 | void UVoxelBuildComponent::UpdatePrefabPreview()
    const bool bWoodGate=Prefab->Id==VillageBuildDefense::WoodGate;
    const bool Gate=bWoodGate||Prefab->Id==VillageBuildDefense::StoneGate;
    if(VillageBuildDefense::IsVillageRecipe(Prefab->Id))
    {
        const auto Size=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,PrefabPlanYaw);
        Transform=DefenseDockPose.IsSet()?DefenseDockPose.GetValue():
            VillageBuildDefense::Placement(Prefab->Id,PrefabCell,Size,PrefabPlanYaw,PlannedGroundYaw());
        if(Gate)
        {
            const float Offset=bWoodGate?AVillageDefenseGate::NarrowHingeOffset:0.f;
            Transform.AddToTranslation(Transform.GetRotation().RotateVector(FVector(-Offset,0.,0.)));
            if(PreviewGateAssembly!=Prefab->Id)
            {
                for(UStaticMeshComponent* Old:VillageGatePreviewParts)Old->DestroyComponent();
                VillageGatePreviewParts.Reset();
                PreviewGateAssembly=Prefab->Id;
                const FSoftObjectPath RightLeaf(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_GateNarrowRight.SM_GateNarrowRight"));
                const FSoftObjectPath LeftMount(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_GateHingeMount.SM_GateHingeMount"));
                const FSoftObjectPath RightMount(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_GateHingeMountRight.SM_GateHingeMountRight"));
                auto AddPart=[this,Offset](const FSoftObjectPath& Path,FTransform Relative)
                {
                    auto* Part=NewObject<UStaticMeshComponent>(PreviewActor.Get(),NAME_None,RF_Transient);
                    PreviewActor->AddInstanceComponent(Part);Part->SetupAttachment(Preview);
                    Relative.AddToTranslation(FVector(Offset,0.,0.));
                    Part->SetRelativeTransform(Relative);Part->SetMobility(EComponentMobility::Movable);
                    Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                    Part->SetCastShadow(false);Part->SetCanEverAffectNavigation(false);
                    if(auto* PartMesh=Cast<UStaticMesh>(Path.TryLoad()))
                    {
                        Part->SetStaticMesh(PartMesh);
                        if(PreviewMID)for(int32 Slot=0;Slot<PartMesh->GetStaticMaterials().Num();++Slot)Part->SetMaterial(Slot,PreviewMID);
                    }
                    Part->RegisterComponent();VillageGatePreviewParts.Add(Part);
                };
                if(bWoodGate)
                {
                    AddPart(RightLeaf,FTransform(FVector(Offset,0.,0.)));
                    AddPart(LeftMount,FTransform(FVector(-Offset,0.,0.)));
                    AddPart(RightMount,FTransform(FVector(Offset,0.,0.)));
                    AddPart(AVillageDefenseGate::PlacedPostMeshPath(),AVillageDefenseGate::PlacedPostTransform(false));
                    AddPart(AVillageDefenseGate::PlacedPostMeshPath(),AVillageDefenseGate::PlacedPostTransform(true));
                }
                else AddPart(AHighVillageGate::PlacedGrilleMeshPath(),FTransform::Identity);
            }
        }

// Lines 108-109 | void UVoxelBuildComponent::UpdatePrefabPreview()
        const FIntVector Size=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,PrefabPlanYaw);
        const FQuat Rotation(FRotator(0.f,PrefabPlanYaw*90.f,0.f));

// Lines 122-122 | void UVoxelBuildComponent::UpdatePrefabPreview()
        Transform=AVoxelBuildPrefabActor::ComputeTransform(*Prefab,Mesh,PrefabCell,PrefabPlanYaw);

// Lines 126-126 | void UVoxelBuildComponent::UpdatePrefabPreview()
    for(UStaticMeshComponent* Part:VillageGatePreviewParts)Part->SetVisibility(Gate);

// Lines 138-138 | void UVoxelBuildComponent::UpdatePreview(FIntVector Size)
    for(UStaticMeshComponent* Part:VillageGatePreviewParts)Part->SetVisibility(false);
