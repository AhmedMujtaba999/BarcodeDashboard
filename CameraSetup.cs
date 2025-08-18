using System;
using System.Collections.Generic;
using BarcodeDashboard.Cameras;   // <-- add this

namespace BarcodeDashboa
{
    public enum CameraKind { Serial, Tcp }

    public sealed class CameraSpec
    {
        public int CamNo { get; set; }
        public CameraKind Kind { get; set; }
        public string PortName { get; set; }
        public int Baud { get; set; } = 9600;
        public string Ip { get; set; }
        public int Port { get; set; }
        public string NewLine { get; set; } = "\r\n";
        public string Label { get; set; }
    }

    public static class CameraSetup
    {
        public static Dictionary<int, IScanner> Build(IDictionary<int, CameraSpec> specs)
        {
            var result = new Dictionary<int, IScanner>();
            foreach (var kv in specs)
            {
                var s = kv.Value;
                IScanner scanner = s.Kind switch
                {
                    CameraKind.Serial => new SerialScanner(s.PortName, s.Baud) { NewLine = s.NewLine },
                    CameraKind.Tcp    => new TcpCameraHandler(s.Ip, s.Port)    { NewLine = s.NewLine },
                    _ => throw new NotSupportedException($"Unsupported camera kind: {s.Kind}")
                };
                result[s.CamNo] = scanner;
            }
            return result;
        }

        public static Dictionary<int, CameraSpec> LoadDefaults()
        {
            return new Dictionary<int, CameraSpec>
            {
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
            };
        }
    }
}
