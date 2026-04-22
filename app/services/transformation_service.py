"""
Transformation Service
Core logic for normalising legacy data formats.
Supports: CSV, XML, COBOL mainframe, fixed-width, pipe-delimited.
"""
import uuid, re, csv, io
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any
from app.models.schemas import RawLegacyPayload, NormalisedRecord, TransformationResponse, LegacySystem

# Supported date patterns ordered from most to least specific.
# Each tuple is (strptime_format, regex_guard).
_DATE_PATTERNS = [
    ("%d/%m/%Y", r"\d{2}/\d{2}/\d{4}"),
    ("%m-%d-%Y", r"\d{2}-\d{2}-\d{4}"),
    ("%Y-%m-%d", r"\d{4}-\d{2}-\d{2}"),
    ("%d%m%Y",   r"\d{8}"),
    ("%Y%m%d",   r"\d{8}"),
]

def _normalise_date(value: str) -> tuple[str | None, str | None]:
    value = value.strip()
    for fmt, pattern in _DATE_PATTERNS:
        if re.fullmatch(pattern, value):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d"), None
            except ValueError:
                continue
    return None, f"Could not normalise date value: '{value}'"

def _normalise_amount(value: str) -> tuple[float | None, str | None]:
    cleaned = re.sub(r"[^\d.\-]", "", value.strip())
    try:
        return float(cleaned), None
    except ValueError:
        return None, f"Could not parse numeric value: '{value}'"

def _parse_csv(raw: str, notes: list[str]) -> dict[str, Any]:
    reader = csv.reader(io.StringIO(raw.strip()))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV payload is empty")
    fields = [f.strip() for f in rows[0]]
    result: dict[str, Any] = {}
    remaining: list[str] = []
    for field in fields:
        if re.fullmatch(r"[\w\s\-']+", field) and "full_name" not in result and not re.search(r"\d", field):
            result["full_name"] = field
        elif re.search(r"@", field) and "email" not in result:
            result["email"] = field.lower()
        elif re.fullmatch(r"[A-Z]{3}", field) and "currency" not in result:
            result["currency"] = field
        elif re.search(r"\d{1,4}[\-/]\d{1,4}[\-/]\d{2,4}|\d{8}", field) and "date_of_birth" not in result:
            iso, warn = _normalise_date(field)
            result["date_of_birth"] = iso
            if warn: notes.append(warn)
        elif re.search(r"\d+\.\d{2}", field) and "amount" not in result:
            amount, warn = _normalise_amount(field)
            result["amount"] = amount
            if warn: notes.append(warn)
        else:
            remaining.append(field)
    result["raw_fields"] = {f"field_{i}": v for i, v in enumerate(remaining)}
    notes.append("Parsed via heuristic CSV field mapping")
    return result

def _parse_xml(raw: str, notes: list[str]) -> dict[str, Any]:
    try:
        root = ET.fromstring(raw.strip())
    except ET.ParseError as exc:
        raise ValueError(f"Malformed XML: {exc}") from exc
    result: dict[str, Any] = {}
    raw_fields: dict[str, Any] = {}
    tag_map = {
        "name": "full_name", "fullname": "full_name", "full_name": "full_name", "n": "full_name",
        "email": "email", "mail": "email",
        "dob": "date_of_birth", "birthdate": "date_of_birth", "date_of_birth": "date_of_birth",
        "currency": "currency", "ccy": "currency",
        "amount": "amount", "value": "amount",
    }
    for child in root.iter():
        tag = child.tag.lower().replace("-", "_")
        text = (child.text or "").strip()
        if not text: continue
        mapped = tag_map.get(tag)
        if mapped == "date_of_birth":
            iso, warn = _normalise_date(text)
            result["date_of_birth"] = iso
            if warn: notes.append(warn)
        elif mapped == "amount":
            amount, warn = _normalise_amount(text)
            result["amount"] = amount
            if warn: notes.append(warn)
        elif mapped:
            result[mapped] = text
        else:
            raw_fields[child.tag] = text
    result["raw_fields"] = raw_fields
    notes.append("Parsed via XML tag mapping")
    return result

def _parse_cobol_mainframe(raw: str, notes: list[str]) -> dict[str, Any]:
    raw = raw.ljust(84)
    result: dict[str, Any] = {}
    result["full_name"] = raw[0:30].strip() or None
    dob_raw      = raw[30:38].strip()
    email_raw    = raw[38:68].strip()
    currency_raw = raw[68:71].strip()
    amount_raw   = raw[71:84].strip()
    if dob_raw:
        iso, warn = _normalise_date(dob_raw)
        result["date_of_birth"] = iso
        if warn: notes.append(warn)
    result["email"]    = email_raw.lower() if email_raw else None
    result["currency"] = currency_raw if currency_raw else None
    if amount_raw:
        try:
            result["amount"] = int(amount_raw) / 100.0
        except ValueError:
            amount, warn = _normalise_amount(amount_raw)
            result["amount"] = amount
            if warn: notes.append(warn)
    result["raw_fields"] = {}
    notes.append("Parsed via COBOL mainframe fixed-width layout (positions 1-84)")
    return result

def _parse_fixed_width(raw: str, notes: list[str]) -> dict[str, Any]:
    parts = re.split(r" {2,}", raw.strip())
    result: dict[str, Any] = {}
    raw_fields: dict[str, Any] = {}
    for i, part in enumerate(parts):
        part = part.strip()
        if not part: continue
        if re.search(r"@", part):
            result["email"] = part.lower()
        elif re.fullmatch(r"[A-Z]{3}", part):
            result["currency"] = part
        elif re.search(r"\d{1,4}[\-/]\d{1,4}[\-/]\d{2,4}|\d{8}", part) and "date_of_birth" not in result:
            iso, warn = _normalise_date(part)
            result["date_of_birth"] = iso
            if warn: notes.append(warn)
        elif re.search(r"^\d+(\.\d+)?$", part) and "amount" not in result:
            amount, warn = _normalise_amount(part)
            result["amount"] = amount
            if warn: notes.append(warn)
        elif "full_name" not in result:
            result["full_name"] = part
        else:
            raw_fields[f"col_{i}"] = part
    result["raw_fields"] = raw_fields
    notes.append("Parsed via fixed-width auto-split heuristic")
    return result

def _parse_pipe_delimited(raw: str, notes: list[str]) -> dict[str, Any]:
    lines = raw.strip().splitlines()
    if not lines:
        raise ValueError("Pipe-delimited payload is empty")
    result: dict[str, Any] = {}
    raw_fields: dict[str, Any] = {}
    first = [f.strip() for f in lines[0].split("|")]
    known_headers = {"name", "full_name", "email", "dob", "currency", "amount", "date_of_birth"}
    if any(h.lower() in known_headers for h in first) and len(lines) > 1:
        headers = [h.lower() for h in first]
        values  = [v.strip() for v in lines[1].split("|")]
        pairs   = dict(zip(headers, values))
    else:
        pairs = {f"col_{i}": v.strip() for i, v in enumerate(first)}
    header_alias = {
        "name": "full_name", "full_name": "full_name",
        "email": "email",
        "dob": "date_of_birth", "date_of_birth": "date_of_birth",
        "currency": "currency", "ccy": "currency",
        "amount": "amount", "value": "amount",
    }
    for key, val in pairs.items():
        mapped = header_alias.get(key)
        if mapped == "date_of_birth":
            iso, warn = _normalise_date(val)
            result["date_of_birth"] = iso
            if warn: notes.append(warn)
        elif mapped == "amount":
            amount, warn = _normalise_amount(val)
            result["amount"] = amount
            if warn: notes.append(warn)
        elif mapped:
            result[mapped] = val
        else:
            raw_fields[key] = val
    result["raw_fields"] = raw_fields
    notes.append("Parsed via pipe-delimited field mapping")
    return result

_PARSERS = {
    LegacySystem.CSV_FLAT_FILE:   _parse_csv,
    LegacySystem.XML_LEGACY:      _parse_xml,
    LegacySystem.COBOL_MAINFRAME: _parse_cobol_mainframe,
    LegacySystem.FIXED_WIDTH:     _parse_fixed_width,
    LegacySystem.PIPE_DELIMITED:  _parse_pipe_delimited,
}

def transform_payload(payload: RawLegacyPayload) -> TransformationResponse:
    notes: list[str] = []
    errors: list[str] = []
    parser = _PARSERS.get(payload.source_format)
    if parser is None:
        return TransformationResponse(
            success=False, system_id=payload.system_id,
            source_format=payload.source_format,
            errors=[f"Unsupported source format: {payload.source_format}"],
        )
    try:
        fields = parser(payload.raw_data, notes)
        # Exclude raw_fields here; it is already inside `known` via model_fields
        known  = {k: v for k, v in fields.items() if k in NormalisedRecord.model_fields}
        record = NormalisedRecord(
            record_id=str(uuid.uuid4()),
            source_system=payload.system_id,
            source_format=payload.source_format.value,
            transformation_notes=notes,
            **known,
        )
    except ValueError as exc:
        return TransformationResponse(
            success=False, system_id=payload.system_id,
            source_format=payload.source_format, errors=[str(exc)],
        )
    return TransformationResponse(
        success=True, system_id=payload.system_id,
        source_format=payload.source_format.value, record=record,
    )
