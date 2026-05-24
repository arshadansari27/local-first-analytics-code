# Business Rules

- `status = warning` is set when any reading approaches a critical threshold:
  temperature 85-92°C, pressure 145-152 PSI, or vibration 10-12 mm/s.
- `status = critical` indicates a reading exceeded a critical threshold
  (temperature > 92°C, pressure > 152 PSI, or vibration > 12 mm/s) and
  requires immediate maintenance attention.
- Normal vibration range for healthy rotating equipment is 0-8 mm/s.
  Values above 10 mm/s suggest bearing wear or misalignment.
- Pumps in facility B03 historically run 2-3°C hotter than other facilities;
  adjust comparisons accordingly.
