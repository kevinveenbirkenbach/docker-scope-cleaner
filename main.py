#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import signal
import time
import shutil

def run(cmd, check=False, capture_output=True):
    """Run shell command with subprocess"""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return e.stdout.strip() if e.stdout else ""

def log(msg):
    print(f"[doscol] {msg}")

def resolve_cid(target):
    """Find container ID from name/partial"""
    # Exact name first
    id_exact = run(["docker", "ps", "-a", "--filter", f"name=^{target}$", "--format", "{{.ID}}"])
    if id_exact:
        return id_exact
    # Substring fallback
    lines = run(["docker", "ps", "-a", "--format", "{{.ID}} {{.Names}}"]).splitlines()
    for line in lines:
        if target in line:
            return line.split()[0]
    return None

def graceful_stop(cid):
    log(f"Trying graceful stop: docker stop -t 20 {cid[:12]}")
    rc = subprocess.call(["docker", "stop", "-t", "20", cid])
    return rc == 0

def hard_kill(cid):
    short = cid[:12]
    # Get container PID
    pid = run(["docker", "inspect", "-f", "{{.State.Pid}}", cid])
    if pid.isdigit() and int(pid) > 1:
        log(f"Killing container PID {pid}")
        try:
            os.kill(int(pid), signal.SIGTERM)
            time.sleep(2)
            os.kill(int(pid), 0)
            log(f"Escalating SIGKILL to {pid}")
            os.kill(int(pid), signal.SIGKILL)
        except ProcessLookupError:
            pass

    # Kill shims/runc processes
    for proc in ["containerd-shim", "runc"]:
        pids = run(["pgrep", "-f", f"{proc}.*{short}"])
        if pids:
            log(f"Killing {proc} pids: {pids}")
            for p in pids.splitlines():
                try:
                    os.kill(int(p), signal.SIGKILL)
                except ProcessLookupError:
                    pass

    # Delete containerd task
    if shutil.which("ctr"):
        tasks = run(["ctr", "-n", "moby", "tasks", "ls"])
        if short in tasks:
            log("Deleting containerd task via ctr")
            subprocess.call(["ctr", "-n", "moby", "tasks", "kill", cid, "SIGKILL"])
            subprocess.call(["ctr", "-n", "moby", "tasks", "delete", cid])
            subprocess.call(["ctr", "-n", "moby", "containers", "delete", cid])

def cleanup_systemd_scope(cid):
    scope = f"docker-{cid}.scope"
    cgdir = f"/sys/fs/cgroup/system.slice/{scope}"

    log(f"Cleaning systemd scope {scope}")
    subprocess.call(["systemctl", "stop", scope])
    subprocess.call(["systemctl", "reset-failed", scope])
    if os.path.isdir(cgdir):
        log(f"Removing cgroup dir {cgdir}")
        try:
            os.rmdir(cgdir)
        except OSError:
            shutil.rmtree(cgdir, ignore_errors=True)

def docker_rm(cid):
    log(f"Force removing container {cid[:12]}")
    subprocess.call(["docker", "rm", "-f", cid])

def restart_daemons():
    log("Restarting containerd/docker daemons")
    subprocess.call(["systemctl", "daemon-reexec"])
    subprocess.call(["systemctl", "restart", "containerd"])
    subprocess.call(["systemctl", "restart", "docker"])

def main():
    parser = argparse.ArgumentParser(
        description="docker-scope-cleaner (doscol): stop stuck containers and cleanup scopes/cgroups."
    )
    parser.add_argument("target", help="Container name or ID (partial)")
    parser.add_argument("--hard", action="store_true", help="Skip graceful stop, do hard cleanup immediately")
    parser.add_argument("--restart-daemons", action="store_true", help="Restart containerd and docker after cleanup")

    args = parser.parse_args()

    cid = resolve_cid(args.target)
    if not cid:
        log(f"No container found for: {args.target}")
        sys.exit(3)

    log(f"Target container: {cid[:12]}")

    if not args.hard:
        if graceful_stop(cid):
            log("Graceful stop succeeded")
            docker_rm(cid)
            if args.restart_daemons:
                restart_daemons()
            return
        else:
            log("Graceful stop failed, continuing with hard cleanup")

    hard_kill(cid)
    cleanup_systemd_scope(cid)
    docker_rm(cid)
    if args.restart_daemons:
        restart_daemons()

    # Verification
    remaining = run(["docker", "ps", "-a", "--format", "{{.ID}}"]).splitlines()
    if cid in remaining:
        log(f"WARNING: Container still present after cleanup: {cid[:12]}")
        sys.exit(4)
    else:
        log(f"Cleanup complete for {cid[:12]}")

if __name__ == "__main__":
    main()
