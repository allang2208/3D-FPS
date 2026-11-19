#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "JasonReviewGraph.generated.h"
class UAnimBlueprint;
class USkeletalMesh;
class UAnimSequence;
UCLASS()
class UJasonReviewGraph : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Jason Authoring")
    static bool AddDrivers(UAnimBlueprint* Blueprint, const TArray<FName>& Bones, const TArray<FName>& Morphs, const TArray<int32>& Axes, const TArray<float>& Starts, const TArray<float>& Ends);
    UFUNCTION(BlueprintCallable, Category="Jason Authoring")
    static void SetMeshMorphFlags(USkeletalMesh* Mesh, const TArray<FName>& Morphs);
    UFUNCTION(BlueprintCallable, Category="Jason Authoring")
    static TArray<float> SampleMorphs(USkeletalMesh* Mesh, UAnimSequence* Clip, float Time, const TArray<FName>& Morphs);
};
