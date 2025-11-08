# SUMO Simulation Builder Pro — Streamlit App (Complete)
# Author: Mahbub Hassan — Chulalongkorn University
# All-in-one SUMO project builder with left/right-hand driving, rich parameter coverage,
# XML generation, project ZIP export, and basic analytics for outputs.

import io
import json
import zipfile
from datetime import datetime
from typing import Dict, Any

import pandas as pd
import streamlit as st
from xml.etree import ElementTree as ET
from xml.dom import minidom

# =============================
# --------- BRANDING ---------
# =============================
APP_TITLE = "SUMO Simulation Builder Pro"
APP_TAGLINE = "Research-grade SUMO scenario designer with global driving modes"
BRAND_OWNER = "Mahbub Hassan"
INSTITUTION = "Chulalongkorn University"

PRIMARY = "#E61E6E"   # CU pink/magenta
PANEL = "#0f172a"      # slate-900
CARD  = "#1e293b"      # slate-800
MUTED = "#94a3b8"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
<style>
  .app-header {{
    background: linear-gradient(90deg, {PRIMARY} 0%, #ff7ab8 100%);
    color: white; padding: 16px 22px; border-radius: 14px;
    box-shadow: 0 8px 30px rgba(0,0,0,.25);
  }}
  .box {{ background: {CARD}; border:1px solid rgba(255,255,255,.06); padding:16px; border-radius:14px; }}
  .muted {{ color:{MUTED}; font-size:12px; }}
  .stTabs [data-baseweb="tab-list"] {{ gap: .5rem; }}
  .stTabs [data-baseweb="tab"] {{ background:{CARD}; color:#e2e8f0; border-radius:10px; }}
  .stTabs [aria-selected="true"] {{ background:{PRIMARY}; color:white; }}
  pre {{ white-space: pre-wrap; }}
</style>
<div class="app-header">
  <h2 style="margin:0;">🚦 {APP_TITLE}</h2>
  <div class="muted">{APP_TAGLINE} • Built by {BRAND_OWNER} • {INSTITUTION}</div>
</div>
""",
    unsafe_allow_html=True,
)

# =============================
# ---------- HELPERS ----------
# =============================

def prettify(xml_string: str) -> str:
    try:
        return minidom.parseString(xml_string).toprettyxml(indent="  ")
    except Exception:
        return xml_string


def xsd_root(tag: str, xsd_url: str) -> ET.Element:
    return ET.Element(
        tag,
        attrib={
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:noNamespaceSchemaLocation": xsd_url,
        },
    )

SCHEMAS = {
    "nodes": "http://sumo.dlr.de/xsd/nodes_file.xsd",
    "edges": "http://sumo.dlr.de/xsd/edges_file.xsd",
    "routes": "http://sumo.dlr.de/xsd/routes_file.xsd",
    "additional": "http://sumo.dlr.de/xsd/additional_file.xsd",
    "sumocfg": "http://sumo.dlr.de/xsd/sumoConfiguration.xsd",
}

# =============================
# ------ DEFAULT TABLES --------
# =============================

default_nodes = pd.DataFrame([
    {"id": "n1", "x": 0.0, "y": 0.0, "type": "priority"},
    {"id": "n2", "x": 100.0, "y": 0.0, "type": "priority"},
])

default_edges = pd.DataFrame([
    {
        "id": "e1", "from": "n1", "to": "n2",
        "numLanes": 2, "speed": 13.89, "priority": 1,
        "laneWidth": 3.2, "allow": "", "disallow": "",
        "shape": "", "spreadType": "center", "endOffset": 0.0,
    }
])

# Vehicle types with extensive parameters
# (Users can add more rows or parameters as columns freely)
default_vtypes = pd.DataFrame([
    {"id":"car","vClass":"passenger","color":"1,0,0","accel":2.6,"decel":4.5,"emergencyDecel":9.0,
     "length":5.0,"minGap":2.5,"maxSpeed":33.33,"sigma":0.5,"tau":1.0,"speedFactor":1.0,"speedDev":0.1,
     "carFollowModel":"IDM","lcStrategic":1.0,"lcCooperative":1.0,"lcKeepRight":0.8,"lcSpeedGain":1.0},
    {"id":"bus","vClass":"bus","color":"0,0,1","accel":1.2,"decel":4.0,"emergencyDecel":7.0,
     "length":12.0,"minGap":3.0,"maxSpeed":22.22,"sigma":0.5,"tau":1.2,"speedFactor":0.9,"speedDev":0.05,
     "carFollowModel":"Krauss","lcStrategic":1.0,"lcCooperative":1.0,"lcKeepRight":0.8,"lcSpeedGain":0.6}
])

default_routes = pd.DataFrame([
    {"id": "r1", "edges": "e1"}
])

default_flows = pd.DataFrame([
    {"id": "f1", "type": "car", "route": "r1", "begin": 0, "end": 3600, "vehsPerHour": 1000}
])

default_trips = pd.DataFrame([
    {"id": "t1", "type": "car", "depart": 0, "from": "e1", "to": "e1"}
])

default_e1 = pd.DataFrame([
    {"id": "det1", "lane": "e1_0", "pos": 50.0, "freq": 60, "file": "e1_output.xml"}
])

default_tl = pd.DataFrame([
    {"id": "tls1", "type": "static", "programID": "p1", "offset": 0, "phaseStates": "GrGr|yryr|rrrr", "durations": "30,4,30"}
])

sim_defaults = {
    "begin": 0, "end": 3600, "stepLength": 0.1, "randomSeed": 42,
    "laneChangeModel": "LC2013", "lateralResolution": 0.8,
    "timeToTeleport": 300, "collisionAction": "warn",
}

outputs_defaults = {
    "tripinfo": {"enabled": True,  "file": "tripinfo.xml"},
    "fcd":      {"enabled": False, "file": "fcd.xml",        "freq": 1},
    "emissions":{"enabled": False, "file": "emissions.xml",   "freq": 60},
    "summary":  {"enabled": True,  "file": "summary.xml",     "freq": 60},
    "edgedata": {"enabled": False, "file": "edgeData.xml",    "freq": 60},
    "lanedata": {"enabled": False, "file": "laneData.xml",    "freq": 60},
}

# =============================
# --------- STATE INIT --------
# =============================
ss = st.session_state
if "nodes" not in ss: ss.nodes = default_nodes.copy()
if "edges" not in ss: ss.edges = default_edges.copy()
if "vtypes" not in ss: ss.vtypes = default_vtypes.copy()
if "routes" not in ss: ss.routes = default_routes.copy()
if "flows"  not in ss: ss.flows  = default_flows.copy()
if "trips"  not in ss: ss.trips  = default_trips.copy()
if "e1"     not in ss: ss.e1     = default_e1.copy()
if "tl"     not in ss: ss.tl     = default_tl.copy()
if "sim"    not in ss: ss.sim    = sim_defaults.copy()
if "outputs"not in ss: ss.outputs= json.loads(json.dumps(outputs_defaults))
if "driving_side" not in ss: ss.driving_side = "right"  # right or left

# =============================
# -------- XML BUILDERS --------
# =============================

def build_nodes_xml(nodes: pd.DataFrame) -> str:
    root = xsd_root("nodes", SCHEMAS["nodes"])
    for _, r in nodes.iterrows():
        ET.SubElement(root, "node", id=str(r["id"]), x=str(r["x"]), y=str(r["y"]), type=str(r.get("type", "priority")))
    return prettify(ET.tostring(root, encoding="unicode"))


def build_edges_xml(edges: pd.DataFrame, driving: str) -> str:
    root = xsd_root("edges", SCHEMAS["edges"])
    # Informational comment (true left-hand geometry/priority is determined during netconvert with --lefthand)
    root.insert(0, ET.Comment(f"Driving side: {driving}-hand (use --lefthand in netconvert if needed)"))
    for _, r in edges.iterrows():
        attrib = {
            "id": str(r["id"]), "from": str(r["from"]), "to": str(r["to"]),
            "numLanes": str(int(r.get("numLanes", 1))), "speed": str(r.get("speed", 13.89)),
            "priority": str(int(r.get("priority", 1))),
        }
        for opt in ("laneWidth","allow","disallow","shape","spreadType","endOffset"):
            val = r.get(opt, "")
            if str(val) != "":
                attrib[opt] = str(val)
        ET.SubElement(root, "edge", attrib)
    return prettify(ET.tostring(root, encoding="unicode"))


def build_routes_xml(vtypes: pd.DataFrame, routes: pd.DataFrame, flows: pd.DataFrame, trips: pd.DataFrame) -> str:
    root = xsd_root("routes", SCHEMAS["routes"])
    # vTypes
    for _, v in vtypes.iterrows():
        attrib = {k: str(v.get(k)) for k in v.index if str(v.get(k)) != ""}
        attrib["id"] = str(v["id"])  # ensure id present
        ET.SubElement(root, "vType", attrib)
    # routes
    for _, r in routes.iterrows():
        ET.SubElement(root, "route", id=str(r["id"]), edges=str(r.get("edges", "")).strip())
    # flows
    for _, f in flows.iterrows():
        attrib = {
            "id": str(f["id"]),
            "type": str(f.get("type", "car")),
            "route": str(f.get("route", "")),
            "begin": str(int(f.get("begin", 0))),
            "end": str(int(f.get("end", 3600))),
            "vehsPerHour": str(int(f.get("vehsPerHour", 1000))),
        }
        ET.SubElement(root, "flow", attrib)
    # trips
    for _, t in trips.iterrows():
        attrib = {k: str(t.get(k)) for k in ["id","type","depart","from","to"] if str(t.get(k, "")) != ""}
        if "id" in attrib:
            ET.SubElement(root, "trip", attrib)
    return prettify(ET.tostring(root, encoding="unicode"))


def build_additional_xml(e1_det: pd.DataFrame, tl: pd.DataFrame) -> str:
    root = xsd_root("additional", SCHEMAS["additional"])
    # e1 detectors
    for _, d in e1_det.iterrows():
        ET.SubElement(
            root,
            "e1Detector",
            {
                "id": str(d.get("id", "det")),
                "lane": str(d.get("lane", "")),
                "pos": str(d.get("pos", 0)),
                "freq": str(int(d.get("freq", 60))),
                "file": str(d.get("file", "e1_output.xml")),
            },
        )
    # traffic lights (simple fixed-time program)
    for _, s in tl.iterrows():
        tl_elem = ET.SubElement(
            root,
            "tlLogic",
            {
                "id": str(s.get("id", "tls1")),
                "type": str(s.get("type", "static")),
                "programID": str(s.get("programID", "p1")),
                "offset": str(int(s.get("offset", 0))),
            },
        )
        states = [x.strip() for x in str(s.get("phaseStates", "GrGr")).split("|") if x.strip()]
        durs = [int(x.strip()) for x in str(s.get("durations", "30")).split(",") if x.strip()]
        if not states:
            states = ["GrGr"]
        if not durs:
            durs = [30]
        for i, stt in enumerate(states):
            dur = durs[i] if i < len(durs) else durs[-1]
            ET.SubElement(tl_elem, "phase", duration=str(dur), state=stt)
    return prettify(ET.tostring(root, encoding="unicode"))


def build_sumocfg_xml(net_file: str, routes_file: str, additional_file: str, sim: Dict[str, Any], outputs: Dict[str, Any]) -> str:
    root = xsd_root("configuration", SCHEMAS["sumocfg"])

    input_node = ET.SubElement(root, "input")
    ET.SubElement(input_node, "net-file", value=net_file)
    ET.SubElement(input_node, "route-files", value=routes_file)
    if additional_file:
        ET.SubElement(input_node, "additional-files", value=additional_file)

    time_node = ET.SubElement(root, "time")
    ET.SubElement(time_node, "begin", value=str(sim.get("begin", 0)))
    ET.SubElement(time_node, "end", value=str(sim.get("end", 3600)))
    ET.SubElement(time_node, "step-length", value=str(sim.get("stepLength", 0.1)))

    proc_node = ET.SubElement(root, "processing")
    ET.SubElement(proc_node, "lateral-resolution", value=str(sim.get("lateralResolution", 0.8)))

    sim_node = ET.SubElement(root, "simulation")
    ET.SubElement(sim_node, "time-to-teleport", value=str(sim.get("timeToTeleport", 300)))

    coll_node = ET.SubElement(root, "collision")
    ET.SubElement(coll_node, "action", value=str(sim.get("collisionAction", "warn")))

    report_node = ET.SubElement(root, "report")
    ET.SubElement(report_node, "verbose", value="true")
    ET.SubElement(report_node, "no-step-log", value="false")

    out_node = ET.SubElement(root, "output")
    if outputs.get("tripinfo", {}).get("enabled"):
        ET.SubElement(out_node, "tripinfo-output", value=outputs["tripinfo"]["file"])
    if outputs.get("fcd", {}).get("enabled"):
        ET.SubElement(out_node, "fcd-output", value=outputs["fcd"]["file"])
        ET.SubElement(out_node, "fcd-output.step", value=str(outputs["fcd"].get("freq", 1)))
    if outputs.get("emissions", {}).get("enabled"):
        ET.SubElement(out_node, "emission-output", value=outputs["emissions"]["file"])
        ET.SubElement(out_node, "emission-output.step", value=str(outputs["emissions"].get("freq", 60)))
    if outputs.get("summary", {}).get("enabled"):
        ET.SubElement(out_node, "summary-output", value=outputs["summary"]["file"])
        ET.SubElement(out_node, "summary-output.step", value=str(outputs["summary"].get("freq", 60)))
    if outputs.get("edgedata", {}).get("enabled"):
        ET.SubElement(out_node, "edgeData-output", value=outputs["edgedata"]["file"])
        ET.SubElement(out_node, "edgeData-output.period", value=str(outputs["edgedata"].get("freq", 60)))
    if outputs.get("lanedata", {}).get("enabled"):
        ET.SubElement(out_node, "laneData-output", value=outputs["lanedata"]["file"])
        ET.SubElement(out_node, "laneData-output.period", value=str(outputs["lanedata"].get("freq", 60)))

    return prettify(ET.tostring(root, encoding="unicode"))

# =============================
# ------------- UI ------------
# =============================
with st.sidebar:
    st.markdown(f"### {BRAND_OWNER}")
    st.caption(INSTITUTION)
    st.markdown("---")
    project_name = st.text_input("Project name", value="sumo_project")
    driving = st.selectbox("Driving side", ["right", "left"], index=0, help="Use left-hand for Thailand, Bangladesh, UK, Japan; right-hand for US/EU.")
    ss.driving_side = driving
    net_name = st.text_input("Network .net.xml", value="network.net.xml")
    rou_name = st.text_input("Routes .rou.xml", value="routes.rou.xml")
    add_name = st.text_input("Additional .add.xml", value="additional.add.xml")
    cfg_name = st.text_input("SUMO config .sumocfg", value="simulation.sumocfg")
    st.markdown("---")
    st.markdown("**Quick commands**")
    lefthand_flag = " --lefthand" if driving == "left" else ""
    st.code(f"netconvert -n nodes.nod.xml -e edges.edg.xml -o {net_name}{lefthand_flag}")
    st.code(f"sumo -c {cfg_name}")

main_tabs = st.tabs([
    "Network", "Edges", "Vehicles & Routes", "Traffic Controls", "Simulation", "Outputs", "XML & Export", "Analytics"
])

# ---------- Network ----------
with main_tabs[0]:
    st.subheader("🗺️ Nodes")
    st.caption("Define intersections and reference points.")
    ss.nodes = st.data_editor(ss.nodes, num_rows="dynamic", use_container_width=True, key="nodes_table")

# ---------- Edges ----------
with main_tabs[1]:
    st.subheader("🛣️ Edges (links between nodes)")
    st.caption("Set lanes, speed, lane width, allow/disallow, shape, etc.")
    ss.edges = st.data_editor(ss.edges, num_rows="dynamic", use_container_width=True, key="edges_table")

# ----- Vehicles & Routes -----
with main_tabs[2]:
    st.subheader("🚗 Vehicle Types (vType)")
    ss.vtypes = st.data_editor(ss.vtypes, num_rows="dynamic", use_container_width=True, key="vtypes_table")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Routes** (space-separated edge IDs)")
        ss.routes = st.data_editor(ss.routes, num_rows="dynamic", use_container_width=True, key="routes_table")
    with c2:
        st.markdown("**Flows**")
        ss.flows = st.data_editor(ss.flows, num_rows="dynamic", use_container_width=True, key="flows_table")

    st.markdown("---")
    st.markdown("**Trips** (optional explicit OD trips)")
    ss.trips = st.data_editor(ss.trips, num_rows="dynamic", use_container_width=True, key="trips_table")

# ------ Traffic Controls ------
with main_tabs[3]:
    st.subheader("🚦 Traffic Lights (fixed-time)")
    st.caption("phaseStates example: GrGr|yryr|rrrr with durations e.g., 30,4,30")
    ss.tl = st.data_editor(ss.tl, num_rows="dynamic", use_container_width=True, key="tl_table")

    st.markdown("---")
    st.subheader("🧲 Detectors — E1 (induction loops)")
    ss.e1 = st.data_editor(ss.e1, num_rows="dynamic", use_container_width=True, key="e1_table")

# --------- Simulation ---------
with main_tabs[4]:
    st.subheader("⚙️ Simulation Settings")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ss.sim["begin"] = st.number_input("Begin (s)", 0, 10_000_000, int(ss.sim["begin"]))
    with c2:
        ss.sim["end"] = st.number_input("End (s)", 0, 10_000_000, int(ss.sim["end"]))
    with c3:
        ss.sim["stepLength"] = st.number_input("Step length (s)", 0.01, 5.0, float(ss.sim["stepLength"]), step=0.01)
    with c4:
        ss.sim["randomSeed"] = st.number_input("Random seed", 0, 1_000_000, int(ss.sim["randomSeed"]))

    c5, c6, c7 = st.columns(3)
    with c5:
        ss.sim["laneChangeModel"] = st.selectbox("Lane-change model", ["LC2013", "SL2015", "DK2008"], index=["LC2013","SL2015","DK2008"].index(ss.sim["laneChangeModel"]))
    with c6:
        # default model label only, per-vehicle model can be set inside vTypes
        st.selectbox("Default car-following model (info)", ["Krauss", "IDM", "EIDM", "Wiedemann"], index=1, help="Set precise models in vType rows via 'carFollowModel'.")
    with c7:
        ss.sim["lateralResolution"] = st.number_input("Lateral resolution", 0.1, 3.0, float(ss.sim["lateralResolution"]))

    st.markdown("---")
    c8, c9 = st.columns(2)
    with c8:
        ss.sim["timeToTeleport"] = st.number_input("time-to-teleport (s)", 0, 10_000, int(ss.sim["timeToTeleport"]))
    with c9:
        ss.sim["collisionAction"] = st.selectbox("collision.action", ["none", "teleport", "remove", "warn"], index=["none","teleport","remove","warn"].index(ss.sim["collisionAction"]))

# ---------- Outputs -----------
with main_tabs[5]:
    st.subheader("📤 Outputs Manager")

    def output_row(name: str, cfg: Dict[str, Any]):
        cols = st.columns((1, 2, 1))
        cfg["enabled"] = cols[0].checkbox(f"Enable {name}", value=cfg.get("enabled", False), key=f"out_{name}")
        cfg["file"] = cols[1].text_input("file", value=cfg.get("file", f"{name}.xml"), key=f"out_{name}_file")
        if "freq" in cfg:
            cfg["freq"] = cols[2].number_input("freq (s)", 1, 10000, int(cfg.get("freq", 60)), key=f"out_{name}_freq")
        st.markdown("---")

    for k in ["tripinfo","fcd","emissions","summary","edgedata","lanedata"]:
        st.markdown(f"**{k}**")
        output_row(k, ss.outputs[k])

# ------- XML & Export ---------
with main_tabs[6]:
    st.subheader("🧩 XML Generation & Export")

    nodes_xml = build_nodes_xml(ss.nodes)
    edges_xml = build_edges_xml(ss.edges, ss.driving_side)
    routes_xml = build_routes_xml(ss.vtypes, ss.routes, ss.flows, ss.trips)
    additional_xml = build_additional_xml(ss.e1, ss.tl)
    sumocfg_xml = build_sumocfg_xml(net_name, rou_name, add_name, ss.sim, ss.outputs)

    with st.expander("nodes.nod.xml"):
        st.code(nodes_xml, language="xml")
    with st.expander("edges.edg.xml"):
        st.code(edges_xml, language="xml")
    with st.expander("routes.rou.xml"):
        st.code(routes_xml, language="xml")
    with st.expander("additional.add.xml"):
        st.code(additional_xml, language="xml")
    with st.expander("simulation.sumocfg", expanded=True):
        st.code(sumocfg_xml, language="xml")

    st.markdown("---")
    st.subheader("📦 Export Project ZIP")
    zip_name = f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("nodes.nod.xml", nodes_xml)
        zf.writestr("edges.edg.xml", edges_xml)
        zf.writestr("routes.rou.xml", routes_xml)
        zf.writestr("additional.add.xml", additional_xml)
        zf.writestr("simulation.sumocfg", sumocfg_xml)
        readme = (
            f"# {APP_TITLE}\n"
            f"Project: {project_name}\n\n"
            "## 1) Build network (.net.xml)\n"
            f"netconvert -n nodes.nod.xml -e edges.edg.xml -o {net_name}{lefthand_flag}\n\n"
            "## 2) Run simulation\n"
            f"sumo -c {cfg_name}\n\n"
            "Notes:\n- Left-hand countries require the --lefthand flag at net conversion stage.\n"
            "- Ensure edge lane IDs (e.g., e1_0) match detector lane inputs.\n"
        )
        zf.writestr("README.txt", readme)

    st.download_button(
        "⬇️ Download Project ZIP",
        data=buf.getvalue(),
        file_name=zip_name,
        mime="application/zip",
    )

# ---------- Analytics ---------
with main_tabs[7]:
    st.subheader("📈 Analytics — Load SUMO Outputs")
    st.caption("Drop tripinfo.xml / summary.xml to visualize key indicators.")

    up_tripinfo = st.file_uploader("Upload tripinfo.xml", type=["xml"], key="up_ti")
    up_summary  = st.file_uploader("Upload summary.xml",  type=["xml"], key="up_sm")

    def parse_tripinfo_xml(file) -> pd.DataFrame:
        try:
            content = file.read()
            root = ET.fromstring(content)
            rows = []
            for t in root.findall("tripinfo"):
                rows.append({
                    "id": t.get("id"),
                    "depart": float(t.get("depart", 0)),
                    "duration": float(t.get("duration", 0)),
                    "routeLength": float(t.get("routeLength", 0)),
                    "waitingTime": float(t.get("waitingTime", 0)),
                    "waitingCount": float(t.get("waitingCount", 0)),
                    "departDelay": float(t.get("departDelay", 0)),
                })
            return pd.DataFrame(rows)
        except Exception as e:
            st.error(f"Failed to parse tripinfo: {e}")
            return pd.DataFrame()

    def parse_summary_xml(file) -> pd.DataFrame:
        try:
            content = file.read()
            root = ET.fromstring(content)
            rows = []
            for s in root.findall("step"):
                rows.append({
                    "time": float(s.get("time", 0)),
                    "loaded": float(s.get("loaded", 0)),
                    "inserted": float(s.get("inserted", 0)),
                    "running": float(s.get("running", 0)),
                    "waiting": float(s.get("waiting", 0)),
                    "ended": float(s.get("ended", 0)),
                    "meanTravelTime": float(s.get("meanTravelTime", 0)),
                })
            return pd.DataFrame(rows)
        except Exception as e:
            st.error(f"Failed to parse summary: {e}")
            return pd.DataFrame()

    if up_tripinfo is not None:
        df_ti = parse_tripinfo_xml(up_tripinfo)
        if not df_ti.empty:
            st.write("Tripinfo sample:", df_ti.head())
            st.metric("Avg travel time (s)", f"{df_ti['duration'].mean():.2f}")
            st.metric("Avg waiting time (s)", f"{df_ti['waitingTime'].mean():.2f}")

    if up_summary is not None:
        df_sm = parse_summary_xml(up_summary)
        if not df_sm.empty:
            st.write("Summary sample:", df_sm.head())
            st.line_chart(df_sm.set_index("time")["meanTravelTime"], use_container_width=True)

st.markdown(
    f"<div class='muted'>© {datetime.now().year} {BRAND_OWNER} • {INSTITUTION} • {APP_TITLE}</div>",
    unsafe_allow_html=True,
)

