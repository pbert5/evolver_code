# Suggested Commands

## evolver (run from `evolver/`)
```bash
nix develop          # enter dev shell with Python + all server deps
nix build            # build evolver-server binary to ./result/
nix build .#evolver  # explicit
# run server manually (dev):
cd evolver && python evolver.py
# run via Nix package:
EVOLVER_DATA_DIR=./data result/bin/evolver-server
```

## dpu (run from `dpu/`)
```bash
nix develop                            # Python 3.9 shell with all deps
python calibration/calibrate.py --help
python calibration/calibrate.py -a <evolver-ip> -g   # list calibration names
python calibration/calibrate.py -a <evolver-ip> -n <cal-name> -t sigmoid -f <fit-name> -p od_90
python experiment/server_test.py       # simple stir/temp test loop
cd graphing/src && python manage.py runserver  # Django graphing app
```

## git (each repo separately)
```bash
# evolver commits:
cd /home/ash/Documents/work/evolver_code/evolver && git add <files> && git commit
# dpu commits:
cd /home/ash/Documents/work/evolver_code/dpu && git add <files> && git commit
```

## Nix flake maintenance
```bash
nix flake update     # update flake.lock (run in evolver/ or dpu/ separately)
nix flake show       # verify outputs
```
