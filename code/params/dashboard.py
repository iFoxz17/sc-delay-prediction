from typing import List, Optional, Set, Tuple, Dict, Any
import requests
from datetime import datetime
import logging

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from dash.dependencies import Output, Input, State

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TABLE_NAME = "params"
API_BASE = f"https://rhwompporf.execute-api.eu-central-1.amazonaws.com/dev/db/tables/{TABLE_NAME}"

TABLE_SIZES: List[int] = [5, 10, 20, 50, 100]
DEFAULT_TABLE_SIZE: int = 50
DELETE_COLUMN: str = "delete"
COLUMNS: List[str] = ["id", "name", "general_category", "category", "description", "value", "created_at", "updated_at", DELETE_COLUMN]
EDITABLE_COLUMNS: Set[str] = set(["name", "general_category", "category", "description", "value"])
EXCLUDE_COLUMNS: Set[str] = {"created_at", "updated_at", DELETE_COLUMN}

PRECISION: int = 4

def is_editable(column: str) -> bool:
    if column not in EDITABLE_COLUMNS:
        logger.warning(f"Column '{column}' is not editable.")
        return False
    logger.info(f"Column '{column}' is editable.")
    return column.lower() in EDITABLE_COLUMNS

# Initialize the app
dash_app = dash.Dash(__name__)

# Layout
dash_app.layout = html.Div([
    html.H1("M4ESTRO Model Parameters Dashboard", className="dashboard-title"),

    html.Div([
        html.Div([
            html.Label("General Category:"),
            dcc.Dropdown(id="filter-general", placeholder="Select General Category", clearable=True)
        ], className="filter-item"),

        html.Div([
            html.Label("Category:"),
            dcc.Dropdown(id="filter-category", placeholder="Select Category", clearable=True)
        ], className="filter-item"),

        html.Div([
            html.Label("Name:"),
            dcc.Input(id="filter-name", type="text", debounce=False, placeholder="Search Name...", className="filter-input")
        ], className="filter-item"),

        html.Button("Clear Filters", id="clear-filters", n_clicks=0, className="btn")
    ], className="filter-container"),

    html.Div([
        html.Div([
            html.Label("Editing Mode:", className="section-label"),
            dcc.RadioItems(
                id="toggle-edit",
                options=[
                    {"label": "Enable", "value": True},
                    {"label": "Disable", "value": False}
                ],
                value=False,
                inline=True,
                className="edit-toggle"
            ),
        ], className="edit-section"),

        html.Div([
            html.Label("Rows per page:", className="section-label"),
            dcc.Dropdown(
                id="page-size-dropdown",
                options=[{"label": str(i), "value": i} for i in TABLE_SIZES],
                value=DEFAULT_TABLE_SIZE,
                clearable=False,
                style={"width": "100px"}
            ),
        ], className="page-size-select"),

        html.Div([
            html.Button("Refresh Data", id="refresh-button", n_clicks=0, className="btn btn-secondary"),
            html.Button("Drop All Data", id="drop-all", n_clicks=0, className="btn btn-danger"),
        ], className="edit-buttons")
    ], className="edit-bar"),

    dcc.Loading(
        id="loading-table",
        type="dot",
        fullscreen=True,
        children=dash_table.DataTable(
            id="table",
            columns=[],
            data=[],
            row_deletable=False,
            editable=False,
            filter_action="none",
            sort_action="native",
            page_size=DEFAULT_TABLE_SIZE,
            persistence=True,
            persisted_props=["data"],
            persistence_type="session",
            style_cell={"textAlign": "center", "padding": "5px"},
            style_cell_conditional=[                # type: ignore
                {
                    "if": {"column_id": "description"},
                    "whiteSpace": "normal",
                    "height": "auto",
                    "textAlign": "left",
                    "minWidth": "200px",
                    "maxWidth": "400px",
                },
            ],
        )
    ),

    html.Div([
        html.Div([
            html.Button("Add Row", id="add-row", n_clicks=0, className="btn btn-primary"),
            html.Button("Discard Changes", id="discard-changes", n_clicks=0, className="btn btn-warning"),
            html.Button("Confirm Changes", id="confirm-changes", n_clicks=0, className="btn btn-success"),
            dcc.ConfirmDialog(id="confirm-drop", message="Are you sure you want to drop all data?"),
            dbc.Alert("", id="update-notification", is_open=False, dismissable=True, color="danger")
        ], className="action-buttons"),

        # Tooltips — shown only if edit mode is OFF
        dbc.Tooltip(
            "Enable edit mode to add new rows.",
            target="add-row",
            id="tooltip-add-row",
            placement="bottom",
            autohide=False,
            style={"display": "none"}  # hidden by default
        ),
        dbc.Tooltip(
            "Enable edit mode to discard changes.",
            target="discard-changes",
            id="tooltip-discard-changes",
            placement="bottom",
            autohide=False,
            style={"display": "none"}
        ),
        dbc.Tooltip(
            "Enable edit mode to confirm changes.",
            target="confirm-changes",
            id="tooltip-confirm-changes",
            placement="bottom",
            autohide=False,
            style={"display": "none"}
        ),
        dbc.Tooltip(
            "Enable edit mode to drop all data.",
            target="drop-all",
            id="tooltip-drop-all",
            placement="top",
            autohide=False,
            style={"display": "none"}
        ),

        dbc.Alert(
            "Invalid value: please enter a valid float.",
            id="alert-invalid-float",
            color="danger",
            dismissable=True,
            is_open=False,
            fade=True,
            className="alert alert-danger",
        )
    ], className="action-bar"),

    # Hidden stores for data management
    dcc.Store(id="edit-mode-store", data=False),
    dcc.Store(id="current-data-store", data={}),
    dcc.Store(id="id-counter", data=0),  # Counter for new row IDs

    # Hidden divs for callbacks
    html.Div(id="dummy", style={"display": "none"}),
    html.Div(id="dummy2", style={"display": "none"})
], className="container")


def clean_timestamp(ts: str) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(ts).isoformat(timespec='seconds').replace("+00:00", "Z")
    except Exception:
        return ts

def format_value(value: float, precision: int = PRECISION) -> str:
    return f"{value:.{precision}f}" if -1 <= value <= 1 else f"{value:.2f}"

def is_updated(r1: Dict, r2: Dict) -> bool:
    return r1.get("name") != r2.get("name") or \
           r1.get("general_category") != r2.get("general_category") or \
            r1.get("category") != r2.get("category") or \
            r1.get("description") != r2.get("description") or \
            float(r1.get("value", 0)) != float(r2.get("value", 0))

def get_new_record_data(record: Dict, exclude: Set[str] = EXCLUDE_COLUMNS) -> Dict:
    exclude.add("id")
    return {k: v for k, v in record.items() if k not in exclude}

def get_record_data(record: Dict, exclude: Set[str] = EXCLUDE_COLUMNS) -> Dict:
    return {k: v for k, v in record.items() if k not in exclude}

'''
Fetch data from the API and return it as a list of dictionaries.
'''
def fetch_data() -> Optional[List[Dict]]:
    resp: requests.Response = requests.get(f"{API_BASE}/data?orderBy=id&direction=asc")
    if not resp.ok:
        logger.error(f"Failed to fetch data: {resp.status_code} - {resp.text}")
        return None

    data: Optional[List] = resp.json().get("data")
    if data is None:
        logger.warning("No data found in response")
        return None
    if not data:
        logger.info("No records found in API response")
        return []
    
    for item in data:
        item[DELETE_COLUMN] = False  # Initialize delete flag

    logger.info(f"Fetched {len(data)} records from API")
    return data



@dash_app.callback(
    Output("tooltip-add-row", "style"),
    Output("tooltip-discard-changes", "style"),
    Output("tooltip-confirm-changes", "style"),
    Output("tooltip-drop-all", "style"),
    Input("toggle-edit", "value"),
)
def toggle_tooltip_visibility(edit_enabled: bool):
    if edit_enabled:
        return {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "none"}
    else:
        return {"display": "block"}, {"display": "block"}, {"display": "block"}, {"display": "block"}


@dash_app.callback(
    Output("table", "columns"),
    Input("toggle-edit", "value")
)
def update_columns_on_edit_mode(enabled: bool) -> List[Dict]:
    return [
        {"name": k, "id": k, "editable": (k in EDITABLE_COLUMNS and enabled)}
        for k in COLUMNS
    ]

@dash_app.callback(
    Output("table", "page_size"),
    Input("page-size-dropdown", "value")
)
def update_page_size(page_size: Optional[int]) -> int:
    if page_size is None or page_size not in TABLE_SIZES:
        logger.warning(f"Invalid page size selected: {page_size}. Using default size {DEFAULT_TABLE_SIZE}.")
        return DEFAULT_TABLE_SIZE

    logger.info(f"Page size set to: {page_size}")
    return page_size


@dash_app.callback(
    Output("update-notification", "children"),
    Output("update-notification", "is_open"),
    Output("update-notification", "color"),
    Output("current-data-store", "data"),
    Output("id-counter", "data", allow_duplicate=True),
    Input("refresh-button", "n_clicks"),
    State("id-counter", "data"),
    prevent_initial_call='initial_duplicate'
)
def load_data(n: int, id_counter: int) -> Tuple[str, bool, str, Dict[str, Dict], int]:
    data: Optional[List[Dict]] = fetch_data()
    if data is None:
        logger.error("Failed to retrieve data from API.")
        return "Could not retrieve data", False, "danger", {}, id_counter

    for row in data:
        row["value"] = format_value(float(row["value"]), PRECISION)
        row["created_at"] = clean_timestamp(row.get("created_at", ""))
        row["updated_at"] = clean_timestamp(row.get("updated_at", ""))

    logger.info(f"Data loaded successfully with {len(data)} records.")

    id_counter = max((int(row.get("id", 0)) for row in data), default=id_counter) + 1
    logger.info(f"ID counter updated to: {id_counter}")

    indexed_data: Dict[str, Dict] = {str(r['id']): r for r in data if 'id' in r}
    logger.info(f"Indexed data by ID: {len(indexed_data)} records.")

    return "Data loaded successfully", True, "success", indexed_data, id_counter


@dash_app.callback(
    Output("table", "data"),
    Output("filter-general", "options"),
    Output("filter-category", "options"),
    Input("current-data-store", "data"),
    Input("filter-general", "value"),
    Input("filter-category", "value"),
    Input("filter-name", "value")
)
def apply_filters(indexed_data: Dict[str, Dict], 
                  general_category_filters: Optional[str], 
                  category_filters: Optional[str], 
                  name_filters: Optional[str]) -> Tuple:

    data: List[Dict] = list(indexed_data.values()).copy()
    filtered: List[Dict] = data

    logger.info(f"Applying filters: general_category={general_category_filters}, category={category_filters}, name={name_filters}")

    # Apply filters one by one on data
    if general_category_filters:
        filtered = [r for r in filtered if r.get("general_category") == general_category_filters]
    if category_filters:
        filtered = [r for r in filtered if r.get("category") == category_filters]
    if name_filters:
        filtered = [r for r in filtered if name_filters.lower() in r.get("name", "").lower()]

    logger.info(f"Filtered {len(filtered)} records")

    # Update dropdown options based on current filtered data
    gen_opts: List[Dict[str, str]] = sorted({r['general_category'] for r in filtered if r.get('general_category')})
    cat_opts: List[Dict[str, str]] = sorted({r['category'] for r in filtered if r.get('category')})

    # Fallback: if filtered list is empty, fallback to all options (to prevent empty dropdowns)
    if not gen_opts:
        gen_opts: List[Dict[str, str]] = sorted({r['general_category'] for r in data if r.get('general_category')})
    if not cat_opts:
        cat_opts: List[Dict[str, str]] = sorted({r['category'] for r in data if r.get('category')})

    return (
        filtered,
        [{"label": v, "value": v} for v in gen_opts],
        [{"label": v, "value": v} for v in cat_opts],
    )

@dash_app.callback(
    Output("filter-general", "value"),
    Output("filter-category", "value"),
    Output("filter-name", "value"),
    Input("clear-filters", "n_clicks"),
    prevent_initial_call=True
)
def clear_filters(n_clicks: int) -> Tuple[Optional[str], Optional[str], str]:
    return None, None, ""


@dash_app.callback(
    Output("current-data-store", "data", allow_duplicate=True),
    Input("table", "data"),
    State("current-data-store", "data"),
    prevent_initial_call=True
)
def update_table_data(updated_data: List[Dict], current_data_store: Dict[str, Dict]) -> Any:
    if not updated_data:
        logger.warning("Received empty data from table.")
        return dash.no_update

    updated_ids: Set[str] = set()
    for item in updated_data:
        maybe_id: Optional[str] = item.get("id")
        if maybe_id is None:
            logger.warning("Item without ID found, skipping.")
            continue
        id: str = str(maybe_id)
        updated_ids.add(id)

        current_data_store[id] = item

    # Update stored data
    logger.info(f"Updating table data with {len(updated_data)} records.")
    return current_data_store


@dash_app.callback(
    Output('current-data-store', 'data', allow_duplicate=True),
    Input('table', 'active_cell'),
    State('table', 'data'),
    State('current-data-store', 'data'),
    State("toggle-edit", "value"),
    prevent_initial_call=True
)
def flag_row_for_deletion(active_cell, table_data, current_data_store, edit_mode_enabled: bool) -> Any:
    if not active_cell or active_cell['column_id'] != DELETE_COLUMN:
        return dash.no_update
    
    if not edit_mode_enabled:
        logger.warning("Edit mode is disabled, cannot flag row for deletion.")
        return dash.no_update
    
    row_idx: int = active_cell['row']
    row_data: Dict = table_data[row_idx]
    id: str = str(row_data['id'])
    flag: bool = not row_data[DELETE_COLUMN]
    row_data[DELETE_COLUMN] = flag
    current_data_store[id][DELETE_COLUMN] = flag

    logger.info(f"Row {id} flagged for deletion: {flag}")
    
    return current_data_store


@dash_app.callback(
    Output("table", "data", allow_duplicate=True),
    Output("id-counter", "data", allow_duplicate=True),
    Input("add-row", "n_clicks"),
    Input("filter-general", "value"),
    Input("filter-category", "value"),
    Input("filter-name", "value"),
    State("table", "data"),
    State("id-counter", "data"),
    prevent_initial_call=True
)
def add_row(n: int, filter_general: str, filter_category: str, filter_name: str, current: List[Dict], id_counter: int) -> Tuple[List[Dict], int]:
    current.append({
        "id": str(id_counter), "created_at": None, "updated_at": None, "name": filter_name or "NEW_PARAMETER",
        "general_category": filter_general or "", "category": filter_category or "", 
        "description": "", "value": 0.0, DELETE_COLUMN: False
    })
    return current, id_counter + 1


@dash_app.callback(
    Output("table", "data", allow_duplicate=True),
    Output("current-data-store", "data", allow_duplicate=True),
    Input("discard-changes", "n_clicks"),
    prevent_initial_call=True
)
def discard_changes(n: int) -> Tuple[Any, Any]:
    data: Optional[List[Dict]] = fetch_data()
    if data is None:
        logger.error("Failed to retrieve data for discard_changes.")
        return [], {}

    current_data_store: Dict[str, Dict] = {str(item['id']): item for item in data if 'id' in item}
    logger.info(f"Discarding changes, resetting to {len(current_data_store)} records.")
    return data, current_data_store


@dash_app.callback(
    Output("table", "editable"),
    Output("add-row", "disabled"),
    Output("discard-changes", "disabled"),
    Output("confirm-changes", "disabled"),
    Output("drop-all", "disabled"),
    Input("toggle-edit", "value"),
)
def toggle_edit_mode(enabled: bool) -> Tuple[bool, bool, bool, bool, bool]:
    logger.info(f"Edit mode enabled: {enabled}")
    disabled: bool = not enabled
    return (
        enabled,         # table editable
        disabled,        # add-row disabled
        disabled,        # discard-changes disabled
        disabled,        # confirm-changes disabled
        disabled,        # drop-all disabled
    )


@dash_app.callback(
    Output("update-notification", "children", allow_duplicate=True),
    Output("update-notification", "is_open", allow_duplicate=True),
    Output("update-notification", "color", allow_duplicate=True),
    Output("current-data-store", "data", allow_duplicate=True),
    Input("confirm-changes", "n_clicks"),   
    State("current-data-store", "data"),
    prevent_initial_call=True
)
def push_modifications(n: int, current_indexed_data: Dict[str, Dict]) -> Tuple[str, bool, str, Any]:
    original_data: Optional[List[Dict]] = fetch_data()
    if original_data is None:
        logger.error("Failed to retrieve original data from API.")
        return "Failed to retrieve original data", True, "danger", []

    new_records: List[Dict] = []
    updated_records: List[Dict] = []
    deleted_records: List[Dict] = []

    original_ids: Set[str] = set()

    for original_record in original_data:
        maybe_id: Optional[int] = original_record.get('id')
        if maybe_id is None:
            logger.warning("Retrieved record without ID, skipping.")
            continue
        id: str = str(maybe_id)
        original_ids.add(id)

        current_record: Optional[Dict] = current_indexed_data.get(id)
        if current_record is None:
            logger.warning(f"Current record not found for ID {id} - skipping.")
            continue

        if current_record.get(DELETE_COLUMN, False):
            deleted_records.append(current_record)
            continue

        if is_updated(original_record, current_record):
            updated_records.append(get_record_data(current_record))

    for current_id, current_record in current_indexed_data.items():
        if current_id not in original_ids:
            new_records.append(get_new_record_data(current_record))

    errors: List[str] = []
    successes: List[str] = []

    logger.info(f"Trying to add {len(new_records)} new records: {new_records}")
    for r in new_records:
        resp = requests.post(API_BASE, json={"data": r})
        if resp.ok:
            successes.append(f"Record added successfully: {r}")
            logger.debug(f"Record added successfully: {r}")
        else:
            errors.append(f"Add failed for record {r}: {resp.text}")
            logger.error(f"Add failed for record {r}: {resp.text}")

    logger.info(f"Trying to update {len(updated_records)} records: {updated_records}")
    for r in updated_records:
        resp = requests.put(f"{API_BASE}/{r['id']}", json={"data": r})
        if resp.ok:
            successes.append(f"Record updated successfully: {r}")
            logger.debug(f"Record updated successfully: {r}")
        else:
            errors.append(f"Update failed for record {r}: {resp.text}")
            logger.error(f"Update failed for record {r}: {resp.text}")

    logger.info(f"Trying to delete {len(deleted_records)} records: {deleted_records}")
    for r in deleted_records:
        resp = requests.delete(f"{API_BASE}/{r['id']}", json={"confirmDelete": True})
        if resp.ok:
            successes.append(f"Record {r} deleted successfully.")
            logger.debug(f"Record {r} deleted successfully.")
        else:
            errors.append(f"Delete failed for record {r}: {resp.text}")
            logger.error(f"Delete failed for record {r}: {resp.text}")

    new_data: Optional[List[Dict]] = fetch_data()
    if new_data is None:
        logger.error("Failed to retrieve updated data from API after changes.")
        return "Failed to retrieve updated data", True, "danger", []
    
    for row in new_data:
        row["value"] = format_value(float(row["value"]), PRECISION)
        row["created_at"] = clean_timestamp(row.get("created_at", ""))
        row["updated_at"] = clean_timestamp(row.get("updated_at", ""))

    new_data_indexed: Dict[str, Dict] = {str(r['id']): r for r in new_data if 'id' in r}

    if errors:
        return (
            f"{len(successes)} {'successes' if len(successes) != 1 else 'success'} and {len(errors)} {'errors' if len(errors) != 1 else 'error'} occurred",
            True,
            "warning" if len(successes) > 0 else "danger",
            new_data_indexed
        )

    if len(successes) == 0:
        message = "No changes made."
    elif len(successes) == 1:
        message = "1 change applied successfully."
    else:
        message = f"{len(successes)} changes applied successfully."
    return (
        message,
        True,
        "success",
        new_data_indexed
    )



@dash_app.callback(Output("confirm-drop", "displayed"), Input("drop-all", "n_clicks"), prevent_initial_call=True)
def confirm_drop(n: int) -> bool:
    return bool(n)


@dash_app.callback(
    Output("update-notification", "children", allow_duplicate=True),
    Output("update-notification", "is_open", allow_duplicate=True),
    Output("update-notification", "color", allow_duplicate=True),
    Output("current-data-store", "data", allow_duplicate=True),
    Input("confirm-drop", "submit_n_clicks"),
    prevent_initial_call=True
)
def drop_all(n: int) -> Tuple[str, bool, str, Any]:
    response: requests.Response = requests.delete(
        f"{API_BASE}/all-records",
        json={"confirmDeleteAll": True, "tableNameConfirmation": TABLE_NAME},
        headers={'Content-Type': 'application/json'}
    )
    if response.ok:
        logger.info("All records deleted successfully.")
        data: Optional[List[Dict]] = fetch_data()
        if data is None:
            logger.error("Failed to retrieve data from API.")
            return "All records deleted successfully", True, "success", []
        
        indexed_data: Dict[str, Dict] = {str(r['id']): r for r in data if 'id' in r}

        return ("All records deleted successfully.", True, "success", indexed_data)

    logger.error(f"Failed to delete all records")
    return (
        f"Failed to delete all records",
        True,
        "danger",
        dash.no_update,
    )