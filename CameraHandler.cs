using System;
using System.IO.Ports;

namespace BarcodeDashboard
{
    public class CameraHandler : IDisposable
    {
        public string PortName { get; private set; }
        public string LastScan { get; private set; }
        public string NewLine { get; set; } = "\r\n";

        private readonly SerialPort _port;

        public event Action<string> BarcodeScanned;      // fires on each scan (string)
        public event Action<Exception> ErrorOccurred;    // optional error event

        public CameraHandler(string portName, int baud = 9600, Parity parity = Parity.None, int dataBits = 8, StopBits stopBits = StopBits.One)
        {
            PortName = portName;
            _port = new SerialPort(portName, baud, parity, dataBits, stopBits);
        }

        public void Start()
        {
            if (_port.IsOpen) return;
            _port.NewLine = NewLine;
            _port.DataReceived += OnData;
            _port.Open();
        }

        public void Stop()
        {
            try
            {
                _port.DataReceived -= OnData;
                if (_port.IsOpen) _port.Close();
            }
            catch (Exception ex)
            {
                if (ErrorOccurred != null) ErrorOccurred(ex);
            }
        }

        private void OnData(object sender, SerialDataReceivedEventArgs e)
        {
            try
            {
                string line = _port.ReadLine();
                line = line == null ? "" : line.Trim();
                LastScan = line;
                if (BarcodeScanned != null) BarcodeScanned(line);
            }
            catch (Exception ex)
            {
                if (ErrorOccurred != null) ErrorOccurred(ex);
            }
        }

        public void Dispose()
        {
            Stop();
            try { _port.Dispose(); } catch { }
        }
    }
}