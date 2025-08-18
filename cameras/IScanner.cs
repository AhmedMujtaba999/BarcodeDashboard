namespace BarcodeDashboard.Cameras
{
    public interface IScanner : System.IDisposable
    {
        event System.Action<string> BarcodeScanned;
        event System.Action<System.Exception> ErrorOccurred;
        void Start();
        void Stop();

        string NewLine { get; set; }
        string LastScan { get; }
    }
}