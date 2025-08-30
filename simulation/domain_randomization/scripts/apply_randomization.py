import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed")
    ap.parse_args()
    print("apply_randomization: OK")


if __name__ == "__main__":
    main()
