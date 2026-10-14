#pragma once
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

namespace SpellbookBookSampling
{
// This mesh has no component tick. Keep the restore data and the live instance
// on the same clock; SetAnimation alone silently does nothing without an instance.
inline bool Sample(USkeletalMeshComponent& Book,UAnimSequence* Clip,float Time)
{
    const auto* Mesh=Book.GetSkeletalMeshAsset();
    if(!Mesh||!Clip||!Book.IsRegistered())return false;
#if WITH_EDITOR
    // UE 5.8 keeps UAnimSequence::IsCompiling protected; sample only when its
    // public compressed-data readiness query reports usable animation data.
    if(Mesh->IsCompiling()||!Clip->IsCompressedDataValid())return false;
#endif
    const float Position=FMath::Clamp(Time,0.f,Clip->GetPlayLength());
    Book.AnimationData.AnimToPlay=Clip;
    Book.AnimationData.bSavedLooping=false;
    Book.AnimationData.bSavedPlaying=false;
    Book.AnimationData.SavedPosition=Position;
    Book.AnimationData.SavedPlayRate=0.f;
    if(Book.GetAnimationMode()!=EAnimationMode::AnimationSingleNode)
        Book.SetAnimationMode(EAnimationMode::AnimationSingleNode);
    if(!Book.GetSingleNodeInstance())Book.InitAnim(true);
    auto* Instance=Book.GetSingleNodeInstance();
    if(!Instance)return false;
    if(Instance->GetCurrentAsset()!=Clip)Instance->SetAnimationAsset(Clip,false,0.f);
    Instance->SetPlaying(false);
    Instance->SetPosition(Position,false);
    Book.SetComponentSpaceTransformsDoubleBuffering(false);
    Book.TickAnimation(0.f,false);
    Book.RefreshBoneTransforms();
    Book.UpdateChildTransforms();
    Book.MarkRenderDynamicDataDirty();
    return true;
}
}
