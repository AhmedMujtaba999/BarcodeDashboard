# BarcodeDashboard

A Windows desktop app (C# / .NET 8, WinForms) that reads barcodes from two scanners at once and tells you instantly whether they match. It supports serial (COM) scanners and TCP/IP cameras behind a single `IScanner` interface, so the UI and comparison logic don't care how a device is connected.

---

## Demo

![BarcodeDashboard demo](/demo.gif)

**Full-quality video:** [▶ Watch demo.mp4](/demo.mp4)

<!-- To show a video player here: edit this file on github.com, drag demo/demo.mp4 onto the empty line below, wait for the https://github.com/user-attachments/assets/... link to appear, then commit. -->


*Animated walkthrough of the scan → compare flow, using the app's real layout and comparison rules.*

---

## Features

- **Two-scanner comparison**: Cam 1 and Cam 2 are compared as soon as both send a new value, and the result shows as **MATCH ✅** or **NO MATCH ❌**
- **Serial (COM) scanners** via `System.IO.Ports`, reading one barcode per line
- **TCP/IP cameras** on a background receive thread, so the UI never freezes
- **One interface for every device**: `IScanner` exposes `BarcodeScanned` and `ErrorOccurred` events, and new transports plug in without UI changes
- **Field selector**: 7 toggle boxes (Field 7 … Field 1); the first two selected from the right are labelled Cam 1 and Cam 2
- **Configurable matching**: trim whitespace and ignore case options in `ComparisonCoordinator`
- **Thread-safe UI updates** with `BeginInvoke`, plus error dialogs for I/O failures

---

## How It Works

```text
 Cam 1: SerialScanner (COM1, 9600)  ──┐
                                      ├──>  IScanner.BarcodeScanned
 Cam 2: TcpCameraHandler (IP:port)  ──┘              │
                                                     v
                                          ComparisonCoordinator
                                   waits for a new value from both cams,
                                   normalizes (trim / case), compares
                                                     │
                                                     v
                                    Form1: "Cam 1 last" / "Cam 2 last"
                                           MATCH ✅ / NO MATCH ❌
```

1. **Start Scan** builds both scanners from `CameraSetup.LoadDefaults()` and starts them.
2. Each read updates the matching **Cam N last** label and is passed to `ComparisonCoordinator`.
3. Once **both** cameras have sent a new value, the coordinator compares the pair and raises `Compared(raw1, raw2, match)`.
4. `Form1` shows the result, and the coordinator waits for the next pair.

---

## Tech Stack

- C# / .NET 8 (`net8.0-windows`)
- Windows Forms
- `System.IO.Ports` for serial communication
- `System.Net.Sockets` (`TcpClient`) for TCP cameras

---

## Project Structure

```text
BarcodeDashboard/
│
├── Program.cs                  # App entry point
├── Form1.cs                    # Main UI: field selector, status, Start/Stop, event wiring
├── Form1.Designer.cs
├── CamSelector.cs              # Row of 7 field toggles, labels Cam 1 / Cam 2
├── CameraSetup.cs              # CameraSpec + LoadDefaults() + Build() — configure devices here
├── ComparisionCoordinator.cs   # ComparisonCoordinator: pairs and compares Cam 1 vs Cam 2
├── CameraHandler.cs            # Original serial handler (superseded by SerialScanner)
├── cameras/
│   ├── IScanner.cs             # Scanner abstraction
│   ├── SerialScanner.cs        # Serial (COM) implementation
│   └── TcpCameraHandler.cs     # TCP/IP implementation
├── demo/                       # Demo video + script that generates it
└── BarcodeDashboard.csproj
```

---

## Getting Started

### Prerequisites

- Windows 10 or 11
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
- Optional: Visual Studio 2022 with the **.NET desktop development** workload

### Build & Run

```bash
git clone https://github.com/AhmedMujtaba999/BarcodeDashboard.git
cd BarcodeDashboard
dotnet build
dotnet run
```

Or open `BarcodeDashboard.csproj` in Visual Studio and press **F5**.

---

## Configure Your Scanners

Devices are defined in one place: `CameraSetup.LoadDefaults()` in `CameraSetup.cs`. The defaults are set up for a Cognex reader on `COM1` and a Keyence camera at `192.168.0.100:2112`:

```csharp
[1] = new CameraSpec
{
    CamNo = 1, Kind = CameraKind.Serial,
    PortName = "COM1", Baud = 9600, NewLine = "\r\n",
    Label = "Cognex RS-232"
},
[2] = new CameraSpec
{
    CamNo = 2, Kind = CameraKind.Tcp,
    Ip = "192.168.0.100", Port = 2112, NewLine = "\r\n",
    Label = "Keyence TCP"
},
```

| Field | Used by | Meaning |
|---|---|---|
| `CamNo` | both | 1 or 2 — which side of the comparison this device feeds |
| `Kind` | both | `CameraKind.Serial` or `CameraKind.Tcp` |
| `PortName` | Serial | COM port, e.g. `COM3` (check Device Manager → Ports) |
| `Baud` | Serial | Baud rate, default `9600` |
| `Ip`, `Port` | TCP | Camera address and port |
| `NewLine` | both | Line terminator the device sends after each barcode, default `\r\n` |
| `Label` | both | Friendly name for the device |

Any mix works: two serial scanners, two TCP cameras, or one of each. Give each scanner its own COM port or TCP endpoint.

---

## Using the App

1. **Select fields.** Click the field boxes to mark which fields the cameras cover. The first selected box from the right becomes **Cam 1** and the second becomes **Cam 2** (shown in green). Any extra selections are marked **(Selected)** in yellow.
2. **Start Scan.** The status line confirms what's connected, e.g. `Listening…  Cam1:SER(COM1)  Cam2:TCP(192.168.0.100:2112)`.
3. **Scan.** Trigger both scanners. Each read updates **Cam 1 last** / **Cam 2 last**, and once both have a new value the status shows **MATCH ✅** in green or **NO MATCH ❌** in red.
4. **Stop.** This closes the COM port and TCP connection. Closing the window stops scanning too.

> Note: the field selector currently labels the fields visually. The devices themselves always come from `CameraSetup.LoadDefaults()`.

---

## Comparison Rules

`ComparisonCoordinator` is configured in `Form1.WireLogic()`:

```csharp
_compare = new ComparisonCoordinator
{
    IgnoreCase = false,     // set true to treat "abc123" and "ABC123" as a match
    TrimWhitespace = true   // ignore leading/trailing spaces
};
```

- A comparison happens only after **both** cameras send a **new** value, in any order.
- After each comparison the coordinator waits for a fresh pair.
- **Start Scan** clears any half-finished pair.

For custom rules (tolerances, timeouts, prioritization), extend `ComparisonCoordinator` or handle them in `Form1`.

---

## Adding a New Scanner Type

1. Implement `IScanner`:

```csharp
public class MyScanner : IScanner
{
    public event Action<string> BarcodeScanned;
    public event Action<Exception> ErrorOccurred;
    public string NewLine { get; set; } = "\r\n";
    public string LastScan { get; private set; } = "";

    public void Start() { /* connect, then raise BarcodeScanned(value) for each read */ }
    public void Stop()  { /* disconnect */ }
    public void Dispose() => Stop();
}
```

2. Add a value to `CameraKind` and a case in `CameraSetup.Build()`.
3. Use it in `LoadDefaults()`. Nothing in `Form1` or `ComparisonCoordinator` needs to change.

---

## Troubleshooting

| Problem | Check |
|---|---|
| `Access to the path 'COM1' is denied` | Another program (e.g. the scanner's setup tool) has the COM port open. Close it. |
| COM port not found | Confirm the port number in Device Manager → Ports and update `PortName`. |
| TCP camera never connects | Ping the IP, confirm the port, and allow the app through Windows Firewall. |
| Scans never show up | The device's line terminator doesn't match `NewLine`. Try `"\r"` or `"\n"`. |
| Always NO MATCH for the same code | Check for case differences (set `IgnoreCase = true`) or prefixes/suffixes added by a scanner. |

---

## Roadmap

- Load device settings from `appsettings.json` instead of code
- Use the field selector to choose which devices are active
- Log every scan and result to CSV
- Auto-reconnect for TCP cameras
- Support more than two cameras

---

## Regenerating the Demo

The demo video is generated by [`demo/make_demo_video.py`](demo/make_demo_video.py) (Python):

```bash
pip install -r demo/requirements.txt
python demo/make_demo_video.py
```

Edit `SCANS` at the top of the script to change the barcodes shown.
