# Personal Folder Setup to Work This:
# /dataset1 (folder)
# /dataset2 (folder)
# /dataset3 (folder)
# /images (folder)
# /annotations (folder)

# Setup
# pip install streamlit
# pip install streamlit-drawable-canvas

import base64
import json
import streamlit as st
from pathlib import Path

# ---------- FOLDER SET-UP ----------
UPLOAD_DIR = Path("images")          
DATASET_DIRS = [Path("dataset1"),    
                Path("dataset2"),
                Path("dataset3")]

for d in [UPLOAD_DIR, *DATASET_DIRS]:
    d.mkdir(exist_ok=True)

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Image Annotation App", layout="centered")
st.title("Image Annotation Tool")

# ---------- HELPERS ----------
def to_data_url(path: Path) -> str:
    """Convert an image file to base-64 data-URL (for <canvas> background)."""
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

def pick_image(label: str, paths: list[Path], key: str) -> None:
    """Dropdown that updates session_state['last_path'] only when user changes."""
    if not paths:
        st.sidebar.write(f"(No images in {label})")
        return

    # Streamlit remembers the widget value in st.session_state[key]
    selected: Path = st.sidebar.selectbox(
        label,
        paths,
        format_func=lambda p: p.name,
        key=key,               # widget key
    )

    # Trigger update if user changed the dropdown
    current = st.session_state.get(f"{key}_selected")
    if selected != current:
        st.session_state["last_path"] = selected
        st.session_state[f"{key}_selected"] = selected

# ---------- SIDEBAR ----------
st.sidebar.header("Choose or Upload an Image")

# -- Upload an image --
uploaded = st.sidebar.file_uploader("Upload image", type=["png", "jpg", "jpeg"])
if uploaded:
    dest = UPLOAD_DIR / uploaded.name
    dest.write_bytes(uploaded.getbuffer())
    st.session_state["last_path"] = dest

# -- Select from uploaded images --
uploads = sorted(UPLOAD_DIR.glob("*.png")) + \
          sorted(UPLOAD_DIR.glob("*.jpg")) + \
          sorted(UPLOAD_DIR.glob("*.jpeg"))
pick_image("Pick image from uploads", uploads, key="uploads")

# -- Select from each dataset folder --
for ds in DATASET_DIRS:
    imgs = sorted(ds.glob("*.png")) + \
           sorted(ds.glob("*.jpg")) + \
           sorted(ds.glob("*.jpeg"))
    pick_image(f"Pick image from {ds.name}", imgs, key=ds.name)

# ---------- DETERMINE BACKGROUND ----------
DEFAULT_IMG = Path("default.jpg")
bg_path = (
    Path(st.session_state["last_path"])
    if st.session_state.get("last_path") and Path(st.session_state["last_path"]).exists()
    else DEFAULT_IMG
)
if not bg_path.exists():       # guard in case default.jpg is missing
    st.info("Upload or select an image to begin.")
    st.stop()

img_url = to_data_url(bg_path)

# ---------- ANNOTATION MODE STATE ----------
if "mode" not in st.session_state:
    st.session_state.mode = "rect"
if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0
if "annotations" not in st.session_state:
    # annotations: {"rects": [[x,y,w,h], ...], "polys": [[[x1,y1],[x2,y2],...], ...]}
    st.session_state.annotations = {"rects": [], "polys": []}

# ---------- TOOLBAR ----------
left, mid, right, far_right = st.columns(4)
with left:
    if st.button("Bounding Boxes"):
        st.session_state.mode = "rect"
with mid:
    if st.button("Reset Annotations"):
        st.session_state.reset_counter += 1
        # Clear annotations when reset pressed
        st.session_state.annotations = {"rects": [], "polys": []}
with right:
    if st.button("Polygons"):
        st.session_state.mode = "polygon"
with far_right:
    export_clicked = st.button("Export Annotations")

mode = st.session_state.mode
reset_counter = st.session_state.reset_counter
st.write(f"**Current mode:** `{mode}`")

# ---------- CANVAS & JS --------------
# The canvas code now includes a hidden textarea to send JSON annotations back to Streamlit on export
canvas_html = f"""
<canvas id="canvas" width="800" height="533"
        style="border:1px solid #888;
               background:url('{img_url}'); background-size:cover;"></canvas>

<!-- Hidden textarea to store JSON annotations -->
<textarea id="annotationData" style="display:none;"></textarea>

<script>
const mode = "{mode}";
const resetCounter = {reset_counter};
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

let startX, startY, isDrag = false;
let rects = [];
let curPoly = [];
let polys = [];

let lastResetCounter = resetCounter;

function redrawAll() {{
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = 3;

    ctx.strokeStyle = "black";
    rects.forEach(([x,y,w,h]) => ctx.strokeRect(x,y,w,h));

    ctx.strokeStyle = "black";
    polys.forEach(pts => drawPolyPath(pts, true));

    if (curPoly.length > 1) {{
        ctx.strokeStyle = "black";
        drawPolyPath(curPoly, false);
    }}
}}

function drawPolyPath(pts, closed) {{
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i=1; i<pts.length; i++) {{
        ctx.lineTo(pts[i][0], pts[i][1]);
    }}
    if (closed) ctx.closePath();
    ctx.stroke();
}}

canvas.addEventListener("mousedown", e => {{
    if (mode === "rect") {{
        startX = e.offsetX; startY = e.offsetY; isDrag = true;
    }} else {{
        curPoly.push([e.offsetX, e.offsetY]);
        redrawAll();
    }}
}});

canvas.addEventListener("mousemove", e => {{
    if (mode === "rect" && isDrag) {{
        redrawAll();
        ctx.strokeStyle = "black";
        ctx.lineWidth = 3;
        ctx.strokeRect(startX, startY,
                       e.offsetX - startX, e.offsetY - startY);
    }}
}});

canvas.addEventListener("mouseup", e => {{
    if (mode === "rect" && isDrag) {{
        rects.push([startX, startY,
                    e.offsetX - startX, e.offsetY - startY]);
        isDrag = false;
        redrawAll();
    }}
}});

canvas.addEventListener("dblclick", e => {{
    if (mode === "polygon" && curPoly.length > 2) {{
        polys.push(curPoly.slice());
        curPoly.length = 0;
        redrawAll();
    }}
}});

setInterval(() => {{
    if (lastResetCounter !== resetCounter) {{
        rects = []; polys = []; curPoly = [];
        redrawAll();
        lastResetCounter = resetCounter;
    }}
}}, 200);

// Function to send current annotations to the hidden textarea
function updateAnnotationData() {{
    const data = JSON.stringify({{rects: rects, polys: polys}});
    document.getElementById('annotationData').value = data;
}}

// Update annotationData every second (or could trigger on changes)
setInterval(updateAnnotationData, 1000);

// Also update before page unload (optional)
window.addEventListener("beforeunload", updateAnnotationData);

redrawAll();
</script>
"""

# Display canvas with annotations textarea
st.components.v1.html(canvas_html, height=600, scrolling=False)

# ---------- EXPORT ANNOTATIONS HANDLING ----------
if export_clicked:
    # Try to read annotations from the hidden textarea using Streamlit's experimental_input workaround
    # Note: Streamlit can't directly read from JS textarea, so we simulate by asking user to paste JSON manually
    # For demo, fallback to last known session annotations if available

    # Here: Let user paste annotation JSON (simulate import)
    st.info("Please paste the annotations JSON from the hidden textarea below (copy from browser console or add integration).")
    user_annotation_json = st.text_area("Paste annotations JSON here", height=150)

    annotations = {"rects": [], "polys": []}
    if user_annotation_json:
        try:
            annotations = json.loads(user_annotation_json)
            st.session_state.annotations = annotations
            st.success("Annotations loaded successfully!")
        except json.JSONDecodeError:
            st.error("Invalid JSON!")

    # Compose COCO-like JSON if annotations available
    if annotations["rects"] or annotations["polys"]:
        coco_format = {
            "images": [
                {
                    "file_name": bg_path.name,
                    "width": 800,
                    "height": 533
                }
            ],
            "annotations": []
        }
        ann_id = 1
        for r in annotations.get("rects", []):
            x, y, w, h = r
            area = abs(w * h)
            coco_ann = {
                "id": ann_id,
                "image_id": 1,
                "category_id": 1,
                "bbox": [x, y, w, h],
                "segmentation": [],
                "area": area,
                "iscrowd": 0
            }
            coco_format["annotations"].append(coco_ann)
            ann_id += 1
        for p in annotations.get("polys", []):
            segmentation = [coord for point in p for coord in point]
            coco_ann = {
                "id": ann_id,
                "image_id": 1,
                "category_id": 1,
                "bbox": [],  # bbox could be calculated here if desired
                "segmentation": [segmentation],
                "area": 0,
                "iscrowd": 0
            }
            coco_format["annotations"].append(coco_ann)
            ann_id += 1
        json_str = json.dumps(coco_format, indent=2)
        filename = bg_path.stem + "_annotations.json"

        st.download_button(
            label="Download Annotation JSON",
            data=json_str,
            file_name=filename,
            mime="application/json"
        )

# ---------- FOOTER ----------
st.markdown("---")
st.subheader("Annotation tools coming soon…")
st.text("COCO export and more features will be added here.")
