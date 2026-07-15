{
  description = "Integrated local eVOLVER runtime prototype";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs =
    { nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      apps = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonEnv = pkgs.python3.withPackages (
            ps: with ps; [
              aiohttp
              pyyaml
              python-socketio
              textual
            ]
          );
          mkRuntime = module: name:
            pkgs.writeShellApplication {
              inherit name;
              runtimeInputs = [ pythonEnv ];
              text = ''
                export PYTHONPATH="$PWD''${PYTHONPATH:+:$PYTHONPATH}"
                exec python -m ${module} "$@"
              '';
            };
          controlPlane = mkRuntime "evolver_integrated.control_daemon" "run-control-plane";
          broadcastIngest =
            mkRuntime "evolver_integrated.broadcast_ingest_daemon" "run-broadcast-ingest";
          supervisor =
            mkRuntime "evolver_integrated.supervisor_daemon" "run-supervisor";
          tui = mkRuntime "evolver_integrated.tui.app" "run-tui";
        in
        {
          "run-control-plane" = {
            type = "app";
            program = "${controlPlane}/bin/run-control-plane";
            meta.description = "Run the integrated eVOLVER control-plane API.";
          };
          "run-broadcast-ingest" = {
            type = "app";
            program = "${broadcastIngest}/bin/run-broadcast-ingest";
            meta.description = "Persist eVOLVER broadcasts as raw data.";
          };
          "run-supervisor" = {
            type = "app";
            program = "${supervisor}/bin/run-supervisor";
            meta.description = "Run the integrated eVOLVER service supervisor.";
          };
          "run-tui" = {
            type = "app";
            program = "${tui}/bin/run-tui";
            meta.description = "Launch the eVOLVER terminal UI.";
          };
          tui = {
            type = "app";
            program = "${tui}/bin/run-tui";
            meta.description = "Launch the eVOLVER terminal UI.";
          };
          default = {
            type = "app";
            program = "${controlPlane}/bin/run-control-plane";
            meta.description = "Run the integrated eVOLVER control-plane API.";
          };
        }
      );

      checks = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          testSrc = pkgs.lib.cleanSourceWith {
            src = ./.;
            filter = path: type:
              let
                name = baseNameOf path;
              in
              ! (
                name == ".venv"
                || name == ".pytest_cache"
                || name == "__pycache__"
              );
          };
          checkPython = pkgs.python3.withPackages (
            ps: with ps; [
              aiohttp
              flake8
              pytest
              pytestcov
              pyyaml
              python-socketio
              textual
            ]
          );
        in
        {
          tests = pkgs.runCommand "integrated-evolver-tests" {
            src = testSrc;
            nativeBuildInputs = [ checkPython ];
          } ''
            cp -r "$src" source
            cd source
            export PYTHONPATH="$PWD"
            flake8 evolver_integrated tests
            python -m pytest --rootdir=. tests -q
            python <<'PY'
            from pathlib import Path
            import yaml

            schema_root = Path("data/integrated system")
            schema_paths = [
                schema_root / "integrated_evolver_schema.linkml.yml",
                *sorted((schema_root / "schemas").glob("*.yaml")),
            ]
            assert len(schema_paths) > 1
            for schema_path in schema_paths:
                schema = yaml.safe_load(schema_path.read_text())
                assert "linkml:types" in schema["imports"]
                assert "classes" in schema or "enums" in schema
            PY
            touch "$out"
          '';
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          linkmlValidate = pkgs.writeShellApplication {
            name = "linkml-validate";
            runtimeInputs = [ pkgs.uv ];
            text = ''
              exec uvx --from linkml linkml-validate "$@"
            '';
          };
          linkmlGenJsonSchema = pkgs.writeShellApplication {
            name = "gen-json-schema";
            runtimeInputs = [ pkgs.uv ];
            text = ''
              exec uvx --from linkml gen-json-schema "$@"
            '';
          };
          devPython = pkgs.python3.withPackages (
            ps: with ps; [
              aiohttp
              flake8
              pip
              pytest
              pytestcov
              pyyaml
              python-socketio
              textual
            ]
          );
        in
        {
          default = pkgs.mkShell {
            name = "integrated-evolver";
            packages = [
              devPython
              pkgs.git
              pkgs.nix
              pkgs.uv
              linkmlValidate
              linkmlGenJsonSchema
            ];
            shellHook = ''
              echo "LinkML support: use 'gen-json-schema data/integrated\\ system/integrated_evolver_schema.linkml.yml' or 'linkml-validate --schema ... <data.yml>'."
            '';
          };
        }
      );
    };
}
