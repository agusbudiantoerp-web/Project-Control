from ai_project_control.advanced_import_service import prepare_xer_workspace_import


def _xer_with_relationships(relationship_rows: str) -> bytes:
    text = "\n".join([
        "%T\tPROJECT",
        "%F\tproj_id\tproj_name\tproj_short_name",
        "%R\tP1\tTest Project\tP1",
        "%T\tTASK",
        "%F\ttask_id\ttask_code\tproj_id\ttask_name\ttarget_drtn_hr_cnt",
        "%R\t1\tA1\tP1\tStart\t8",
        "%R\t2\tA2\tP1\tFinish\t8",
        "%T\tTASKPRED",
        "%F\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt",
        relationship_rows,
        "%E",
        "",
    ])
    return text.encode("latin-1")


def test_prepare_xer_collapses_exact_duplicate_predecessor_rows():
    raw = _xer_with_relationships(
        "%R\t2\t1\tPR_FS\t0\n%R\t2\t1\tPR_FS\t0"
    )

    prepared = prepare_xer_workspace_import(
        raw,
        project_id="TEST-P6",
        project_name="Test P6",
        currency="IDR",
        source_project_id="P1",
    )

    assert prepared["counts"]["activities"] == 2
    assert prepared["counts"]["duplicate_relationships_removed"] == 1
    successor = next(row for row in prepared["activities"] if row["activity_id"] == "A2")
    assert successor["predecessor_ids"] == "A1"
    assert any("Removed 1 exact duplicate" in note for note in prepared["limitations"])


def test_prepare_xer_does_not_merge_relationships_with_different_lags():
    raw = _xer_with_relationships(
        "%R\t2\t1\tPR_FS\t0\n%R\t2\t1\tPR_FS\t8"
    )

    try:
        prepare_xer_workspace_import(
            raw,
            project_id="TEST-P6",
            project_name="Test P6",
            currency="IDR",
            source_project_id="P1",
        )
    except ValueError as exc:
        assert "non-zero lag" in str(exc)
    else:
        raise AssertionError("A distinct non-zero-lag relationship must not be silently merged.")
