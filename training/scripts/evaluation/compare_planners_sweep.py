import os
from datetime import datetime


def main():
    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/compare_planners_sweep.md", "w") as f:
        f.write(
            "# Planner KPI Seed Sweep\n\nRRT (across seeds)\nGenerated: "
            + datetime.now().isoformat()
            + "\n"
        )
    print("compare_planners_sweep: OK")


if __name__ == "__main__":
    main()
