# Boost.Asio 1.92 Windows allocator correction

The IOCP context starts an internal worker when requested and starts its timer
thread on the first timer registration. Both upstream thread constructors use
the default allocator for their callable state, even when the context has a
supplied allocator. The patch passes the context allocator into `win_thread`'s
existing allocator-aware overload. Thread scheduling and shutdown are unchanged.

The Asio and compiled Cobalt targets select this private overlay only for
`target-os=windows`. Its manifest pins both the original and resulting file
hashes. Preparation reuses the checked Asio patch tool and never edits installed
Boost. An incompatible Boost version or modified header is rejected.

`allocation_native` and `allocation_native_release` remain the runtime
regressions. They construct a new context and its first timer inside the counted
window and require zero allocations through global `operator new`. The build
regression `test_asio_windows_allocator_overlay_reaches_sources_and_consumers`
checks that the overlay reaches both consumers and compiled Cobalt and is absent
for other targets.
