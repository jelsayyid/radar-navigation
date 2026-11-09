# Jetson optional Nav2 native teardown issue

Observed during November 8 consolidation on aarch64/Humble, installed
`nav2_costmap_2d` 1.1.20. This server is **not part of the stationary system**.

The real StaticLayer test successfully marks occupied cells and propagates an
all-unknown source map to the configured unmarked local costmap. After lifecycle
deactivate/cleanup, however, the native server exits with SIGSEGV. The old test
ignored process exit status and reported success; the strengthened test now
reports this failure instead of hiding it.

GDB located the crash in `rclcpp::CallbackGroup::~CallbackGroup()`, called during
`NodeBase` / `rclcpp_lifecycle::LifecycleNode` destruction. These did not fix it:

1. Explicit lifecycle shutdown after deactivate and cleanup.
2. A small standalone C++ diagnostic that destroys executor/node before calling
   `rclcpp::shutdown()`; it still exited -11. This diagnostic is retained in
   Jetson artifacts, not used as a production workaround.

No installed ROS library was changed. A separate test-cleanup bug was fixed so
an assertion failure still closes the Python ROS context and does not cause
cascading `Context.init() must only be called once` errors in later tests.

Evidence: `/home/tejas/radar_integration_artifacts/consolidation_20261108T1900/`,
including `nav2_debug.log`, `nav2_lifetime_build.log`, `nav2_lifetime_test.log` and
full middleware runs. Reproduce with:

```bash
ROS_DOMAIN_ID=89 python3 -m unittest discover -s tests_ros -p test_nav2_costmap.py -v
```

Full middleware discovery includes this optional failure on the observed Jetson.
The required stationary suite is `test_cloud_input.py` plus `test_system.py`;
dry watchdog/localization regressions are separate and must also remain checked.
Do not describe the full Jetson middleware suite as all passing until native
teardown is resolved. Investigate matched ROS/Nav2 package versions and a minimal
callback-group reproduction before enabling a physical Nav2 control milestone.

## CI isolation investigation (November 8, 2026)

The dedicated CI branch starts from `9f6d201`; no physical deployment changes.
The reported Jetson backtrace and prior lifecycle/shutdown-order experiments
above remain evidence from that host, not a newly reproduced cloud backtrace.

Source review of Nav2's Humble `Costmap2DROS` finds an empty destructor;
`on_deactivate` joins the map update thread, while `on_cleanup` resets the layered
costmap, TF listener/buffer, footprint endpoints, publisher and clear service
before resetting the internal executor thread. The standalone executable calls
`rclcpp::shutdown()` before destruction of its local node shared pointer.
These are lifetime-order investigation leads, not proof of a race or ABI defect.
No upstream library patch or unverified package pin is applied.

Cloud reproduction environment: official `ros:humble-ros-base`, amd64, digest
`sha256:d9bcf2e6f72df127fdee07048c2e87b1b4b9a59a74af0592f4489fc2844aa855`.
Installed rclcpp, rclcpp-components and rclcpp-lifecycle are all
`16.0.21-1jammy.20260907` builds (suffixes 213403, 223024, 223044 respectively).
There is no evidence yet of an ABI mismatch. Nav2 installation failed because
this cloud proxy returned HTTP 403 for packages.ros.org; apt could not retrieve
the signed InRelease and could not locate ros-humble-nav2-costmap-2d. Therefore
native reproduction, installed Nav2 version comparison, ldd and GDB remain
blocked in this environment. TLS and package verification remain enabled.

Required Humble CI now discovers every test_*.py except test_nav2_costmap.py.
This includes test_cloud_input, test_system, test_humble and
test_localization_gate; new ROS regression files are included automatically.
A separate job explicitly labeled nonblocking runs the native test on every
push and PR. Its test step still fails on crashes and uploads full output,
package versions and linked libraries with `if: always()`. Job-level
continue-on-error isolates its effect on the workflow; it does not turn the
unittest into a passing test. Branch protection must require the middleware job,
not the optional diagnostic; repository protection settings were not changed.

The native test now launches the installed executable directly to report its
actual status (e.g. -11 for SIGSEGV), preserves both occupied/cleared assertions,
and only signals a still-running child. It prints full logs and status. This is
diagnostic cleanup, not a claimed crash fix. The upstream/library versus test
root cause is unresolved. Do not enable physical Nav2 control on this evidence.
