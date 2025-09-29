# docker-scope-cleaner 🐳🧹

**docker-scope-cleaner** (short: **doscol**) is a lightweight fix tool for Docker containers stuck with stale **systemd transient scopes** or **cgroups**.  
It helps when `docker stop` fails with errors like:

```

Error response from daemon: cannot stop container: <ID>: tried to kill container, but did not receive an exit event

````

---

## 🚀 Installation

Using [Kevin’s Package Manager](https://github.com/kevinveenbirkenbach/pkgmgr):

```bash
pkgmgr install doscol
````

(`doscol` = **do**cker **sco**pe **l**eaner)

If you cloned this repo directly, see `make install` for a hint.

---

## 🛠 Usage

Run the CLI directly:

```bash
python3 main.py <container-name-or-id>
```

Or after installing with **pkgmgr**:

```bash
doscol <container-name-or-id>
```

### Examples

```bash
# Try graceful stop, fall back to hard cleanup if needed
doscol taiga-taiga-async-1

# Immediately perform hard cleanup
doscol taiga-taiga-async-1 --hard

# Cleanup + restart containerd/docker afterwards
doscol taiga-taiga-async-1 --restart-daemons
```

---

## ✨ Features

* Detects and removes stale `docker-*.scope` units
* Cleans orphaned cgroups under `/sys/fs/cgroup/system.slice`
* Kills stuck `containerd-shim` / `runc` processes
* Optionally deletes containerd tasks via `ctr`
* Reloads systemd and restarts Docker/Containerd daemons if needed

---

## 🧪 Development

### Run tests

This project includes unittests in `test.py`:

```bash
make test
```

### Install (hint only)

`make install` does **not** install files.
It just reminds you to use **pkgmgr**:

```bash
make install
```

Output:

```
⚠️  Installation is handled via pkgmgr.
   Please run:
       pkgmgr install doscol
```

---

## 📖 Background

This tool was developed to address recurring Docker restart issues where systemd refused to create a new container scope:

```
OCI runtime create failed: unable to apply cgroup configuration:
Unit docker-<ID>.scope was already loaded or has a fragment file
```

---

## 👨‍💻 Author

Created by **Kevin Veen-Birkenbach**
🌍 [https://www.veen.world](https://www.veen.world)

---

## 📜 License

This project is licensed under the [MIT License](./LICENSE).
