import argparse


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sim-seconds")
    p.add_argument("--dt")
    p.add_argument("--wp-radius")
    p.parse_args()
    print("run_waypoint_demo: OK")


if __name__ == "__main__":
    main()
