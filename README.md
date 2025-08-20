# docker-scope-cleaner
docker-scope-cleaner is a small utility script that fixes Docker containers stuck with stale systemd transient scope or cgroup entries. It detects and removes orphaned docker-&lt;ID>.scope units, cleans up leftover cgroups and shim processes, and optionally reloads systemd and restarts Docker’s control plane.
