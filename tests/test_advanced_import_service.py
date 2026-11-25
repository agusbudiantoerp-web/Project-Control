import pytest

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
    ).replace(b"proj_id\ttask_id", b"task_id")
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
