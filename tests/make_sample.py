"""Write a small synthetic model (sample.glb + sample.json) with the real pipeline writer, for CI checks: a muscle with
fibres and the bones of an arm, skinned, with their movements."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))
from anatomo_models import fibers, rig  # noqa: E402
from anatomo_models.model import build  # noqa: E402
from test_pipeline import sample  # noqa: E402
from test_rig import arm  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
bones, marks = arm()
items = [x for x in sample() if x["system"] != "os"] + bones
fibers.annotate(items, [])  # optional _FIBER and _TENDON attributes on the muscles
build(items, os.path.join(out, "sample.glb"), os.path.join(out, "sample.json"), "sample", "0.0.0", [],
      rig=lambda entries, positions: rig.build_rig(entries, positions, marks))  # optional skin and movements
