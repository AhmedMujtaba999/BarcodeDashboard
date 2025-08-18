using System;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;

namespace BarcodeDashboard
{
    public class CamSelector
    {
        private readonly FlowLayoutPanel _row;
        private readonly List<CheckBox> _boxes = new List<CheckBox>();

        public Control Control => _row;   // expose the whole row for Form1
        public IReadOnlyList<CheckBox> Boxes => _boxes;

        public event Action SelectionChanged;

        public CamSelector()
        {
            _row = new FlowLayoutPanel();
            _row.Dock = DockStyle.Top;
            _row.Height = 100;
            _row.Padding = new Padding(12);
            _row.FlowDirection = FlowDirection.LeftToRight;
            _row.WrapContents = false;
            _row.AutoScroll = true;

            for (int i = 0; i < 7; i++)
            {
                CheckBox cb = CreateToggleBox();
                cb.Tag = i; // left index
                cb.CheckedChanged += (s, e) => UpdateCamLabels();
                _boxes.Add(cb);
                _row.Controls.Add(cb);
            }

            RefreshFieldLabels();
            UpdateCamLabels();
        }

        private CheckBox CreateToggleBox()
        {
            CheckBox cb = new CheckBox();
            cb.Appearance = Appearance.Button;
            cb.TextAlign = ContentAlignment.MiddleCenter;
            cb.AutoSize = false;
            cb.Width = 110;
            cb.Height = 60;
            cb.Margin = new Padding(8);
            cb.FlatStyle = FlatStyle.Flat;
            cb.UseVisualStyleBackColor = false;
            cb.BackColor = Color.Gainsboro;
            cb.FlatAppearance.BorderSize = 2;
            cb.FlatAppearance.BorderColor = Color.Gray;
            return cb;
        }

        private int RightBasedFieldNumber(int leftIndex)
        {
            return _boxes.Count - leftIndex; // left 0 -> Field 7, right 6 -> Field 1
        }

        private void RefreshFieldLabels()
        {
            for (int i = 0; i < _boxes.Count; i++)
            {
                CheckBox cb = _boxes[i];
                if (!cb.Checked)
                {
                    int fieldNum = RightBasedFieldNumber(i);
                    cb.Text = "Field " + fieldNum;
                    cb.BackColor = Color.Gainsboro;
                    cb.FlatAppearance.BorderColor = Color.Gray;
                    cb.Font = new Font(cb.Font, FontStyle.Regular);
                }
            }
        }

        private void UpdateCamLabels()
        {
            RefreshFieldLabels();

            int cam = 1;
            for (int i = _boxes.Count - 1; i >= 0; i--)
            {
                CheckBox cb = _boxes[i];
                if (!cb.Checked) continue;

                int fieldNum = RightBasedFieldNumber(i);
                if (cam <= 2)
                {
                    cb.Text = "Field " + fieldNum + "\nCam " + cam;
                    cb.BackColor = Color.LightGreen;
                    cb.FlatAppearance.BorderColor = Color.SeaGreen;
                    cb.Font = new Font(cb.Font, FontStyle.Bold);
                    cam++;
                }
                else
                {
                    cb.Text = "Field " + fieldNum + "\n(Selected)";
                    cb.BackColor = Color.LightYellow;
                    cb.FlatAppearance.BorderColor = Color.Goldenrod;
                    cb.Font = new Font(cb.Font, FontStyle.Bold);
                }
            }

            SelectionChanged?.Invoke();
        }
    }
}