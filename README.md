## BarcodeDashboard

Windows desktop app (C#/.NET 8, WinForms) for reading barcodes from multiple scanners/cameras and comparing their outputs. It supports serial (COM) scanners and TCP/IP-based cameras behind a simple `IScanner` abstraction.

### Features
- Connect to barcode scanners over Serial (COM) or TCP/IP
- Unified scanner interface via `IScanner`
- Compare barcode data from two sources and show match/mismatch
- Basic UI to view scans and switch/select devices

### Tech Stack
- .NET 8 (Windows)
- WinForms (`Form1` as the main form)
- Serial and TCP handlers in `cameras/`

### Project Layout (key files)
- `Program.cs`: App entry point
- `Form1.cs`: Main UI and event wiring
- `cameras/IScanner.cs`: Scanner abstraction
- `cameras/SerialScanner.cs`: Serial COM implementation
- `cameras/TcpCameraHandler.cs`: TCP/IP implementation
- `CameraHandler.cs`, `CameraSetup.cs`, `CamSelector.cs`: Device setup and selection
- `ComparisionCoordinator.cs`: Core logic to compare two scanner streams

### Build & Run
1. Install .NET 8 SDK (Windows).
2. Open the solution folder in your IDE or run:
   - `dotnet build`
   - `dotnet run` (or start from IDE)

### Add Two Scanners (basic steps)
1. Connect devices:
   - Serial scanner(s): Plug in via USB; note COM port(s).
   - TCP camera(s): Ensure each has a reachable IP and port.
2. Configure in code (typical entry points: `CameraSetup` or `Form1`):
   - Create two `IScanner` instances (any mix of `SerialScanner`/`TcpCameraHandler`).
   - Subscribe to their scan events and register them as active devices.
3. Initialize on startup:
   - Open the serial port(s) and/or connect TCP clients.
   - Use `CamSelector` or UI controls to pick the active devices if needed.
4. Compare:
   - Feed both scanners into `ComparisionCoordinator`.
   - React to match/mismatch events in `Form1` (e.g., highlight or notify).
5. Test:
   - Trigger each scanner and verify both the raw values and comparison result in the UI.

Tip: Keep each scanner on unique COM ports or unique TCP endpoints. For custom rules (tolerances, timeouts, prioritization), extend `ComparisionCoordinator` or handle in `Form1`.


