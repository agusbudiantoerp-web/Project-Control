"""Import Primavera P6 XER schedules and review Gemini drawing takeoff drafts."""
from __future__ import annotations

import hashlib
import math
import os
import sqlite3

import streamlit as st

from ai_project_control.advanced_import_service import (
    analyze_drawing_page_with_gemini,
    import_xer_to_workspace,
    list_xer_source_projects,
    prepare_xer_workspace_import,
)
from ai_project_control.project_store import ProjectStore
from ai_project_control.telegram_document_intake import fetch_latest_telegram_pdf
from ai_project_control.workspace_config import get_workspace_database_path

st.set_page_config(page_title="P6 XER & Drawing BOQ Intake", page_icon="📐", layout="wide")
st.title("Primavera P6 XER & Drawing-to-BOQ Intake")
st.caption(
    "Import jadwal P6 ke workspace utama dan buat draft BOQ dari satu halaman gambar "
    "dengan analisis Gemini yang memerlukan persetujuan eksplisit."
)

def _text_cell(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "<na>", "nan", "none"} else text


database_path = get_workspace_database_path()
try:
    store = ProjectStore(database_path)
except (OSError, RuntimeError, sqlite3.Error) as exc:
    st.error("Primary workspace database is unavailable: " + str(exc))
    st.stop()

st.info(
    "P6 XER dipetakan ke dataset Project Master, WBS dan Activities pada workspace utama. "
    "Durasi jam P6 dikonversi menjadi hari nominal 8 jam; kalender kerja, lag, constraint, "
    "resource leveling dan relasi non-FS tetap perlu ditinjau di Primavera P6."
)

with st.expander("A. Import Primavera P6 XER", expanded=True):
    xer_upload = st.file_uploader("Pilih file Primavera P6 .xer", type=["xer"], key="pc_xer_upload")
    if xer_upload is None:
        st.info("Upload file XER untuk melihat daftar project dan preview aktivitas.")
    else:
        xer_bytes = xer_upload.getvalue()
        try:
            source_projects = list_xer_source_projects(xer_bytes)
            if source_projects:
                labels = {
                    f"{item['project_name']} ({item['source_project_id']})": item
                    for item in source_projects
                }
                selected_label = st.selectbox("Pilih project di dalam file XER", list(labels))
                selected_source = labels[selected_label]
                source_project_id = selected_source["source_project_id"]
                suggested_name = selected_source["project_name"]
                suggested_code = selected_source.get("project_code") or source_project_id
            else:
                source_project_id = None
                suggested_name = "Imported P6 Project"
                suggested_code = "P6-IMPORT"

            c1, c2, c3 = st.columns(3)
            with c1:
                target_project_id = st.text_input(
                    "Project ID di workspace utama",
                    value=str(suggested_code).strip().replace(" ", "-"),
                    key="pc_xer_target_id",
                ).strip()
            with c2:
                target_project_name = st.text_input(
                    "Nama proyek", value=suggested_name, key="pc_xer_target_name"
                ).strip()
            with c3:
                target_currency = st.text_input(
                    "Mata uang proyek", value="IDR", max_chars=3, key="pc_xer_currency"
                ).strip().upper()

            import_mode = st.radio(
                "Mode impor WBS & Activities",
                ["Upsert (tambah/perbarui)", "Replace dataset WBS & Activities"],
                horizontal=True,
                key="pc_xer_import_mode",
            )
            mode = "replace" if import_mode.startswith("Replace") else "upsert"
            confirm_replace = True
            if mode == "replace":
                st.warning("Replace menghapus seluruh WBS dan Activities lama untuk Project ID ini sebelum menyimpan hasil XER.")
                xer_scope = hashlib.sha256(xer_bytes).hexdigest()[:10] + "_" + str(source_project_id or "all")
                replace_nonce_key = f"pc_xer_replace_nonce_{target_project_id}_{xer_scope}"
                replace_nonce = st.session_state.get(replace_nonce_key, 0)
                confirm_replace = st.checkbox(
                    "Saya mengonfirmasi penggantian seluruh dataset WBS dan Activities proyek ini.",
                    key=f"pc_xer_confirm_replace_{target_project_id}_{xer_scope}_{replace_nonce}",
                )

            prepared = prepare_xer_workspace_import(
                xer_bytes,
                project_id=target_project_id,
                project_name=target_project_name,
                currency=target_currency,
                source_project_id=source_project_id,
            )
            st.caption(
                f"Preview: {prepared['counts']['wbs']} WBS · "
                f"{prepared['counts']['activities']} activities"
            )
            st.dataframe(prepared["activities"][:30], use_container_width=True, hide_index=True)
            if prepared["wbs"]:
                with st.expander("WBS preview"):
                    st.dataframe(prepared["wbs"][:30], use_container_width=True, hide_index=True)
            for note in prepared["limitations"]:
                st.caption("• " + note)

            if st.button(
                "Import XER to primary workspace",
                type="primary",
                disabled=not confirm_replace,
                key="pc_xer_import_button",
            ):
                result = import_xer_to_workspace(
                    store,
                    xer_bytes,
                    project_id=target_project_id,
                    project_name=target_project_name,
                    currency=target_currency,
                    source_project_id=source_project_id,
                    mode=mode,
                )
                st.success(
                    f"XER imported: {result['saved']['wbs']['saved_count']} WBS and "
                    f"{result['saved']['activities']['saved_count']} activities saved."
                )
                if mode == "replace":
                    st.session_state[replace_nonce_key] = replace_nonce + 1
        except (TypeError, ValueError, OSError, sqlite3.Error) as exc:
            st.error("XER could not be prepared: " + str(exc))

st.divider()
with st.expander("B. Drawing PDF → Gemini takeoff → reviewed BOQ draft", expanded=False):
    project_ids = store.list_project_ids()
    if not project_ids:
        st.warning("Buat atau impor Project Master terlebih dahulu sebelum menyimpan draft BOQ.")
    else:
        target_project = st.selectbox("Project tujuan draft BOQ", project_ids, key="pc_drawing_project")

        with st.expander("Ambil PDF gambar dari Telegram", expanded=False):
            telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            telegram_chat = os.getenv("TELEGRAM_CHAT_ID", "")
            if not telegram_token:
                try:
                    telegram_token = str(st.secrets.get("TELEGRAM_BOT_TOKEN", ""))
                except Exception:
                    telegram_token = ""
            if not telegram_chat:
                try:
                    telegram_chat = str(st.secrets.get("TELEGRAM_CHAT_ID", ""))
                except Exception:
                    telegram_chat = ""
            st.caption(
                "Kirim PDF sebagai Document ke private chat bot, lalu tekan Fetch. "
                "Polling getUpdates memerlukan bot tanpa webhook aktif."
            )
            telegram_pdf_key = "pc_telegram_pdf_intake"
            bot_fingerprint = hashlib.sha256(telegram_token.encode("utf-8")).hexdigest()[:12]
            telegram_offset_key = f"pc_telegram_update_offset_{bot_fingerprint}"
            persistent_offset_key = f"telegram_update_offset:{bot_fingerprint}"
            if not telegram_token or not telegram_chat:
                st.warning("Konfigurasikan TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID terlebih dahulu.")
            if st.button(
                "Fetch latest Telegram PDF",
                disabled=not (telegram_token and telegram_chat),
                key="pc_telegram_fetch_pdf",
            ):
                try:
                    current_offset = st.session_state.get(telegram_offset_key)
                    if current_offset is None:
                        stored_offset = store.get_metadata(persistent_offset_key)
                        if stored_offset is not None:
                            try:
                                current_offset = int(stored_offset)
                            except ValueError:
                                current_offset = None
                    fetched = fetch_latest_telegram_pdf(
                        telegram_token, telegram_chat, offset=current_offset,
                    )
                    if fetched["next_offset"] is not None:
                        st.session_state[telegram_offset_key] = fetched["next_offset"]
                        store.set_metadata(persistent_offset_key, str(fetched["next_offset"]))
                    if fetched["status"] == "PDF_READY":
                        st.session_state[telegram_pdf_key] = fetched
                        st.success("PDF diterima dari Telegram: " + fetched["file_name"])
                    else:
                        st.info("Tidak ada PDF baru dari chat Telegram yang diizinkan.")
                except (TypeError, ValueError, RuntimeError) as telegram_error:
                    st.error("Telegram PDF intake failed: " + str(telegram_error))

        pdf_upload = st.file_uploader("Upload PDF gambar teknik (atau gunakan PDF dari Telegram)", type=["pdf"], key="pc_drawing_pdf")
        telegram_pdf = st.session_state.get("pc_telegram_pdf_intake")
        if pdf_upload is not None:
            pdf_bytes = pdf_upload.getvalue()
            pdf_file_name = pdf_upload.name
        elif telegram_pdf and telegram_pdf.get("status") == "PDF_READY":
            pdf_bytes = telegram_pdf["bytes"]
            pdf_file_name = telegram_pdf["file_name"]
            st.caption("Using Telegram document: " + pdf_file_name)
        else:
            pdf_bytes = None
            pdf_file_name = ""

        if pdf_bytes is not None:
            if len(pdf_bytes) > 20 * 1024 * 1024:
                st.error("PDF melebihi batas 20 MB.")
            else:
                try:
                    import fitz

                    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
                        page_count = document.page_count
                        if page_count < 1:
                            raise ValueError("PDF tidak memiliki halaman.")
                        if page_count > 300:
                            raise ValueError("PDF melebihi batas 300 halaman; pecah dokumen terlebih dahulu.")
                        page_number = st.number_input(
                            "Halaman yang dianalisis",
                            min_value=1, max_value=page_count, value=1, step=1,
                            key="pc_drawing_page_number",
                        )
                        page = document.load_page(int(page_number) - 1)
                        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                        image_bytes = pixmap.tobytes("png")
                    st.image(image_bytes, caption=f"Preview halaman {page_number} — {pdf_file_name}", use_container_width=True)

                    api_key = os.getenv("GEMINI_API_KEY", "")
                    if not api_key:
                        try:
                            api_key = str(st.secrets.get("GEMINI_API_KEY", ""))
                        except Exception:
                            api_key = ""
                    consent_nonce_key = (
                        f"pc_gemini_consent_nonce_{target_project}_"
                        f"{hashlib.sha256(pdf_bytes).hexdigest()[:10]}_{page_number}"
                    )
                    consent_nonce = st.session_state.get(consent_nonce_key, 0)
                    consent_key = f"{consent_nonce_key}_{consent_nonce}"
                    consent = st.checkbox(
                        "Saya menyetujui halaman gambar terpilih dikirim ke Google Gemini untuk membuat draft takeoff.",
                        key=consent_key,
                    )
                    if not api_key:
                        st.warning("Konfigurasikan GEMINI_API_KEY melalui environment variable atau Streamlit secrets.")
                    analyze_key = f"pc_gemini_takeoff_{target_project}"
                    file_signature = hashlib.sha256(pdf_bytes).hexdigest()
                    if st.button(
                        "Analyze selected page with Gemini",
                        disabled=not (consent and api_key),
                        key="pc_gemini_analyze_button",
                    ):
                        rows = analyze_drawing_page_with_gemini(image_bytes, api_key)
                        st.session_state[analyze_key] = {
                            "signature": file_signature,
                            "page": int(page_number),
                            "rows": rows,
                        }
                        st.session_state[consent_nonce_key] = consent_nonce + 1
                        st.success("Draft takeoff diterima. Periksa dan edit setiap baris sebelum disimpan.")

                    draft_state = st.session_state.get(analyze_key)
                    if (
                        draft_state
                        and draft_state.get("signature") == file_signature
                        and draft_state.get("page") == int(page_number)
                    ):
                        import pandas as pd

                        draft_frame = pd.DataFrame(draft_state["rows"])
                        edited = st.data_editor(
                            draft_frame,
                            use_container_width=True,
                            hide_index=True,
                            num_rows="dynamic",
                            key=f"pc_gemini_editor_{target_project}_{file_signature[:10]}_{page_number}",
                        )
                        st.warning(
                            "Semua kuantitas adalah draft. Periksa dimensi, skala, satuan, metode ukur, "
                            "asumsi dan confidence terhadap gambar sumber. Set review_status menjadi VERIFIED "
                            "hanya setelah pemeriksaan quantity surveyor."
                        )
                        verified_nonce_key = f"pc_gemini_verified_nonce_{target_project}_{file_signature[:10]}_{page_number}"
                        verified_nonce = st.session_state.get(verified_nonce_key, 0)
                        verified = st.checkbox(
                            "Saya telah memeriksa semua baris dan menyetujui penyimpanan BOQ draft.",
                            key=f"{verified_nonce_key}_{verified_nonce}",
                        )
                        if st.button(
                            "Save reviewed BOQ draft to Project Workspace",
                            disabled=not verified or edited.empty,
                            key="pc_gemini_save_button",
                        ):
                            boq_rows = []
                            errors = []
                            for index, row in edited.iterrows():
                                if str(row.get("review_status", "")).strip().upper() != "VERIFIED":
                                    errors.append(f"Baris {index + 1}: review_status harus VERIFIED.")
                                    continue
                                raw_quantity = row.get("quantity")
                                try:
                                    quantity = float(raw_quantity)
                                except (TypeError, ValueError):
                                    errors.append(f"Baris {index + 1}: quantity harus diisi angka.")
                                    continue
                                if isinstance(raw_quantity, bool) or not math.isfinite(quantity) or quantity < 0:
                                    errors.append(f"Baris {index + 1}: quantity harus finite dan non-negatif.")
                                    continue
                                description = _text_cell(row.get("description", ""))
                                unit = _text_cell(row.get("unit", ""))
                                if not description or not unit:
                                    errors.append(f"Baris {index + 1}: description dan unit wajib diisi.")
                                    continue
                                boq_id = (
                                    f"DWG-{file_signature[:8].upper()}-P{int(page_number):03d}-{index + 1:03d}"
                                )
                                boq_rows.append({
                                    "project_id": target_project,
                                    "boq_id": boq_id,
                                    "wbs_id": _text_cell(row.get("wbs_id", "")),
                                    "description": description,
                                    "item_code": _text_cell(row.get("item_code", "")),
                                    "unit": unit,
                                    "quantity": quantity,
                                    "unit_rate": None,
                                    "amount": None,
                                    "source_format": "GEMINI_DRAWING_TAKEOFF_DRAFT",
                                    "drawing_sha256": file_signature,
                                    "drawing_page": int(page_number),
                                    "measurement_method": _text_cell(row.get("measurement_method", "")),
                                    "confidence": _text_cell(row.get("confidence", "Low")),
                                    "assumptions": _text_cell(row.get("assumptions", "")),
                                    "review_status": "VERIFIED",
                                })
                            if errors:
                                for error in errors:
                                    st.error(error)
                            elif boq_rows:
                                saved = store.save_dataset(target_project, "boq", boq_rows, mode="upsert")
                                st.session_state[verified_nonce_key] = verified_nonce + 1
                                st.success(f"Saved {saved['saved_count']} reviewed BOQ draft rows for {target_project}.")
                except ImportError:
                    st.error("PDF drawing preview requires PyMuPDF. Install dependencies from the root requirements.txt.")
                except (RuntimeError, ValueError, OSError, sqlite3.Error) as exc:
                    st.error("Drawing takeoff could not be prepared: " + str(exc))
        else:
            st.info("Upload PDF atau ambil PDF dari Telegram untuk memilih halaman dan meninjau hasil takeoff.")
