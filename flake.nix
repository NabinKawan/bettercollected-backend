{
  description = "bettercollected-backend-server flake";
  nixConfig.bash-prompt = ''\n\[\033[1;32m\][nix-develop:\w]\$\[\033[0m\] '';

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-22.11";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix = {
      url = "github:nix-community/poetry2nix?ref=1.38.0";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    {
      overlays.default = nixpkgs.lib.composeManyExtensions [
        poetry2nix.overlay
        (import ./overlay.nix)
        (final: prev: {
          bettercollected-backend-server = prev.callPackage ./default.nix {
            python = final.python3;
            poetry2nix = final.poetry2nix;
          };
          bettercollected-backend-server-dev = prev.callPackage ./editable.nix {
            python = final.python3;
            poetry2nix = final.poetry2nix;
          };
        })
      ];
    } // (flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
        };
      in
      rec {
        packages = {
          default = pkgs.bettercollected-backend-server;
          bettercollected-backend-server-py38 = pkgs.bettercollected-backend-server.override { python = pkgs.python38; };
          bettercollected-backend-server-py39 = pkgs.bettercollected-backend-server.override { python = pkgs.python39; };
          bettercollected-backend-server-py310 = pkgs.bettercollected-backend-server.override { python = pkgs.python310; };
          poetryEnv = pkgs.bettercollected-backend-server-dev;
        } // pkgs.lib.optionalAttrs pkgs.stdenv.isLinux {
          image = pkgs.callPackage ./image.nix {
            inherit pkgs;
            app = pkgs.bettercollected-backend-server;
          };
        };

        apps = {
          bettercollected-backend-server = flake-utils.lib.mkApp { drv = pkgs.bettercollected-backend-server; };
          metrics = {
            type = "app";
            program = toString (pkgs.writeScript "metrics" ''
              export PATH="${pkgs.lib.makeBinPath [
                  pkgs.bettercollected-backend-server-dev
                  pkgs.git
              ]}"
              echo "[nix][metrics] Run bettercollected-backend-server PEP 8 checks."
              flake8 --select=E,W,I --max-line-length 88 --import-order-style pep8 --statistics --count bettercollected_backend_server
              echo "[nix][metrics] Run bettercollected-backend-server PEP 257 checks."
              flake8 --select=D --ignore D301 --statistics --count bettercollected_backend_server
              echo "[nix][metrics] Run bettercollected-backend-server pyflakes checks."
              flake8 --select=F --statistics --count bettercollected_backend_server
              echo "[nix][metrics] Run bettercollected-backend-server code complexity checks."
              flake8 --select=C901 --statistics --count bettercollected_backend_server
              echo "[nix][metrics] Run bettercollected-backend-server open TODO checks."
              flake8 --select=T --statistics --count bettercollected_backend_server tests
              echo "[nix][metrics] Run bettercollected-backend-server black checks."
              black -l 80 --check bettercollected_backend_server
            '');
          };
          docs = {
            type = "app";
            program = toString (pkgs.writeScript "docs" ''
              export PATH="${pkgs.lib.makeBinPath [
                  pkgs.bettercollected-backend-server-dev
                  pkgs.git
              ]}"
              echo "[nix][docs] Build bettercollected-backend-server documentation."
              sphinx-build docs site
            '');
          };
          unit-test = {
            type = "app";
            program = toString (pkgs.writeScript "unit-test" ''
              export PATH="${pkgs.lib.makeBinPath [
                  pkgs.bettercollected-backend-server-dev
                  pkgs.git
              ]}"
              echo "[nix][unit-test] Run bettercollected-backend-server unit tests."
              pytest tests/unit
            '');
          };
          integration-test = {
            type = "app";
            program = toString (pkgs.writeScript "integration-test" ''
              export PATH="${pkgs.lib.makeBinPath [
                  pkgs.bettercollected-backend-server-dev
                  pkgs.git
                  pkgs.coreutils
              ]}"
              echo "[nix][integration-test] Run bettercollected-backend-server unit tests."
              pytest tests/integration
            '');
          };
          coverage = {
            type = "app";
            program = toString (pkgs.writeScript "coverage" ''
              export PATH="${pkgs.lib.makeBinPath [
                  pkgs.bettercollected-backend-server-dev
                  pkgs.git
                  pkgs.coreutils
              ]}"
              echo "[nix][coverage] Run bettercollected-backend-server tests coverage."
              pytest --cov=bettercollected_backend_server --cov-fail-under=90 --cov-report=xml --cov-report=term-missing tests
            '');
          };
          test = {
            type = "app";
            program = toString (pkgs.writeScript "test" ''
              ${apps.unit-test.program}
              ${apps.integration-test.program}
            '');
          };
        };

        devShells = {
          default = pkgs.bettercollected-backend-server-dev.env.overrideAttrs (oldAttrs: {
            buildInputs = [
              pkgs.git
              pkgs.poetry
            ];
          });
          poetry = import ./shell.nix { inherit pkgs; };
        };
      }));
}