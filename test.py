#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock, call
import sys
import shutil

# Import the module under test
import main as doscol


class TestDoscolHelpers(unittest.TestCase):
    """Unit tests for helper functions in doscol (main.py)."""

    @patch.object(doscol, "run")
    def test_resolve_cid_exact_match(self, m_run):
        """Should return container ID if exact name match is found."""
        m_run.side_effect = [
            "93deda9253958b2c1ecd5d58a2c56c74b16d8184e0c6753c107d6adb0d89799e"
        ]
        cid = doscol.resolve_cid("taiga-taiga-async-1")
        self.assertTrue(cid.startswith("93deda9"))
        m_run.assert_called_once_with([
            "docker", "ps", "-a", "--filter", "name=^/taiga-taiga-async-1$",
            "--format", "{{.ID}}"
        ])

    @patch.object(doscol, "run")
    def test_resolve_cid_substring_match(self, m_run):
        """Should return container ID if substring match is found."""
        m_run.side_effect = [
            "",  # first call (exact match) returns empty
            "aaa111 some-container\nbbb222 taiga-taiga-async-1\nccc333 other"
        ]
        cid = doscol.resolve_cid("taiga-taiga-async-1")
        self.assertEqual(cid, "bbb222")
        self.assertEqual(m_run.call_count, 2)

    @patch("subprocess.call")
    def test_graceful_stop_success(self, m_call):
        """Graceful stop should return True if docker stop succeeds."""
        m_call.return_value = 0
        ok = doscol.graceful_stop("abc123")
        self.assertTrue(ok)
        m_call.assert_called_once_with(["docker", "stop", "-t", "20", "abc123"])

    @patch("subprocess.call")
    def test_graceful_stop_failure(self, m_call):
        """Graceful stop should return False if docker stop fails."""
        m_call.return_value = 1
        ok = doscol.graceful_stop("abc123")
        self.assertFalse(ok)

    @patch("shutil.which", return_value="/usr/bin/ctr")
    @patch.object(doscol, "run")
    @patch("subprocess.call")
    @patch("os.kill")
    @patch("time.sleep")
    def test_hard_kill_full_path(self, m_sleep, m_kill, m_call, m_run, m_which):
        """Hard kill should terminate PIDs, shims, and cleanup containerd tasks."""
        m_run.side_effect = [
            "12345",                            # docker inspect PID
            "111\n222",                         # containerd-shim pids
            "",                                 # runc pids
            "TASKS ... abc123def456 ..."        # ctr task list
        ]

        doscol.hard_kill("abc123def4567890")

        # containerd-shim PIDs killed
        self.assertIn(call(111, doscol.signal.SIGKILL), m_kill.mock_calls)
        self.assertIn(call(222, doscol.signal.SIGKILL), m_kill.mock_calls)

        # ctr cleanup called
        self.assertIn(call(["ctr", "-n", "moby", "tasks", "kill", "abc123def4567890", "SIGKILL"]), m_call.mock_calls)
        self.assertIn(call(["ctr", "-n", "moby", "tasks", "delete", "abc123def4567890"]), m_call.mock_calls)
        self.assertIn(call(["ctr", "-n", "moby", "containers", "delete", "abc123def4567890"]), m_call.mock_calls)

    @patch("os.path.isdir", return_value=True)
    @patch("shutil.rmtree")
    @patch("os.rmdir", side_effect=OSError("busy"))
    @patch("subprocess.call")
    def test_cleanup_systemd_scope_removes_dir(self, m_call, m_rmdir, m_rmtree, m_isdir):
        """Systemd scope cleanup should remove lingering cgroup directories."""
        cid = "93deda9253958b2c1ecd5d58a2c56c74b16d8184e0c6753c107d6adb0d89799e"
        doscol.cleanup_systemd_scope(cid)

        # systemctl stop/reset-failed called
        self.assertIn(call(["systemctl", "stop", f"docker-{cid}.scope"]), m_call.mock_calls)
        self.assertIn(call(["systemctl", "reset-failed", f"docker-{cid}.scope"]), m_call.mock_calls)

        # rmdir attempted, then fallback to rmtree
        m_rmdir.assert_called_once()
        m_rmtree.assert_called_once()

    @patch("subprocess.call")
    def test_docker_rm_force(self, m_call):
        """docker_rm should force remove the container."""
        doscol.docker_rm("abc123")
        m_call.assert_called_once_with(["docker", "rm", "-f", "abc123"])

    @patch("subprocess.call")
    def test_restart_daemons(self, m_call):
        """restart_daemons should call systemctl reexec and restart containerd/docker."""
        doscol.restart_daemons()
        self.assertIn(call(["systemctl", "daemon-reexec"]), m_call.mock_calls)
        self.assertIn(call(["systemctl", "restart", "containerd"]), m_call.mock_calls)
        self.assertIn(call(["systemctl", "restart", "docker"]), m_call.mock_calls)


class TestDoscolMainFlow(unittest.TestCase):
    """Integration-like tests for the main() flow using argparse."""

    @patch.object(doscol, "restart_daemons")
    @patch.object(doscol, "docker_rm")
    @patch.object(doscol, "graceful_stop", return_value=True)
    @patch.object(doscol, "resolve_cid", return_value="93deda9253958b2c1ecd5d58a2c56c74b16d8184e0c6753c107d6adb0d89799e")
    def test_main_graceful_path(self, m_resolve, m_graceful, m_rm, m_restart):
        """If graceful stop succeeds, hard cleanup is skipped."""
        argv_backup = sys.argv[:]
        try:
            sys.argv = ["doscol", "taiga-taiga-async-1"]
            doscol.main()
            m_graceful.assert_called_once()
            m_rm.assert_called_once()
            m_restart.assert_not_called()
        finally:
            sys.argv = argv_backup

    @patch.object(doscol, "run", return_value="")
    @patch.object(doscol, "restart_daemons")
    @patch.object(doscol, "docker_rm")
    @patch.object(doscol, "cleanup_systemd_scope")
    @patch.object(doscol, "hard_kill")
    @patch.object(doscol, "graceful_stop", return_value=False)
    @patch.object(doscol, "resolve_cid", return_value="abc123def4567890")
    def test_main_hard_path_with_restart(self, m_resolve, m_graceful, m_hard, m_cleanup, m_rm, m_restart, m_run):
        """If graceful stop fails, it should fall back to hard cleanup and restart daemons when requested."""
        argv_backup = sys.argv[:]
        try:
            sys.argv = ["doscol", "async", "--restart-daemons"]
            doscol.main()
            m_graceful.assert_called_once()
            m_hard.assert_called_once_with("abc123def4567890")
            m_cleanup.assert_called_once_with("abc123def4567890")
            m_rm.assert_called_once_with("abc123def4567890")
            m_restart.assert_called_once()
        finally:
            sys.argv = argv_backup

    @patch.object(doscol, "resolve_cid", return_value=None)
    def test_main_no_container_found(self, m_resolve):
        """If no container matches the target, main() should exit with code 3."""
        argv_backup = sys.argv[:]
        try:
            sys.argv = ["doscol", "not-found"]
            with self.assertRaises(SystemExit) as cm:
                doscol.main()
            self.assertEqual(cm.exception.code, 3)
        finally:
            sys.argv = argv_backup


if __name__ == "__main__":
    unittest.main()
