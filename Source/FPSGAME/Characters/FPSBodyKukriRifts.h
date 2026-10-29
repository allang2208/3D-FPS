#pragma once
#include "CoreMinimal.h"

class UDynamicMeshComponent;
class UMaterialInstanceDynamic;
struct FStreamableHandle;

// Cosmetic, observer-local history. Never replicated or used for hit detection.
struct FFPSBodyKukriRifts
{
    struct FPoint { FVector Inner,Outer; double At=0.; float Travel=0.f; };
    struct FTrail
    {
        TWeakObjectPtr<UDynamicMeshComponent> Mesh;
        TWeakObjectPtr<UMaterialInstanceDynamic> Material;
        TArray<FPoint> Points;
        FString Weapon;
        FName Action;
        float Progress=-1.f;
        double LastSample=-1.;
        bool Whirlwind=false;
        FTransform ProbeKnife;
        float ProbeProgress=-1.f;
        FTransform PreviousKnife;
        FString PreviousWeapon;
        double PreviousAt=-1.;
    };
    FTrail Trails[2];
    TSharedPtr<FStreamableHandle> MaterialLoad;
    void Sample(AActor* Owner,int32 Hand,const FString& Weapon,FName Action,float Progress,
        bool Whirlwind,const FTransform& Knife,double Now);
    void Advance(double Now);
    void RememberPose(int32 Hand,const FString& Weapon,const FTransform& Knife,double Now);
    void SampleWindow(AActor* Owner,int32 Hand,const FString& Weapon,FName Action,float Progress,
        float Start,float End,bool Whirlwind,const FTransform& Knife,double Now);
    void Clear(AActor* Owner);
};
