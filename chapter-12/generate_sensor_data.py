import argparse
import os
from datetime import datetime, timedelta
import random
import string

import polars as pl


def rand_id(prefix: str = "S_", n: int = 4) -> str:
    return f"{prefix}{''.join(random.choices(string.digits, k=n))}"


def synthesize_day(date: datetime, rows: int, facilities: list[str], device_types: list[str]) -> pl.DataFrame:
    rng = random.Random(int(date.strftime('%Y%m%d')))
    sensor_ids = [rand_id(n=rng.randint(3, 5)) for _ in range(rows)]
    device_type = [rng.choice(device_types) for _ in range(rows)]
    facility = [rng.choice(facilities) for _ in range(rows)]

    base_ts = datetime(date.year, date.month, date.day)
    ts = [base_ts + timedelta(seconds=rng.randint(0, 86399)) for _ in range(rows)]

    temp = [round(rng.gauss(70, 10), 1) for _ in range(rows)]
    pressure = [round(rng.gauss(120, 20), 1) for _ in range(rows)]
    vibration = [round(max(0.0, rng.gauss(6, 3)), 1) for _ in range(rows)]

    status = []
    for i in range(rows):
        s = "normal"
        if temp[i] > 85 or pressure[i] > 145 or vibration[i] > 10:
            s = "warning"
        if temp[i] > 92 or pressure[i] > 152 or vibration[i] > 12:
            s = "critical"
        status.append(s)

    return pl.DataFrame(
        {
            "timestamp": ts,
            "sensor_id": sensor_ids,
            "device_type": device_type,
            "temperature": temp,
            "pressure": pressure,
            "vibration": vibration,
            "status": status,
            "facility": facility,
        }
    )


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic sensor readings as Parquet files")
    parser.add_argument("--out", default="data/sensors", help="Output base directory")
    parser.add_argument("--start", default="2024-12-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to generate")
    parser.add_argument("--rows-per-day", type=int, default=20000, help="Rows per day")
    parser.add_argument("--facilities", default="A01,B01,B03,C05", help="Comma-separated facility codes")
    parser.add_argument("--device-types", default="pump,motor,compressor", help="Comma-separated device types")
    args = parser.parse_args()

    facilities = [x.strip() for x in args.facilities.split(",") if x.strip()]
    device_types = [x.strip() for x in args.device_types.split(",") if x.strip()]

    start = datetime.fromisoformat(args.start)
    out_base = args.out.rstrip("/")

    for d in range(args.days):
        day = start + timedelta(days=d)
        year = f"year={day.year:04d}"
        month = f"month={day.month:02d}"
        daydir = f"day={day.day:02d}"
        out_dir = os.path.join(out_base, year, month, daydir)
        os.makedirs(out_dir, exist_ok=True)

        df = synthesize_day(day, args.rows_per_day, facilities, device_types)
        out_path = os.path.join(out_dir, f"sensors_{day.strftime('%Y%m%d')}.parquet")
        df.write_parquet(out_path)
        print(f"Wrote {out_path} with {df.height} rows")


if __name__ == "__main__":
    main()

