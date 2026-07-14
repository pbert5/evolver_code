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
          checkPython = pkgs.python3.withPackages (
            ps: with ps; [
              aiohttp
              flake8
              pytest
              pyyaml
              python-socketio
              textual
            ]
          );
        in
        {
          tests = pkgs.runCommand "integrated-evolver-tests" {
            src = ./.;
            nativeBuildInputs = [ checkPython ];
          } ''
            cp -r "$src" source
            cd source
            export PYTHONPATH="$PWD"
            flake8 evolver_integrated tests
            python -m pytest --rootdir=. tests -q
            touch "$out"
          '';
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          devPython = pkgs.python3.withPackages (
            ps: with ps; [
              aiohttp
              flake8
              pytest
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
            ];
          };
        }
      );
    };
}
