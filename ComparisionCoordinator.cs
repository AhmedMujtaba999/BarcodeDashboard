using System;

namespace BarcodeDashboard
{
    public class ComparisonCoordinator
    {
        private string _last1 = "";
        private string _last2 = "";
        private bool _new1 = false;
        private bool _new2 = false;

        // Options
        public bool IgnoreCase { get; set; } = false;
        public bool TrimWhitespace { get; set; } = true;

        // Fires when both cams have new values; args: (raw1, raw2, match)
        public event Action<string, string, bool> Compared;

        private string Normalize(string s)
        {
            if (s == null) return "";
            if (TrimWhitespace) s = s.Trim();
            return IgnoreCase ? s.ToUpperInvariant() : s;
        }

        public void OnCam1(string value)
        {
            _last1 = value;
            _new1 = true;
            TryCompare();
        }

        public void OnCam2(string value)
        {
            _last2 = value;
            _new2 = true;
            TryCompare();
        }

        public void ResetPending()
        {
            _new1 = false;
            _new2 = false;
        }

        private void TryCompare()
        {
            if (_new1 && _new2)
            {
                string n1 = Normalize(_last1);
                string n2 = Normalize(_last2);
                bool match = (n1 == n2);

                if (Compared != null) Compared(_last1, _last2, match);

                // wait for next pair
                _new1 = false;
                _new2 = false;
            }
        }
    }
}