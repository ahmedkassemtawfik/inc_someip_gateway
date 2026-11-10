# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

from collections.abc import Iterator
import contextlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest

from quality.pytest.process import assert_process_creates_network_instance
from quality.pytest.process import stop_process
from quality.pytest.process import wait_for_output


class GatewaydTest(unittest.TestCase):
    def setUp(self) -> None:
        self.gatewayd = Path(sys.argv[1])
        self.someipd = Path(sys.argv[2])
        self.configuration = Path(sys.argv[3])
        self.service_instance_manifest = Path(sys.argv[4])
        self.someipd_service_instance_manifest = Path(sys.argv[5])
        self.local_service_provider = Path(sys.argv[6])

    def test_help_returns_success_and_prints_usage(self) -> None:
        result = subprocess.run([self.gatewayd, "--help"], capture_output=True, check=False, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Syntax: gatewayd -h/--help", result.stdout)

    def test_does_not_offer_a_local_service_without_provider(self) -> None:
        with self._started_daemons(with_provider=False) as someipd_process:
            with self.assertRaises(AssertionError):
                wait_for_output(someipd_process, "OFFER(0100): [0001.0001", timeout_seconds=3)

    def test_offers_a_local_service_only_while_its_gatewayd_runs(self) -> None:
        # Issue #366: someipd withdraws the offer when the bridged service goes away.
        with self._started_daemons(with_provider=True) as someipd_process:
            wait_for_output(
                someipd_process,
                "OFFER(0100): [0001.0001",
                failure_prefix="someipd did not offer the local service",
            )
            _terminate(self._gatewayd_process)
            wait_for_output(
                someipd_process,
                "STOP OFFER(0100): [0001.0001",
                failure_prefix="someipd did not withdraw the local service",
            )

    def test_creates_remote_network_instance(self) -> None:
        self._assert_creates_network_instance(
            "Creating remote service instance: echo_response*Gateway started, waiting for shutdown signal...",
            "REQUEST(0100): [4321.5678",
        )

    def _assert_creates_network_instance(self, expected_gatewayd_output: str, expected_someipd_output: str) -> None:
        someipd_process = subprocess.Popen(
            [
                self.someipd,
                "--service_instance_manifest",
                self.someipd_service_instance_manifest,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            wait_for_output(
                someipd_process, "SomeipdService offered", failure_prefix="someipd did not offer SomeipdService"
            )
            assert_process_creates_network_instance(
                [
                    self.gatewayd,
                    "--configuration",
                    self.configuration,
                    "--service_instance_manifest",
                    self.service_instance_manifest,
                ],
                expected_gatewayd_output,
                failure_prefix="gatewayd did not initialize successfully",
            )
            wait_for_output(
                someipd_process,
                expected_someipd_output,
                failure_prefix="someipd did not create a network instance",
            )
        finally:
            stop_process(someipd_process)

    @contextlib.contextmanager
    def _started_daemons(self, *, with_provider: bool) -> Iterator[subprocess.Popen[bytes]]:
        """Start someipd, optionally the provider of window_control, and gatewayd; yield someipd."""
        processes: list[subprocess.Popen[bytes]] = []
        try:
            someipd_process = _start(
                [self.someipd, "--service_instance_manifest", self.someipd_service_instance_manifest]
            )
            processes.append(someipd_process)
            wait_for_output(
                someipd_process, "SomeipdService offered", failure_prefix="someipd did not offer SomeipdService"
            )
            if with_provider:
                provider_process = _start(
                    [
                        self.local_service_provider,
                        self.service_instance_manifest,
                        "gatewayd/application_window_control",
                        "window_control",
                    ]
                )
                processes.append(provider_process)
                wait_for_output(provider_process, "[provider] offered", failure_prefix="provider did not start")
            self._gatewayd_process = _start(
                [
                    self.gatewayd,
                    "--configuration",
                    self.configuration,
                    "--service_instance_manifest",
                    self.service_instance_manifest,
                ]
            )
            processes.append(self._gatewayd_process)
            wait_for_output(
                self._gatewayd_process,
                "Creating local service instance: window_control*Gateway started, waiting for shutdown signal...",
                failure_prefix="gatewayd did not initialize successfully",
            )
            yield someipd_process
        finally:
            for process in reversed(processes):
                stop_process(process)


def _start(command: list[Path | str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)


def _terminate(process: subprocess.Popen[bytes]) -> None:
    """Ask the process to shut down, as on a regular stop."""
    os.killpg(process.pid, signal.SIGTERM)


if __name__ == "__main__":
    _ = unittest.main(argv=[sys.argv[0]])
