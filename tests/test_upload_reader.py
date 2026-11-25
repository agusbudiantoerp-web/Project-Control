from io import BytesIO

import pytest

from ai_project_control.upload_reader import prepare_upload_for_table, read_tabular_upload


class Upload(BytesIO):
    def __init__(self, name, data):
        super().__init__(data)
        self.name = name


def test_reads_csv_and_detects_headers():
    upload = Upload("boq.csv", b"Project ID,BOQ ID,Quantity\nP1,B1,10\n")
    result = read_tabular_upload(upload)
    assert result["columns"] == ["Project ID", "BOQ ID", "Quantity"]
    assert result["row_count"] == 1
    assert result["rows"][0]["Quantity"] == "10"


def test_prepares_csv_with_mapping_and_validation():
    upload = Upload("boq.csv", b"Project ID,BOQ ID,Quantity\nP1,B1,10\n")
    result = prepare_upload_for_table(upload, "boq")
    assert result["mapping_result"]["ready_for_analysis"] is True
    assert result["mapping_result"]["rows"][0]["boq_id"] == "B1"


def test_rejects_unsupported_extension_and_empty_file():
    with pytest.raises(ValueError):
        read_tabular_upload(Upload("data.xls", b"abc"))
    with pytest.raises(ValueError):
        read_tabular_upload(Upload("empty.csv", b""))


def test_rejects_duplicate_headers():
    with pytest.raises(ValueError, match="Duplicate column headers"):
        read_tabular_upload(Upload("bad.csv", b"Project ID,Project ID\nP1,P2\n"))


def test_rejects_invalid_utf8():
    with pytest.raises(ValueError, match="UTF-8"):
        read_tabular_upload(Upload("bad.csv", b"\xff\xfe\xfa"))


def test_xlsx_requires_openpyxl_or_reads_workbook():
    pytest.importorskip("openpyxl")
    from openpyxl import Workbook
    from io import BytesIO

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Project ID", "BOQ ID", "Quantity"])
    sheet.append(["P1", "B1", 3])
    stream = BytesIO()
    workbook.save(stream)
    result = read_tabular_upload(Upload("boq.xlsx", stream.getvalue()))
    assert result["row_count"] == 1
    assert result["rows"][0]["Quantity"] == 3


def test_rejects_wrong_extension_and_oversized_upload():
    with pytest.raises(ValueError):
        read_tabular_upload(Upload("boq.txt", b"a,b\n1,2"))
    with pytest.raises(ValueError, match="exceeds"):
        read_tabular_upload(Upload("large.csv", b"x" * (15 * 1024 * 1024 + 1)))


def test_rejects_header_count_over_limit_before_reading_rows():
    headers = [f"column_{index}" for index in range(201)]
    upload = Upload("wide.csv", (",".join(headers) + "\n").encode("utf-8"))
    with pytest.raises(ValueError, match="200 column limit"):
        read_tabular_upload(upload)


def test_rejects_blank_header_row():
    with pytest.raises(ValueError, match="No usable header row"):
        read_tabular_upload(Upload("blank.csv", b",,\n1,2,3\n"))


def test_normalizes_headers_and_rejects_case_insensitive_duplicates():
    upload = Upload("bad.csv", b" Project ID ,project id\nP1,P2\n")
    with pytest.raises(ValueError, match="Duplicate column headers"):
        read_tabular_upload(upload)


def test_rejects_blank_column_header_between_valid_headers():
    upload = Upload("bad.csv", b"Project ID,,Quantity\nP1,B1,10\n")
    with pytest.raises(ValueError, match="Blank column headers"):
        read_tabular_upload(upload)


def test_rejects_csv_rows_with_more_values_than_headers():
    upload = Upload("bad.csv", b"Project ID,BOQ ID\nP1,B1,unexpected\n")
    with pytest.raises(ValueError, match="more values than the header"):
        read_tabular_upload(upload)


def test_trims_csv_header_whitespace():
    upload = Upload("ok.csv", b" Project ID , BOQ ID \nP1,B1\n")
    result = read_tabular_upload(upload)
    assert result["columns"] == ["Project ID", "BOQ ID"]
    assert result["rows"][0]["BOQ ID"] == "B1"


def test_xlsx_rejects_values_beyond_declared_headers():
    pytest.importorskip("openpyxl")
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Project ID", "BOQ ID"])
    sheet.append(["P1", "B1", "unexpected"])
    stream = BytesIO()
    workbook.save(stream)

    with pytest.raises(ValueError, match="beyond the header columns"):
        read_tabular_upload(Upload("bad.xlsx", stream.getvalue()))


def test_xlsx_skips_fully_blank_rows():
    pytest.importorskip("openpyxl")
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Project ID", "BOQ ID"])
    sheet.append([None, None])
    sheet.append(["P1", "B1"])
    stream = BytesIO()
    workbook.save(stream)

    result = read_tabular_upload(Upload("ok.xlsx", stream.getvalue()))
    assert result["row_count"] == 1
    assert result["rows"][0]["Project ID"] == "P1"


def test_reader_preserves_upload_stream_for_repeated_preview():
    upload = Upload("boq.csv", b"Project ID,BOQ ID,Quantity\nP1,B1,10\n")
    first = read_tabular_upload(upload)
    second = read_tabular_upload(upload)
    assert first["rows"] == second["rows"]
    assert upload.tell() == 0
