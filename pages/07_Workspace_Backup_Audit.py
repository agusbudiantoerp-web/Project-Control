"""Local workspace backup and per-project import history."""
import sqlite3
import streamlit as st

from ai_project_control.project_store import ProjectStore
from ai_project_control.workspace_backup import build_workspace_backup
from ai_project_control.workspace_restore import restore_workspace_backup
from ai_project_control.workspace_config import get_workspace_database_path

st.set_page_config(page_title="Workspace Backup & Audit", page_icon="🗄️", layout="wide")
st.title("Workspace Backup & Import History")
st.caption("Backup file SQLite dan riwayat impor lokal untuk membantu pengelolaan data.")
restore_result = st.session_state.pop("workspace_restore_result", None)
if restore_result:
    st.success(
        f"Workspace berhasil dipulihkan: {restore_result['project_count']} proyek dan "
        f"{restore_result['record_count']} record."
    )
    if restore_result.get("safety_backup_path"):
        st.info("Snapshot sebelum restore disimpan di: " + restore_result["safety_backup_path"])
database_path = get_workspace_database_path()
try:
    store = ProjectStore(database_path)
    project_ids = store.list_project_ids()
    st.metric("Saved projects", len(project_ids))
    if project_ids:
        project_id = st.selectbox("Project", project_ids)
        history = store.import_history(project_id, limit=100)
        st.subheader("Import history")
        if history:
            st.dataframe(history, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada riwayat impor untuk proyek ini.")
    else:
        st.info("Belum ada proyek tersimpan di workspace.")
    st.divider()
    st.subheader("Download workspace backup")
    st.warning("Backup dapat berisi data biaya, kontrak, dan informasi sensitif. Simpan file di lokasi terenkripsi dengan akses terbatas. Jangan unggah ke repository publik.")
    backup_state_key = f"workspace_backup_bytes::{database_path}"
    if st.button("Prepare SQLite backup"):
        st.session_state[backup_state_key] = build_workspace_backup(database_path)
        st.success("Snapshot SQLite berhasil disiapkan. Unduh file melalui tombol di bawah.")

    backup_bytes = st.session_state.get(backup_state_key)
    if backup_bytes:
        st.download_button(
            "Download SQLite backup",
            data=backup_bytes,
            file_name="project_control_workspace_backup.sqlite3",
            mime="application/vnd.sqlite3",
        )

    st.divider()
    st.subheader("Restore workspace from SQLite backup")
    st.warning(
        "Restore akan mengganti seluruh database workspace aktif. Tutup aplikasi lain yang "
        "mengakses database ini terlebih dahulu. File backup harus berasal dari AI Project Control "
        "dengan versi skema yang didukung. Snapshot database saat ini dibuat otomatis sebelum restore."
    )
    restore_nonce_key = "workspace_restore_nonce"
    restore_nonce = st.session_state.get(restore_nonce_key, 0)
    restore_upload = st.file_uploader(
        "Pilih file backup .sqlite3 atau .db",
        type=["sqlite3", "db"],
        key=f"workspace_restore_upload_{restore_nonce}",
    )
    confirm_restore = st.checkbox(
        "Saya memahami bahwa restore akan mengganti seluruh data workspace aktif.",
        key=f"workspace_restore_confirm_{restore_nonce}",
    )
    if st.button(
        "Validate and restore workspace",
        type="primary",
        disabled=restore_upload is None or not confirm_restore,
        key=f"workspace_restore_button_{restore_nonce}",
    ):
        try:
            restored = restore_workspace_backup(database_path, restore_upload.getvalue())
            st.session_state["workspace_restore_result"] = restored
            st.session_state[restore_nonce_key] = restore_nonce + 1
            st.session_state.pop(backup_state_key, None)
            st.rerun()
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            st.error("Workspace restore ditolak; database aktif tidak diganti: " + str(exc))
except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
    st.error("Workspace backup unavailable: " + str(exc))
