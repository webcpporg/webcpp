#!/usr/bin/env python3
# Copyright (c) 2026 WebCpp.org
#
# Distributed under the Boost Software License, Version 1.0. (See
# accompanying file LICENSE_1_0.txt or copy at
# https://www.boost.org/LICENSE_1_0.txt)

"""Build and run actual consumers from an unpacked, B2-free source snapshot."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def run(command: list[str], environment: dict[str, str], expected: str = "",
        directory: Path | None = None) -> None:
    print(shlex.join(command), flush=True)
    result = subprocess.run(command, env=environment, cwd=directory, check=True, timeout=240,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if expected and expected not in result.stdout:
        raise RuntimeError("consumer exited without its completion witness: " + expected)


def compiler_search_paths(command: list[str], environment: dict[str, str]) -> list[Path]:
    """Ask the selected compiler/target for its header and library search roots."""
    result = subprocess.run(command + ["-E", "-x", "c++", "-v", "-"], input="", text=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            env=environment, check=True, timeout=60)
    paths = []
    reading = False
    for line in result.stderr.splitlines():
        if '-cc1' in line:
            words = shlex.split(line)
            for flag in ("-isysroot", "-resource-dir"):
                if flag in words:
                    paths.append(Path(words[words.index(flag) + 1]).resolve())
        if line == "#include <...> search starts here:":
            reading = True
        elif line == "End of search list.":
            reading = False
        elif reading:
            paths.append(Path(line.strip().removesuffix(" (framework directory)")).resolve())
    if not paths:
        raise RuntimeError("compiler did not report its system include paths")
    result = subprocess.run(command + ["-print-search-dirs"], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=environment, check=True, timeout=60)
    for line in result.stdout.splitlines():
        if line.startswith("libraries: ="):
            # CMake's linker depfiles also record system libraries, such as libm.
            # Trust only the selected driver's declared paths, not a host prefix.
            paths += [Path(path).resolve() for path in
                      line.removeprefix("libraries: =").split(os.pathsep) if path]
    return paths


def dependency_audit(stage: Path, build: Path, commands: list[dict],
                     boost: Path, expected_cobalt: set[str], policy: list[str],
                     compiler_roots: list[Path]) -> dict:
    """Inspect compiler depfiles and commands, including system headers and all source units."""
    dependencies: set[Path] = set()
    depfiles = list(build.rglob("*.d"))
    if not depfiles:
        raise RuntimeError("no compiler dependency files were produced")
    for depfile in depfiles:
        body = depfile.read_text().replace("\\\n", "")
        for rule in body.splitlines():
            if not rule.strip():
                continue
            parts = re.split(r"(?<!\\):(?:\s|$)", rule, maxsplit=1)
            if len(parts) != 2:
                raise RuntimeError("invalid compiler dependency file: " + str(depfile))
            # Linkers and -MP emit additional rules, including empty phony targets.
            for name in shlex.split(parts[1]):
                path = Path(name)
                dependencies.add((path if path.is_absolute() else build / path).resolve())
    stage = stage.resolve()
    boost = boost.resolve()
    for path in dependencies:
        if path.is_relative_to(ROOT.resolve()) and not path.is_relative_to(stage):
            raise RuntimeError("compiler used a checkout dependency: " + str(path))
        if not path.is_file():
            raise RuntimeError("compiler dependency is missing: " + str(path))
        if not path.is_relative_to(stage) and not path.is_relative_to(boost) and not any(
                path.is_relative_to(root) for root in compiler_roots):
            raise RuntimeError("compiler used an undeclared dependency: " + str(path))
        if path.is_relative_to(stage) and "/boost/" in str(path):
            raise RuntimeError("source package contains a replacement Boost header: " + str(path))
    cobalt: set[str] = set()
    for entry in commands:
        source = Path(entry["file"]).resolve()
        if not source.is_relative_to(stage):
            raise RuntimeError("compiler used a source outside the archive: " + str(source))
        if source not in dependencies:
            raise RuntimeError("source has no compiler dependency evidence: " + str(source))
        arguments = entry.get("arguments") or shlex.split(entry["command"])
        if source.is_relative_to(stage / "libs/cobalt/src"):
            cobalt.add(source.relative_to(stage / "libs/cobalt").as_posix())
            for flag in policy:
                if flag not in arguments:
                    raise RuntimeError("Cobalt source has a different configuration: "
                                       + str(source) + ": missing " + flag)
    if cobalt != expected_cobalt:
        raise RuntimeError("compiled Cobalt inventory mismatch: "
                           + repr(cobalt.symmetric_difference(expected_cobalt)))
    groups = {"archive": [], "boost": [], "toolchain": []}
    for path in sorted(dependencies):
        group = "archive" if path.is_relative_to(stage) else (
            "boost" if path.is_relative_to(boost) else "toolchain")
        groups[group].append(str(path))
    if not groups["archive"] or not groups["boost"]:
        raise RuntimeError("incomplete compiler dependency evidence")
    print(f"Dependency audit: {len(commands)} compilations, {len(dependencies)} files, "
          f"{len(cobalt)} declared Cobalt sources; no checkout or replacement Boost headers.",
          flush=True)
    return {"commands": commands, "dependencies": groups, "cobalt_sources": sorted(cobalt),
            "compiler_search_roots": [str(path) for path in compiler_roots]}


def copy_sources(destination: Path) -> None:
    for library in ("config", "asio", "cobalt", "beast"):
        source = ROOT / "libs" / library
        target = destination / "libs" / library
        shutil.copytree(source / "include", target / "include", symlinks=True)
        if library in ("asio", "cobalt"):
            # Source files and pinned ABI declarations, but no build scripts or caches.
            shutil.copytree(source / "src", target / "src", symlinks=True,
                            ignore=shutil.ignore_patterns("Jamfile", "*.jam", "__pycache__"))
        if library in ("asio", "cobalt"):
            shutil.copyfile(source / "sources.json", target / "sources.json")
        shutil.copyfile(source / "LICENSE_1_0.txt", target / "LICENSE_1_0.txt")
        if library in ("asio", "cobalt", "beast"):
            # Audit records and maintainer inputs travel with the derived source.
            # Consumers inspect them; they never need to execute the importer.
            shutil.copytree(source / "upstream", target / "upstream", symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    fixtures = destination / "consumers"
    fixtures.mkdir()
    for library, name in (("asio", "network.cpp"), ("asio", "browser.cpp"),
                          ("asio", "customizations.cpp"), ("asio", "customizations.hpp"),
                          ("asio", "peer.cpp"),
                          ("cobalt", "timers.cpp"), ("cobalt", "configuration.cpp"),
                          ("cobalt", "consumer_config.hpp"), ("cobalt", "threads.cpp")):
        shutil.copyfile(ROOT / "libs" / library / "test/distribution" / name, fixtures / name)
    shutil.copyfile(ROOT / "libs/beast/test/socket_test.cpp", fixtures / "beast.cpp")
    shutil.copyfile(ROOT / "tools/throw_exception.cpp", fixtures / "throw_exception.cpp")
    shutil.copyfile(ROOT / "tools/test/fixtures/portable-network/CMakeLists.txt",
                    destination / "CMakeLists.txt")
    tests = fixtures / "include/webcpp/test"
    tests.mkdir(parents=True)
    shutil.copyfile(ROOT / "tools/node-test/include/webcpp/test/exit_status.hpp",
                    tests / "exit_status.hpp")
    for name in ("client", "state", "cancel"):
        shutil.copyfile(ROOT / f"libs/cobalt/test/tls/cobalt_ssl_{name}.cpp",
                        fixtures / f"ssl_{name}.cpp")
    shutil.copyfile(ROOT / "tools/openssl/test/tls.py", fixtures / "tls.py")
    for path in destination.rglob("*"):
        if path.is_symlink():
            raise RuntimeError("source snapshot contains a symlink: " + str(path))
        if path.name in (".git", ".local", "bin", "Jamfile", "Jamroot"):
            raise RuntimeError("source snapshot leaked a checkout/build dependency: " + str(path))


def snapshot(destination: Path) -> None:
    """Pack real source bytes, delete staging, then extract and verify the archive."""
    staging = destination.parent / "source staging"
    copy_sources(staging)
    hashes = {path.relative_to(staging).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(staging.rglob("*")) if path.is_file()}
    (staging / "archive-manifest.json").write_text(
        json.dumps({"schema": 1, "sha256": hashes}, indent=2) + "\n")
    archive = destination.parent / "webcpp-network.tar.gz"
    with archive.open("wb") as output, gzip.GzipFile(
            fileobj=output, filename="", mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as packed:
            for path in sorted(staging.rglob("*")):
                if not path.is_file():
                    continue
                if path.is_symlink():
                    raise RuntimeError("source archive cannot contain symlinks: " + str(path))
                info = packed.gettarinfo(str(path), arcname=path.relative_to(staging).as_posix())
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                info.mode = 0o644
                with path.open("rb") as content:
                    packed.addfile(info, content)
    shutil.rmtree(staging)
    with tarfile.open(archive) as packed:
        # Extract only our regular files, also on supported Python versions that
        # predate tarfile's extraction filters. No links or external paths.
        for member in packed:
            path = Path(member.name)
            if not member.isfile() or path.is_absolute() or ".." in path.parts:
                raise RuntimeError("invalid source archive entry: " + member.name)
            content = packed.extractfile(member)
            if content is None:
                raise RuntimeError("missing source archive entry: " + member.name)
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with content, target.open("wb") as output:
                shutil.copyfileobj(content, output)
    for name, digest in hashes.items():
        if hashlib.sha256((destination / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("source archive hash mismatch: " + name)
    print(f"Extracted source archive: {len(hashes)} files; SHA256="
          + hashlib.sha256(archive.read_bytes()).hexdigest(), flush=True)


def tls_dependencies(stage: Path, prefix: Path, authorities: Path) -> None:
    """Copy explicitly supplied, already built dependencies into the clean snapshot."""
    dependency = stage / "dependencies/openssl"
    shutil.copytree(prefix / "include", dependency / "include")
    for name in ("libssl.a", "libcrypto.a"):
        shutil.copyfile(prefix / name, dependency / name)
    ca = stage / "dependencies/include/webcpp/asio/detail/ca_certificates.hpp"
    ca.parent.mkdir(parents=True)
    shutil.copyfile(authorities, ca)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--boost-include", type=Path, required=True)
    parser.add_argument("--target", choices=("native", "wasip2", "wasip3", "emscripten"),
                        required=True)
    parser.add_argument("--exceptions", choices=("on", "off"), default="on")
    parser.add_argument("--threads", choices=("single", "multi"), default="single")
    parser.add_argument("--suspend", choices=("jspi", "asyncify"), default="jspi")
    parser.add_argument("--cobalt-executor", choices=("any", "io_context", "custom"), default="any")
    parser.add_argument("--cobalt-pmr", choices=("std", "none", "custom"), default="std")
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--wasi-sdk", type=Path)
    parser.add_argument("--build-system", choices=("direct", "cmake"), default="direct")
    parser.add_argument("--cmake", default="cmake")
    parser.add_argument("--archiver", type=Path)
    parser.add_argument("--ranlib", type=Path)
    parser.add_argument("--evidence-dir", type=Path,
                        help="Keep the tested source archive and compiler dependency receipt")
    parser.add_argument("--openssl-prefix", type=Path,
                        help="Explicit matching provider with include/, libssl.a and libcrypto.a")
    parser.add_argument("--ca-header", type=Path, help="Explicit generated embedded CA header")
    args = parser.parse_args()
    if bool(args.openssl_prefix) != bool(args.ca_header):
        parser.error("TLS requires both --openssl-prefix and --ca-header")
    if args.openssl_prefix and args.target == "emscripten":
        parser.error("Guest OpenSSL is not a browser transport")
    environment = dict(os.environ)
    for name in ("CPATH", "CPLUS_INCLUDE_PATH", "C_INCLUDE_PATH", "CXXFLAGS", "CPPFLAGS",
                 "CFLAGS", "LDFLAGS", "CMAKE_PREFIX_PATH", "CMAKE_TOOLCHAIN_FILE"):
        environment.pop(name, None)
    try:
        with tempfile.TemporaryDirectory(prefix="webcpp unpacked consumer ") as temporary:
            stage = Path(temporary) / "unpacked"
            snapshot(stage)
            # Installed developer tools must not accidentally rescue this consumer.
            unavailable = Path(temporary) / "unavailable-build-tools"
            unavailable.mkdir()
            for name in ("b2", "bjam", "git", "patch"):
                tool = unavailable / name
                tool.write_text("#!/bin/sh\n"
                                f"echo 'Source consumer cannot use {name}' >&2\nexit 127\n")
                tool.chmod(0o755)
            environment["PATH"] = str(unavailable) + os.pathsep + environment.get("PATH", "")
            print("Consumer PATH: B2, Git and patch unavailable (guarded).", flush=True)
            if args.openssl_prefix:
                tls_dependencies(stage, args.openssl_prefix.resolve(), args.ca_header.resolve())
            # Preserve clang++'s basename: resolving its symlink to clang selects
            # the C driver and drops the C++ standard-library link automatically.
            command = [str(args.compiler.absolute()), "-std=c++20", "-O2",
                       "-DBOOST_COBALT_NO_LIB=1"]
            command += ["-isystem", str(args.boost_include.resolve())]
            policy: list[str] = []
            if args.cobalt_executor == "io_context":
                policy += ["-DBOOST_COBALT_USE_IO_CONTEXT=1"]
            if args.cobalt_pmr == "none":
                policy += ["-DBOOST_COBALT_NO_PMR=1"]
            if args.cobalt_executor == "custom":
                policy += ["-DBOOST_COBALT_CUSTOM_EXECUTOR=1"]
            if args.cobalt_pmr == "custom":
                policy += ["-DBOOST_COBALT_USE_CUSTOM_PMR=1"]
            command += policy
            if args.cobalt_executor == "custom" or args.cobalt_pmr == "custom":
                command += ["-include", str(stage / "consumers/consumer_config.hpp")]
            for library in ("config", "asio", "cobalt", "beast"):
                command += ["-I", str(stage / "libs" / library / "include")]
            asio = stage / "libs/asio"
            asio_profile = json.loads((asio / "sources.json").read_text())["profiles"][args.target]
            runtime_sources = [str(asio / source) for source in asio_profile["runtime"]]
            for include in asio_profile["private_include"]:
                command += ["-I", str(asio / include)]
            links: list[str] = []
            if args.target.startswith("wasi"):
                if not args.wasi_sdk or not args.runtime:
                    parser.error("WASI requires --wasi-sdk and --runtime")
                sdk = args.wasi_sdk.resolve()
                command += ["--target=wasm32-" + args.target]
                private = stage / "libs/asio/src" / args.target
                run(["python3", str(private / "verify.py"), "--sdk", str(sdk)], environment)
                if args.threads == "multi":
                    if args.target != "wasip3" or args.exceptions != "off":
                        parser.error("SDK 34 supports cooperative P3 threads "
                                     "only without exceptions")
                    sysroot = sdk / "share/wasi-sysroot/experimental-coop-threads"
                    command += ["--sysroot=" + str(sysroot), "-pthread", "-isystem",
                                str(sdk / "share/wasi-sysroot/include/c++/v1")]
                if args.exceptions == "on":
                    command += ["-fwasm-exceptions", "-mllvm", "-wasm-use-legacy-eh=false"]
                    links += ["-lunwind"]
            elif args.target == "emscripten":
                if not args.runtime:
                    parser.error("Emscripten requires --runtime (Node)")
                if args.threads == "multi":
                    parser.error("The external consumer worker profile needs a browser harness")
                links += ["-lembind", "-sEXIT_RUNTIME=1", "-sENVIRONMENT=node",
                          "-Wl,--export=emscripten_stack_get_current",
                          "-Wl,--export=_emscripten_stack_restore"]
                if args.suspend == "jspi":
                    links += ["-sJSPI"]
                    if args.exceptions == "on":
                        command += ["-fwasm-exceptions"]
                else:
                    links += ["-sASYNCIFY", "-sASYNCIFY_STACK_SIZE=8192"]
                    if args.exceptions == "on":
                        command += ["-fexceptions"]
            elif args.threads == "multi":
                command += ["-pthread"]
            if args.exceptions == "off":
                command += ["-fno-exceptions"]
                runtime_sources += [str(stage / "consumers/throw_exception.cpp")]
            compiler_roots = compiler_search_paths(command, environment)
            suffix = ".js" if args.target == "emscripten" else (
                ".wasm" if args.target.startswith("wasi") else "")
            programs = ([("browser", "distribution browser Promise/timer/HTTP: passed")]
                        if args.target == "emscripten" else
                        [("network", "8 completions, 0 failures"),
                         ("beast", "No errors detected.")])
            programs += [("timers", "distribution Cobalt/Asio timers: passed")]
            programs += [("customizations", "public token/trait specializations and multiple TUs")]
            if args.threads == "multi":
                programs += [("threads", "distribution Cobalt thread coroutine and join: passed")]
            if args.openssl_prefix:
                programs += [("ssl_client", ""), ("ssl_state", ""), ("ssl_cancel", "")]
            build = stage
            commands: list[dict] = []
            contract = json.loads((stage / "libs/cobalt/sources.json").read_text())["profiles"][
                args.target]
            expected_cobalt = set(contract["core"] + contract["runner"])
            if args.threads == "multi":
                expected_cobalt.update(contract["multi_add"])
            if args.openssl_prefix:
                expected_cobalt.update(contract["ssl"])
            if args.build_system == "cmake":
                build = stage / "build"
                configure = [args.cmake, "-S", str(stage), "-B", str(build),
                             "-DCMAKE_CXX_COMPILER=" + str(args.compiler.absolute()),
                             "-DCMAKE_BUILD_TYPE=Release", "-DWEBCPP_SOURCE_ROOT=" + str(stage),
                             "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
                             "-DBOOST_INCLUDE_DIR=" + str(args.boost_include.resolve()),
                             "-DWEBCPP_TARGET=" + args.target, "-DWEBCPP_SUSPEND=" + args.suspend,
                             "-DWEBCPP_COBALT_EXECUTOR=" + args.cobalt_executor,
                             "-DWEBCPP_COBALT_PMR=" + args.cobalt_pmr,
                             "-DWEBCPP_EXCEPTIONS=" + ("ON" if args.exceptions == "on" else "OFF"),
                             "-DWEBCPP_THREADS=" + ("ON" if args.threads == "multi" else "OFF")]
                if args.openssl_prefix:
                    configure += ["-DWEBCPP_OPENSSL_PREFIX=" + str(stage / "dependencies/openssl"),
                                  "-DWEBCPP_CA_INCLUDE=" + str(stage / "dependencies/include")]
                if args.target != "native":
                    configure += ["-DCMAKE_SYSTEM_NAME=Generic",
                                  "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY"]
                if args.wasi_sdk:
                    configure += ["-DWEBCPP_WASI_SDK=" + str(args.wasi_sdk.resolve())]
                    configure += ["-DCMAKE_AR=" + str(args.wasi_sdk.absolute() / "bin/llvm-ar"),
                                  "-DCMAKE_RANLIB=" + str(
                                      args.wasi_sdk.absolute() / "bin/llvm-ranlib")]
                if args.target == "emscripten" and (not args.archiver or not args.ranlib):
                    parser.error("CMake Emscripten requires explicit --archiver emar "
                                 "and --ranlib emranlib")
                for variable, path in (("CMAKE_AR", args.archiver), ("CMAKE_RANLIB", args.ranlib)):
                    if path:
                        configure += ["-D" + variable + "=" + str(path.absolute())]
                run(configure, environment, directory=stage)
                run([args.cmake, "--build", str(build), "--parallel", "4"], environment,
                    directory=stage)
                commands = json.loads((build / "compile_commands.json").read_text())
            objects: dict[str, Path] = {}
            for name, witness in programs:
                executable = build / (name + suffix)
                sources = [str(stage / "consumers" / (name + ".cpp"))] + runtime_sources
                extra_flags: list[str] = []
                extra_links: list[str] = []
                if name == "customizations":
                    sources += [str(stage / "consumers/peer.cpp")]
                if name in ("timers", "threads") or name.startswith("ssl_"):
                    sources += [str(stage / "consumers/configuration.cpp")]
                    library = stage / "libs/cobalt"
                    profiles = json.loads((library / "sources.json").read_text())["profiles"]
                    contract = profiles[args.target]
                    selected = contract["core"] + (contract["runner"] if name != "threads" else [])
                    if args.threads == "multi":
                        selected += contract["multi_add"]
                    if name.startswith("ssl_"):
                        selected += contract["ssl"]
                        provider = stage / "dependencies/openssl"
                        extra_flags = ["-DWEBCPP_ASIO_HAS_OPENSSL=1", "-DWEBCPP_COBALT_LINK_SSL=1",
                                       "-I", str(provider / "include"),
                                       "-I", str(stage / "dependencies/include"),
                                       "-I", str(stage / "consumers/include")]
                        extra_links = [str(provider / "libssl.a"), str(provider / "libcrypto.a")]
                        if args.target.startswith("wasi"):
                            extra_links += ["-lwasi-emulated-getpid", "-lwasi-emulated-signal",
                                            "-lwasi-emulated-process-clocks",
                                            "-lwasi-emulated-mman"]
                    sources += [str(library / path) for path in selected]
                if args.build_system == "direct":
                    linked_objects = []
                    for source in sources:
                        key = hashlib.sha256(json.dumps(command + extra_flags + [source]).encode()
                                             ).hexdigest()[:20]
                        if key not in objects:
                            obj = build / "objects" / (key + ".o")
                            obj.parent.mkdir(exist_ok=True)
                            invocation = command + extra_flags + ["-MD", "-MF", str(obj) + ".d",
                                                                 "-c", source, "-o", str(obj)]
                            run(invocation, environment, directory=stage)
                            commands.append({"directory": str(stage), "file": source,
                                             "arguments": invocation})
                            objects[key] = obj
                        linked_objects.append(str(objects[key]))
                    run(command + extra_flags + linked_objects + extra_links + links +
                        ["-o", str(executable)], environment, directory=stage)
                if name.startswith("ssl_"):
                    tls_environment = dict(environment)
                    if args.runtime:
                        tls_environment["WASMTIME"] = str(args.runtime.resolve())
                    invocation = [sys.executable, str(stage / "consumers/tls.py"), str(executable)]
                    invocation += (["--embedded", "--require-sni"] if name == "ssl_client"
                                   else ["--state-test"])
                    if args.target == "wasip2":
                        invocation += ["--wasip2"]
                    run(invocation, tls_environment, "PASS", directory=stage)
                    print(f"PASS {name}: target={args.target} EH={args.exceptions} "
                          f"threads={args.threads}", flush=True)
                    continue
                invocation = [str(executable)]
                if args.target.startswith("wasi"):
                    invocation = [str(args.runtime.resolve()), "run"]
                    if args.target == "wasip3":
                        invocation += ["-S", "p3", "-W", "component-model-async=y"]
                        if args.threads == "multi":
                            invocation += ["-W", "component-model-threading=y"]
                    invocation += ["-S", "inherit-network=y", "-S", "tcp=y", "-S", "udp=y",
                                   "-S", "allow-ip-name-lookup=y", str(executable)]
                elif args.target == "emscripten":
                    invocation = [str(args.runtime.resolve()), str(executable)]
                run(invocation, environment, witness, directory=stage)
                print(f"PASS {name}: target={args.target} EH={args.exceptions} "
                      f"threads={args.threads}", flush=True)
            receipt = dependency_audit(stage, build, commands, args.boost_include,
                                       expected_cobalt, policy, compiler_roots)
            if args.evidence_dir:
                args.evidence_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(stage.parent / "webcpp-network.tar.gz",
                                args.evidence_dir / "webcpp-network.tar.gz")
                (args.evidence_dir / "compiler-receipt.json").write_text(
                    json.dumps(receipt, indent=2) + "\n")
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout, end="", flush=True)
        return error.returncode or 1
    print("Unpacked source consumer passed without B2, Git, patches or checkout include paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
