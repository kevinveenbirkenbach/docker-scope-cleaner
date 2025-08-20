#!/bin/bash
cgdir="/sys/fs/cgroup/system.slice/docker-${cid}.scope"
sudo systemd-cgls /system.slice | grep -A2 -B2 "${cid:0:12}" || true
if [ -d "$cgdir" ]; then
  sudo rmdir "$cgdir" 2>/dev/null || sudo rm -rf "$cgdir"
fi
systemctl daemon-reexec
systemctl restart containerd
systemctl restart docker
