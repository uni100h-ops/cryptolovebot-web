#!/usr/bin/env python3
"""Import completed simulator trades from a local XLSX; Python 3.9+, stdlib only.

Example:
  python3 import_history.py /path/to/trades.xlsx --start-year 2025 --end-year 2026

The source exports local clock times in F/G and an explicit UTC opening in Q.
Europe/Madrid matches the supplied workbook; change --timezone only when the
source machine used another timezone. No URLs, network calls or formula execution.
"""
import argparse
import hashlib
import json
import math
import posixpath
import re
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from zoneinfo import ZoneInfo

UTC = timezone.utc
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
FIELDS = {
    "coin": "moneda", "side": "sentido",
    "open": "dia_hora_apertura_operacion", "close": "dia_hora_cierre_operacion",
    "priceReturnPct": "beneficio_perdida_pct", "status": "calculo_beneficio",
    "entry": "Precio entrada", "exit": "Precio de salida",
    "profitUsdc": "beneficio_usdc", "capitalReturnPct": "beneficio_%",
    "accountBalance": "saldo_cuenta_usd", "utcOpen": "TradingView",
}


def xml_member(archive, member):
    data = archive.read(member)
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("XML declarations/entities are not supported")
    return ET.fromstring(data)


def read_rows(path, sheet_name):
    with ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > 2000 or sum(i.file_size for i in entries) > 100_000_000:
            raise ValueError("Workbook exceeds importer size limit (100 MB expanded)")
        workbook = xml_member(archive, "xl/workbook.xml")
        properties = workbook.find("s:workbookPr", NS)
        epoch = datetime(1904, 1, 1) if properties is not None and properties.get("date1904") in {"1", "true"} else datetime(1899, 12, 30)
        sheet = next((s for s in workbook.findall("s:sheets/s:sheet", NS) if s.get("name") == sheet_name), None)
        if sheet is None:
            raise ValueError(f"Missing worksheet: {sheet_name}")
        rid = sheet.get("{" + R_NS + "}id")
        relationships = xml_member(archive, "xl/_rels/workbook.xml.rels")
        relation = next((r for r in relationships if r.get("Id") == rid), None)
        if relation is None or relation.get("TargetMode") == "External":
            raise ValueError("Worksheet must be embedded in this local workbook")
        target = relation.get("Target", "")
        member = posixpath.normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
        if not member.startswith("xl/worksheets/"):
            raise ValueError("Invalid worksheet path")
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = ["".join(si.itertext()) for si in xml_member(archive, "xl/sharedStrings.xml").findall("s:si", NS)]
        data = []
        for row in xml_member(archive, member).findall("s:sheetData/s:row", NS):
            values = {}
            for cell in row.findall("s:c", NS):
                column = re.sub(r"\d", "", cell.get("r", ""))
                value = cell.find("s:v", NS)
                inline = cell.find("s:is", NS)
                text = value.text if value is not None else "".join(inline.itertext()) if inline is not None else ""
                if cell.get("t") == "s":
                    text = shared[int(text)]
                if cell.get("t") == "e":
                    raise ValueError(f"Excel error in {cell.get('r')}: {text}")
                values[column] = text or ""
            if values:
                data.append((int(row.get("r")), values))
        return data, epoch


def local_date(value, epoch):
    try:
        # Round away the floating-point microseconds in Excel serial dates.
        return epoch + timedelta(seconds=round(float(value) * 86400))
    except ValueError:
        for pattern in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(value, pattern)
            except ValueError:
                pass
    raise ValueError(f"Unsupported date: {value!r}")


def to_utc(local, zone):
    candidates = []
    for fold in (0, 1):
        utc = local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if utc.astimezone(zone).replace(tzinfo=None) == local and utc not in candidates:
            candidates.append(utc)
    if len(candidates) != 1:
        raise ValueError(f"Ambiguous or nonexistent local closing time {local}; provide source with explicit UTC")
    return candidates[0]


def iso(value):
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def numeric(value, label, row):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Non-finite {label} in row {row}")
    return result


def build(path, sheet_name, zone_name, start_year=None, end_year=None):
    rows, epoch = read_rows(path, sheet_name)
    if not rows:
        raise ValueError("Empty worksheet")
    header = {label: col for col, label in rows[0][1].items()}
    missing = set(FIELDS.values()) - set(header)
    if missing:
        raise ValueError("Missing source columns: " + ", ".join(sorted(missing)))
    columns = {key: header[label] for key, label in FIELDS.items()}
    zone = ZoneInfo(zone_name)
    excluded = {"notExecuted": 0, "incomplete": 0, "outsidePeriod": 0}
    offsets = Counter()
    checked = 0
    candidates = []
    for row_id, raw in rows[1:]:
        cells = {key: raw.get(col, "").strip() for key, col in columns.items()}
        if not cells["coin"]:
            excluded["incomplete"] += 1
            continue
        opened = None
        if cells["open"] and cells["utcOpen"]:
            match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC", cells["utcOpen"])
            if not match:
                raise ValueError(f"Missing explicit UTC opening label in row {row_id}")
            opened = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            local_open = local_date(cells["open"], epoch)
            converted = opened.astimezone(zone).replace(tzinfo=None)
            if local_open != converted and local_open != converted.replace(second=0, microsecond=0):
                raise ValueError(f"Timezone {zone_name} does not match UTC label in row {row_id}")
            checked += 1
            offsets[str(opened.astimezone(zone).utcoffset())] += 1
        if cells["status"].casefold().startswith("no ejecutada"):
            excluded["notExecuted"] += 1
            continue
        if not opened or not cells["close"] or any(not cells[key] for key in ("entry", "exit", "priceReturnPct", "profitUsdc", "capitalReturnPct", "accountBalance")):
            excluded["incomplete"] += 1
            continue
        closed = to_utc(local_date(cells["close"], epoch), zone)
        if closed < opened:
            raise ValueError(f"Closing precedes opening in row {row_id}")
        side = {"ALZA": "LONG", "BAJA": "SHORT", "LONG": "LONG", "SHORT": "SHORT"}.get(cells["side"].upper())
        if not side:
            raise ValueError(f"Unknown side in row {row_id}")
        trade = {"id": row_id, "coin": cells["coin"], "side": side, "open": iso(opened), "close": iso(closed)}
        for key in ("entry", "exit", "priceReturnPct", "capitalReturnPct", "profitUsdc", "accountBalance"):
            trade[key] = numeric(cells[key], key, row_id)
        if trade["entry"] <= 0 or trade["exit"] <= 0:
            raise ValueError(f"Non-positive price in row {row_id}")
        candidates.append(trade)
    if not candidates:
        raise ValueError("No completed executed trades found")
    end_year = end_year or max(int(t["close"][:4]) for t in candidates)
    start_year = start_year or end_year - 1
    if start_year > end_year:
        raise ValueError("Start year cannot exceed end year")
    start = iso(datetime(start_year, 1, 1, tzinfo=UTC))
    end = iso(datetime(end_year + 1, 1, 1, tzinfo=UTC))
    trades = sorted((t for t in candidates if start <= t["close"] < end), key=lambda t: (t["close"], t["id"]))
    excluded["outsidePeriod"] = len(candidates) - len(trades)
    if not trades:
        raise ValueError("No completed trades in selected years")
    result = {
        "source": path.name,
        "period": {"from": start, "to": trades[-1]["close"], "endExclusive": end},
        "methodology": "Illustrative index compounds column H price returns in closing-time order. Only executed, completed simulator trades are included. Overlapping positions, leverage, capital allocation, exchange costs and CryptoLove fees are not reproduced by this index. This is historical simulation, not live performance.",
        "excluded": excluded,
        "provenance": {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "sheet": sheet_name,
            "sourceRows": len(rows) - 1, "sourceLocalTimezone": zone_name,
            "timezoneBasis": "Source code exports host-local dates without timezone. All available opening times were checked against explicit UTC labels in column Q. Closing UTC is inferred using the matching local timezone.",
            "utcOpeningsVerified": checked, "verifiedLocalOffsets": dict(offsets),
            "openingPrecision": "seconds from column Q", "closingPrecision": "minutes in supplied workbook; seconds padded with zero",
            "returnUnits": "percentage points: 5 means 5%, not 0.05",
            "capitalReturnColumn": "O: net simulated PnL / allocated capital, including source leverage and source estimated costs",
            "accountBalanceColumn": "P: source simulator account balance, not the normalized index",
        },
        "trades": trades,
    }
    normalized = 100.0
    peak = normalized
    max_drawdown = 0.0
    for trade in trades:
        normalized *= 1 + trade["priceReturnPct"] / 100
        peak = max(peak, normalized)
        max_drawdown = max(max_drawdown, (peak - normalized) / peak * 100)
    audit = {
        "source": result["source"], "sha256": result["provenance"]["sha256"],
        "sourceRows": len(rows) - 1, "excluded": excluded, "included": len(trades),
        "byClosingYear": dict(Counter(t["close"][:4] for t in trades)),
        "uniqueCoins": len({t["coin"] for t in trades}),
        "winningPriceReturns": sum(t["priceReturnPct"] > 0 for t in trades),
        "losingPriceReturns": sum(t["priceReturnPct"] < 0 for t in trades),
        "flatPriceReturns": sum(t["priceReturnPct"] == 0 for t in trades),
        "firstClose": trades[0]["close"], "lastClose": trades[-1]["close"],
        "openingsBeforeWindow": sum(t["open"] < start for t in trades),
        "normalizedStart": 100, "normalizedEnd": normalized,
        "normalizedReturnPct": normalized - 100, "normalizedMaxDrawdownPct": max_drawdown,
        "methodology": result["methodology"], "provenance": result["provenance"],
    }
    return result, audit


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        json.dump(data, temp, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        temp.write("\n")
        temporary = Path(temp.name)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("history.json"))
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--sheet", default="Operaciones")
    parser.add_argument("--timezone", default="Europe/Madrid")
    parser.add_argument("--start-year", type=int)
    parser.add_argument("--end-year", type=int)
    args = parser.parse_args()
    if "://" in str(args.xlsx) or not args.xlsx.is_file() or args.xlsx.suffix.lower() != ".xlsx":
        parser.error("Provide an existing local .xlsx file")
    if args.output.resolve() == args.xlsx.resolve() or (args.audit and args.audit.resolve() in {args.xlsx.resolve(), args.output.resolve()}):
        parser.error("Input, history output and audit output must be different files")
    result, audit = build(args.xlsx, args.sheet, args.timezone, args.start_year, args.end_year)
    save_json(args.output, result)
    if args.audit:
        save_json(args.audit, audit)
    print(json.dumps({key: audit[key] for key in ("included", "excluded", "byClosingYear", "firstClose", "lastClose")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
