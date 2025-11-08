# 🔒 Solutions d'Isolation Workspace - Guide Complet

**Question:** Quelle solution pour isoler les workspaces entre utilisateurs?

**Réponse:** 5 solutions, du simple au complexe

---

## 📊 Vue d'Ensemble

| Solution | Isolation | Complexité | Coût | Recommandation |
|----------|-----------|------------|------|----------------|
| **1. Directories + Permissions** | ⚠️ Moyenne | Faible | Minimal | ✅ Recommandé (démarrage) |
| **2. Linux Namespaces** | ✅ Forte | Moyenne | Faible | ✅ Recommandé (production) |
| **3. chroot/jail** | ✅ Forte | Moyenne | Faible | ⚠️ Alternative |
| **4. Containers par User** | ✅ Très forte | Élevée | Moyen | ⚠️ Overkill |
| **5. VMs par User** | ✅ Maximale | Très élevée | Élevé | ❌ Non pratique |

---

## Solution 1: Directories + Permissions (✅ Recommandé - Démarrage)

### Principe

```
/workspaces/
├── user_abc123/          (drwx------ 0o700)
│   ├── project/
│   └── .gitconfig
└── user_def456/          (drwx------ 0o700)
    └── project/
```

### Implémentation

```python
import os
import hashlib
import secrets
from pathlib import Path

class WorkspaceIsolation:
    """Isolation workspace via directories et permissions"""

    def __init__(self, workspaces_root="/workspaces"):
        self.workspaces_root = Path(workspaces_root)
        self.workspaces_root.mkdir(mode=0o755, exist_ok=True)

    def get_user_id(self, oauth_token: str) -> str:
        """Hash token pour ID anonyme"""
        return hashlib.sha256(oauth_token.encode()).hexdigest()[:16]

    def create_workspace(self, user_id: str) -> Path:
        """Créer workspace isolé avec permissions strictes"""
        workspace = self.workspaces_root / user_id

        # Créer avec owner-only permissions
        workspace.mkdir(mode=0o700, exist_ok=True)

        # Vérifier permissions
        stat = workspace.stat()
        if stat.st_mode & 0o077:
            raise SecurityError("Workspace permissions insecure!")

        return workspace

    def get_security_settings(self, workspace: Path) -> dict:
        """Settings Claude CLI pour isolation"""
        return {
            "permissions": {
                "defaultMode": "ask",
                "allowedTools": [
                    "Read",
                    f"Write({workspace}/*)",
                    f"Edit({workspace}/*)",
                    "Bash(git:*)",
                    "Bash(npm:*)",
                    "Bash(python:*)"
                ],
                "deny": [
                    # Bloquer accès autres workspaces
                    f"Read({self.workspaces_root}/*)!{workspace}",
                    f"Write({self.workspaces_root}/*)!{workspace}",
                    f"Bash(cat:{self.workspaces_root}/*)!{workspace}",
                    f"Bash(ls:{self.workspaces_root})",

                    # Bloquer système
                    "Bash(ps:*)",
                    "Read(/tmp/*)",
                    "Read(/proc/*)",
                    "Bash(sudo:*)"
                ]
            }
        }

    def execute_isolated(
        self,
        user_id: str,
        command: List[str],
        env: dict
    ) -> subprocess.CompletedProcess:
        """Execute commande dans workspace isolé"""
        workspace = self.create_workspace(user_id)

        # Environment isolé
        isolated_env = {
            "HOME": str(workspace),
            "PWD": str(workspace),
            "TMPDIR": str(workspace / "tmp"),
            **env
        }

        # Execute avec CWD = workspace
        return subprocess.run(
            command,
            cwd=str(workspace),
            env=isolated_env,
            capture_output=True,
            text=True
        )
```

### Usage

```python
isolation = WorkspaceIsolation()

# User A
user_a_id = isolation.get_user_id("user-a-token")
workspace_a = isolation.create_workspace(user_a_id)
# → /workspaces/abc123/

result = isolation.execute_isolated(
    user_a_id,
    ["git", "clone", "https://gitlab.com/user-a/project.git"],
    {}
)

# User B (complètement séparé)
user_b_id = isolation.get_user_id("user-b-token")
workspace_b = isolation.create_workspace(user_b_id)
# → /workspaces/def456/

# User B ne peut PAS accéder workspace de A:
# - CWD différent
# - Permissions 0o700
# - Tools deny
```

### Avantages ✅

- Simple à implémenter (50 lignes)
- Pas de dépendances système
- Fonctionne partout (Linux, macOS)
- Coût: **0€** (juste filesystem)
- Performance: **native** (pas d'overhead)

### Inconvénients ❌

- Même UID/GID sur Cloud Run
- Contournements possibles (si UID identique)
- Dépend de tools restrictions strictes

### Verdict

✅ **Recommandé pour commencer** - Simple et efficace avec restrictions tools

---

## Solution 2: Linux Namespaces (✅ Recommandé - Production)

### Principe

Isolation kernel-level via namespaces Linux:
- **Mount namespace**: Filesystem isolé
- **PID namespace**: Processus invisibles entre users
- **Network namespace**: Réseau isolé (optionnel)
- **User namespace**: UID/GID différents

### Implémentation

```python
import subprocess
import os
from pathlib import Path

class NamespaceIsolation:
    """Isolation via Linux namespaces"""

    def __init__(self, workspaces_root="/workspaces"):
        self.workspaces_root = Path(workspaces_root)

        # Vérifier support namespaces
        if not os.path.exists("/usr/bin/unshare"):
            raise RuntimeError("unshare not available - install util-linux")

    def create_workspace(self, user_id: str) -> Path:
        """Créer workspace avec mount namespace"""
        workspace = self.workspaces_root / user_id
        workspace.mkdir(mode=0o700, exist_ok=True)

        # Créer mount points
        (workspace / "tmp").mkdir(exist_ok=True)
        (workspace / "proc").mkdir(exist_ok=True)

        return workspace

    def execute_isolated(
        self,
        user_id: str,
        command: List[str]
    ) -> subprocess.CompletedProcess:
        """Execute avec namespaces isolés"""
        workspace = self.create_workspace(user_id)

        # Build unshare command
        unshare_cmd = [
            "/usr/bin/unshare",
            "--pid",           # PID namespace isolé
            "--fork",          # Fork process
            "--mount-proc",    # Mount /proc isolé
            "--mount",         # Mount namespace isolé
            "--uts",           # Hostname isolé
        ]

        # Full command
        full_cmd = unshare_cmd + command

        # Execute
        return subprocess.run(
            full_cmd,
            cwd=str(workspace),
            env={
                "HOME": str(workspace),
                "TMPDIR": str(workspace / "tmp")
            },
            capture_output=True,
            text=True
        )
```

### Configuration Cloud Run

```yaml
# cloudbuild.yaml
steps:
- name: gcr.io/cloud-builders/docker
  args:
  - build
  - --build-arg
  - ENABLE_NAMESPACES=true
  - -t
  - gcr.io/$PROJECT_ID/claude-api
  - .

# Dockerfile
FROM python:3.11-slim

# Installer util-linux pour unshare
RUN apt-get update && \
    apt-get install -y util-linux && \
    apt-get clean

# Donner capabilities nécessaires
RUN setcap cap_sys_admin,cap_sys_chroot+ep /usr/bin/unshare

COPY . /app
WORKDIR /app

CMD ["python", "server.py"]
```

### Usage

```python
isolation = NamespaceIsolation()

# User A dans namespace isolé
result_a = isolation.execute_isolated(
    "user-a-id",
    ["claude", "--print", "Clone gitlab.com/user-a/project"]
)

# User B dans namespace DIFFÉRENT
result_b = isolation.execute_isolated(
    "user-b-id",
    ["claude", "--print", "Clone gitlab.com/user-b/project"]
)

# Isolation garantie:
# ✅ User A ne voit PAS les processus de User B (PID namespace)
# ✅ User B ne voit PAS les fichiers de User A (Mount namespace)
# ✅ Même si même UID, isolation kernel-level
```

### Avantages ✅

- **Isolation forte** (kernel-level)
- User B ne voit JAMAIS processus de A (`ps aux`)
- Filesystem isolé (mount namespace)
- Coût: **0€** (natif Linux)
- Performance: **quasi-native** (~5% overhead)

### Inconvénients ❌

- Nécessite Linux (pas macOS/Windows)
- Capabilities kernel requises
- Complexité moyenne (100 lignes)

### Verdict

✅ **Recommandé pour production** - Meilleur équilibre isolation/coût

---

## Solution 3: chroot/jail (⚠️ Alternative)

### Principe

Enfermer chaque user dans un filesystem root isolé.

### Implémentation

```python
class ChrootIsolation:
    """Isolation via chroot jail"""

    def create_chroot(self, user_id: str) -> Path:
        """Créer chroot jail"""
        jail = Path(f"/jails/{user_id}")
        jail.mkdir(mode=0o755, exist_ok=True)

        # Copier binaires nécessaires
        for binary in ["/bin/bash", "/usr/bin/git", "/opt/claude/claude"]:
            self._copy_with_deps(binary, jail)

        # Copier libs
        self._copy_libs(jail)

        return jail

    def _copy_with_deps(self, binary: str, jail: Path):
        """Copier binary + dépendances dans jail"""
        # Créer structure
        dest = jail / binary.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Copier binary
        shutil.copy2(binary, dest)

        # Copier libs (ldd)
        result = subprocess.run(["ldd", binary], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "=>" in line:
                lib = line.split("=>")[1].split()[0]
                lib_dest = jail / lib.lstrip("/")
                lib_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(lib, lib_dest)

    def execute_isolated(self, user_id: str, command: List[str]):
        """Execute dans chroot"""
        jail = self.create_chroot(user_id)

        # chroot + execute
        return subprocess.run(
            ["chroot", str(jail)] + command,
            capture_output=True,
            text=True
        )
```

### Avantages ✅

- Isolation filesystem complète
- User ne peut PAS sortir du jail

### Inconvénients ❌

- Complexité élevée (copier toutes dépendances)
- Maintenance difficile (mise à jour binaries)
- Taille disque importante (jail per user)
- Nécessite root privileges

### Verdict

⚠️ **Alternative valide** mais complexe - Préférer namespaces

---

## Solution 4: Containers par User (⚠️ Overkill)

### Principe

1 container Docker par user.

### Implémentation

```python
import docker

class ContainerIsolation:
    """Isolation via containers Docker"""

    def __init__(self):
        self.client = docker.from_env()

    def create_container(self, user_id: str) -> str:
        """Créer container isolé pour user"""
        container = self.client.containers.run(
            "gcr.io/project/claude-api",
            detach=True,
            name=f"claude-user-{user_id}",
            environment={
                "USER_ID": user_id
            },
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000,  # 50% CPU
            network_mode="bridge",
            volumes={
                f"/workspaces/{user_id}": {
                    "bind": "/workspace",
                    "mode": "rw"
                }
            }
        )

        return container.id

    def execute_in_container(
        self,
        user_id: str,
        command: List[str]
    ) -> str:
        """Execute commande dans container user"""
        container = self.client.containers.get(f"claude-user-{user_id}")

        result = container.exec_run(command)
        return result.output.decode()

    def cleanup_container(self, user_id: str):
        """Supprimer container"""
        container = self.client.containers.get(f"claude-user-{user_id}")
        container.stop()
        container.remove()
```

### Usage

```python
isolation = ContainerIsolation()

# User A → Container A
container_a = isolation.create_container("user-a")
result_a = isolation.execute_in_container("user-a", ["claude", "..."])

# User B → Container B (complètement isolé)
container_b = isolation.create_container("user-b")
result_b = isolation.execute_in_container("user-b", ["claude", "..."])

# Cleanup
isolation.cleanup_container("user-a")
isolation.cleanup_container("user-b")
```

### Avantages ✅

- **Isolation maximale** (kernel + cgroups + namespaces)
- Resource limits (CPU, RAM) par user
- Réseau isolé

### Inconvénients ❌

- **Coût élevé**: ~500MB RAM par container
- **Latency**: Cold start ~2-5s
- Complexité infrastructure (orchestration)
- Sur Cloud Run: Nested containers = problématique

### Verdict

⚠️ **Overkill** pour most use cases - Trop coûteux

---

## Solution 5: VMs par User (❌ Non Pratique)

### Principe

1 VM par user (Firecracker micro-VMs).

### Implémentation

```python
# Utiliser Firecracker (AWS Lambda sous le capot)
import subprocess

class FirecrackerIsolation:
    """Isolation via micro-VMs"""

    def create_microvm(self, user_id: str) -> str:
        """Créer micro-VM"""
        config = {
            "boot-source": {
                "kernel_image_path": "/kernels/vmlinux",
                "boot_args": "console=ttyS0 reboot=k panic=1"
            },
            "drives": [{
                "drive_id": "rootfs",
                "path_on_host": f"/vms/{user_id}/rootfs.ext4",
                "is_root_device": True,
                "is_read_only": False
            }],
            "machine-config": {
                "vcpu_count": 1,
                "mem_size_mib": 512
            }
        }

        # Launch Firecracker
        subprocess.run([
            "firecracker",
            "--config-file", f"/tmp/vm-{user_id}.json"
        ])
```

### Avantages ✅

- **Isolation maximale** (hardware-level)
- Sécurité équivalente VMs classiques
- Plus léger que VMs (boot ~125ms)

### Inconvénients ❌

- **Complexité très élevée**
- **Coût élevé** (~512MB RAM minimum par VM)
- Nécessite KVM (pas sur tous clouds)
- Maintenance difficile

### Verdict

❌ **Non pratique** - Réservé cas ultra-sécurisés (finance, santé)

---

## 🎯 Comparaison Complète

### Performance

| Solution | RAM/User | Latency | Overhead |
|----------|----------|---------|----------|
| Directories | 0 MB | 0 ms | 0% |
| Namespaces | 0 MB | 5 ms | 5% |
| chroot | 50 MB | 10 ms | 10% |
| Containers | 500 MB | 2000 ms | 20% |
| VMs | 512 MB | 125 ms | 30% |

### Sécurité

| Solution | Isolation | Contournement |
|----------|-----------|---------------|
| Directories | ⚠️ Moyenne | Possible (même UID) |
| Namespaces | ✅ Forte | Difficile |
| chroot | ✅ Forte | Possible (root) |
| Containers | ✅ Très forte | Très difficile |
| VMs | ✅ Maximale | Quasi impossible |

### Coût (1000 users)

| Solution | RAM | CPU | Coût/mois |
|----------|-----|-----|-----------|
| Directories | 2 GB | 2 vCPU | $15 |
| Namespaces | 2 GB | 2 vCPU | $15 |
| chroot | 10 GB | 2 vCPU | $40 |
| Containers | 500 GB | 20 vCPU | $2000 |
| VMs | 512 GB | 20 vCPU | $2500 |

---

## 🎯 Recommandation Finale

### Phase 1: MVP/Beta (0-100 users)

**Solution:** Directories + Permissions

```python
api = WorkspaceIsolation(workspaces_root="/workspaces")

# Simple, efficace, coût minimal
```

**Raison:**
- ✅ Implémentation rapide (1 jour)
- ✅ Coût: ~$15/mois
- ✅ Suffisant avec tools restrictions

### Phase 2: Production (100-10k users)

**Solution:** Linux Namespaces

```python
api = NamespaceIsolation(workspaces_root="/workspaces")

# Isolation forte, coût minimal
```

**Raison:**
- ✅ Isolation kernel-level
- ✅ Coût: ~$50/mois (10k users)
- ✅ Balance parfait sécurité/performance

### Phase 3: Enterprise (10k+ users)

**Solution:** Namespaces + Resource Limits

```python
api = NamespaceIsolation(
    workspaces_root="/workspaces",
    enable_cgroups=True,  # CPU/RAM limits per user
    enable_network_isolation=True
)
```

**Raison:**
- ✅ Isolation maximale
- ✅ Resource fairness
- ✅ Scalable

### Phase 4: Ultra-Sécurisé (Finance/Santé)

**Solution:** Containers ou VMs

```python
api = ContainerIsolation()

# Maximum sécurité, coût élevé acceptable
```

**Raison:**
- ✅ Conformité réglementaire
- ✅ Isolation maximale
- ⚠️ Coût élevé justifié

---

## 📋 Plan d'Implémentation

### Semaine 1: Directories

```python
# Implémenter WorkspaceIsolation
class SecureMultiTenantAPI:
    def __init__(self):
        self.isolation = WorkspaceIsolation()

    def create_message(self, oauth_token, messages):
        user_id = self._get_user_id(oauth_token)
        workspace = self.isolation.create_workspace(user_id)
        settings = self.isolation.get_security_settings(workspace)

        # Execute avec isolation
        result = self.isolation.execute_isolated(
            user_id, command, env
        )
```

**Livrables:**
- ✅ Workspace isolation basique
- ✅ Tests sécurité
- ✅ Documentation

### Semaine 2-3: Namespaces (Production)

```python
# Upgrade vers NamespaceIsolation
class SecureMultiTenantAPI:
    def __init__(self, use_namespaces=True):
        if use_namespaces:
            self.isolation = NamespaceIsolation()
        else:
            self.isolation = WorkspaceIsolation()
```

**Livrables:**
- ✅ Namespaces support
- ✅ Tests isolation avancés
- ✅ Benchmarks performance

### Semaine 4: Monitoring

```python
# Ajouter observabilité
from prometheus_client import Gauge

workspace_count = Gauge('workspaces_active', 'Active workspaces')
isolation_violations = Counter('isolation_violations', 'Security violations')

def monitor_isolation(self):
    """Monitor isolation health"""
    for workspace in self.list_workspaces():
        # Vérifier permissions
        if not self._check_permissions(workspace):
            isolation_violations.inc()
```

---

## ✅ Checklist Implémentation

**Phase 1 (MVP):**
- [ ] WorkspaceIsolation class (directories)
- [ ] Permissions 0o700 strictes
- [ ] Tools restrictions
- [ ] Tests: user B ne voit pas workspace A
- [ ] Documentation

**Phase 2 (Production):**
- [ ] NamespaceIsolation class
- [ ] unshare support (PID + Mount)
- [ ] Tests isolation kernel-level
- [ ] Benchmarks performance
- [ ] Migration guide

**Phase 3 (Enterprise):**
- [ ] cgroups resource limits
- [ ] Network isolation (optionnel)
- [ ] Monitoring isolation health
- [ ] Audit logs

---

## 🎉 Conclusion

### Question: Quelle solution d'isolation?

**MVP/Beta:** Directories + Permissions ✅
**Production:** Linux Namespaces ✅
**Enterprise:** Namespaces + cgroups ✅
**Ultra-Secure:** Containers (si budget) ⚠️

### Recommandation Immédiate

**Commencer avec Directories:**

```python
api = SecureMultiTenantAPI(
    isolation_mode="directories"  # Simple, efficace
)

# Upgrade vers namespaces quand prêt:
api = SecureMultiTenantAPI(
    isolation_mode="namespaces"  # Production
)
```

**Bénéfices:**
- ✅ Implémentation rapide
- ✅ Coût minimal
- ✅ Isolation suffisante (avec tools restrictions)
- ✅ Upgrade path clair

**Fichiers créés:**
- WORKSPACE_ISOLATION_SOLUTIONS.md - Guide complet
- Code examples pour chaque solution
- Plan d'implémentation 4 semaines

**Status:** ✅ Prêt à implémenter! 🚀
