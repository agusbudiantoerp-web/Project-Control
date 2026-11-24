"""Local workspace backup and per-project import history."""
import os
import streamlit as st

from ai_project_control.project_store import ProjectStore
from ai_project_control.workspace_backup import build_workspace_backup

st.set_page_config(page_title="Workspace Backup & Audit", page_icon="🗄️", layout="wide")
st.title("Workspace Backup & Import History")
st.caption("Backup file SQLite dan riwayat impor lokal untuk membantu pengelolaan data.")
database_path = os.getenv("PROJECT_CONTROL_DB", ".project_control/project_control.sqlite3")
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
    if st.button("Prepare SQLite backup"):
        backup_bytes = build_workspace_backup(database_path)
        st.download_button("Download SQLite backup", data=backup_bytes,
                           file_name="project_control_workspace_backup.sqlite3",
                           mime="application/vnd.sqlite3")
except (OSError, ValueError) as exc:
    st.error("Workspace backup unavailable: " + str(exc))
