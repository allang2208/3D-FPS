#pragma once
#include "CoreMinimal.h"
#include "FPSBodyMotionSample.generated.h"

// Cosmetic contacts only: two wrists, thirty finger joints and the equipped
// mechanical parts. No actor movement, damage or inventory values are carried.
struct FFPSBodyMotionHand
{
    FTransform Wrist=FTransform::Identity;
    FQuat Fingers[15];
    FFPSBodyMotionHand(){for(auto& Q:Fingers)Q=FQuat::Identity;}
};
struct FFPSBodyMotionRig
{
    uint32 Schema=0;
    FTransform Root=FTransform::Identity;
    TArray<FTransform> Bones,Parts;
    TArray<uint8> VisibleParts;
    uint32 Sections=MAX_uint32;
    bool Visible=true;
    bool Valid=false;
};

USTRUCT()
struct FFPSBodyMotionSample
{
    GENERATED_BODY()
    FName Channel,Consumable;
    uint8 Fingers=0,Wrists=0,PropVisibility=0,DiscardFlags=0;
    uint16 ConsumableSerial=0;
    bool CoupledWrists=false;
    bool HasSupportGrip=false;
    FTransform SupportGrip=FTransform::Identity;
    bool DroppedBottle=false;
    float LiquidLevel=0.f,Light=0.f;
    FFPSBodyMotionHand Hands[2];
    TArray<FFPSBodyMotionRig> Rigs;
    FTransform Props[3]={FTransform::Identity,FTransform::Identity,FTransform::Identity};
    bool NetSerialize(FArchive& Ar,UPackageMap* Map,bool& Success);
    bool IsSane() const;
    bool Identical(const FFPSBodyMotionSample* Other,uint32 PortFlags) const;
};
template<> struct TStructOpsTypeTraits<FFPSBodyMotionSample>:TStructOpsTypeTraitsBase2<FFPSBodyMotionSample>
{enum{WithNetSerializer=true,WithCopy=true,WithIdentical=true};};
