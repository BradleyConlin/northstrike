import sys, pathlib
_p = pathlib.Path(__file__).resolve()
while _p.name != "scripts" and _p.parent != _p: _p = _p.parent
sys.path.insert(0, str(_p.parent))
from training.scripts.run_waypoint_demo import main
if __name__ == "__main__": main()
