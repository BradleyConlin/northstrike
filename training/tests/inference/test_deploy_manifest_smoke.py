import json, pathlib
import onnxruntime as ort

MAN = "deploy/models/manifest.json"

def _iter_model_paths(man):
    # support dict {"name": {...}} or list [{"path": ...}, ...]
    if isinstance(man, dict):
        recs = man.values()
    elif isinstance(man, list):
        recs = man
    else:
        recs = []
    for r in recs:
        p = r.get("dst") or r.get("path")
        if p:
            yield pathlib.Path(p)

def test_deploy_manifest_smoke():
    m = json.load(open(MAN))
    paths = list(_iter_model_paths(m))
    assert paths, "manifest must contain at least one model path"
    for p in paths:
        assert p.is_file(), f"missing model file: {p}"
        sess = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
        # sanity: session has IO
        assert sess.get_inputs() and sess.get_outputs()
