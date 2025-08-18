using System;
using System.IO.Ports;

namespace BarcodeDashboard.Cameras
{
    public class SerialScanner : IScanner
    {
        public string PortName { get; private set; }
        public string LastScan { get; private set; }
        public string NewLine { get; set; } = "\r\n";

        private readonly SerialPort _port;

        public event Action<string> BarcodeScanned;
        public event Action<Exception> ErrorOccurred;

        public SerialScanner(string portName, int baud = 9600, Parity parity = Parity.None, int dataBits = 8, StopBits stopBits = StopBits.One)
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
                ErrorOccurred?.Invoke(ex);
            }
        }

        private void OnData(object sender, SerialDataReceivedEventArgs e)
        {
            try
            {
                string line = _port.ReadLine();
                line = line == null ? "" : line.Trim();
                LastScan = line;
                BarcodeScanned?.Invoke(line);
            }
            catch (Exception ex)
            {
                ErrorOccurred?.Invoke(ex);
            }
        }

        public void Dispose()
        {
            Stop();
            try { _port.Dispose(); } catch { }
        }
    }
}
