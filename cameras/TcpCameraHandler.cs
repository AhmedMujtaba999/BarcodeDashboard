using System;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace BarcodeDashboard.Cameras
{
    public class TcpCameraHandler : IScanner
    {
        public string IpAddress { get; private set; }
        public int    Port      { get; private set; }
        public string LastScan  { get; private set; } = "";
        public string NewLine   { get; set; } = "\r\n";

        public event Action<string>   BarcodeScanned;
        public event Action<Exception> ErrorOccurred;

        private TcpClient _client;
        private NetworkStream _stream;
        private Thread _rxThread;
        private volatile bool _running;

        public TcpCameraHandler(string ipAddress, int port)
        {
            IpAddress = ipAddress;
            Port      = port;
        }

        public void Start()
        {
            if (_running) return;
            _running = true;
            _rxThread = new Thread(ReceiveLoop) { IsBackground = true, Name = "TcpCameraReceiver" };
            _rxThread.Start();
        }

        private void ReceiveLoop()
        {
            try
            {
                _client = new TcpClient();
                _client.Connect(IpAddress, Port);
                _stream = _client.GetStream();

                byte[] buf = new byte[4096];
                var sb = new StringBuilder();

                while (_running)
                {
                    int n = _stream.Read(buf, 0, buf.Length);
                    if (n <= 0) break;

                    sb.Append(Encoding.ASCII.GetString(buf, 0, n));

                    string text = sb.ToString();
                    int idx;
                    while (!string.IsNullOrEmpty(NewLine) &&
                           (idx = text.IndexOf(NewLine, StringComparison.Ordinal)) >= 0)
                    {
                        string line = text.Substring(0, idx).Trim();
                        text = text.Substring(idx + NewLine.Length);
                        if (line.Length > 0)
                        {
                            LastScan = line;
                            BarcodeScanned?.Invoke(line);
                        }
                    }
                    sb.Clear();
                    sb.Append(text);
                }
            }
            catch (Exception ex)
            {
                if (_running) ErrorOccurred?.Invoke(ex);
            }
        }

        public void Stop()
        {
            _running = false;
            try { _stream?.Close(); } catch { }
            try { _client?.Close(); } catch { }
            _stream = null;
            _client = null;
        }

        public void Dispose() => Stop();
    }
}
