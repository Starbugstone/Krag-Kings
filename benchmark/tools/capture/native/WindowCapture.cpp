// Explicit-window-only Windows Graphics Capture producer. No desktop API exists here.
#define NOMINMAX
#include <windows.h>
#include <d3d11.h>
#include <dxgi.h>
#include <windows.graphics.capture.interop.h>
#include <windows.graphics.directx.direct3d11.interop.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Graphics.Capture.h>
#include <winrt/Windows.Graphics.DirectX.h>
#include <winrt/Windows.Graphics.DirectX.Direct3D11.h>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <thread>
#include <vector>
using namespace winrt;
using namespace winrt::Windows::Graphics::Capture;
using namespace winrt::Windows::Graphics::DirectX;
using namespace winrt::Windows::Graphics::DirectX::Direct3D11;
using Clock=std::chrono::steady_clock;
static double UnixMicroseconds(){FILETIME ft{};GetSystemTimePreciseAsFileTime(&ft);ULARGE_INTEGER t{};t.LowPart=ft.dwLowDateTime;t.HighPart=ft.dwHighDateTime;return static_cast<double>(t.QuadPart-116444736000000000ULL)/10.0;}
struct Options {HWND hwnd{};DWORD pid{};int width{},height{},fps=30;std::wstring pipe,stop,metadata;};
static Options Parse(int argc,wchar_t** argv){
 Options o;
 for(int i=1;i<argc;i+=2){if(i+1>=argc)throw std::runtime_error("Every option requires a value");std::wstring k=argv[i],v=argv[i+1];
 if(k==L"--hwnd")o.hwnd=reinterpret_cast<HWND>(std::stoull(v));else if(k==L"--pid")o.pid=std::stoul(v);else if(k==L"--width")o.width=std::stoi(v);else if(k==L"--height")o.height=std::stoi(v);else if(k==L"--fps")o.fps=std::stoi(v);else if(k==L"--pipe")o.pipe=v;else if(k==L"--stop")o.stop=v;else if(k==L"--metadata")o.metadata=v;else throw std::runtime_error("Unknown option");}
 if(!o.hwnd||!o.pid||o.width<640||o.height<360||o.fps<15||o.fps>60||o.pipe.rfind(L"\\\\.\\pipe\\KragKingsCapture-",0)!=0||o.stop.empty()||o.metadata.empty())throw std::runtime_error("Explicit game HWND, owner PID, dimensions, named pipe and output paths required");return o;
}
static void CheckWindow(Options const&o){DWORD pid{};GetWindowThreadProcessId(o.hwnd,&pid);RECT r{};if(!IsWindow(o.hwnd)||pid!=o.pid||IsIconic(o.hwnd)||GetForegroundWindow()!=o.hwnd||!GetClientRect(o.hwnd,&r)||r.right!=o.width||r.bottom!=o.height)throw std::runtime_error("Game window ownership, foreground, visibility or client dimensions changed");}
static void Metadata(Options const&o,bool complete,uint64_t frames,uint64_t duplicates,double firstUtc,double firstCompositorUtc){
 auto temporary=o.metadata+L".tmp";std::ofstream f{std::filesystem::path(temporary),std::ios::trunc};f.precision(17);
 f<<"{\"backend\":\"WindowsGraphicsCapture\",\"explicitHwndOnly\":true,\"desktopCapture\":false,\"completed\":"<<(complete?"true":"false")<<",\"hwnd\":"<<reinterpret_cast<uintptr_t>(o.hwnd)<<",\"processId\":"<<o.pid<<",\"width\":"<<o.width<<",\"height\":"<<o.height<<",\"frameRate\":"<<o.fps<<",\"pixelFormat\":\"BGRA8 SDR\",\"frames\":"<<frames<<",\"duplicatedFrames\":"<<duplicates<<",\"firstOutputUnixMicroseconds\":"<<firstUtc<<",\"firstCompositorUnixMicroseconds\":"<<firstCompositorUtc<<",\"timing\":\"Real-time CFR schedule; newest available compositor frame, repeat only when compositor has no newer frame\"}";f.close();if(!f)throw std::runtime_error("Metadata write failed");if(!MoveFileExW(temporary.c_str(),o.metadata.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))throw std::runtime_error("Metadata replace failed");
}
int wmain(int argc,wchar_t**argv){HANDLE pipe=INVALID_HANDLE_VALUE;
 try{
  auto o=Parse(argc,argv);SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);CheckWindow(o);init_apartment(apartment_type::multi_threaded);
  if(!GraphicsCaptureSession::IsSupported())throw std::runtime_error("Windows Graphics Capture unsupported");
  auto interop=get_activation_factory<GraphicsCaptureItem,IGraphicsCaptureItemInterop>();GraphicsCaptureItem item{nullptr};
  check_hresult(interop->CreateForWindow(o.hwnd,guid_of<GraphicsCaptureItem>(),put_abi(item)));
  auto size=item.Size();if(size.Width!=o.width||size.Height!=o.height)throw std::runtime_error("WGC surface differs from game client; use the intended borderless viewport, no implicit crop");
  com_ptr<ID3D11Device> device;com_ptr<ID3D11DeviceContext> context;D3D_FEATURE_LEVEL level{};
  check_hresult(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_HARDWARE,nullptr,D3D11_CREATE_DEVICE_BGRA_SUPPORT,nullptr,0,D3D11_SDK_VERSION,device.put(),&level,context.put()));
  auto dxgi=device.as<IDXGIDevice>();com_ptr<IInspectable> inspectable;check_hresult(CreateDirect3D11DeviceFromDXGIDevice(dxgi.get(),inspectable.put()));auto winDevice=inspectable.as<IDirect3DDevice>();
  auto pool=Direct3D11CaptureFramePool::CreateFreeThreaded(winDevice,DirectXPixelFormat::B8G8R8A8UIntNormalized,2,size);auto session=pool.CreateCaptureSession(item);session.IsCursorCaptureEnabled(false);
  // Keep Windows' capture border; do not request permission to suppress it.
  pipe=CreateNamedPipeW(o.pipe.c_str(),PIPE_ACCESS_OUTBOUND,PIPE_TYPE_BYTE|PIPE_READMODE_BYTE|PIPE_WAIT|PIPE_REJECT_REMOTE_CLIENTS,1,1048576,0,0,nullptr);
  if(pipe==INVALID_HANDLE_VALUE)throw std::runtime_error("Named pipe creation failed");
  std::ofstream(std::filesystem::path(o.metadata+L".pipe-ready"))<<"ready";
  std::cout<<"WGC_PIPE_READY"<<std::endl;
  if(!ConnectNamedPipe(pipe,nullptr)&&GetLastError()!=ERROR_PIPE_CONNECTED)throw std::runtime_error("Encoder pipe connection failed");
  session.StartCapture();com_ptr<ID3D11Texture2D> staging;std::vector<uint8_t> pixels(static_cast<size_t>(o.width)*o.height*4);
  uint64_t frames=0,duplicates=0;double firstUtc=0,firstCompositorUtc=0;int64_t previousTimestamp=-1;bool haveFrame=false;
  auto start=Clock::now();auto next=start;auto period=std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(1.0/o.fps));
  while(!std::filesystem::exists(o.stop)){
   if(Clock::now()-start>std::chrono::seconds(240))throw std::runtime_error("Capture maximum duration reached without stop signal");
   CheckWindow(o);Direct3D11CaptureFrame frame{nullptr};while(auto newest=pool.TryGetNextFrame())frame=std::move(newest);
   bool fresh=false;double compositorUtc=0;
   if(frame){auto content=frame.ContentSize();if(content.Width!=o.width||content.Height!=o.height)throw std::runtime_error("Captured surface resized");
    int64_t stamp=frame.SystemRelativeTime().count();fresh=stamp!=previousTimestamp;previousTimestamp=stamp;
    auto access=frame.Surface().as<::Windows::Graphics::DirectX::Direct3D11::IDirect3DDxgiInterfaceAccess>();com_ptr<ID3D11Texture2D> texture;check_hresult(access->GetInterface(__uuidof(ID3D11Texture2D),texture.put_void()));
    D3D11_TEXTURE2D_DESC desc{};texture->GetDesc(&desc);if(desc.Width!=static_cast<UINT>(o.width)||desc.Height!=static_cast<UINT>(o.height)||desc.Format!=DXGI_FORMAT_B8G8R8A8_UNORM)throw std::runtime_error("Unexpected WGC SDR texture");
    if(!staging){desc.Usage=D3D11_USAGE_STAGING;desc.BindFlags=0;desc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;desc.MiscFlags=0;check_hresult(device->CreateTexture2D(&desc,nullptr,staging.put()));}
    context->CopyResource(staging.get(),texture.get());D3D11_MAPPED_SUBRESOURCE mapped{};check_hresult(context->Map(staging.get(),0,D3D11_MAP_READ,0,&mapped));
    for(int y=0;y<o.height;y++)memcpy(pixels.data()+static_cast<size_t>(y)*o.width*4,static_cast<uint8_t*>(mapped.pData)+static_cast<size_t>(y)*mapped.RowPitch,static_cast<size_t>(o.width)*4);context->Unmap(staging.get(),0);haveFrame=true;
    LARGE_INTEGER qpc{},frequency{};QueryPerformanceCounter(&qpc);QueryPerformanceFrequency(&frequency);compositorUtc=UnixMicroseconds()+(static_cast<double>(stamp)/10.0-static_cast<double>(qpc.QuadPart)*1000000.0/frequency.QuadPart);
   }
   if(!haveFrame){if(Clock::now()-start>std::chrono::seconds(10))throw std::runtime_error("No game frame received");std::this_thread::sleep_for(std::chrono::milliseconds(2));continue;}
   if(frames==0){next=Clock::now();firstUtc=UnixMicroseconds();firstCompositorUtc=compositorUtc;Metadata(o,false,0,0,firstUtc,firstCompositorUtc);}
   if(Clock::now()-next>std::chrono::milliseconds(500))throw std::runtime_error("Capture cannot sustain real time; preserve incomplete video, do not accelerate replay");
   if(!fresh)duplicates++;
   size_t written=0;while(written<pixels.size()){DWORD count=0;DWORD amount=static_cast<DWORD>(std::min<size_t>(1048576,pixels.size()-written));if(!WriteFile(pipe,pixels.data()+written,amount,&count,nullptr)||count==0)throw std::runtime_error("Encoder pipe write failed");written+=count;}
   frames++;next+=period;std::this_thread::sleep_until(next);
  }
  session.Close();pool.Close();if(!FlushFileBuffers(pipe))throw std::runtime_error("Encoder pipe flush failed");CloseHandle(pipe);pipe=INVALID_HANDLE_VALUE;Metadata(o,true,frames,duplicates,firstUtc,firstCompositorUtc);std::cout<<"WGC_COMPLETE frames="<<frames<<" duplicates="<<duplicates<<std::endl;return 0;
 }catch(hresult_error const&e){std::wcerr<<L"WGC_FAILED "<<e.message().c_str()<<L" HRESULT="<<std::hex<<e.code().value<<std::endl;}catch(std::exception const&e){std::cerr<<"WGC_FAILED "<<e.what()<<std::endl;}
 if(pipe!=INVALID_HANDLE_VALUE)CloseHandle(pipe);return 1;
}
