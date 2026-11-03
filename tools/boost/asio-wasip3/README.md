# Boost.Asio WASIp3 compatibility patch

This bundle adapts Boost.Asio 1.92.0's platform layer, keeping its scheduler,
select reactor, operation objects and associated allocators. The source headers
retain Christopher M. Kohlhoff's copyright and the Boost Software License 1.0.
The upstream baseline is the Boost 1.92.0 distribution; `manifest.json` pins each
input and patched header by SHA-256.

`/webcpp/asio//asio` selects this bundle only for `clang-wasip3`. `prepare.py`
checks the version and every input hash before applying the patch in a temporary
directory. It verifies every output hash before replacing private headers under
`bin/boost-asio-wasip3/include`. It does not modify the source installation and
refuses to apply to a different Boost version or a locally modified input.
Stale extra files or symlinks in the private overlay stop preparation; clean that
private directory and rebuild after changing the set of patched headers.
Only patched headers are copied; other headers continue to come from Boost.

`/webcpp/asio-wasip3//host-headers` exposes association and completion-token
traits to the single-threaded WASIp2 host HTTP scheduler. The only platform
change selected on WASIp2 is the signal-free wait in `null_event`: WASI uses
`poll` instead of the unavailable POSIX `pause`. This does not enable the Asio
socket reactor on WASIp2. Host operations supply their own executor and never
fall back to `system_executor` or an operating-system thread pool.

The changes address missing POSIX signals/interface names, no-thread waiting,
thread-safe signal-blocker selection, shutdown error mapping, unavailable socket
options, scalar socket I/O, and resolver thread-pool initiation without threads.
WASI has no process signals, so the port does not add `MSG_NOSIGNAL`, which the
current UDP libc implementation rejects. TCP sequences use partial transfers.
For UDP `send_to`/`async_send_to`, the WASIp3-only service patch gathers the full
buffer sequence before iovec truncation, then sends one contiguous datagram.
Multiple nonempty buffers require a copy, allocated through the context for
synchronous sends and the handler's associated allocator for asynchronous sends.
The async operation owns the copy and frees it before invoking the handler.
UDP receive and connected `send`/`async_send` still reject multiple nonempty buffers.
Zero-byte operations use a live dummy byte when libc rejects a null pointer,
without allocating a temporary buffer.

The patch makes no changes to wasi-libc. Upstream implementations of
`sendmsg`/`recvmsg`, missing socket operations and additional cooperative C++
runtimes would allow some compatibility code to be removed. Do not replace
missing constants globally or implement UDP sequences as multiple sends.

The tested SDK is wasi-sdk 34.0 (wasi-libc
`2e6fb9d8ee0cdf9e431fbcabe8af3115de000a13`). The cooperative C++ sysroot currently
contains the no-exceptions runtime only. The project selects Wasmtime 50.0.1 for both profiles. Earlier tests found that
47.0.3 could not load the cooperative component, while 49.0.3 could. `run.sh` is a bounded local-test
launcher, using `wasmtime` on `PATH` and granting network/name-lookup access.
It is not a production capability policy.

The launcher bounds each guest's execution to 600 seconds by default. The global
WASIp3 lane includes finite document and Unicode workloads, not only short
network tests: unchanged debug document tests took 127-147 seconds locally
under concurrent build load, and the benchmark smoke pass completed in 155
seconds. A benchmark run under heavier contention exceeded even 180 seconds.
The earlier 15-second limit interrupted these tests. The default provides
about four times the longest completed measurement for shared runners while
still terminating a stuck guest. Set
`WEBCPP_WASIP3_TEST_TIMEOUT` to a positive integer number of seconds to change
the bound. Empty, zero, negative and noninteger values fail before launch.
For focused loopback tests, use `WEBCPP_WASIP3_TEST_TIMEOUT=15`. This setting
changes only the execution bound; all runtime options and guest arguments are
forwarded unchanged.

Run from the superproject root:

```bash
python3 tools/boost/asio-wasip3/prepare_test.py
python3 tools/boost/asio-wasip3/run_test.py
python3 tools/test/asio_wasip3_test.py
b2 -a toolset=clang-wasip3 variant=release threading=single \
  testing.launcher=tools/boost/asio-wasip3/run.sh libs/asio/test libs/asio/example
b2 -a toolset=clang-wasip3 variant=release threading=multi exception-handling=off \
  testing.launcher=tools/boost/asio-wasip3/run.sh \
  libs/asio/test libs/asio/test//wasi_core_threads libs/asio/example
```

For a new Boost baseline, review the upstream changes, regenerate the unified
patch and input/output hashes from clean and modified source headers, and repeat
the single-thread, cooperative-thread and native controls. Never relax the hash
check to apply a patch approximately. The feature and build-profile contract is
in `libs/asio/doc/capabilities.adoc`; build instructions are in `doc/wasip3.adoc`
within that library. No CI is started by the commands above.
