
import streamlit as st
import pandas as pd
from datetime import datetime
from io import StringIO, BytesIO

APP_TITLE = "TaskDB — Personal Task Database"
FILE_TEMPLATE_NAME = "taskdb_tasks.csv"
STATUS_OPTIONS = ["Planned", "In Progress", "Done"]

# ---------- Helpers ----------

def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{['th','st','nd','rd','th','th','th','th','th','th'][n%10]}"

def iso_to_friendly(iso_str: str | None) -> str:
    """Return '17th October 2025, Friday, 5 pm' (or '5:07 pm' if minutes > 0)."""
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str)
        day = _ordinal(dt.day)
        month = dt.strftime('%B')          # October
        year = dt.strftime('%Y')           # 2025
        weekday = dt.strftime('%A')        # Friday
        # time: '5 pm' if :00 else '5:07 pm'
        h = dt.strftime('%I').lstrip('0') or '0'
        m = dt.minute
        ampm = dt.strftime('%p').lower()   # am/pm
        time_str = f"{h} pm" if (ampm=='pm' and m==0) else (f"{h}:{m:02d} {ampm}") if m>0 else f"{h} {ampm}"
        return f"{day} {month} {year}, {weekday}, {time_str}"
    except Exception:
        return iso_str


def make_empty_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Entry": pd.Series(dtype="string"),               # ISO datetime string (read-only)
            "Title / Description": pd.Series(dtype="string"),
            "Task": pd.Series(dtype="string"),
            "Schedule": pd.Series(dtype="string"),            # ISO datetime string
            "Status": pd.Categorical([], categories=STATUS_OPTIONS)
        }
    )


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure all required columns exist and are in the correct order/types
    base = make_empty_df().head(0)
    for col in base.columns:
        if col not in df.columns:
            df[col] = "" if col != "Status" else pd.Categorical([], categories=STATUS_OPTIONS)
    # Drop extras but keep order
    df = df[list(base.columns)]

    # Coerce dtypes
    df["Entry"] = df["Entry"].astype("string")
    df["Title / Description"] = df["Title / Description"].astype("string")
    df["Task"] = df["Task"].astype("string")
    df["Schedule"] = df["Schedule"].astype("string")
    df["Status"] = pd.Categorical(df["Status"].astype("string").where(df["Status"].isin(STATUS_OPTIONS), other="Planned"), categories=STATUS_OPTIONS)

    return df


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    # Save only canonical 5 columns
    out = df[["Entry", "Title / Description", "Task", "Schedule", "Status"]].copy()
    csv_str = out.to_csv(index=False)
    return csv_str.encode("utf-8")


# ---------- UI Chrome (Apple‑like minimal) ----------

CUSTOM_CSS = """
<style>
:root {
  --bg: #0b0c0f;             /* deep neutral for contrast */
  --card: #111318;
  --ink: #e6e7ea;
  --muted: #a9acb2;
  --bluegray: #9bb0c8;
  --amber: #f2c14e;
  --green: #3fb983;
  --radius: 18px;
}
/* Base */
html, body, [data-testid="stAppViewContainer"] {
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Apple Color Emoji", "Segoe UI Emoji";
}
[data-testid="stAppViewContainer"] {
  background: var(--bg);
}
/* Page title */
h1, .app-title {
  color: var(--ink);
}
/* Soft card */
.card {
  background: var(--card);
  border-radius: var(--radius);
  padding: 18px 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.03);
}
/* Pills */
.pill { display:inline-flex; align-items:center; gap:.5ch; padding:.15rem .6rem; border-radius:999px; font-size:.86rem; font-weight:600; letter-spacing:.2px; }
.pill.planned { background: rgba(123, 148, 177, .16); color: var(--bluegray); border: 1px solid rgba(123,148,177,.25); }
.pill.progress { background: rgba(242, 193, 78, .15); color: var(--amber); border: 1px solid rgba(242,193,78,.3); }
.pill.done { background: rgba(63, 185, 131, .15); color: var(--green); border: 1px solid rgba(63,185,131,.3); }
.timestamp { color: var(--muted); line-height: 1.2; font-variant-numeric: tabular-nums; }
.table-preview { width: 100%; border-collapse: collapse; }
.table-preview th, .table-preview td { border-bottom: 1px solid rgba(255,255,255,.06); padding: 14px 10px; vertical-align: top; color: var(--ink); white-space: normal; word-break: break-word; overflow: visible; }
.table-preview th { color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: .8rem; letter-spacing: .8px; }
.table-preview td .title { font-weight: 600; }
</style>
"""

st.set_page_config(page_title=APP_TITLE, page_icon="🗂️", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(f"<h1 class='app-title'>🗂️ {APP_TITLE}</h1>", unsafe_allow_html=True)

st.caption("A standalone, private, local application for logging daily tasks with permanent records, automatic timestamps, and a clean minimal interface. All data stays local.")

# ---------- File load / new ----------

if "df" not in st.session_state:
    st.session_state.df = make_empty_df()
if "current_filename" not in st.session_state:
    st.session_state.current_filename = FILE_TEMPLATE_NAME

with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    left, mid, right = st.columns([2,2,2])

    with left:
        up = st.file_uploader("Load a TaskDB file (.csv)", type=["csv"], accept_multiple_files=False)
        if up is not None:
            content = up.getvalue().decode("utf-8", errors="ignore")
            try:
                df = pd.read_csv(StringIO(content))
                df = normalize_df(df)
                st.session_state.df = df
                st.session_state.current_filename = up.name
                st.success(f"Loaded {up.name} ✔")
            except Exception as e:
                st.error(f"Could not parse this file as TaskDB CSV. Details: {e}")

    with mid:
        if st.button("Create New Blank File", use_container_width=True):
            st.session_state.df = make_empty_df()
            st.session_state.current_filename = FILE_TEMPLATE_NAME
            st.toast("Blank TaskDB created.")

    with right:
        new_title = st.text_input("Rename file (on save as)", value=st.session_state.current_filename)
        if new_title.strip():
            st.session_state.current_filename = new_title.strip()

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Toolbar ----------

st.markdown("<div class='card'>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns([1.1, 1.1, 1.2, 3])

with col1:
    if st.button("➕ Add Task", use_container_width=True):
        df = st.session_state.df.copy()
        new_row = {
            "Entry": now_iso(),
            "Title / Description": "",
            "Task": "",
            "Schedule": "",
            "Status": "Planned",
        }
        st.session_state.df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

with col2:
    if st.button("🧹 Remove Marked", use_container_width=True):
        df = st.session_state.df.copy()
        if "_delete" in df.columns:
            st.session_state.df = df[df["_delete"] != True].drop(columns=["_delete"])  # noqa: E712
        else:
            st.info("Tick the Delete? checkboxes in the table first.")

with col3:
    if st.button("💾 Commit & Download", use_container_width=True):
        csv_bytes = df_to_csv_bytes(st.session_state.df.drop(columns=["_delete"], errors="ignore"))
        st.download_button(
            label=f"Download {st.session_state.current_filename}",
            data=csv_bytes,
            file_name=st.session_state.current_filename,
            mime="text/csv",
        )

with col4:
    st.caption("Tip: Add tasks, edit inline, mark rows with Delete? to remove them, then **Commit & Download** to save.")

st.markdown("</div>", unsafe_allow_html=True)

# ---------- Editor ----------

editor_cols = {
    "Entry": st.column_config.TextColumn(
        "Entry (auto)",
        help="Auto‑generated ISO timestamp when a row is added. Read‑only.",
        disabled=True,
        width="small",
    ),
    "Title / Description": st.column_config.TextColumn(
        "Title / Description",
        help="Short title of the task. Multi‑line supported.",
        width="large",
    ),
    "Task": st.column_config.TextColumn(
        "Task",
        help="Detailed notes / subtasks. Multi‑line supported.",
        width="large",
    ),
    "Schedule": st.column_config.TextColumn(
        "Schedule (ISO)",
        help="When planned, stored as ISO e.g., 2025-10-17T15:00:00.",
        width="medium",
    ),
    "Status": st.column_config.SelectboxColumn(
        "Status",
        options=STATUS_OPTIONS,
        help="Planned → In Progress → Done",
        required=True,
        width="medium",
    ),
    "_delete": st.column_config.CheckboxColumn(
        "Delete?",
        help="Tick to mark this row for deletion.",
        default=False,
        width="small",
    ),
}

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.write("### Edit Tasks")

edited_df = st.data_editor(
    st.session_state.df.assign(_delete=False) if "_delete" not in st.session_state.df.columns else st.session_state.df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config=editor_cols,
)

# Persist edits
st.session_state.df = edited_df
st.markdown("</div>", unsafe_allow_html=True)

# ---------- Quick Scheduler (optional calendar) ----------

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.write("### Quick Scheduler — Pick a row, set date & time")

if len(st.session_state.df) > 0:
    idx = st.number_input("Row # (1-based)", min_value=1, max_value=len(st.session_state.df), value=1, step=1)
    rzero = idx - 1
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        d = st.date_input("Date", value=datetime.today().date())
    with c2:
        t = st.time_input("Time", value=datetime.now().time().replace(second=0, microsecond=0))
    with c3:
        if st.button("Set Schedule", use_container_width=True):
            iso_val = datetime.combine(d, t).strftime("%Y-%m-%dT%H:%M:%S")
            df = st.session_state.df.copy()
            df.loc[rzero, "Schedule"] = iso_val
            st.session_state.df = df
            st.success(f"Row {idx} schedule set to {iso_val}")
else:
    st.caption("Add at least one task to use the scheduler.")

st.markdown("</div>", unsafe_allow_html=True)

# ---------- Pretty Preview (read‑only, Apple‑ish) ----------

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.write("### Preview")

# Build an HTML table for the pretty preview
headers = ["Entry", "Title / Description", "Task", "Schedule", "Status"]
html = ["<table class='table-preview'>", "<thead><tr>" + ''.join([f"<th>{h}</th>" for h in headers]) + "</tr></thead><tbody>"]

for _, row in st.session_state.df.iterrows():
    e_str = iso_to_friendly(str(row.get("Entry", "")))
s_str = iso_to_friendly(str(row.get("Schedule", "")))
    status = (row.get("Status") or "Planned").strip()
    pill_class = "planned" if status == "Planned" else ("progress" if status == "In Progress" else "done")
    pill_html = f"<span class='pill {pill_class}'>{status}</span>"

    html.append(
        "<tr>" +
        f"<td><div class='timestamp'>🗓 {e_str}</div></td>" +
        f"<td><div class='title'>{(row.get('Title / Description') or '').strip()}</div></td>" +
        f"<td>{(row.get('Task') or '').strip()}</td>" +
        f"<td><div class='timestamp'>🗓 {s_str}</div></td>" +
        f"<td>{pill_html}</td>" +
        "</tr>"
    )

html.append("</tbody></table>")
st.markdown("\n".join(html), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ---------- Footer ----------

st.markdown(
    "<div class='card'>This app stores data only in the file you load or download. No servers, no cloud. Keep your CSV in the same folder as the app if you prefer a single portable directory.</div>",
    unsafe_allow_html=True,
)
