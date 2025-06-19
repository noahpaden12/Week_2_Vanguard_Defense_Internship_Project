# app.py – Image annotation tool with on-screen coordinate display
# ----------------------------------------------------------------
# Run with:
#     streamlit run app.py

import base64
import json
import streamlit as st
from pathlib import Path
import streamlit.components.v1 as components

# ---------- FOLDER SET-UP ----------
UPLOAD_DIR      = Path("images")
ANNOTATION_DIR  = Path("annotations")
DATASET_DIRS    = [Path("dataset1"), Path("dataset2"), Path("dataset3")]

for d in [UPLOAD_DIR, ANNOTATION_DIR, *DATASET_DIRS]:
    d.mkdir(exist_ok=True)

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Image Annotation App", layout="centered")
st.title("Image Annotation Tool")

# ---------- SESSION STATE ----------
def init_state():
    defaults = {
        "selected_dataset": None,
        "current_index": 0,
        "mode": "rect",
        "annotations_dict": {},
        "selected_class": "Unlabeled",
        "last_export_path": "",
        "reset_counter": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
init_state()

# ---------- HELPERS ----------

def to_data_url(path: Path) -> str:
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

def get_class_id(name):          # class_options defined later
    return class_options.index(name) + 1

def get_annotation_path(img_path: Path) -> Path:
    dataset_name = st.session_state.selected_dataset.name
    class_name   = st.session_state.selected_class
    save_dir     = ANNOTATION_DIR / dataset_name / class_name
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir / f"{img_path.stem}_annotations.json"

# Shoelace formula to compute polygon area
def polygon_area(points):
    n = len(points)
    area = 0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - y1 * x2
    return abs(area) / 2

# Compute bounding box from polygon points: [x_min, y_min, width, height]
def polygon_bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    return [x_min, y_min, x_max - x_min, y_max - y_min]

def save_annotation(img_path: Path, data: dict):
    coco_format = {
        "images": [{
            "id": 1, "file_name": img_path.name, "width": 800, "height": 533
        }],
        "annotations": [],
        "categories": [{
            "id": get_class_id(st.session_state.selected_class),
            "name": st.session_state.selected_class,
            "supercategory": "none",
        }],
    }
    ann_id = 1
    for r in data.get("rects", []):
        # Ensure COCO bbox format: [x, y, width, height]
        x, y, w, h = r
        # Defensive: if width or height negative, fix to positive and adjust x,y accordingly
        if w < 0:
            x += w
            w = abs(w)
        if h < 0:
            y += h
            h = abs(h)
        coco_format["annotations"].append({
            "id": ann_id, "image_id": 1,
            "category_id": get_class_id(st.session_state.selected_class),
            "bbox": [x, y, w, h], "segmentation": [],
            "area": w * h, "iscrowd": 0,
        })
        ann_id += 1
    for p in data.get("polys", []):
        segmentation = [coord for pt in p for coord in pt]
        area = polygon_area(p)
        bbox = polygon_bbox(p)
        coco_format["annotations"].append({
            "id": ann_id, "image_id": 1,
            "category_id": get_class_id(st.session_state.selected_class),
            "bbox": bbox,
            "segmentation": [segmentation],
            "area": area,
            "iscrowd": 0,
        })
        ann_id += 1
    json_path = get_annotation_path(img_path)
    with open(json_path, "w") as f:
        json.dump(coco_format, f, indent=2)
    st.session_state.last_export_path = str(json_path)

# ---------- UI AND NAVIGATION ----------
st.sidebar.header("Select a Dataset")
for ds in DATASET_DIRS:
    if st.sidebar.button(f"\U0001F4C2 {ds.name}"):
        st.session_state.selected_dataset = ds
        st.session_state.current_index = 0

uploaded = st.sidebar.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
if uploaded:
    dest = UPLOAD_DIR / uploaded.name
    dest.write_bytes(uploaded.getbuffer())
    st.session_state.selected_dataset = UPLOAD_DIR
    st.session_state.current_index = 0

DEFAULT_IMG = Path("default.jpg")
if st.session_state.selected_dataset:
    images = (
        sorted(st.session_state.selected_dataset.glob("*.jpg")) +
        sorted(st.session_state.selected_dataset.glob("*.jpeg")) +
        sorted(st.session_state.selected_dataset.glob("*.png"))
    )
    if images:
        current_index = max(0, min(st.session_state.current_index, len(images) - 1))
        st.session_state.current_index = current_index
        bg_path = images[current_index]
        st.markdown(f"### Image {current_index + 1} of {len(images)}: `{bg_path.name}`")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("⬅️ Previous"):
                st.session_state.current_index = max(0, st.session_state.current_index - 1)
                st.rerun()
        with col2:
            if st.button("Next ➡️"):
                st.session_state.current_index = min(len(images) - 1, st.session_state.current_index + 1)
                st.rerun()
    else:
        st.warning("No images found in selected dataset.")
        bg_path = DEFAULT_IMG
else:
    st.info("Please select a dataset or upload an image to begin.")
    bg_path = DEFAULT_IMG

if not bg_path.exists():
    st.stop()

img_url = to_data_url(bg_path)
img_key = str(bg_path.resolve())
if img_key not in st.session_state.annotations_dict:
    st.session_state.annotations_dict[img_key] = {"rects": [], "polys": []}
annotations = st.session_state.annotations_dict[img_key]

class_options = ["Unlabeled", "Car", "Truck", "Building", "Tank", "Tree"]
st.selectbox("Class Label", class_options,
             index=class_options.index(st.session_state.selected_class),
             key="selected_class")

st.markdown("### Annotation Tools")
c0, c1, c2, c3, _ = st.columns(5)
if c0.button("Rectangular"): 
    st.session_state.mode = "rect"
if c1.button("Polygonal"):   
    st.session_state.mode = "polygon"
if c2.button("Reset Annotations"):
    st.session_state.annotations_dict[img_key] = {"rects": [], "polys": []}
    st.session_state["annotation_json"] = json.dumps({"rects": [], "polys": []})
    st.session_state.reset_counter += 1
    st.rerun()

mode = st.session_state.mode
st.write(f"**Current mode:** `{mode}`")

# ---------- CANVAS + LIVE COORD DISPLAY ----------
canvas_html = f"""
<canvas id="canvas" width="800" height="533"
        style="border:1px solid #888; background:url('{img_url}'); background-size:cover;"></canvas>

<textarea id="coordsBox"
          style="width:800px;height:100px;margin-top:8px;" readonly></textarea>

<textarea id="jsonData" style="display:none;"></textarea>

<script>
const canvas    = document.getElementById("canvas");
const ctx       = canvas.getContext("2d");
const coordsBox = document.getElementById("coordsBox");
const jsonData  = document.getElementById("jsonData");
const mode      = "{mode}";
let rects       = {json.dumps(annotations['rects'])};
let polys       = {json.dumps(annotations['polys'])};
let curPoly     = [];
let startX, startY, isDrag = false;

function formatPointsFlat(points) {{
    // Flatten points [[x,y], [x,y], ...] => "x1, y1, x2, y2, ..."
    return points.flat().join(", ");
}}

function updateCoordsBox() {{
    // Format rects: each rect is [x, y, w, h]
    const formattedRects = rects.map(r => {{
        const [x, y, w, h] = r;
        return `[${{x}}, ${{y}}, ${{w}}, ${{h}}]`;
    }});

    // Format polygons as JSON strings of nested coordinate arrays
    const formattedPolys = polys.map(p => JSON.stringify(p));
    const formattedCurPoly = curPoly.length > 1 ? [JSON.stringify(curPoly)] : [];

    // Combine all and join by newlines
    const combined = [...formattedRects, ...formattedPolys, ...formattedCurPoly];
    coordsBox.value = combined.join("\\n");

    // Also update hidden textarea with JSON string of annotations
    jsonData.value = JSON.stringify({{rects: rects, polys: polys}});
}}

function drawPolyPath(pts, closed) {{
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    if (closed) ctx.closePath();
    ctx.stroke();
}}

function redrawAll() {{
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = 3; ctx.strokeStyle = "black";
    rects.forEach(([x,y,w,h]) => ctx.strokeRect(x,y,w,h));
    polys.forEach(pts => drawPolyPath(pts, true));
    if (curPoly.length > 1) drawPolyPath(curPoly, false);
    updateCoordsBox();
}}

/* Mouse handlers */
canvas.addEventListener("mousedown", e => {{
    if (mode === "rect") {{
        startX = e.offsetX; startY = e.offsetY; isDrag = true;
    }} else {{
        curPoly.push([e.offsetX, e.offsetY]); redrawAll();
    }}
}});

canvas.addEventListener("mousemove", e => {{
    if (mode === "rect" && isDrag) {{
        redrawAll();
        ctx.strokeRect(startX, startY, e.offsetX - startX, e.offsetY - startY);
    }}
}});

/* -------------- SINGLE-RECTANGLE LOGIC -------------- */
canvas.addEventListener("mouseup", e => {{
    if (mode === "rect" && isDrag) {{
        rects = [[startX, startY, e.offsetX - startX, e.offsetY - startY]];
        isDrag = false;
        redrawAll();
    }}
}});
/* ---------------------------------------------------- */

canvas.addEventListener("dblclick", e => {{
    if (mode === "polygon" && curPoly.length > 2) {{
        polys.push([...curPoly]); curPoly = []; redrawAll();
    }}
}});

redrawAll();
</script>
"""

components.html(
    canvas_html + f"<!-- {st.session_state.reset_counter} -->",
    height=680,
    scrolling=False,
)

# Hidden Streamlit textarea holding JSON data from JS (initial value)
annotation_json = st.text_area(
    "Annotation Data (hidden)",
    value=json.dumps(annotations),
    key="annotation_json",
    height=68,
    label_visibility="collapsed"
)

# Button to save annotations from the textarea back to session state and to file
if st.button("Save Annotations from Canvas"):
    try:
        data = json.loads(annotation_json)
        st.session_state.annotations_dict[img_key] = data
        save_annotation(bg_path, data)
        st.success(f"Annotations saved to {st.session_state.last_export_path}")
    except Exception as e:
        st.error(f"Failed to save annotations: {e}")
