import os
from datetime import datetime


def main():
    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/compare_planners.md", "w") as f:
        f.write("# Planner KPI Compare\n\n")
        f.write("| Planner | PathLen_m | Time_s | Notes |\n")
        f.write("|---|---:|---:|---|\n")
        f.write("| A* | 10.0 | 1.5 | demo |\n")
        f.write("| RRT | 10.5 | 1.6 | demo |\n")
        f.write("\nGenerated: " + datetime.now().isoformat() + "\n")
    print("compare_planners: OK")


if __name__ == "__main__":
    main()
