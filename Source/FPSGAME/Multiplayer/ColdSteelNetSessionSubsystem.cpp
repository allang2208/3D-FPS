#include "ColdSteelNetSessionSubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/World.h"
#include "Engine/NetDriver.h"

bool UColdSteelNetSessionSubsystem::BindRoom(UWorld* World)
{
    if(!World||World->GetGameInstance()!=GetGameInstance()||World->GetNetMode()==NM_Client)return false;
    UNetDriver* Driver=World->GetNetDriver();
    if(!Driver)return false;
    if(RoomDriver.Get()!=Driver)
    {
        // Seamless travel keeps the driver. PIE may fall back to hard travel:
        // carry our in-memory room identity in that server travel URL as well.
        FGuid IncomingRoom;
        FGuid::Parse(World->URL.GetOption(TEXT("ColdSteelRoom="),TEXT("")),IncomingRoom);
        if(!RoomId.IsValid()||IncomingRoom!=RoomId){GuestKeys.Reset();GuestProfiles.Reset();RoomId=FGuid::NewGuid();}
        RoomDriver=Driver;
    }
    return true;
}
void UColdSteelNetSessionSubsystem::RememberGuestKeys(UWorld* World,FGuid Profile,const TArray<FName>& Keys)
{
    if(Profile.IsValid()&&BindRoom(World))GuestKeys.Add(Profile,Keys);
}
TArray<FName> UColdSteelNetSessionSubsystem::RestoreGuestKeys(UWorld* World,FGuid Profile)
{
    return Profile.IsValid()&&BindRoom(World)?GuestKeys.FindRef(Profile):TArray<FName>{};
}
void UColdSteelNetSessionSubsystem::RememberGuestProfile(UWorld* World,FGuid Profile,UColdSteelStatusModel* Model)
{
    if(Profile.IsValid()&&Model&&Model->Snapshot().NetworkProfileId==Profile&&BindRoom(World))GuestProfiles.Add(Profile,Model);
}
UColdSteelStatusModel* UColdSteelNetSessionSubsystem::RestoreGuestProfile(UWorld* World,FGuid Profile)
{
    return Profile.IsValid()&&BindRoom(World)?GuestProfiles.FindRef(Profile).Get():nullptr;
}
FString UColdSteelNetSessionSubsystem::TravelOption(UWorld* World)
{
    return BindRoom(World)?TEXT("ColdSteelRoom=")+RoomId.ToString(EGuidFormats::Digits):FString();
}
