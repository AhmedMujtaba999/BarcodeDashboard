// Form1.cs
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;
using BarcodeDashboard.Cameras;   // IScanner, SerialScanner, TcpCameraHandler
                                  // (in Cameras/ folder)
namespace BarcodeDashboard
{
    public partial class Form1 : Form
    {
        // UI
        private CamSelector _selector;
        private Label _lblStatus;
        private Label _lblCam1;
        private Label _lblCam2;
        private Button _btnStart;
        private Button _btnStop;

        // Services
        private readonly Dictionary<int, IScanner> _scanners = new();
        private ComparisonCoordinator _compare;

        public Form1()
        {
            InitializeComponent();   // safe even if minimal designer
            BuildUI();
            WireLogic();
        }

        private void BuildUI()
        {
            Text = "Field Selector → Start Scan → Auto Compare";
            Width = 980;
            Height = 420;
            StartPosition = FormStartPosition.CenterScreen;

            // Row with 7 right-based boxes that auto-assign "Cam 1" then "Cam 2"
            _selector = new CamSelector();
            Controls.Add(_selector.Control);

            // Status group
            var grp = new GroupBox
            {
                Text = "Status",
                Left = 12,
                Top = _selector.Control.Bottom + 8,
                Width = ClientSize.Width - 24,
                Height = 150,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
            };
            Controls.Add(grp);

            _lblStatus = new Label
            {
                Text = "Waiting to start…",
                Left = 16,
                Top = 28,
                AutoSize = true,
                Font = new Font("Segoe UI", 12, FontStyle.Bold),
                ForeColor = Color.Black
            };
            grp.Controls.Add(_lblStatus);

            _lblCam1 = new Label
            {
                Text = "Cam 1 last: —",
                Left = 16,
                Top = 65,
                AutoSize = true
            };
            grp.Controls.Add(_lblCam1);

            _lblCam2 = new Label
            {
                Text = "Cam 2 last: —",
                Left = 16,
                Top = 95,
                AutoSize = true
            };
            grp.Controls.Add(_lblCam2);

            // Start/Stop
            _btnStart = new Button
            {
                Text = "Start Scan",
                Left = grp.Right - 220,
                Top = 28,
                Width = 90,
                Anchor = AnchorStyles.Top | AnchorStyles.Right
            };
            _btnStop = new Button
            {
                Text = "Stop",
                Left = grp.Right - 120,
                Top = 28,
                Width = 90,
                Anchor = AnchorStyles.Top | AnchorStyles.Right,
                Enabled = false
            };
            _btnStart.Click += (s, e) => StartScanning();
            _btnStop.Click  += (s, e) => StopScanning();
            grp.Controls.Add(_btnStart);
            grp.Controls.Add(_btnStop);
        }

        private void WireLogic()
        {
            _compare = new ComparisonCoordinator
            {
                IgnoreCase = false,
                TrimWhitespace = true
            };

            _compare.Compared += (raw1, raw2, match) =>
            {
                if (InvokeRequired)
                    BeginInvoke(new Action(() => ShowCompare(raw1, raw2, match)));
                else
                    ShowCompare(raw1, raw2, match);
            };
        }

        private void ShowCompare(string raw1, string raw2, bool match)
        {
            _lblCam1.Text = "Cam 1 last: " + (string.IsNullOrEmpty(raw1) ? "—" : raw1);
            _lblCam2.Text = "Cam 2 last: " + (string.IsNullOrEmpty(raw2) ? "—" : raw2);

            _lblStatus.Text = match ? "MATCH ✅" : "NO MATCH ❌";
            _lblStatus.ForeColor = match ? Color.Green : Color.Red;
        }

        private void StartScanning()
        {
            try
            {
                _compare.ResetPending();
                _lblStatus.Text = "Waiting for scans…";
                _lblStatus.ForeColor = Color.Black;
                _lblCam1.Text = "Cam 1 last: —";
                _lblCam2.Text = "Cam 2 last: —";

                // Build scanner instances from a single definition point
                var specs    = CameraSetup.LoadDefaults();   // edit ports/IPs in CameraSetup.cs
                var scanners = CameraSetup.Build(specs);     // CamNo -> IScanner

                foreach (var kv in scanners)
                {
                    int camNo = kv.Key;
                    IScanner scanner = kv.Value;

                    scanner.BarcodeScanned += value => OnCamRead(camNo, value);
                    scanner.ErrorOccurred  += ex    => ShowError($"Cam {camNo}", ex);

                    scanner.Start();
                    _scanners[camNo] = scanner;
                }

                _btnStart.Enabled = false;
                _btnStop.Enabled  = true;

                // Show active transports in status
                _lblStatus.Text = BuildActiveSourcesLine(specs);
                _lblStatus.ForeColor = Color.Black;
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to start scanning:\n" + ex.Message, "Error");
                StopScanning();
            }
        }

        private string BuildActiveSourcesLine(IDictionary<int, CameraSpec> specs)
        {
            var parts = new System.Text.StringBuilder("Listening…  ");
            foreach (var s in specs.Values)
            {
                if (s.Kind == CameraKind.Serial)
                    parts.Append($"Cam{s.CamNo}:SER({s.PortName})  ");
                else
                    parts.Append($"Cam{s.CamNo}:TCP({s.Ip}:{s.Port})  ");
            }
            return parts.ToString().TrimEnd();
        }

        private void OnCamRead(int camNo, string code)
        {
            // UI update for individual cam
            if (InvokeRequired) BeginInvoke(new Action(() =>
            {
                if (camNo == 1) _lblCam1.Text = "Cam 1 last: " + code;
                if (camNo == 2) _lblCam2.Text = "Cam 2 last: " + code;
            }));
            else
            {
                if (camNo == 1) _lblCam1.Text = "Cam 1 last: " + code;
                if (camNo == 2) _lblCam2.Text = "Cam 2 last: " + code;
            }

            // Feed comparison engine (current design compares Cam 1 vs Cam 2)
            if (camNo == 1) _compare.OnCam1(code);
            if (camNo == 2) _compare.OnCam2(code);

            // Helpful hint while waiting for the "other" side
            bool has1 = _scanners.ContainsKey(1);
            bool has2 = _scanners.ContainsKey(2);
            if ((camNo == 1 && has1 && !has2) || (camNo == 2 && has2 && !has1))
            {
                if (InvokeRequired) BeginInvoke(new Action(() =>
                    _lblStatus.Text = $"Cam {camNo} received, waiting for the other camera…"));
                else
                    _lblStatus.Text = $"Cam {camNo} received, waiting for the other camera…";
            }
        }

        private void ShowError(string camLabel, Exception ex)
        {
            if (InvokeRequired) BeginInvoke(new Action(() =>
                MessageBox.Show($"{camLabel} error: {ex.Message}", "I/O Error")));
            else
                MessageBox.Show($"{camLabel} error: {ex.Message}", "I/O Error");
        }

        private void StopScanning()
        {
            foreach (var kv in _scanners)
            {
                try { kv.Value.Dispose(); } catch { }
            }
            _scanners.Clear();

            _btnStart.Enabled = true;
            _btnStop.Enabled  = false;
            _lblStatus.Text = "Stopped.";
            _lblStatus.ForeColor = Color.Black;
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            StopScanning();
            base.OnFormClosing(e);
        }
    }
}