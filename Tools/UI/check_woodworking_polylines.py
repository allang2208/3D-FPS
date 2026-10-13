"""Offline C++ regression for production woodworking presentation source.

Compiles the real WoodworkingPresentation.cpp against small checked container/math
stand-ins. The Add guard models UE TArray::CheckAddress, including spare capacity.
This does not launch Unreal, Slate, a game, or a map; UE compatibility is verified
separately by the normal Editor/Game builds. Requires Visual Studio C++ tools.
"""
from pathlib import Path
import argparse,subprocess,hashlib,json,re,datetime

p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
src=args.project/'Source/FPSGAME/UI';out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
shim=r'''
#pragma once
#include <vector>
#include <map>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <utility>
#include <initializer_list>
using int32=int;using uint8=unsigned char;
enum class EAllowShrinking{No};template<int> struct TInlineAllocator{};
template<class T> auto&& MoveTemp(T& Value){return std::move(Value);}
struct FIntPoint{int X=0,Y=0;bool operator<(const FIntPoint& B)const{return X<B.X||(X==B.X&&Y<B.Y);}bool operator!=(const FIntPoint& B)const{return X!=B.X||Y!=B.Y;}};
struct FVector2D{
    double X=0,Y=0;FVector2D()=default;FVector2D(double A,double B):X(A),Y(B){};explicit FVector2D(FIntPoint P):X(P.X),Y(P.Y){}
    bool operator==(const FVector2D& B)const{return X==B.X&&Y==B.Y;}
    FVector2D operator-(const FVector2D& B)const{return {X-B.X,Y-B.Y};}
    static double CrossProduct(FVector2D A,FVector2D B){return A.X*B.Y-A.Y*B.X;}
};
namespace FMath{inline double Abs(double V){return std::abs(V);}}
template<class T,class Alloc=void> class TArray{
    std::vector<T> Data;
    void CheckAddress(const T* P)const{
        const auto Addr=reinterpret_cast<std::uintptr_t>(P),Begin=reinterpret_cast<std::uintptr_t>(Data.data());
        if(Addr>=Begin&&Addr<Begin+Data.capacity()*sizeof(T))throw std::logic_error("TArray self-alias");
    }
public:
    TArray()=default;TArray(std::initializer_list<T> V):Data(V){}
    int Num()const{return int(Data.size());}int Max()const{return int(Data.capacity());}bool IsEmpty()const{return Data.empty();}
    void Reserve(int N){Data.reserve(N);}void Reset(){Data.clear();}void Init(const T& V,int N){Data.assign(N,V);}
    int Add(const T& V){CheckAddress(&V);Data.push_back(V);return Num()-1;}
    int Add(T&& V){CheckAddress(&V);Data.push_back(std::move(V));return Num()-1;}
    T& operator[](int I){return Data.at(I);}const T& operator[](int I)const{return Data.at(I);}
    T& Last(){return Data.at(Data.size()-1);}const T& Last()const{return Data.at(Data.size()-1);}
    T Pop(EAllowShrinking){T V=std::move(Data.back());Data.pop_back();return V;}
};
template<class K,class V> class TMap{
    std::map<K,V> Data;
public:
    bool IsEmpty()const{return Data.empty();}V& FindOrAdd(const K& Key){return Data[Key];}
    V* Find(const K& Key){auto I=Data.find(Key);return I==Data.end()?nullptr:&I->second;}
    void Remove(const K& Key){Data.erase(Key);}
    struct Iterator{typename std::map<K,V>::const_iterator I;const K& Key()const{return I->first;}};
    Iterator CreateConstIterator()const{return {Data.cbegin()};}
};
'''
tests=r'''
#include "WoodworkingPresentation.h"
#include <iostream>
#include <string>
static int Cases=0;
void Require(bool OK,const char* Message){if(!OK)throw std::runtime_error(Message);}
template<class F> void Case(const char* Name,F Test){Test();++Cases;std::cout<<"PASS "<<Name<<"\n";}
int main(){try{
    using WoodworkingPresentation::ClosePolyline;
    Case("empty",[]{TArray<FVector2D> P;ClosePolyline(P);Require(P.Num()==0,"empty changed");});
    Case("single",[]{TArray<FVector2D> P={{1,2}};ClosePolyline(P);Require(P.Num()==1,"single changed");});
    Case("two distinct points",[]{TArray<FVector2D> P={{1,2},{3,4}};ClosePolyline(P);Require(P.Num()==3&&P[0]==P.Last(),"not closed");});
    Case("already closed",[]{TArray<FVector2D> P={{1,2},{3,4},{1,2}};ClosePolyline(P);ClosePolyline(P);Require(P.Num()==3,"duplicate closure");});
    Case("identical pair",[]{TArray<FVector2D> P={{1,2},{1,2}};ClosePolyline(P);Require(P.Num()==2,"duplicate point");});
    for(int Capacity:{34,35}){
        Case(Capacity==35?"reported Num34 Max35":"closure with reallocation",[Capacity]{
            TArray<FVector2D> P;P.Reserve(Capacity);for(int I=0;I<34;++I)P.Add(FVector2D(I,I*2));
            Require(P.Num()==34&&P.Max()==Capacity,"wrong setup");ClosePolyline(P);Require(P.Num()==35&&P.Last()==P[0],"closure failed");
            for(int I=0;I<34;++I)Require(P[I]==FVector2D(I,I*2),"prefix changed");ClosePolyline(P);Require(P.Num()==35,"closure not idempotent");
        });
        Case(Capacity==35?"old expression rejected with slack":"old expression rejected at capacity",[Capacity]{
            TArray<FVector2D> P;P.Reserve(Capacity);for(int I=0;I<34;++I)P.Add(FVector2D(I,I));
            bool Rejected=false;try{P.Add(P[0]);}catch(const std::logic_error&){Rejected=true;}Require(Rejected,"negative control missed alias");
        });
    }
    Case("empty target mask",[]{TArray<uint8> M;TArray<TArray<FVector2D>> O;WoodworkingPresentation::TargetContours(M,0,0,O);Require(O.Num()==0,"unexpected contour");});
    Case("empty foreground",[]{TArray<uint8> M={0};TArray<TArray<FVector2D>> O;WoodworkingPresentation::TargetContours(M,1,1,O);Require(O.Num()==0,"unexpected contour");});
    Case("single pixel contour",[]{TArray<uint8> M={1};TArray<TArray<FVector2D>> O;WoodworkingPresentation::TargetContours(M,1,1,O);Require(O.Num()==1&&O[0].Num()==5&&O[0][0]==O[0].Last(),"bad pixel loop");});
    Case("invalid mask size",[]{TArray<uint8> M={1};TArray<TArray<FVector2D>> O;WoodworkingPresentation::TargetContours(M,2,2,O);Require(O.Num()==0,"invalid mask accepted");});
    Case("outer and hole contours",[]{TArray<uint8> M={1,1,1,1,0,1,1,1,1};TArray<TArray<FVector2D>> O;WoodworkingPresentation::TargetContours(M,3,3,O);Require(O.Num()==2,"missing hole");for(int I=0;I<O.Num();++I){const int N=O[I].Num();Require(N>=4&&O[I][0]==O[I].Last(),"open loop");ClosePolyline(O[I]);Require(O[I].Num()==N,"closed contour changed");}});
    std::cout<<"CASES_PASSED="<<Cases<<"\n";return 0;
}catch(const std::exception& E){std::cerr<<"FAIL "<<E.what()<<"\n";return 1;}}
'''
(out/'CoreMinimal.h').write_text(shim);(out/'regression.cpp').write_text(tests)
widget=(src/'ColdSteelWoodworkingWidget.cpp').read_text(encoding='utf-8-sig')
assert 'WoodworkingPresentation::ClosePolyline(KnifeBoundary)' in widget
assert 'if(Points.Num()<2)return;FSlateDrawElement::MakeLines' in widget
source_files=list(src.glob('*Woodworking*.cpp'))+list(src.glob('*Woodworking*.h'))+list((args.project/'Source/FPSGAME/Building').glob('Woodworking*'))
alias=re.compile(r'\b(\w+)\.(?:Add|Emplace|Insert)\s*\(\s*(?:MoveTemp\s*\(\s*)?\1\s*(?:\[|\.Last\s*\()')
for f in source_files:assert not alias.search(f.read_text(encoding='utf-8-sig')),f'Self-alias expression: {f}'
vs=Path('C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/Tools/VsDevCmd.bat');assert vs.exists()
# All command arguments are fixed filesystem paths; reject cmd metacharacters.
def q(path):
    value=str(path.resolve());assert not any(c in value for c in '"%&|<>^\r\n');return '"'+value+'"'
command=f'@echo off\ncall {q(vs)} -arch=x64 -host_arch=x64 >nul\nif errorlevel 1 exit /b 1\ncl.exe /nologo /EHsc /std:c++17 /W4 /I{q(out)} /I{q(src)} {q(out/"regression.cpp")} {q(src/"WoodworkingPresentation.cpp")} /Fe:{q(out/"regression.exe")}\nexit /b %errorlevel%\n'
(out/'build.cmd').write_text(command,encoding='ascii')
r=subprocess.run('cmd.exe /d /c '+q(out/'build.cmd'),cwd=out,capture_output=True)
(out/'compile.log').write_bytes(r.stdout+r.stderr)
assert r.returncode==0,f'Standalone compile failed: {out / "compile.log"}'
r=subprocess.run([str(out/'regression.exe')],cwd=out,capture_output=True,text=True)
(out/'regression.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'offline C++ production functions with checked container stand-ins','cases_passed':int(re.search(r'CASES_PASSED=(\d+)',r.stdout)[1]),'static_self_alias_scan_files':len(source_files),'game_or_editor_launched':False,'production_source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [src/'WoodworkingPresentation.cpp',src/'WoodworkingPresentation.h',src/'ColdSteelWoodworkingWidget.cpp']}}
(out/'receipt.json').write_text(json.dumps(record,indent=2));print(r.stdout);print(json.dumps(record,indent=2))
