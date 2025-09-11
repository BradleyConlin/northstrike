#!/usr/bin/env python3
import argparse;
def main():
    p=argparse.ArgumentParser(description="Assert hover KPIs");
    p.add_argument("--csv"); p.add_argument("--radius",type=float,default=0.5)
    p.parse_args()
if __name__=="__main__": main()
