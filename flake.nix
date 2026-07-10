{
  description = "eVOLVER workspace entrypoints";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs =
    { nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
      workspacePrelude = dir: ''
        workspace="''${EVOLVER_WORKSPACE_DIR:-$PWD}"
        target="$workspace/${dir}"
        if [ ! -f "$target/flake.nix" ]; then
          echo "ERROR: expected ${dir}/flake.nix under $workspace"
          echo "Run from the evolver_code workspace root or set EVOLVER_WORKSPACE_DIR."
          exit 1
        fi
        cd "$target"
      '';
      mkApp =
        pkgs: name: dir: description:
        let
          app = pkgs.writeShellApplication {
            name = "workspace-${name}";
            runtimeInputs = [ pkgs.nix ];
            text = ''
              set -euo pipefail
              ${workspacePrelude dir}
              exec nix run ".#${name}" -- "$@"
            '';
          };
        in
        {
          type = "app";
          program = "${app}/bin/workspace-${name}";
          meta.description = description;
        };
      mkCheckApp =
        pkgs: name: dir: description:
        let
          app = pkgs.writeShellApplication {
            name = "workspace-${name}";
            runtimeInputs = [ pkgs.nix ];
            text = ''
              set -euo pipefail
              ${workspacePrelude dir}
              exec nix flake check "$@"
            '';
          };
        in
        {
          type = "app";
          program = "${app}/bin/workspace-${name}";
          meta.description = description;
        };
    in
    {
      apps = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          evolverApp = name: description: mkApp pkgs name "evolver" description;
          dpuApp = name: description: mkApp pkgs name "dpu" description;
          arduinoApp = name: description: mkApp pkgs name "evolver-arduino" description;
          checkAll = pkgs.writeShellApplication {
            name = "workspace-check-all";
            runtimeInputs = [ pkgs.nix ];
            text = ''
              set -euo pipefail
              workspace="''${EVOLVER_WORKSPACE_DIR:-$PWD}"
              for dir in evolver dpu evolver-arduino; do
                target="$workspace/$dir"
                if [ ! -f "$target/flake.nix" ]; then
                  echo "ERROR: expected $dir/flake.nix under $workspace"
                  echo "Run from the evolver_code workspace root or set EVOLVER_WORKSPACE_DIR."
                  exit 1
                fi
                echo "==> nix flake check $dir"
                (cd "$target" && nix flake check)
              done
            '';
          };
        in
        {
          default = evolverApp "run-server" "Run the eVOLVER socket.io server.";
          "run-server" = evolverApp "run-server" "Run the eVOLVER socket.io server.";
          "run-virtual-evolver" =
            evolverApp "run-virtual-evolver" "Run the eVOLVER server in virtual output mode.";
          "discover-devices" = evolverApp "discover-devices" "Discover connected eVOLVER serial devices.";
          "provision-device" = evolverApp "provision-device" "Provision identity data onto an eVOLVER device.";
          "export-calibration" = evolverApp "export-calibration" "Export device calibration data.";
          "test-virtual-dpu" = evolverApp "test-virtual-dpu" "Run the virtual DPU integration smoke test.";

          "run-dpu" = dpuApp "run-dpu" "Run the DPU experiment controller.";

          "setup-arduino" = arduinoApp "setup-arduino" "Set up Arduino tooling for SAMD21 firmware.";
          "build-firmware" = arduinoApp "build-firmware" "Build SAMD21 eVOLVER firmware.";
          "upload-firmware" = arduinoApp "upload-firmware" "Upload SAMD21 eVOLVER firmware.";
          "setup-arduino-nano" = arduinoApp "setup-arduino-nano" "Set up Arduino Nano tooling.";
          "build-firmware-nano" = arduinoApp "build-firmware-nano" "Build Arduino Nano eVOLVER firmware.";
          "upload-firmware-nano" = arduinoApp "upload-firmware-nano" "Upload Arduino Nano eVOLVER firmware.";

          "check-evolver" = mkCheckApp pkgs "check-evolver" "evolver" "Run the eVOLVER flake checks.";
          "check-dpu" = mkCheckApp pkgs "check-dpu" "dpu" "Run the DPU flake checks.";
          "check-arduino" =
            mkCheckApp pkgs "check-arduino" "evolver-arduino" "Run the Arduino firmware flake checks.";
          "check-all" = {
            type = "app";
            program = "${checkAll}/bin/workspace-check-all";
            meta.description = "Run all workspace subproject flake checks.";
          };
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            name = "evolver-code-workspace";
            packages = [
              pkgs.git
              pkgs.nix
            ];
          };
        }
      );
    };
}
