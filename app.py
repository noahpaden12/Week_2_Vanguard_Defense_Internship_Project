import base64
import json
import streamlit as st
from pathlib import Path
import os

# ---------- FOLDER SET-UP ----------
UPLOAD_DIR = Path("images")
ANNOTATION_DIR = Path("annotations")
DATASET_DIRS = [Path("dataset1"), Path("dataset2"), Path("dataset3")]

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
        "reset_counter": 0
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ---------- HELPERS ----------
def to_data_url(path: Path) -> str:
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def get_class_id(name):
    return class_options.index(name) + 1


def get_annotation_path(img_path: Path) -> Path:
    dataset_name = st.session_state.selected_dataset.name
    class_name = st.session_state.selected_class
    save_dir = ANNOTATION_DIR / dataset_name / class_name
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir / f"{img_path.stem}_annotations.json"


def save_annotation(img_path: Path, data: dict):
    json_path = get_annotation_path(img_path)

    coco_format = {
        "images": [
            {
                "id": 1,
                "file_name": img_path.name,
                "width": 800,
                "height": 533
            }
        ],
        "annotations": [],
        "categories": [
            {
                "id": get_class_id(st.session_state.selected_class),
                "name": st.session_state.selected_class,
                "supercategory": "none"
            }
        ]
    }
    ann_id = 1
    for r in data.get("rects", []):
        x, y, w, h = r
        coco_format["annotations"].append({
            "id": ann_id,
            "image_id": 1,
            "category_id": get_class_id(st.session_state.selected_class),
            "bbox": [x, y, w, h],
            "segmentation": [],
            "area": abs(w * h),
            "iscrowd": 0
        })
        ann_id += 1
    for p in data.get("polys", []):
        segmentation = [coord for point in p for coord in point]
        coco_format["annotations"].append({
            "id": ann_id,
            "image_id": 1,
            "category_id": get_class_id(st.session_state.selected_class),
            "bbox": [],
            "segmentation": [segmentation],
            "area": 0,
            "iscrowd": 0
        })
        ann_id += 1

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
    images = sorted(st.session_state.selected_dataset.glob("*.jpg")) + \
             sorted(st.session_state.selected_dataset.glob("*.jpeg")) + \
             sorted(st.session_state.selected_dataset.glob("*.png"))

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
st.selectbox("Class Label", class_options, index=class_options.index(st.session_state.selected_class),
             key="selected_class")

st.markdown("### Annotation Tools")
col_tools = st.columns([1, 1, 1, 1, 1])
with col_tools[0]:
    if st.button("Rectangular"):
        st.session_state.mode = "rect"
with col_tools[1]:
    if st.button("Polygonal"):
        st.session_state.mode = "polygon"
with col_tools[2]:
    if st.button("Reset Annotations"):
        st.session_state.annotations_dict[img_key] = {"rects": [], "polys": []}
        st.session_state.reset_counter += 1
        st.rerun()


with col_tools[3]:
    if st.button("Export Annotations"):
        save_annotation(bg_path, annotations)
        st.success("Manually exported to annotations folder.")
with col_tools[4]:
    if st.button("❌ Delete Last Export"):
        last_path_str = st.session_state.last_export_path
        if last_path_str:
            path_obj = Path(last_path_str)
            if path_obj.exists():
                try:
                    path_obj.unlink()  # Delete the file
                    st.session_state.last_export_path = ""  # Clear session state
                    st.success(f"Deleted: `{path_obj.name}`")
                    st.rerun()  # Force full rerun to reflect deletion
                except Exception as e:
                    st.error(f"Error deleting file: {e}")
            else:
                st.warning(f"File already deleted or missing: `{path_obj}`")
                st.session_state.last_export_path = ""
                st.rerun()
        else:
            st.warning("No export path recorded.")



mode = st.session_state.mode
st.write(f"**Current mode:** `{mode}`")

canvas_html = f"""
<canvas id=\"canvas\" width=\"800\" height=\"533\"
        style=\"border:1px solid #888; background:url('{img_url}'); background-size:cover;\"></canvas>
<script>
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const mode = "{mode}";
let rects = {json.dumps(annotations['rects'])};
let polys = {json.dumps(annotations['polys'])};
let curPoly = [];
let startX, startY, isDrag = false;

function redrawAll() {{
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = 3;
    ctx.strokeStyle = "black";
    rects.forEach(([x,y,w,h]) => ctx.strokeRect(x,y,w,h));
    polys.forEach(pts => drawPolyPath(pts, true));
    if (curPoly.length > 1) drawPolyPath(curPoly, false);
}}

function drawPolyPath(pts, closed) {{
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    if (closed) ctx.closePath();
    ctx.stroke();
}}

canvas.addEventListener("mousedown", e => {{
    if (mode === "rect") {{
        startX = e.offsetX;
        startY = e.offsetY;
        isDrag = true;
    }} else {{
        curPoly.push([e.offsetX, e.offsetY]);
        redrawAll();
    }}
}});

canvas.addEventListener("mousemove", e => {{
    if (mode === "rect" && isDrag) {{
        redrawAll();
        ctx.strokeRect(startX, startY, e.offsetX - startX, e.offsetY - startY);
    }}
}});

canvas.addEventListener("mouseup", e => {{
    if (mode === "rect" && isDrag) {{
        rects.push([startX, startY, e.offsetX - startX, e.offsetY - startY]);
        isDrag = false;
        redrawAll();
    }}
}});

canvas.addEventListener("dblclick", e => {{
    if (mode === "polygon" && curPoly.length > 2) {{
        polys.push(curPoly.slice());
        curPoly = [];
        redrawAll();
    }}
}});

redrawAll();
</script>
"""

st.components.v1.html(canvas_html + f"<!-- {st.session_state.reset_counter} -->", height=600, scrolling=False)

# ---------- AUTO SAVE ----------
save_annotation(bg_path, annotations)
