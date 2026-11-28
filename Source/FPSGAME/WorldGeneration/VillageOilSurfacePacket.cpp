#include "VillageHotOil.h"
#include "Misc/Compression.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"

namespace
{
// At most 625 grid samples and eight five-byte cut records per sample.
constexpr uint32 MaxSurfaceBytes=48*1024;
constexpr int DX[]={1,1,0,-1,-1,-1,0,1},DY[]={0,1,1,1,0,-1,-1,-1};

uint8 FlowCode(FVector2D Flow)
{
    const int X=FMath::RoundToInt(Flow.X),Y=FMath::RoundToInt(Flow.Y);
    for(uint8 D=0;D<8;++D)if(DX[D]==X && DY[D]==Y)return D;
    return 8;
}
}

bool FVillageOilSurfacePacket::NetSerialize(FArchive& Ar,UPackageMap*,bool& Success)
{
    Ar<<Serial;
    uint32 Size=Bytes.Num();
    Ar.SerializeIntPacked(Size);
    if(Size>MaxSurfaceBytes){Ar.SetError();Success=false;return false;}
    if(Ar.IsLoading())Bytes.SetNumUninitialized(Size);
    if(Size)Ar.Serialize(Bytes.GetData(),Size);
    Success=!Ar.IsError();
    return Success;
}

void FVillageOilSpread::PackSurface(TArray<uint8>& Packet) const
{
    TArray<uint8> Raw;FMemoryWriter W(Raw);
    uint8 Extent=Built;float SpreadRadius=Radius,NoiseSeed=Seed;FVector2D Direction=Incoming;
    uint16 Revision=SupportRevision;
    W<<Extent<<Revision<<SpreadRadius<<NoiseSeed<<Direction;
    for(int Y=-Built;Y<=Built;++Y)for(int X=-Built;X<=Built;++X)
    {
        const auto& C=Cells[(Y+Half)*Side+X+Half];
        uint8 Code=C.bGround && C.Arrival<999.f?FlowCode(C.Flow):255;
        W<<Code;if(Code==255)continue;
        int16 Z=FMath::RoundToInt(C.P.Z*4.);
        int8 Nx=FMath::RoundToInt(C.N.X*127.),Ny=FMath::RoundToInt(C.N.Y*127.);
        uint8 Links=C.Links;
        float Arrival=C.Arrival,Edge=C.Edge,Film=C.FilmMM;
        W<<Z<<Nx<<Ny<<Links<<Arrival<<Edge<<Film;
    }
    TArray<int32> Keys;EdgeCuts.GetKeys(Keys);Keys.Sort();
    uint16 Count=Keys.Num();W<<Count;
    for(int Key:Keys)
    {
        const int I=Key/Cells.Num(),J=Key%Cells.Num();
        const int Ax=J%Side-I%Side,Ay=J/Side-I/Side;
        uint16 Pair=I*8+FlowCode(FVector2D(Ax,Ay));
        const FVector P=EdgeCuts.FindChecked(Key);
        const FVector2D Grid((I%Side-Half)*Step,(I/Side-Half)*Step);
        uint8 Fraction=FMath::Clamp(FMath::RoundToInt(32.*(Ax?(P.X-Grid.X)/Ax:(P.Y-Grid.Y)/Ay)/Step),0,32);
        int16 Z=FMath::RoundToInt(P.Z*4.);W<<Pair<<Fraction<<Z;
    }
    int32 Size=Raw.Num();
    int32 Packed=FCompression::CompressMemoryBound(NAME_LZ4,Size);
    Packet.SetNumUninitialized(sizeof(Size)+Packed);
    FMemory::Memcpy(Packet.GetData(),&Size,sizeof(Size));
    if(!FCompression::CompressMemory(NAME_LZ4,Packet.GetData()+sizeof(Size),Packed,Raw.GetData(),Size) || Packed>=Size)
    {
        Packed=Size;Size=-Size;
        FMemory::Memcpy(Packet.GetData(),&Size,sizeof(Size));
        FMemory::Memcpy(Packet.GetData()+sizeof(Size),Raw.GetData(),Packed);
    }
    Packet.SetNum(sizeof(Size)+Packed,EAllowShrinking::No);
}

bool FVillageOilSpread::UnpackSurface(const TArray<uint8>& Packet)
{
    int32 Size=0;
    if(Packet.Num()<=sizeof(Size))return false;
    FMemory::Memcpy(&Size,Packet.GetData(),sizeof(Size));
    if(Size==0 || Size< -int32(MaxSurfaceBytes) || Size>int32(MaxSurfaceBytes))return false;
    const bool Compressed=Size>0;
    Size=FMath::Abs(Size);
    TArray<uint8> Raw;Raw.SetNumUninitialized(Size);
    if(Compressed)
    {
        if(!FCompression::UncompressMemory(NAME_LZ4,Raw.GetData(),Size,Packet.GetData()+sizeof(Size),Packet.Num()-sizeof(Size)))return false;
    }
    else
    {
        if(Packet.Num()!=int32(sizeof(Size))+Size)return false;
        FMemory::Memcpy(Raw.GetData(),Packet.GetData()+sizeof(Size),Size);
    }
    FMemoryReader R(Raw);
    uint8 Extent=0;R<<Extent<<SupportRevision<<Radius<<Seed<<Incoming;
    if(Extent>Half || Radius<50.f || Radius>600.f || R.IsError())return false;
    Built=Extent;Cells.Reset();Cells.SetNum(Side*Side);EdgeCuts.Reset();
    for(int Y=-Built;Y<=Built;++Y)for(int X=-Built;X<=Built;++X)
    {
        uint8 Code=255;R<<Code;if(Code==255)continue;
        if(Code>8)return false;
        auto& C=Cells[(Y+Half)*Side+X+Half];int16 Z=0;int8 Nx=0,Ny=0;
        R<<Z<<Nx<<Ny<<C.Links<<C.Arrival<<C.Edge<<C.FilmMM;
        C.P=FVector(X*Step,Y*Step,Z*.25);C.bGround=true;
        const double A=Nx/127.,B=Ny/127.;
        C.N=FVector(A,B,FMath::Sqrt(FMath::Max(0.,1.-A*A-B*B)));
        C.Flow=X==0 && Y==0?Incoming:(Code<8?FVector2D(DX[Code],DY[Code]).GetSafeNormal():FVector2D::ZeroVector);
    }
    uint16 Count=0;R<<Count;
    if(Count>Side*Side*8)return false;
    for(int K=0;K<Count;++K)
    {
        uint16 Pair=0;uint8 Fraction=0;int16 Z=0;R<<Pair<<Fraction<<Z;
        const int I=Pair/8,D=Pair%8,X=I%Side,Y=I/Side,NX=X+DX[D],NY=Y+DY[D];
        if(I>=Cells.Num() || NX<0 || NX>=Side || NY<0 || NY>=Side || Fraction>32)return false;
        const FVector2D A((X-Half)*Step,(Y-Half)*Step),Delta(DX[D]*Step,DY[D]*Step);
        EdgeCuts.Add(I*Cells.Num()+NY*Side+NX,FVector(A+Delta*(Fraction/32.),Z*.25));
    }
    if(R.IsError() || R.Tell()!=Size)return false;
    BuildShores(Built);UpdateBounds();
    return true;
}
