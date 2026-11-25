import pytest

import ai_project_control.advanced_import_service as import_service

from ai_project_control.advanced_import_service import (
    analyze_drawing_page_with_gemini,
    import_xer_to_workspace,
    list_xer_source_projects,
    prepare_xer_workspace_import,
)
from ai_project_control.project_store import ProjectStore


SINGLE_PROJECT_XER = b"""%T\tPROJECT
%F\tproj_id\tproj_short_name\tproj_name
%R\tP6-1\tP6-CODE\tPlant Upgrade
%T\tPROJWBS
%F\tproj_id\twbs_id\tparent_wbs_id\twbs_name
%R\tP6-1\tW1\t\tCivil Works
%T\tTASK
%F\tproj_id\ttask_id\ttask_code\ttask_name\twbs_id\ttarget_drtn_hr_cnt\ttarget_start_date\ttarget_end_date
%R\tP6-1\tT1\tA1\tExcavate\tW1\t80\t2026-01-01 08:00\t2026-01-10 17:00
%R\tP6-1\tT2\tA2\tPour Concrete\tW1\t40\t2026-01-11 08:00\t2026-01-15 17:00
%T\tTASKPRED
%F\tproj_id\ttask_id\tpred_task_id
%R\tP6-1\tT2\tT1
"""


def test_lists_p6_source_projects_and_prepares_workspace_records():
    projects = list_xer_source_projects(SINGLE_PROJECT_XER)
    assert projects == [{
        "source_project_id": "P6-1",
        "project_name": "Plant Upgrade",
        "project_code": "P6-CODE",
    }]
    prepared = prepare_xer_workspace_import(
        SINGLE_PROJECT_XER,
        project_id="P1",
        project_name="Plant Upgrade",
        currency="IDR",
        source_project_id="P6-1",
    )
    assert prepared["counts"] == {"wbs": 1, "activities": 2}
    assert prepared["activities"][0]["duration_days"] == 10
    assert prepared["activities"][1]["duration_days"] == 5
    assert prepared["activities"][1]["predecessor_ids"] == "A1"


def test_xer_import_commits_all_datasets_and_preserves_existing_bac(tmp_path):
    store = ProjectStore(tmp_path / "workspace.sqlite3")
    store.save_dataset("P1", "project_master", [{
        "project_id": "P1", "project_name": "Existing Name",
        "currency": "IDR", "BAC": 500000,
    }])
    result = import_xer_to_workspace(
        store, SINGLE_PROJECT_XER,
        project_id="P1", project_name="Plant Upgrade",
        currency="IDR", source_project_id="P6-1",
    )
    assert result["status"] == "COMMITTED"
    master = store.load_dataset("P1", "project_master")[0]
    assert master["BAC"] == 500000
    assert master["project_name"] == "Plant Upgrade"
    assert len(store.load_dataset("P1", "wbs")) == 1
    activities = store.load_dataset("P1", "activities")
    assert len(activities) == 2
    assert store.validate_workspace("P1")["status"] == "VALID"


def test_xer_with_multiple_projects_requires_explicit_source_selection():
    multi = SINGLE_PROJECT_XER.replace(
        b"%R\tP6-1\tT2\tA2\tPour Concrete\tW1\t40\t2026-01-11 08:00\t2026-01-15 17:00",
        b"%R\tP6-1\tT2\tA2\tPour Concrete\tW1\t40\t2026-01-11 08:00\t2026-01-15 17:00\n"
        b"%R\tP6-2\tT3\tB1\tOther Project Task\tW2\t16\t2026-02-01 08:00\t2026-02-02 17:00",
    )
    with pytest.raises(ValueError, match="multiple projects"):
        prepare_xer_workspace_import(
            multi, project_id="P1", project_name="Plant Upgrade", currency="IDR"
        )


def test_xer_rejects_missing_or_invalid_task_duration():
    invalid = SINGLE_PROJECT_XER.replace(b"\t80\t2026-01-01", b"\tbad\t2026-01-01")
    with pytest.raises(ValueError, match="invalid P6 duration"):
        prepare_xer_workspace_import(
            invalid, project_id="P1", project_name="Plant Upgrade",
            currency="IDR", source_project_id="P6-1",
        )


def test_gemini_drawing_service_validates_inputs_before_network():
    with pytest.raises(ValueError, match="image is empty"):
        analyze_drawing_page_with_gemini(b"", "secret")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        analyze_drawing_page_with_gemini(b"png", "")
    with pytest.raises(ValueError, match="finite positive"):
        analyze_drawing_page_with_gemini(b"png", "secret", timeout=float("inf"))


def test_multi_project_xer_without_task_project_ids_is_rejected():
    multi = SINGLE_PROJECT_XER.replace(
        b"%R\tP6-1\tP6-CODE\tPlant Upgrade",
        b"%R\tP6-1\tP6-CODE\tPlant Upgrade\n%R\tP6-2\tP6-OTHER\tOther Project",
    ).replace(
        b"%F\tproj_id\ttask_id",
        b"%F\ttask_id",
    ).replace(
        b"%R\tP6-1\tT1\tA1",
        b"%R\tT1\tA1",
    ).replace(
        b"%R\tP6-1\tT2\tA2",
        b"%R\tT2\tA2",
    ).replace(
        b"%R\tP6-1\tT2\tT1",
        b"%R\tT2\tT1",
    )
    with pytest.raises(ValueError, match="cannot be safely isolated"):
        prepare_xer_workspace_import(
            multi, project_id="P1", project_name="Plant Upgrade",
            currency="IDR", source_project_id="P6-1",
        )


def test_xer_import_cannot_change_existing_project_currency(tmp_path):
    store = ProjectStore(tmp_path / "workspace.sqlite3")
    store.save_dataset("P1", "project_master", [{
        "project_id": "P1", "project_name": "Plant Upgrade", "currency": "IDR",
    }])
    with pytest.raises(ValueError, match="does not match"):
        import_xer_to_workspace(
            store, SINGLE_PROJECT_XER,
            project_id="P1", project_name="Plant Upgrade",
            currency="USD", source_project_id="P6-1",
        )
    assert store.load_dataset("P1", "wbs") == []
    assert store.load_dataset("P1", "activities") == []


def test_xer_import_rejects_non_finish_to_start_relationships():
    unsupported = SINGLE_PROJECT_XER.replace(
        b"%F\tproj_id\ttask_id\tpred_task_id\n%R\tP6-1\tT2\tT1",
        b"%F\tproj_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt\n"
        b"%R\tP6-1\tT2\tT1\tPR_SS\t0",
    )
    with pytest.raises(ValueError, match="unsupported type"):
        prepare_xer_workspace_import(
            unsupported, project_id="P1", project_name="Plant Upgrade",
            currency="IDR", source_project_id="P6-1",
        )


def test_xer_import_rejects_nonzero_relationship_lags():
    lagged = SINGLE_PROJECT_XER.replace(
        b"%F\tproj_id\ttask_id\tpred_task_id\n%R\tP6-1\tT2\tT1",
        b"%F\tproj_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt\n"
        b"%R\tP6-1\tT2\tT1\tPR_FS\t8",
    )
    with pytest.raises(ValueError, match="non-zero lag"):
        prepare_xer_workspace_import(
            lagged, project_id="P1", project_name="Plant Upgrade",
            currency="IDR", source_project_id="P6-1",
        )


def test_xer_import_rejects_missing_wbs_parent_links():
    invalid = SINGLE_PROJECT_XER.replace(
        b"%R\tP6-1\tW1\t\tCivil Works",
        b"%R\tP6-1\tW1\tMISSING\tCivil Works",
    )
    with pytest.raises(ValueError, match="missing parent WBS"):
        prepare_xer_workspace_import(
            invalid, project_id="P1", project_name="Plant Upgrade",
            currency="IDR", source_project_id="P6-1",
        )


def test_gemini_drawing_response_becomes_pending_review_rows(monkeypatch):
    import ai_project_control.advanced_import_service as service

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [{
                    "content": {"parts": [{
                        "text": '[{"item_code":"C-01","description":"Concrete slab",'
                                '"unit":"m3","quantity":"12.5","confidence":"High"}]'
                    }]}
                }]
            }

    def fake_post(*args, **kwargs):
        assert kwargs["headers"]["x-goog-api-key"] == "test-key"
        assert kwargs["timeout"] == 120.0
        return Response()

    monkeypatch.setattr(service.requests, "post", fake_post)
    rows = service.analyze_drawing_page_with_gemini(b"\x89PNG\r\n\x1a\nfake-png", "test-key")
    assert rows[0]["quantity"] == 12.5
    assert rows[0]["confidence"] == "High"
    assert rows[0]["review_status"] == "PENDING_REVIEW"


def test_gemini_invalid_quantity_remains_blank_for_human_review(monkeypatch):
    import ai_project_control.advanced_import_service as service

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [{
                    "content": {"parts": [{
                        "text": '[{"description":"Unknown quantity","unit":"m","quantity":"unknown"}]'
                    }]}
                }]
            }

    monkeypatch.setattr(service.requests, "post", lambda *args, **kwargs: Response())
    rows = service.analyze_drawing_page_with_gemini(b"\x89PNG\r\n\x1a\nfake-png", "test-key")
    assert rows[0]["quantity"] is None
    assert rows[0]["review_status"] == "PENDING_REVIEW"


def test_xer_import_rejects_cyclic_activity_dependencies():
    cyclic = SINGLE_PROJECT_XER + "%R\tP6-1\tT1\tT2\n".encode("ascii")
    with pytest.raises(ValueError, match="valid finish-to-start CPM network"):
        prepare_xer_workspace_import(
            cyclic, project_id="P1", project_name="Plant Upgrade",
            currency="IDR", source_project_id="P6-1",
        )


def test_gemini_rejects_model_name_with_path_or_url_characters():
    with pytest.raises(ValueError, match="unsupported characters"):
        analyze_drawing_page_with_gemini(b"png", "test-key", model="../other/model")


def test_gemini_rejects_non_string_or_oversized_response_text(monkeypatch):
    import ai_project_control.advanced_import_service as service

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "x" * 1_000_001}]}}]}

    monkeypatch.setattr(service.requests, "post", lambda *args, **kwargs: Response())
    with pytest.raises(RuntimeError, match="drawing analysis failed"):
        analyze_drawing_page_with_gemini(b"\x89PNG\r\n\x1a\nfake-png", "test-key")


def test_gemini_rejects_takeoff_response_over_review_limit(monkeypatch):
    import json
    import ai_project_control.advanced_import_service as service

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [{
                "text": json.dumps([{"description": "Item"}] * 501)
            }]}}]}

    monkeypatch.setattr(service.requests, "post", lambda *args, **kwargs: Response())
    with pytest.raises(RuntimeError, match="review limit"):
        analyze_drawing_page_with_gemini(b"\x89PNG\r\n\x1a\nfake-png", "test-key")


def test_xer_parser_enforces_table_limit(monkeypatch):
    monkeypatch.setattr(import_service, "MAX_XER_TABLES", 1)
    raw = b"%T\tONE\n%F\tid\n%R\t1\n%T\tTWO\n%F\tid\n%R\t2\n"
    with pytest.raises(ValueError, match="table limit"):
        import_service.parse_xer_tables(raw)


def test_xer_parser_enforces_field_limit(monkeypatch):
    monkeypatch.setattr(import_service, "MAX_XER_FIELDS", 1)
    raw = b"%T\tTASK\n%F\tid\tname\n%R\t1\tA\n"
    with pytest.raises(ValueError, match="field limit"):
        import_service.parse_xer_tables(raw)


def test_xer_parser_enforces_row_limit(monkeypatch):
    monkeypatch.setattr(import_service, "MAX_XER_ROWS_PER_TABLE", 1)
    raw = b"%T\tTASK\n%F\tid\n%R\t1\n%R\t2\n"
    with pytest.raises(ValueError, match="row limit"):
        import_service.parse_xer_tables(raw)


def test_xer_parser_enforces_line_length_limit(monkeypatch):
    monkeypatch.setattr(import_service, "MAX_XER_LINE_CHARS", 6)
    raw = b"%T\tTASK\n"
    with pytest.raises(ValueError, match="line length"):
        import_service.parse_xer_tables(raw)


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), True, 10**1000])
def test_gemini_rejects_invalid_timeout_values(timeout):
    with pytest.raises(ValueError, match="finite positive"):
        import_service.analyze_drawing_page_with_gemini(
            b"\x89PNG\r\n\x1a\nfake-png", "test-key", timeout=timeout
        )


def test_gemini_rejects_non_object_takeoff_rows(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": '[{"description":"ok"}, "bad-row"]}]}}]}

    monkeypatch.setattr(import_service.requests, "post", lambda *args, **kwargs: Response())
    with pytest.raises(RuntimeError, match="item 2 must be a JSON object"):
        import_service.analyze_drawing_page_with_gemini(
            b"\x89PNG\r\n\x1a\nfake-png", "test-key"
        )


def test_gemini_rejects_nested_or_oversized_takeoff_text(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [{
                "text": '[{"description":{"unexpected":"object"}}]'
            }]}}]}

    monkeypatch.setattr(import_service.requests, "post", lambda *args, **kwargs: Response())
    with pytest.raises(RuntimeError, match="invalid description"):
        import_service.analyze_drawing_page_with_gemini(
            b"\x89PNG\r\n\x1a\nfake-png", "test-key"
        )


def test_xer_import_rejects_duplicate_wbs_ids():
    duplicate = SINGLE_PROJECT_XER.replace(
        b"%T\tTASK\n",
        b"%R\tP6-1\tW1\t\tDuplicate WBS\n%T\tTASK\n",
    )
    with pytest.raises(ValueError, match="duplicate WBS IDs"):
        import_service.prepare_xer_workspace_import(
            duplicate, project_id="P1", project_name="Plant Upgrade",
            currency="IDR", source_project_id="P6-1",
        )


def test_xer_replace_does_not_clear_existing_wbs_when_source_has_none():
    class Store:
        def __init__(self):
            self.saved = None

        def load_dataset(self, project_id, dataset):
            if dataset == "wbs":
                return [{"wbs_id": "KEEP"}]
            return []

        def save_datasets(self, project_id, datasets, mode):
            self.saved = (project_id, datasets, mode)
            return {"project_id": project_id}

    store = Store()
    source_without_wbs = SINGLE_PROJECT_XER.replace(
        b"%T\tPROJWBS\n%F\tproj_id\twbs_id\tparent_wbs_id\twbs_name\n"
        b"%R\tP6-1\tW1\t\tCivil Works\n",
        b"",
    )
    with pytest.raises(ValueError, match="existing WBS dataset was left unchanged"):
        import_service.import_xer_to_workspace(
            store, source_without_wbs, project_id="P1",
            project_name="Plant Upgrade", currency="IDR",
            source_project_id="P6-1", mode="replace",
        )
    assert store.saved is None


def test_gemini_rejects_oversized_description_and_invalid_confidence(monkeypatch):
    import json

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": json.dumps(self.payload)}]}}]}

    payloads = [
        [{"description": "D" * 1001}],
        [{"description": "valid", "confidence": {"unexpected": "object"}}],
    ]
    for payload in payloads:
        monkeypatch.setattr(
            import_service.requests, "post",
            lambda *args, _payload=payload, **kwargs: Response(_payload),
        )
        with pytest.raises(RuntimeError):
            import_service.analyze_drawing_page_with_gemini(
                b"\\x89PNG\\r\\n\\x1a\\nfake-png", "test-key"
            )


def test_gemini_handles_huge_numeric_quantity_as_unavailable(monkeypatch):
    import json

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            huge_quantity = 10 ** 1000
            return {"candidates": [{"content": {"parts": [{
                "text": json.dumps([{"description": "Unknown scale", "quantity": huge_quantity}])
            }]}}]}

    monkeypatch.setattr(import_service.requests, "post", lambda *args, **kwargs: Response())
    rows = import_service.analyze_drawing_page_with_gemini(
        b"\\x89PNG\\r\\n\\x1a\\nfake-png", "test-key"
    )
    assert rows[0]["quantity"] is None
    assert rows[0]["review_status"] == "PENDING_REVIEW"
