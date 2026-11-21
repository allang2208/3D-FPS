// Source/FPSGAME/Building/VoxelBuildInput.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 13-13 | file scope
#include "VillageBuildDefense.h"

// Lines 17-17 | file scope
#include "../FPSGAMEPlayerController.h"

// Lines 22-22 | file scope
#include "../WorldGeneration/VillageDefenseSection.h"

// Lines 37-44 | file scope

void UVoxelBuildComponent::RefreshPlacementInput()
{
    FeedbackTime=0;
    PlacementCheckAt=0;
    TargetUpdateAt=0;
    UpdateTarget();
}

// Lines 113-114 | bool UVoxelBuildComponent::HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen)
    const bool bWheel=Key==EKeys::MouseScrollUp||Key==EKeys::MouseScrollDown;
    if(bWheel||Key==EKeys::R)

// Lines 118-130 | bool UVoxelBuildComponent::HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen)
            const int32 Step=Key==EKeys::MouseScrollDown?-1:1;
            if(const FVoxelBuildPrefab* Piece=SelectedPrefab())
            {
                if(PlannedGroundYaw()!=INDEX_NONE)
                {
                    const int32 Degrees=bWheel?Step:90;
                    GroundYawDegrees=(GroundYawDegrees+Degrees+360)%360;
                }
                else if(Piece->Mount!=EVoxelPrefabMount::Wall)ComponentYaw=(ComponentYaw+Step+4)%4;
            }
            else if(bWheel)Brush=(Brush+Step+ShapeCount())%ShapeCount();
            else BrushRotation=(BrushRotation+1)&3;
            RefreshPlacementInput();

// Lines 134-134 | bool UVoxelBuildComponent::HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen)
    if(Key==EKeys::F){if(Pressed){bSnapEnabled=!bSnapEnabled;RefreshPlacementInput();}return true;}

// Lines 152-168 | bool UVoxelBuildComponent::HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen)
    if(Key==EKeys::MiddleMouseButton)
    {
        if(!Pressed)return true;
        const auto* Piece=Cast<AVoxelBuildPrefabActor>(AimedPrefab.Get());
        if(Piece&&Piece->GetOwner()==BuildWorld&&!Piece->IsFalling()&&VillageBuildDefense::IsVillageRecipe(Piece->PrefabId()))
        {
            const FName Id=Piece->PrefabId();
            SelectComponent(Id);
            if(SelectedComponent==Id&&CanBuildVillagePieces())
            {
                GroundYawDegrees=FMath::RoundToInt(FRotator::ClampAxis(Piece->GetActorRotation().Yaw))%360;
                RefreshPlacementInput();
            }
        }
        else if(!Removal.IsEmpty())SelectMaterial(BuildWorld->VolumeMaterialAt(HitCell.Volume,HitCell.Cell));
        return true;
    }

// Lines 173-181 | bool UVoxelBuildComponent::HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen)
            auto* RemovalTarget=Cast<AVoxelBuildPrefabActor>(AimedPrefab.Get());
            if(Key==EKeys::RightMouseButton)
            {
                // A collapsed player-built piece keeps its footprint but has no collision to aim at.
                const auto* Breach=Cast<AVillageDefenseSection>(ColdSteelWorldInteraction::TraceUseTargets(PC).Target);
                if(Breach && Breach->GetHealth()<=0.f)
                    if(auto* Placed=Cast<AVoxelBuildPrefabActor>(Breach->GetAttachParentActor()))
                        RemovalTarget=Placed;
            }

// Lines 188-199 | bool UVoxelBuildComponent::HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen)
                    if(const auto* P=SelectedPrefab())
                    {
                        if(!bPrefabValid)return true;
                        R.Mode=DefenseDockPose.IsSet()?TEXT("wallDockPrefab"):TEXT("prefab");
                        R.Definition=P->Id;R.Anchor=PrefabCell;R.Orientation=PrefabPlanYaw;
                        const int32 GroundYaw=PlannedGroundYaw();
                        if(GroundYaw!=INDEX_NONE)
                        {
                            R.Mode=TEXT("groundDefensePrefab");
                            R.Orientation=GroundYaw;
                        }
                        R.Target=DefenseDockTarget.Get();

// Lines 206-206 | bool UVoxelBuildComponent::HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen)
                else if(RemovalTarget){R.Mode=TEXT("removePrefab");R.Target=RemovalTarget;R.Anchor=RemovalTarget->AnchorCell();}

// Lines 250-251 | bool UVoxelBuildComponent::HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen)
            else if(RemovalTarget)
            {bFeedbackValid=BuildWorld->RemovePrefab(RemovalTarget);Feedback=BuildWorld->ResultMessage();}

// Lines 283-291 | bool UVoxelBuildComponent::HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen)
    if(Key==EKeys::E)
    {
        if(Pressed && !bPanelOpen)
            if(auto* Player=Cast<AFPSGAMEPlayerController>(PC))
                if(auto* Breach=Cast<AVillageDefenseSection>(ColdSteelWorldInteraction::TraceUseTargets(Player).Target))
                    Player->RequestVillageRepair(Breach);
        return true;
    }
    if(Key==EKeys::G||Key==EKeys::Three||Key==EKeys::Four||Key==EKeys::Five)return true;

// Lines 355-358 | void UVoxelBuildComponent::PlacePrefab()
    if(DefenseDockPose.IsSet()&&!DefenseDockTarget.IsValid())
    {bFeedbackValid=false;Feedback=TEXT("吸附目标已消失");FeedbackTime=2;return;}
    bFeedbackValid=BuildWorld->PlacePrefab(Prefab->Id,PrefabCell,PrefabPlanYaw,DefenseDockPose.IsSet(),
        DefenseDockTarget.Get(),PlannedGroundYaw());
