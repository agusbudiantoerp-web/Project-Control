from executive_reporting import build_executive_summary


def test_executive_summary_reports_only_available_metrics():
    report = build_executive_summary(
        "P-1", "Plant", "2026-11-24",
        {
            "SPI": 0.92,
            "CPI": 0.97,
            "BAC": 1_000_000,
            "EAC": 1_080_000,
            "Integrated forecast finish": "2027-03-31",
            "Risk-adjusted finish P80": "2027-04-15",
            "Critical activities (integrated)": 4,
            "Risk cost P80": 125_000,
            "Risk schedule days P80": 18,
            "Overloaded resource days": 3,
        },
    )
    assert "SPI 0.920" in report
    assert "CPI 0.970" in report
    assert "1,000,000.00" in report
    assert "1,080,000.00" in report
    assert "Risk cost exposure P80: 125,000.00" in report
    assert "Risk schedule exposure P80: 18.0 days" in report
    assert "Overloaded resource days: 3" in report


def test_executive_summary_does_not_invent_missing_metrics():
    report = build_executive_summary("P-2", "Road", "2026-11-24", {})
    assert "SPI" in report and "unavailable" in report
    assert "CPI" in report and "unavailable" in report
    assert "Risk schedule exposure P80" not in report
    assert "Risk cost exposure P80" not in report


def test_indonesian_report_uses_indonesian_labels_without_english_duplicates():
    report = build_executive_summary(
        "P-3", "Jalan", "2026-11-24",
        {
            "SPI": 0.95,
            "CPI": 0.90,
            "Risk cost P80": 125_000,
            "Risk schedule days P80": 18,
            "Overloaded resource days": 3,
        },
        language="id",
    )
    assert "- Kinerja jadwal: SPI 0.950" in report
    assert "- Kinerja biaya: CPI 0.900" in report
    assert "- Eksposur biaya risiko P80: 125,000.00." in report
    assert "- Eksposur keterlambatan risiko P80: 18.0 hari." in report
    assert "- Hari-resource mengalami overload: 3." in report
    assert "Schedule performance (English label)" not in report
    assert "Risk cost exposure P80" not in report
    assert "Risk schedule exposure P80" not in report
    assert "Overloaded resource days:" not in report


def test_english_report_uses_english_labels_without_indonesian_duplicates():
    report = build_executive_summary(
        "P-4", "Bridge", "2026-11-24",
        {
            "SPI": 0.95,
            "CPI": 0.90,
            "Risk cost P80": 125_000,
            "Risk schedule days P80": 18,
            "Overloaded resource days": 3,
        },
        language="en",
    )
    assert "Schedule performance: SPI 0.950" in report
    assert "Cost performance: CPI 0.900" in report
    assert "Risk cost exposure P80: 125,000.00." in report
    assert "Risk schedule exposure P80: 18.0 days." in report
    assert "Overloaded resource days: 3." in report
    assert "Eksposur biaya risiko P80" not in report
    assert "Eksposur keterlambatan risiko P80" not in report
    assert "Hari-resource mengalami overload" not in report

def test_indonesian_missing_cpi_message_is_fully_localized():
    report = build_executive_summary("P-5", "Jembatan", "2026-11-24", {"SPI": 1.0}, language="id")
    assert "- Kinerja biaya: CPI belum tersedia (data biaya aktual belum lengkap)." in report
    assert "CPI unavailable" not in report
