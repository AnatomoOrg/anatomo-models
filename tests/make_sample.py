"""Write a small synthetic model (sample.glb + sample.json) with the real pipeline writer, for CI checks."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))
from anatomo_models.model import build  # noqa: E402
from test_pipeline import sample  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
build(sample(), os.path.join(out, "sample.glb"), os.path.join(out, "sample.json"), "sample", "0.0.0", [])
