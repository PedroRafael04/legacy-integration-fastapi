"""
Test Suite — Transformation Service
Covers all supported legacy formats and edge cases.
"""
import pytest
from app.models.schemas import RawLegacyPayload, LegacySystem
from app.services.transformation_service import transform_payload


def make_payload(source_format, raw_data, system_id="TEST-001"):
    return RawLegacyPayload(system_id=system_id, source_format=source_format, raw_data=raw_data)


class TestCSVParser:
    def test_basic_csv(self):
        p = make_payload(LegacySystem.CSV_FLAT_FILE, "Jane Smith,1990-07-04,jane@example.com,EUR,2500.00")
        r = transform_payload(p)
        assert r.success
        assert r.record.full_name == "Jane Smith"
        assert r.record.email    == "jane@example.com"
        assert r.record.currency == "EUR"
        assert r.record.amount   == 2500.00

    def test_csv_date_normalisation(self):
        p = make_payload(LegacySystem.CSV_FLAT_FILE, "Bob Jones,04/07/1990,bob@example.com,USD,100.00")
        r = transform_payload(p)
        assert r.success
        assert r.record.date_of_birth == "1990-07-04"

    def test_csv_empty_payload(self):
        r = transform_payload(make_payload(LegacySystem.CSV_FLAT_FILE, ""))
        assert not r.success


class TestXMLParser:
    def test_basic_xml(self):
        xml = "<record><n>Alice Brown</n><dob>1985-03-12</dob><email>alice@example.com</email><currency>GBP</currency><amount>750.50</amount></record>"
        r = transform_payload(make_payload(LegacySystem.XML_LEGACY, xml))
        assert r.success
        assert r.record.full_name == "Alice Brown"
        assert r.record.amount   == 750.50

    def test_xml_alternate_tags(self):
        xml = "<data><fullname>Carlos Lima</fullname><birthdate>01/01/1975</birthdate><mail>carlos@example.com</mail><ccy>BRL</ccy><value>3000.00</value></data>"
        r = transform_payload(make_payload(LegacySystem.XML_LEGACY, xml))
        assert r.success
        assert r.record.full_name == "Carlos Lima"
        assert r.record.currency  == "BRL"

    def test_xml_malformed(self):
        r = transform_payload(make_payload(LegacySystem.XML_LEGACY, "<broken><tag>"))
        assert not r.success
        assert any("Malformed XML" in e for e in r.errors)


class TestCOBOLParser:
    def test_cobol_fixed_layout(self):
        raw = "John Doe                      12031985johndoe@mail.com              USD000000150000"
        r = transform_payload(make_payload(LegacySystem.COBOL_MAINFRAME, raw))
        assert r.success
        assert r.record.full_name     == "John Doe"
        assert r.record.date_of_birth == "1985-03-12"
        assert r.record.currency      == "USD"
        assert r.record.amount        == 1500.00


class TestFixedWidthParser:
    def test_basic_fixed_width(self):
        raw = "Maria Silva       1992-11-20  maria@example.com  BRL  4200.00"
        r = transform_payload(make_payload(LegacySystem.FIXED_WIDTH, raw))
        assert r.success
        assert r.record.email    == "maria@example.com"
        assert r.record.currency == "BRL"


class TestPipeDelimitedParser:
    def test_with_header(self):
        raw = "name|dob|email|currency|amount\nLucia Fernandez|1988-06-15|lucia@example.com|USD|1200.00"
        r = transform_payload(make_payload(LegacySystem.PIPE_DELIMITED, raw))
        assert r.success
        assert r.record.full_name == "Lucia Fernandez"
        assert r.record.amount   == 1200.00

    def test_without_header(self):
        raw = "Pedro Costa|1995-02-28|pedro@example.com|EUR|900.00"
        assert transform_payload(make_payload(LegacySystem.PIPE_DELIMITED, raw)).success

    def test_pipe_empty_payload(self):
        assert not transform_payload(make_payload(LegacySystem.PIPE_DELIMITED, "")).success


class TestGeneral:
    def test_record_has_unique_id(self):
        p  = make_payload(LegacySystem.CSV_FLAT_FILE, "Test User,2000-01-01,test@example.com,USD,100.00")
        r1 = transform_payload(p)
        r2 = transform_payload(p)
        assert r1.record.record_id != r2.record.record_id

    def test_source_system_preserved(self):
        p = make_payload(LegacySystem.CSV_FLAT_FILE, "Test User,2000-01-01,test@example.com,USD,100.00", system_id="ERP-999")
        assert transform_payload(p).record.source_system == "ERP-999"
