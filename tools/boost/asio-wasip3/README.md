# WASI test launchers

`run.sh` grants the local networking capabilities required by the WASIp3 tests,
enables the component-model async/threading features, and enforces a finite
runtime bound. `../asio-wasip2/run.sh` supplies the corresponding P2 launcher.
These are test launchers, not consumer build adapters or deployment policies.

The Asio implementation, SDK ABI declarations, verifier and runtime sources ship
under `libs/asio`. Its `sources.json` inventory selects the required sources.
There is no consumer header overlay and no `prepared.stamp` target here.

Run launcher and ABI checks locally with:

```sh
python3 tools/boost/asio-wasip3/run_test.py
python3 tools/test/asio_sdk_abi_test.py
```
