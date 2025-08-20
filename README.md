# docker-scope-cleaner 🐳🧹

**docker-scope-cleaner** is a lightweight fix tool for Docker containers stuck with stale **systemd transient scopes** or **cgroups**.
It ships a single script – `main.sh` – that cleans up orphaned `docker-<ID>.scope` units, removes lingering cgroups, kills leftover shim/runc processes, and reloads systemd/Docker when necessary.

### 🚀 Installation

Using [Kevin’s Package Manager](https://github.com/kevinveenbirkenbach/pkgmgr):

```bash
pkgmgr install doscol
```

(`doscol` = **do**cker **sco**pe **l**eaner)

### 🛠 Usage

Directly from the repo:

```bash
bash main.sh <container-name>
# Example:
bash main.sh openresty
```

After installation via **pkgmgr**:

```bash
doscol <container-name>
# Example:
doscol openresty
```

### ✨ Features

* Detects and removes stale `docker-*.scope` units
* Cleans orphaned cgroups under `/sys/fs/cgroup/system.slice`
* Kills stuck `containerd-shim`/`runc` processes
* Reloads systemd and restarts Docker daemons if needed

### 📖 Background

This tool was developed to address recurring Docker restart issues where systemd refused to create a new container scope:

```
OCI runtime create failed: unable to apply cgroup configuration:
Unit docker-<ID>.scope was already loaded or has a fragment file
```

👉 See the full conversation and debugging process here: [ChatGPT Conversation]([https://chat.openai.com/share/6c7b1632-23c4-4c26-91b3-77c73ad7a8a7](https://chatgpt.com/share/68a5e136-8068-800f-ae53-1e166897fe10))

### 👨‍💻 Author

Created by **Kevin Veen-Birkenbach**
🌍 [https://www.veen.world](https://www.veen.world)

