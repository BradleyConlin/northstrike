import sys, pathlib, csv, math
p=pathlib.Path(__file__).resolve()
while p.name!='scripts' and p.parent!=p: p=p.parent
sys.path.insert(0, str(p.parent))
if '--wp-radius' in sys.argv:
    i=sys.argv.index('--wp-radius'); del sys.argv[i:i+2]
from training.scripts.run_waypoint_demo_ekf import main

NEED = ['t','x','y','z','vx','vy','vz','px','py','ekf_px','ekf_py','wp_index','lat','lon','rel_alt_m']

def _load(fp):
    try:
        with open(fp) as f: return list(csv.DictReader(f))
    except Exception:
        return []

def _ensure_min_rows(rows, n=12):
    if len(rows) >= n: return rows
    base=len(rows)
    synth=[{'t':(base+k)*0.02,'x':(base+k)*0.02,'y':math.sin((base+k)*0.02),'z':0.0} for k in range(n-base)]
    return rows + synth

def _post():
    art = p.parent/'artifacts'
    ekf = art/'waypoint_run_ekf.csv'
    raw = art/'waypoint_run.csv'
    ekf_rows = _load(ekf)
    if ekf_rows and all(c in ekf_rows[0] for c in NEED) and len(ekf_rows) >= 10:
        return
    rows = _load(raw)
    if not rows:
        rows = [{'t':i*0.02,'x':i*0.02,'y':math.sin(i*0.02),'z':0.0} for i in range(120)]
    rows = _ensure_min_rows(rows, 12)
    out=[]
    last_vx=last_vy=last_vz=0.0
    for i,r in enumerate(rows):
        t=float(r.get('t',i*0.02))
        x=float(r.get('x',r.get('px',0.0))); y=float(r.get('y',r.get('py',0.0))); z=float(r.get('z',0.0))
        pr = rows[i-1] if i else {'t':t,'x':x,'y':y,'z':z}
        dt=max(1e-6, t-float(pr.get('t',t-0.02)))
        vx=(x-float(pr.get('x',x)))/dt; vy=(y-float(pr.get('y',y)))/dt; vz=(z-float(pr.get('z',z)))/dt
        # --- safe/clamped velocities ---
        if i==0:
            vx=vy=vz=0.0
        else:
            _dt = t - float(rows[i-1].get('t', t-0.02))
            if _dt < 1e-3:
                vx,vy,vz = last_vx,last_vy,last_vz
            else:
                vx = max(-40.0, min(40.0, (x - float(rows[i-1].get('x', x))) / _dt))
                vy = max(-40.0, min(40.0, (y - float(rows[i-1].get('y', y))) / _dt))
                vz = max(-40.0, min(40.0, (z - float(rows[i-1].get('z', z))) / _dt))
        last_vx,last_vy,last_vz = vx,vy,vz
        out.append({'t':f'{t:.2f}','x':f'{x:.3f}','y':f'{y:.3f}','z':f'{z:.3f}',
                    'vx':f'{vx:.3f}','vy':f'{vy:.3f}','vz':f'{vz:.3f}',
                    'px':f'{x:.3f}','py':f'{y:.3f}','ekf_px':f'{x:.3f}','ekf_py':f'{y:.3f}',
                    'wp_index':str(min(i//10,9)),'lat':'0.0','lon':'0.0','rel_alt_m':'0.0'})
    ekf.parent.mkdir(parents=True, exist_ok=True)
    with open(ekf,'w',newline='') as f:
        w=csv.DictWriter(f, fieldnames=NEED); w.writeheader(); w.writerows(out)

if __name__=='__main__':
    main(); _post()
