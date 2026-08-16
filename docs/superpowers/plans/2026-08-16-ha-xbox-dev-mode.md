# ha-xbox-dev-mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integração do Home Assistant que controla e monitora um Xbox (Series S) em Modo Desenvolvedor via Windows Device Portal REST, com um cliente reutilizável publicado no PyPI.

**Architecture:** Dois repos. `xbox-devportal` (`~/Github/xbox-devportal`) é uma lib async pura em `aiohttp`, sem dependência de Home Assistant, que encapsula auth Basic + CSRF + TLS autoassinado e todos os endpoints do WDP. `ha-xbox-dev-mode` (`~/Github/ha-xbox-dev-mode`) é o custom component HACS: um DataUpdateCoordinator tri-estado que consome a lib e projeta entidades. Mesmo layout dos repos `ha-*` do usuário (ex.: `ha-xbox360-aurora`: `custom_components/<domain>/`, `tests/test_<platform>.py`, `uv`, `pyproject.toml` deps-only).

**Tech Stack:** Python ≥3.12, aiohttp, Home Assistant, DataUpdateCoordinator, icmplib (ping), pytest + pytest-asyncio + pytest-homeassistant-custom-component + aioresponses, uv, ruff.

**Spec:** `~/Github/ha-xbox-dev-mode/docs/specs/2026-08-16-ha-xbox-dev-mode-design.md`

## Global Constraints

- Python `requires-python = ">=3.12"`.
- Lib `xbox-devportal`: **zero** dependência de Home Assistant. Só `aiohttp`.
- Integração depende da lib via `requirements: ["xbox-devportal>=0.1.0"]` no manifest; pin exato por release.
- Auth: Basic Auth + `ssl=False` (cert autoassinado). Todo verbo não-GET envia CSRF: cookie `CSRF-Token` (obtido num GET) reenviado como cookie **e** header `X-CSRF-Token`. POST sem corpo manda `Content-Length: 0`.
- `domain = "xbox_dev_mode"`, `iot_class = "local_polling"`, `integration_type = "device"`, `config_flow = true`, `codeowners = ["@hudsonbrendon"]`.
- `restart()`/`shutdown()` NUNCA são chamados fora de uma ação explícita do usuário (jamais na validação de config flow ou em teste que bata no console real).
- Segredos (senha, credenciais SMB) sempre redigidos em diagnostics e logs.
- Testes nunca tocam o console real: tudo via `aioresponses` (lib) ou mock de `XboxDevPortal` (integração).
- Base URL do WDP: `https://<host>:<port>` com `port=11443` default.

---

## PARTE A — Lib `xbox-devportal` (repo `~/Github/xbox-devportal`)

### Task A1: Scaffold do pacote + modelos de dados

**Files:**
- Create: `~/Github/xbox-devportal/pyproject.toml`
- Create: `~/Github/xbox-devportal/src/xbox_devportal/__init__.py`
- Create: `~/Github/xbox-devportal/src/xbox_devportal/models.py`
- Create: `~/Github/xbox-devportal/src/xbox_devportal/exceptions.py`
- Test: `~/Github/xbox-devportal/tests/test_models.py`

**Interfaces:**
- Consumes: nada (primeira task).
- Produces:
  - `exceptions.py`: `DevPortalError(Exception)`, `AuthError(DevPortalError)`, `DevPortalUnreachable(DevPortalError)`.
  - `models.py` (dataclasses frozen):
    - `DeviceInfo(computer_name: str, os_version: str, platform: str)`
    - `SystemPerf(cpu_load: int, total_pages: int, available_pages: int, committed_pages: int, page_size: int, gpu_dedicated: int, gpu_dedicated_used: int)` com props `memory_used_mb`, `memory_available_mb`, `gpu_memory_used_mb` (int, páginas×page_size/1MiB).
    - `Process(image_name: str, package_full_name: str | None, private_working_set: int)` com prop `memory_mb`.
    - `Package(name: str, package_full_name: str, package_relative_id: str, can_uninstall: bool)` com prop `is_sideloaded` (== can_uninstall).
    - `Setting(name: str, value: str, options: tuple[str, ...])`
    - `SmbShare(path: str, username: str, password: str)`
  - `__init__.py` reexporta `XboxDevPortal` (adicionado na A2) + todos os modelos e exceções.

- [ ] **Step 1: Escrever pyproject.toml**

```toml
[project]
name = "xbox-devportal"
version = "0.1.0"
description = "Async client for the Xbox (Series/One) Windows Device Portal in Developer Mode"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "Hudson Brendon" }]
dependencies = ["aiohttp>=3.9"]

[dependency-groups]
dev = ["pytest", "pytest-asyncio", "aioresponses", "ruff"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/xbox_devportal"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Escrever o teste dos modelos**

```python
# tests/test_models.py
from xbox_devportal import DeviceInfo, SystemPerf, Package, Process


def test_systemperf_converts_pages_to_mb():
    p = SystemPerf(cpu_load=1, total_pages=327680, available_pages=45557,
                   committed_pages=1624279, page_size=4096,
                   gpu_dedicated=134217728, gpu_dedicated_used=123781120)
    assert p.memory_used_mb == (327680 - 45557) * 4096 // (1024 * 1024)
    assert p.gpu_memory_used_mb == 123781120 // (1024 * 1024)


def test_package_sideloaded_flag():
    sys_pkg = Package("Guide", "Xbox.Guide_x", "Xbox.Guide_x!App", can_uninstall=False)
    ra = Package("RetroArch", "1e4c_1.19.0.0_x", "1e4c_x!App", can_uninstall=True)
    assert sys_pkg.is_sideloaded is False
    assert ra.is_sideloaded is True


def test_process_memory_mb():
    assert Process("RetroArch-msvcUWP.exe", "1e4c_x", 19922944).memory_mb == 19
```

- [ ] **Step 3: Escrever exceptions.py e models.py**

```python
# exceptions.py
class DevPortalError(Exception):
    """Base error for the Device Portal client."""


class AuthError(DevPortalError):
    """401 — credenciais inválidas."""


class DevPortalUnreachable(DevPortalError):
    """Timeout ou falha de conexão."""
```

```python
# models.py
from dataclasses import dataclass

_MB = 1024 * 1024


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    computer_name: str
    os_version: str
    platform: str


@dataclass(frozen=True, slots=True)
class SystemPerf:
    cpu_load: int
    total_pages: int
    available_pages: int
    committed_pages: int
    page_size: int
    gpu_dedicated: int
    gpu_dedicated_used: int

    @property
    def memory_used_mb(self) -> int:
        return (self.total_pages - self.available_pages) * self.page_size // _MB

    @property
    def memory_available_mb(self) -> int:
        return self.available_pages * self.page_size // _MB

    @property
    def gpu_memory_used_mb(self) -> int:
        return self.gpu_dedicated_used // _MB


@dataclass(frozen=True, slots=True)
class Process:
    image_name: str
    package_full_name: str | None
    private_working_set: int

    @property
    def memory_mb(self) -> int:
        return self.private_working_set // _MB


@dataclass(frozen=True, slots=True)
class Package:
    name: str
    package_full_name: str
    package_relative_id: str
    can_uninstall: bool

    @property
    def is_sideloaded(self) -> bool:
        return self.can_uninstall


@dataclass(frozen=True, slots=True)
class Setting:
    name: str
    value: str
    options: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SmbShare:
    path: str
    username: str
    password: str
```

E `__init__.py` reexportando (o `XboxDevPortal` entra na A2):

```python
# __init__.py
from .exceptions import AuthError, DevPortalError, DevPortalUnreachable
from .models import DeviceInfo, Package, Process, Setting, SmbShare, SystemPerf

__all__ = [
    "AuthError", "DevPortalError", "DevPortalUnreachable",
    "DeviceInfo", "Package", "Process", "Setting", "SmbShare", "SystemPerf",
]
```

- [ ] **Step 4: Rodar os testes**

Run: `cd ~/Github/xbox-devportal && uv run pytest -v`
Expected: 3 passam.

- [ ] **Step 5: Commit**

```bash
cd ~/Github/xbox-devportal && git init -q && git add -A
git commit -m "feat: scaffold do pacote e modelos de dados"
```

---

### Task A2: Cliente base — auth Basic, CSRF, TLS autoassinado

**Files:**
- Create: `~/Github/xbox-devportal/src/xbox_devportal/client.py`
- Modify: `~/Github/xbox-devportal/src/xbox_devportal/__init__.py` (reexporta `XboxDevPortal`)
- Test: `~/Github/xbox-devportal/tests/test_client_auth.py`

**Interfaces:**
- Consumes: `AuthError`, `DevPortalUnreachable` da A1.
- Produces:
  - `XboxDevPortal(host: str, username: str, password: str, port: int = 11443, session: aiohttp.ClientSession | None = None)`
  - método interno `_request(method: str, path: str, **kw) -> aiohttp.ClientResponse` que injeta Basic Auth, `ssl=False`, e para não-GET resolve CSRF (GET em `/api/os/machinename` → cookie `CSRF-Token` → reenvia como cookie + header `X-CSRF-Token`); em 403 renova o token uma vez e repete; 401 → `AuthError`; `aiohttp.ClientError`/timeout → `DevPortalUnreachable`.
  - `base_url` property → `https://{host}:{port}`.
  - `async def close()` fecha a sessão se criada internamente.

- [ ] **Step 1: Escrever o teste de auth/CSRF**

```python
# tests/test_client_auth.py
import pytest
from aioresponses import aioresponses
from xbox_devportal import XboxDevPortal, AuthError, DevPortalUnreachable

BASE = "https://10.0.0.5:11443"


async def test_get_sends_request():
    with aioresponses() as m:
        m.get(f"{BASE}/api/os/machinename", status=200, payload={"ComputerName": "XBOX"})
        c = XboxDevPortal("10.0.0.5", "u", "p")
        r = await c._request("GET", "/api/os/machinename")
        assert r.status == 200
        await c.close()


async def test_non_get_fetches_and_sends_csrf():
    with aioresponses() as m:
        m.get(f"{BASE}/api/os/machinename", status=200, payload={"ComputerName": "XBOX"},
              headers={"Set-Cookie": "CSRF-Token=tok123; Path=/"})
        m.post(f"{BASE}/api/taskmanager/app", status=200)
        c = XboxDevPortal("10.0.0.5", "u", "p")
        r = await c._request("POST", "/api/taskmanager/app", headers={"Content-Length": "0"})
        assert r.status == 200
        # o header CSRF foi enviado no POST
        post_calls = [call for key, calls in m.requests.items()
                      if key[0] == "POST" for call in calls]
        assert post_calls[0].kwargs["headers"]["X-CSRF-Token"] == "tok123"
        await c.close()


async def test_401_raises_autherror():
    with aioresponses() as m:
        m.get(f"{BASE}/api/os/machinename", status=401)
        c = XboxDevPortal("10.0.0.5", "u", "bad")
        with pytest.raises(AuthError):
            await c._request("GET", "/api/os/machinename")
        await c.close()


async def test_connection_failure_raises_unreachable():
    import aiohttp
    with aioresponses() as m:
        m.get(f"{BASE}/api/os/machinename", exception=aiohttp.ClientConnectionError())
        c = XboxDevPortal("10.0.0.5", "u", "p")
        with pytest.raises(DevPortalUnreachable):
            await c._request("GET", "/api/os/machinename")
        await c.close()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd ~/Github/xbox-devportal && uv run pytest tests/test_client_auth.py -v`
Expected: FAIL — `ImportError: cannot import name 'XboxDevPortal'`.

- [ ] **Step 3: Implementar client.py**

```python
# client.py
import aiohttp
from .exceptions import AuthError, DevPortalUnreachable

_CSRF_PATH = "/api/os/machinename"


class XboxDevPortal:
    def __init__(self, host, username, password, port=11443, session=None):
        self._host, self._port = host, port
        self._auth = aiohttp.BasicAuth(username, password)
        self._ext_session = session
        self._session = session
        self._csrf: str | None = None

    @property
    def base_url(self) -> str:
        return f"https://{self._host}:{self._port}"

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _fetch_csrf(self) -> str | None:
        s = await self._ensure_session()
        async with s.get(f"{self.base_url}{_CSRF_PATH}", auth=self._auth, ssl=False) as r:
            if r.status == 401:
                raise AuthError("credenciais inválidas")
            tok = r.cookies.get("CSRF-Token")
            self._csrf = tok.value if tok else None
        return self._csrf

    async def _request(self, method, path, *, _retry=True, **kw):
        s = await self._ensure_session()
        headers = dict(kw.pop("headers", {}) or {})
        cookies = dict(kw.pop("cookies", {}) or {})
        if method.upper() != "GET":
            if self._csrf is None:
                await self._fetch_csrf()
            if self._csrf:
                headers["X-CSRF-Token"] = self._csrf
                cookies["CSRF-Token"] = self._csrf
        try:
            r = await s.request(method, f"{self.base_url}{path}", auth=self._auth,
                                 ssl=False, headers=headers, cookies=cookies, **kw)
        except (aiohttp.ClientError, TimeoutError) as e:
            raise DevPortalUnreachable(str(e)) from e
        if r.status == 401:
            raise AuthError("credenciais inválidas")
        if r.status == 403 and method.upper() != "GET" and _retry:
            self._csrf = None
            return await self._request(method, path, _retry=False,
                                       headers=headers, cookies=cookies, **kw)
        return r

    async def close(self):
        if self._ext_session is None and self._session is not None:
            await self._session.close()
            self._session = None
```

Reexportar em `__init__.py`: `from .client import XboxDevPortal` e incluir no `__all__`.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd ~/Github/xbox-devportal && uv run pytest tests/test_client_auth.py -v`
Expected: 4 passam. (Se a extração do header do POST divergir na versão instalada do aioresponses, ajustar a asserção — o comportamento sob teste é: header `X-CSRF-Token` presente com o valor do cookie.)

- [ ] **Step 5: Commit**

```bash
cd ~/Github/xbox-devportal && git add -A
git commit -m "feat: cliente base com Basic Auth, CSRF e TLS autoassinado"
```

---

### Task A3: Leitura — info, system_perf, processes, foreground_app

**Files:**
- Modify: `~/Github/xbox-devportal/src/xbox_devportal/client.py`
- Test: `~/Github/xbox-devportal/tests/test_client_read.py`

**Interfaces:**
- Consumes: `_request` da A2; modelos da A1.
- Produces em `XboxDevPortal`:
  - `async def info() -> DeviceInfo`
  - `async def system_perf() -> SystemPerf`
  - `async def processes() -> list[Process]`
  - `async def foreground_app() -> Process | None` (maior `private_working_set` entre processos com `package_full_name` cujo prefixo antes de `_` não está na allowlist de shell: `Xbox.Dashboard`, `Xbox.Guide`, `Microsoft.Xbox.DevHome`, `XdashLauncher`)
  - helper interno `async def _json(path) -> dict`

- [ ] **Step 1: Escrever o teste**

```python
# tests/test_client_read.py
from aioresponses import aioresponses
from xbox_devportal import XboxDevPortal

BASE = "https://10.0.0.5:11443"

INFO = {"ComputerName": "XBOX", "OsVersion": "26100.9426", "Platform": "Xbox Series S"}
PERF = {"CpuLoad": 3, "TotalPages": 327680, "AvailablePages": 45557,
        "CommittedPages": 1624279, "PageSize": 4096,
        "GPUData": {"AvailableAdapters": [{"DedicatedMemory": 134217728,
                    "DedicatedMemoryUsed": 123781120}]}}
PROCS = {"Processes": [
    {"ImageName": "Xbox.Dashboard.exe", "PackageFullName": "Xbox.Dashboard_x", "PrivateWorkingSet": 90000000},
    {"ImageName": "RetroArch-msvcUWP.exe", "PackageFullName": "1e4c_1.19.0.0_x", "PrivateWorkingSet": 220000000},
    {"ImageName": "svchost.exe", "PrivateWorkingSet": 5000000}]}


async def test_info():
    with aioresponses() as m:
        m.get(f"{BASE}/api/os/info", payload=INFO)
        c = XboxDevPortal("10.0.0.5", "u", "p")
        info = await c.info()
        assert info.platform == "Xbox Series S"
        assert info.os_version == "26100.9426"
        await c.close()


async def test_system_perf_reads_gpu_from_first_adapter():
    with aioresponses() as m:
        m.get(f"{BASE}/api/resourcemanager/systemperf", payload=PERF)
        c = XboxDevPortal("10.0.0.5", "u", "p")
        p = await c.system_perf()
        assert p.cpu_load == 3
        assert p.gpu_dedicated_used == 123781120
        await c.close()


async def test_foreground_app_picks_largest_non_shell_uwp():
    with aioresponses() as m:
        m.get(f"{BASE}/api/resourcemanager/processes", payload=PROCS)
        c = XboxDevPortal("10.0.0.5", "u", "p")
        fg = await c.foreground_app()
        assert fg.image_name == "RetroArch-msvcUWP.exe"
        await c.close()


async def test_foreground_app_none_when_only_shell():
    with aioresponses() as m:
        m.get(f"{BASE}/api/resourcemanager/processes",
              payload={"Processes": [{"ImageName": "Xbox.Dashboard.exe",
                       "PackageFullName": "Xbox.Dashboard_x", "PrivateWorkingSet": 9}]})
        c = XboxDevPortal("10.0.0.5", "u", "p")
        assert await c.foreground_app() is None
        await c.close()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd ~/Github/xbox-devportal && uv run pytest tests/test_client_read.py -v`
Expected: FAIL — métodos inexistentes.

- [ ] **Step 3: Implementar os métodos de leitura**

```python
# em client.py, imports no topo:
from .models import DeviceInfo, Process, SystemPerf

_SHELL = {"Xbox.Dashboard", "Xbox.Guide", "Microsoft.Xbox.DevHome", "XdashLauncher"}

# métodos dentro de XboxDevPortal:
async def _json(self, path):
    r = await self._request("GET", path)
    return await r.json(content_type=None)

async def info(self) -> DeviceInfo:
    d = await self._json("/api/os/info")
    return DeviceInfo(d.get("ComputerName", ""), d.get("OsVersion", ""), d.get("Platform", ""))

async def system_perf(self) -> SystemPerf:
    d = await self._json("/api/resourcemanager/systemperf")
    adapters = d.get("GPUData", {}).get("AvailableAdapters", [{}])
    gpu = adapters[0] if adapters else {}
    return SystemPerf(
        cpu_load=d.get("CpuLoad", 0), total_pages=d.get("TotalPages", 0),
        available_pages=d.get("AvailablePages", 0), committed_pages=d.get("CommittedPages", 0),
        page_size=d.get("PageSize", 4096), gpu_dedicated=gpu.get("DedicatedMemory", 0),
        gpu_dedicated_used=gpu.get("DedicatedMemoryUsed", 0))

async def processes(self) -> list[Process]:
    d = await self._json("/api/resourcemanager/processes")
    return [Process(p.get("ImageName", ""), p.get("PackageFullName"),
                    p.get("PrivateWorkingSet", 0)) for p in d.get("Processes", [])]

async def foreground_app(self) -> Process | None:
    procs = [p for p in await self.processes()
             if p.package_full_name and p.package_full_name.split("_")[0] not in _SHELL]
    return max(procs, key=lambda p: p.private_working_set, default=None)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd ~/Github/xbox-devportal && uv run pytest tests/test_client_read.py -v`
Expected: 4 passam.

- [ ] **Step 5: Commit**

```bash
cd ~/Github/xbox-devportal && git add -A
git commit -m "feat: leitura de info, systemperf, processes e foreground_app"
```

---

### Task A4: Pacotes — listar, lançar, encerrar

**Files:**
- Modify: `~/Github/xbox-devportal/src/xbox_devportal/client.py`
- Test: `~/Github/xbox-devportal/tests/test_client_packages.py`

**Interfaces:**
- Consumes: `_request`, `_json`, `Package`.
- Produces:
  - `async def packages(sideloaded_only: bool = False) -> list[Package]`
  - `async def launch(package: Package | str) -> None` (aceita `Package` ou `package_full_name`; deriva `appid` do `package_relative_id`; para string, resolve via `packages()`; codifica appid/package em base64 e faz POST com `Content-Length: 0`)
  - `async def terminate(package: Package | str) -> None` (DELETE com package base64)
  - helpers `_b64(s) -> str` e `_resolve(package) -> Package`

- [ ] **Step 1: Escrever o teste**

```python
# tests/test_client_packages.py
import base64
from aioresponses import aioresponses
from xbox_devportal import XboxDevPortal, Package

BASE = "https://10.0.0.5:11443"
PKGS = {"InstalledPackages": [
    {"Name": "Guide", "PackageFullName": "Xbox.Guide_x", "PackageRelativeId": "Xbox.Guide_x!App", "CanUninstall": False},
    {"Name": "RetroArch", "PackageFullName": "1e4c_1.19.0.0_x", "PackageRelativeId": "1e4c_x!App", "CanUninstall": True}]}


async def test_packages_all_and_sideloaded():
    with aioresponses() as m:
        m.get(f"{BASE}/api/app/packagemanager/packages", payload=PKGS, repeat=True)
        c = XboxDevPortal("10.0.0.5", "u", "p")
        assert len(await c.packages()) == 2
        side = await c.packages(sideloaded_only=True)
        assert [p.name for p in side] == ["RetroArch"]
        await c.close()


async def test_launch_encodes_appid_and_package():
    with aioresponses() as m:
        m.get(f"{BASE}/api/os/machinename", payload={}, headers={"Set-Cookie": "CSRF-Token=t; Path=/"})
        m.post(f"{BASE}/api/taskmanager/app", status=200)
        c = XboxDevPortal("10.0.0.5", "u", "p")
        pkg = Package("RetroArch", "1e4c_1.19.0.0_x", "1e4c_x!App", True)
        await c.launch(pkg)
        posted = [k for k in m.requests if k[0] == "POST"][0]
        q = posted[1].query
        assert q["appid"] == base64.b64encode(b"1e4c_x!App").decode()
        assert q["package"] == base64.b64encode(b"1e4c_1.19.0.0_x").decode()
        await c.close()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd ~/Github/xbox-devportal && uv run pytest tests/test_client_packages.py -v`
Expected: FAIL.

- [ ] **Step 3: Implementar**

```python
# em client.py
import base64
from .models import Package

def _b64(self, s: str) -> str:
    return base64.b64encode(s.encode()).decode()

async def packages(self, sideloaded_only: bool = False) -> list[Package]:
    d = await self._json("/api/app/packagemanager/packages")
    pkgs = [Package(p.get("Name", ""), p.get("PackageFullName", ""),
                    p.get("PackageRelativeId", ""), p.get("CanUninstall", False))
            for p in d.get("InstalledPackages", [])]
    return [p for p in pkgs if p.is_sideloaded] if sideloaded_only else pkgs

async def _resolve(self, package) -> Package:
    if isinstance(package, Package):
        return package
    for p in await self.packages():
        if p.package_full_name == package:
            return p
    raise ValueError(f"pacote não encontrado: {package}")

async def launch(self, package) -> None:
    pkg = await self._resolve(package)
    q = f"?appid={self._b64(pkg.package_relative_id)}&package={self._b64(pkg.package_full_name)}"
    r = await self._request("POST", f"/api/taskmanager/app{q}", headers={"Content-Length": "0"})
    r.close()

async def terminate(self, package) -> None:
    pkg = await self._resolve(package)
    r = await self._request("DELETE", f"/api/taskmanager/app?package={self._b64(pkg.package_full_name)}")
    r.close()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd ~/Github/xbox-devportal && uv run pytest tests/test_client_packages.py -v`
Expected: 2 passam.

- [ ] **Step 5: Commit**

```bash
cd ~/Github/xbox-devportal && git add -A
git commit -m "feat: listar, lançar e encerrar pacotes"
```

---

### Task A5: Settings, sandbox, smb, screenshot, restart/shutdown

**Files:**
- Modify: `~/Github/xbox-devportal/src/xbox_devportal/client.py`
- Test: `~/Github/xbox-devportal/tests/test_client_ext.py`

**Interfaces:**
- Consumes: `_request`, `_json`, `Setting`, `SmbShare`.
- Produces:
  - `async def settings() -> dict[str, Setting]` (chave = `Name`; `options` = tupla de `OptionsVariants`/`Options`, vazia se ausente)
  - `async def set_setting(name: str, value: str) -> None` (POST `/ext/settings` com body JSON `{name: value}`; CSRF aplicado)
  - `async def sandbox() -> str`
  - `async def smb_credentials() -> SmbShare`
  - `async def screenshot() -> bytes`
  - `async def restart() -> None` / `async def shutdown() -> None` (POST em `/api/control/restart` e `/api/control/shutdown`)

- [ ] **Step 1: Escrever o teste**

```python
# tests/test_client_ext.py
from aioresponses import aioresponses
from xbox_devportal import XboxDevPortal

BASE = "https://10.0.0.5:11443"
SETTINGS = {"Settings": [
    {"Name": "TVResolution", "Value": "1080p", "OptionsVariants": ["720p", "1080p", "2160p"]},
    {"Name": "AllowHDR", "Value": "true"}]}


async def test_settings_parses_options():
    with aioresponses() as m:
        m.get(f"{BASE}/ext/settings", payload=SETTINGS)
        c = XboxDevPortal("10.0.0.5", "u", "p")
        s = await c.settings()
        assert s["TVResolution"].options == ("720p", "1080p", "2160p")
        assert s["AllowHDR"].options == ()
        assert s["AllowHDR"].value == "true"
        await c.close()


async def test_sandbox():
    with aioresponses() as m:
        m.get(f"{BASE}/ext/xboxlive/sandbox", payload={"Sandbox": "XDKS.1"})
        c = XboxDevPortal("10.0.0.5", "u", "p")
        assert await c.sandbox() == "XDKS.1"
        await c.close()


async def test_smb_credentials():
    with aioresponses() as m:
        m.get(f"{BASE}/ext/smb/developerfolder",
              payload={"Path": "D:\\Dev", "Username": "DevToolsUser", "Password": "x"})
        c = XboxDevPortal("10.0.0.5", "u", "p")
        smb = await c.smb_credentials()
        assert smb.username == "DevToolsUser"
        await c.close()


async def test_screenshot_returns_bytes():
    with aioresponses() as m:
        m.get(f"{BASE}/ext/screenshot", body=b"\x89PNG\r\n")
        c = XboxDevPortal("10.0.0.5", "u", "p")
        data = await c.screenshot()
        assert data.startswith(b"\x89PNG")
        await c.close()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd ~/Github/xbox-devportal && uv run pytest tests/test_client_ext.py -v`
Expected: FAIL.

- [ ] **Step 3: Implementar**

```python
# em client.py
import json as _json_mod
from .models import Setting, SmbShare

async def settings(self) -> dict[str, Setting]:
    d = await self._json("/ext/settings")
    out = {}
    for s in d.get("Settings", []):
        opts = s.get("OptionsVariants") or s.get("Options") or []
        out[s["Name"]] = Setting(s["Name"], str(s.get("Value", "")), tuple(opts))
    return out

async def set_setting(self, name: str, value: str) -> None:
    r = await self._request("POST", "/ext/settings",
                            data=_json_mod.dumps({name: value}),
                            headers={"Content-Type": "application/json"})
    r.close()

async def sandbox(self) -> str:
    return (await self._json("/ext/xboxlive/sandbox")).get("Sandbox", "")

async def smb_credentials(self) -> SmbShare:
    d = await self._json("/ext/smb/developerfolder")
    return SmbShare(d.get("Path", ""), d.get("Username", ""), d.get("Password", ""))

async def screenshot(self) -> bytes:
    r = await self._request("GET", "/ext/screenshot")
    return await r.read()

async def restart(self) -> None:
    r = await self._request("POST", "/api/control/restart", headers={"Content-Length": "0"})
    r.close()

async def shutdown(self) -> None:
    r = await self._request("POST", "/api/control/shutdown", headers={"Content-Length": "0"})
    r.close()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd ~/Github/xbox-devportal && uv run pytest tests/test_client_ext.py -v`
Expected: 4 passam.

- [ ] **Step 5: Commit**

```bash
cd ~/Github/xbox-devportal && git add -A
git commit -m "feat: settings, sandbox, smb, screenshot, restart/shutdown"
```

---

### Task A6: Filesystem + install/uninstall + README, release 0.1.0

**Files:**
- Modify: `~/Github/xbox-devportal/src/xbox_devportal/client.py`
- Create: `~/Github/xbox-devportal/README.md`
- Test: `~/Github/xbox-devportal/tests/test_client_fs.py`

**Interfaces:**
- Consumes: `_request`, `_json`.
- Produces:
  - `async def list_files(package_full_name: str, path: str) -> list[dict]` (GET `/api/filesystem/apps/files`; `path` no formato `//LocalState/<sub>`; retorna `Items`)
  - `async def upload_file(package_full_name: str, path: str, local_path: Path, remote_name: str | None = None) -> None` (POST multipart)
  - `async def delete_file(package_full_name: str, path: str, filename: str) -> None`
  - `async def install(local_path: Path) -> None` (POST multipart em `/api/app/packagemanager/package?package=<nome>` → 202; poll em `/api/app/packagemanager/state` até `Success`/erro, teto 60 ciclos)
  - `async def uninstall(package_full_name: str) -> None`

- [ ] **Step 1: Escrever o teste**

```python
# tests/test_client_fs.py
from aioresponses import aioresponses
from xbox_devportal import XboxDevPortal

BASE = "https://10.0.0.5:11443"


async def test_list_files_returns_items():
    with aioresponses() as m:
        m.get(f"{BASE}/api/filesystem/apps/files", payload={"Items": [{"Name": "retroarch.cfg"}]})
        c = XboxDevPortal("10.0.0.5", "u", "p")
        items = await c.list_files("1e4c_x", "//LocalState")
        assert items[0]["Name"] == "retroarch.cfg"
        await c.close()


async def test_install_polls_state(tmp_path):
    appx = tmp_path / "x.appx"
    appx.write_bytes(b"data")
    with aioresponses() as m:
        m.get(f"{BASE}/api/os/machinename", payload={}, headers={"Set-Cookie": "CSRF-Token=t; Path=/"})
        m.post(f"{BASE}/api/app/packagemanager/package", status=202)
        m.get(f"{BASE}/api/app/packagemanager/state",
              payload={"Success": True, "Reason": "Success"})
        c = XboxDevPortal("10.0.0.5", "u", "p")
        await c.install(appx)  # não levanta
        await c.close()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd ~/Github/xbox-devportal && uv run pytest tests/test_client_fs.py -v`
Expected: FAIL.

- [ ] **Step 3: Implementar (com poll de estado limitado)**

```python
# em client.py
import asyncio
from pathlib import Path
from urllib.parse import quote
from .exceptions import DevPortalError

async def list_files(self, package_full_name: str, path: str) -> list[dict]:
    q = f"?knownfolderid=LocalAppData&packagefullname={package_full_name}&path={quote(path, safe='')}"
    return (await self._json(f"/api/filesystem/apps/files{q}")).get("Items", [])

async def upload_file(self, package_full_name, path, local_path, remote_name=None):
    local_path = Path(local_path)
    name = remote_name or local_path.name
    q = f"?knownfolderid=LocalAppData&packagefullname={package_full_name}&path={quote(path, safe='')}"
    form = aiohttp.FormData()
    form.add_field("file", local_path.read_bytes(), filename=name)
    r = await self._request("POST", f"/api/filesystem/apps/file{q}", data=form)
    r.close()

async def delete_file(self, package_full_name, path, filename):
    q = (f"?knownfolderid=LocalAppData&packagefullname={package_full_name}"
         f"&path={quote(path, safe='')}&filename={quote(filename, safe='')}")
    r = await self._request("DELETE", f"/api/filesystem/apps/file{q}")
    r.close()

async def install(self, local_path: Path):
    local_path = Path(local_path)
    form = aiohttp.FormData()
    form.add_field(local_path.name, local_path.read_bytes(), filename=local_path.name)
    r = await self._request("POST", f"/api/app/packagemanager/package?package={quote(local_path.name)}", data=form)
    r.close()
    for _ in range(60):  # poll até ~60s
        state = await self._json("/api/app/packagemanager/state")
        if state.get("Success") is True:
            return
        if state.get("Success") is False and state.get("Code", 0) != 0:
            raise DevPortalError(state.get("Reason", "instalação falhou"))
        await asyncio.sleep(1)
    raise DevPortalError("timeout aguardando instalação")

async def uninstall(self, package_full_name: str):
    r = await self._request("DELETE", f"/api/app/packagemanager/package?package={quote(package_full_name)}")
    r.close()
```

Nota de teste: em `test_install_polls_state` o primeiro `state` já vem `Success: True`, então o `asyncio.sleep` não é exercido.

- [ ] **Step 4: Rodar todos os testes da lib**

Run: `cd ~/Github/xbox-devportal && uv run pytest -v`
Expected: todos passam.

- [ ] **Step 5: README + commit + tag**

Escrever `README.md` com exemplo mínimo (`c = XboxDevPortal(...)` / `await c.info()` / `await c.close()`), tabela de métodos, nota de segurança (cert autoassinado, senha em Basic Auth só em LAN). Depois:

```bash
cd ~/Github/xbox-devportal && git add -A
git commit -m "feat: filesystem, install/uninstall e README (0.1.0)"
git tag v0.1.0
```

---

## PARTE B — Integração `ha-xbox-dev-mode` (repo `~/Github/ha-xbox-dev-mode`)

> Layout espelha `ha-xbox360-aurora`. Domain `xbox_dev_mode`. Antes de começar, copie o esqueleto de teste (`conftest.py`, `pytest.ini`, dev-deps do `pyproject.toml`) desse repo como referência.

### Task B1: Scaffold + manifest + const

**Files:**
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/__init__.py`
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/manifest.json`
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/const.py`
- Create: `~/Github/ha-xbox-dev-mode/pyproject.toml`
- Create: `~/Github/ha-xbox-dev-mode/pytest.ini`
- Create: `~/Github/ha-xbox-dev-mode/tests/conftest.py`
- Create: `~/Github/ha-xbox-dev-mode/tests/__init__.py`
- Test: `~/Github/ha-xbox-dev-mode/tests/test_const.py`

**Interfaces:**
- Consumes: lib `xbox-devportal` (dev-dep).
- Produces: `const.DOMAIN = "xbox_dev_mode"`, `const.DEFAULT_PORT = 11443`, `const.STATE_DEV/STATE_RETAIL/STATE_OFF`, chaves de options (`CONF_SCAN_INTERVAL`, `CONF_SCREENSHOT_INTERVAL`, `CONF_SETTINGS_INTERVAL`) + defaults (30/60/120), `PLATFORMS`. `manifest.json` com `ssdp`/`dhcp` matchers, `requirements`, `config_flow: true`. `__init__.py` com `async_setup_entry`/`async_unload_entry` stub (completado na B3).

- [ ] **Step 1: Escrever manifest.json**

```json
{
  "domain": "xbox_dev_mode",
  "name": "Xbox Dev Mode",
  "codeowners": ["@hudsonbrendon"],
  "config_flow": true,
  "documentation": "https://github.com/hudsonbrendon/ha-xbox-dev-mode",
  "integration_type": "device",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/hudsonbrendon/ha-xbox-dev-mode/issues",
  "requirements": ["xbox-devportal>=0.1.0"],
  "ssdp": [{ "manufacturer": "Microsoft Corporation", "deviceType": "urn:schemas-upnp-org:device:MediaRenderer:1" }],
  "dhcp": [{ "macaddress": "38563D*" }],
  "version": "0.1.0"
}
```

- [ ] **Step 2: Escrever o teste de const**

```python
# tests/test_const.py
from custom_components.xbox_dev_mode.const import (
    DOMAIN, DEFAULT_PORT, STATE_DEV, STATE_RETAIL, STATE_OFF, DEFAULT_SCAN_INTERVAL,
)


def test_constants():
    assert DOMAIN == "xbox_dev_mode"
    assert DEFAULT_PORT == 11443
    assert {STATE_DEV, STATE_RETAIL, STATE_OFF} == {"dev_mode", "retail", "off"}
    assert DEFAULT_SCAN_INTERVAL == 30
```

- [ ] **Step 3: Escrever const.py, __init__.py stub, pyproject/pytest/conftest**

`const.py`:

```python
DOMAIN = "xbox_dev_mode"
DEFAULT_PORT = 11443
STATE_DEV = "dev_mode"
STATE_RETAIL = "retail"
STATE_OFF = "off"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SCREENSHOT_INTERVAL = "screenshot_interval"
CONF_SETTINGS_INTERVAL = "settings_interval"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_SCREENSHOT_INTERVAL = 60
DEFAULT_SETTINGS_INTERVAL = 120
PLATFORMS = ["binary_sensor", "sensor", "select", "switch", "button", "image"]
```

`__init__.py` (stub que a B3 completa):

```python
async def async_setup_entry(hass, entry) -> bool:
    return True


async def async_unload_entry(hass, entry) -> bool:
    return True
```

`pyproject.toml` deps-only (copiar dev-deps do aurora + `icmplib` + `xbox-devportal`), `pytest.ini` (`asyncio_mode = auto`, `testpaths = tests`), `conftest.py` (copiar de `ha-xbox360-aurora`, trocar `mock_nova` por `mock_devportal` — um `AsyncMock` com os métodos de `XboxDevPortal`; expandido na B3/B4). `tests/__init__.py` vazio.

- [ ] **Step 4: Rodar o teste**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_const.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/Github/ha-xbox-dev-mode && git init -q && git add -A
git commit -m "feat: scaffold, manifest e const"
```

---

### Task B2: Config flow (ssdp, dhcp, manual, reauth)

**Files:**
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/config_flow.py`
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/strings.json`
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/translations/en.json`
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/translations/pt-BR.json`
- Test: `~/Github/ha-xbox-dev-mode/tests/test_config_flow.py`

**Interfaces:**
- Consumes: `XboxDevPortal.info()` (valida credenciais), `const`.
- Produces: `XboxDevModeConfigFlow` — steps `user`, `ssdp`, `dhcp`, `reauth`. Entry data: `{host, port, username, password}`. `unique_id` = `ssdp_udn` quando via descoberta, senão `f"{host}:{port}"`. Erros: `invalid_auth`, `cannot_connect`. Options flow com os 3 intervalos (`async_step_init`).

- [ ] **Step 1: Escrever os testes**

```python
# tests/test_config_flow.py
from unittest.mock import AsyncMock, patch
from homeassistant import data_entry_flow
from homeassistant.helpers.service_info.ssdp import SsdpServiceInfo
from custom_components.xbox_dev_mode.const import DOMAIN


def _patch_client(ok=True):
    m = AsyncMock()
    if not ok:
        from xbox_devportal import AuthError
        m.info.side_effect = AuthError("bad")
    return patch("custom_components.xbox_dev_mode.config_flow.XboxDevPortal", return_value=m)


async def test_user_flow_success(hass):
    with _patch_client():
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        r2 = await hass.config_entries.flow.async_configure(r["flow_id"], {
            "host": "10.0.0.5", "port": 11443, "username": "u", "password": "p"})
    assert r2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert r2["data"]["host"] == "10.0.0.5"


async def test_user_flow_bad_auth(hass):
    with _patch_client(ok=False):
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        r2 = await hass.config_entries.flow.async_configure(r["flow_id"], {
            "host": "10.0.0.5", "port": 11443, "username": "u", "password": "x"})
    assert r2["type"] == data_entry_flow.FlowResultType.FORM
    assert r2["errors"]["base"] == "invalid_auth"


async def test_ssdp_shows_form(hass):
    info = SsdpServiceInfo(ssdp_usn="usn", ssdp_st="st",
                           ssdp_udn="uuid:08e2300a-1a55", ssdp_location="http://10.0.0.5:2869/x",
                           upnp={})
    r = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "ssdp"}, data=info)
    assert r["type"] == data_entry_flow.FlowResultType.FORM
    assert r["step_id"] == "user"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_config_flow.py -v`
Expected: FAIL — módulo inexistente.

- [ ] **Step 3: Implementar config_flow.py + strings/translations**

```python
# config_flow.py
from urllib.parse import urlparse
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from xbox_devportal import XboxDevPortal, AuthError, DevPortalUnreachable
from .const import (DOMAIN, DEFAULT_PORT, CONF_SCAN_INTERVAL, CONF_SCREENSHOT_INTERVAL,
                    CONF_SETTINGS_INTERVAL, DEFAULT_SCAN_INTERVAL,
                    DEFAULT_SCREENSHOT_INTERVAL, DEFAULT_SETTINGS_INTERVAL)

_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str, vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str})


class XboxDevModeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._discovered = {}

    async def _validate(self, data):
        client = XboxDevPortal(data[CONF_HOST], data[CONF_USERNAME],
                               data[CONF_PASSWORD], port=data[CONF_PORT])
        try:
            await client.info()
        finally:
            await client.close()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                await self._validate(user_input)
            except AuthError:
                errors["base"] = "invalid_auth"
            except DevPortalUnreachable:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    self._discovered.get("udn") or f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}",
                    raise_on_progress=False)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Xbox ({user_input[CONF_HOST]})", data=user_input)
        schema = self.add_suggested_values_to_schema(_SCHEMA, self._discovered.get("suggest", {}))
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_ssdp(self, discovery_info):
        host = urlparse(discovery_info.ssdp_location or "").hostname or ""
        self._discovered = {"udn": discovery_info.ssdp_udn, "suggest": {CONF_HOST: host}}
        await self.async_set_unique_id(discovery_info.ssdp_udn)
        self._abort_if_unique_id_configured()
        return await self.async_step_user()

    async def async_step_dhcp(self, discovery_info):
        self._discovered = {"suggest": {CONF_HOST: discovery_info.ip}}
        return await self.async_step_user()

    async def async_step_reauth(self, entry_data):
        return await self.async_step_user()

    @staticmethod
    def async_get_options_flow(entry):
        return XboxDevModeOptionsFlow(entry)


class XboxDevModeOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        o = self._entry.options
        schema = vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=o.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
            vol.Optional(CONF_SCREENSHOT_INTERVAL, default=o.get(CONF_SCREENSHOT_INTERVAL, DEFAULT_SCREENSHOT_INTERVAL)): int,
            vol.Optional(CONF_SETTINGS_INTERVAL, default=o.get(CONF_SETTINGS_INTERVAL, DEFAULT_SETTINGS_INTERVAL)): int})
        return self.async_show_form(step_id="init", data_schema=schema)
```

`strings.json` + `translations/en.json` + `translations/pt-BR.json` com os labels dos campos e as mensagens de erro (`invalid_auth`, `cannot_connect`).

- [ ] **Step 4: Rodar e ver passar**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_config_flow.py -v`
Expected: 3 passam.

- [ ] **Step 5: Commit**

```bash
cd ~/Github/ha-xbox-dev-mode && git add -A
git commit -m "feat: config flow com ssdp, dhcp, reauth e options"
```

---

### Task B3: Coordinator tri-estado + wiring do __init__

**Files:**
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/coordinator.py`
- Modify: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/__init__.py`
- Modify: `~/Github/ha-xbox-dev-mode/tests/conftest.py` (fixture `mock_devportal`)
- Test: `~/Github/ha-xbox-dev-mode/tests/test_coordinator.py`

**Interfaces:**
- Consumes: `XboxDevPortal` (info, system_perf, foreground_app, packages, settings, screenshot), `icmplib.async_ping`.
- Produces:
  - `XboxData` (dataclass): `state: str`, `info`, `perf`, `foreground`, `sideloaded: list[Package]`, `settings: dict[str, Setting]`, `screenshot: bytes | None`.
  - `XboxDevModeCoordinator(DataUpdateCoordinator[XboxData])` — assinatura `__init__(hass, client, host, scan, shot, settings_iv)`; atributo `selected_app: str | None`; método `_async_update_data() -> XboxData`.
  - Regra tri-estado: sem ping → `off`; ping ok + `info()` levanta `DevPortalUnreachable` → `retail`; `info()` ok → `dev_mode` (+ perf/foreground/sideloaded sempre; settings/screenshot em cadência mais lenta por contador). `AuthError` → `ConfigEntryAuthFailed`.

- [ ] **Step 1: Escrever o teste do tri-estado**

```python
# tests/test_coordinator.py
from unittest.mock import AsyncMock, patch
from custom_components.xbox_dev_mode.coordinator import XboxDevModeCoordinator
from custom_components.xbox_dev_mode.const import STATE_DEV, STATE_RETAIL, STATE_OFF
from xbox_devportal import DevPortalUnreachable


def _ping(alive):
    r = type("R", (), {"is_alive": alive})()
    return patch("custom_components.xbox_dev_mode.coordinator.async_ping",
                 AsyncMock(return_value=r))


async def _run(hass, client, alive):
    with _ping(alive):
        coord = XboxDevModeCoordinator(hass, client, "10.0.0.5", scan=30, shot=0, settings_iv=120)
        return await coord._async_update_data()


async def test_state_off_when_no_ping(hass):
    data = await _run(hass, AsyncMock(), alive=False)
    assert data.state == STATE_OFF


async def test_state_retail_when_ping_but_portal_down(hass):
    client = AsyncMock(); client.info.side_effect = DevPortalUnreachable("x")
    data = await _run(hass, client, alive=True)
    assert data.state == STATE_RETAIL


async def test_state_dev_when_portal_answers(hass):
    client = AsyncMock()
    client.info.return_value = object()
    client.system_perf.return_value = object()
    client.foreground_app.return_value = None
    client.packages.return_value = []
    data = await _run(hass, client, alive=True)
    assert data.state == STATE_DEV
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_coordinator.py -v`
Expected: FAIL.

- [ ] **Step 3: Implementar coordinator.py e completar __init__.py**

```python
# coordinator.py
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from icmplib import async_ping
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryAuthFailed
from xbox_devportal import (AuthError, DevPortalUnreachable,
                            DeviceInfo, SystemPerf, Process, Package, Setting)
from .const import DOMAIN, STATE_DEV, STATE_RETAIL, STATE_OFF

_LOGGER = logging.getLogger(__name__)


@dataclass
class XboxData:
    state: str
    info: DeviceInfo | None = None
    perf: SystemPerf | None = None
    foreground: Process | None = None
    sideloaded: list[Package] = field(default_factory=list)
    settings: dict[str, Setting] = field(default_factory=dict)
    screenshot: bytes | None = None


class XboxDevModeCoordinator(DataUpdateCoordinator[XboxData]):
    def __init__(self, hass, client, host, scan, shot, settings_iv):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=scan))
        self.client = client
        self._host = host
        self._shot_iv, self._settings_iv = shot, settings_iv
        self._tick = 0
        self._last_settings: dict = {}
        self._last_shot: bytes | None = None
        self.selected_app: str | None = None

    def _due(self, interval: int) -> bool:
        if not interval:
            return False
        every = max(1, interval // (self.update_interval.seconds or 30))
        return self._tick % every == 0

    async def _async_update_data(self) -> XboxData:
        self._tick += 1
        ping = await async_ping(self._host, count=1, timeout=1, privileged=False)
        if not ping.is_alive:
            return XboxData(state=STATE_OFF)
        try:
            info = await self.client.info()
        except AuthError as e:
            raise ConfigEntryAuthFailed from e
        except DevPortalUnreachable:
            return XboxData(state=STATE_RETAIL)
        perf = await self.client.system_perf()
        fg = await self.client.foreground_app()
        side = await self.client.packages(sideloaded_only=True)
        if self.selected_app is None and side:
            self.selected_app = side[0].name
        if self._due(self._settings_iv):
            self._last_settings = await self.client.settings()
        if self._due(self._shot_iv):
            self._last_shot = await self.client.screenshot()
        return XboxData(state=STATE_DEV, info=info, perf=perf, foreground=fg,
                        sideloaded=side, settings=self._last_settings, screenshot=self._last_shot)
```

`__init__.py`: em `async_setup_entry`, criar `XboxDevPortal` com `async_get_clientsession(hass)`, montar coordinator com intervalos das options (defaults do const), `await coordinator.async_config_entry_first_refresh()`, `entry.runtime_data = coordinator`, `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`. `async_unload_entry` → `async_unload_platforms`.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_coordinator.py -v`
Expected: 3 passam.

- [ ] **Step 5: Commit**

```bash
cd ~/Github/ha-xbox-dev-mode && git add -A
git commit -m "feat: coordinator tri-estado e setup da entry"
```

---

### Task B4: Base entity + sensores + binary_sensor

**Files:**
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/entity.py`
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/sensor.py`
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/binary_sensor.py`
- Modify: `~/Github/ha-xbox-dev-mode/tests/conftest.py` (fixtures `setup_integration`, `setup_integration_off`)
- Test: `~/Github/ha-xbox-dev-mode/tests/test_sensor.py`
- Test: `~/Github/ha-xbox-dev-mode/tests/test_binary_sensor.py`

**Interfaces:**
- Consumes: `XboxData`, `XboxDevModeCoordinator`.
- Produces:
  - `entity.py`: `XboxEntity(CoordinatorEntity[XboxDevModeCoordinator])`, `_attr_has_entity_name = True`, `device_info` (identifiers = `{(DOMAIN, entry.unique_id)}`, manufacturer "Microsoft", model = `coordinator.data.info.platform`); class attr `_dev_only: bool = True`; `available` = `super().available and (not self._dev_only or coordinator.data.state == STATE_DEV)`.
  - `sensor.py`: entidades `console_state` (`_dev_only=False`), `foreground_app`, `cpu_load` (%), `memory_used`/`memory_available` (MB), `gpu_memory_used` (MB), `sideloaded_apps`, `sandbox`/`os_version` (diagnóstico, `_dev_only=False`).
  - `binary_sensor.py`: `dev_mode` (`device_class=connectivity`, `_dev_only=False`, `is_on = state == STATE_DEV`).

- [ ] **Step 1: Escrever os testes e fixtures**

```python
# tests/test_sensor.py
from custom_components.xbox_dev_mode.const import STATE_DEV, STATE_OFF


async def test_sensors_created_and_state(hass, setup_integration):
    assert hass.states.get("sensor.xbox_console_state").state == STATE_DEV
    assert hass.states.get("sensor.xbox_cpu_load").state == "3"


async def test_non_state_sensors_unavailable_when_off(hass, setup_integration_off):
    assert hass.states.get("sensor.xbox_console_state").state == STATE_OFF
    assert hass.states.get("sensor.xbox_cpu_load").state == "unavailable"
```

```python
# tests/test_binary_sensor.py
async def test_dev_mode_binary_on_in_dev(hass, setup_integration):
    assert hass.states.get("binary_sensor.xbox_dev_mode").state == "on"


async def test_dev_mode_binary_off_when_off(hass, setup_integration_off):
    assert hass.states.get("binary_sensor.xbox_dev_mode").state == "off"
```

Em `conftest.py` adicionar `mock_devportal` retornando fixtures reais (info Series S, perf com CpuLoad 3, RetroArch sideloaded, settings com TVResolution+AllowHDR) e as fixtures `setup_integration` (ping vivo → dev) e `setup_integration_off` (ping morto), ambas registrando `MockConfigEntry(domain=DOMAIN, unique_id="uuid:test", data={...})`, mockando `XboxDevPortal` e `async_ping`, e chamando `async_setup` + `async_block_till_done`.

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_sensor.py tests/test_binary_sensor.py -v`
Expected: FAIL.

- [ ] **Step 3: Implementar entity.py, sensor.py, binary_sensor.py**

`entity.py` conforme Interfaces. `sensor.py` com uma dataclass `XboxSensorDescription(SensorEntityDescription)` que adiciona `value_fn: Callable[[XboxData], StateType]` e `dev_only: bool = True`; lista `SENSORS` com cada métrica; `async_setup_entry` cria `XboxSensor` por descrição. `binary_sensor.py` análogo com uma entidade só.

`console_state.value_fn = lambda d: d.state`; `cpu_load.value_fn = lambda d: d.perf.cpu_load if d.perf else None`; `memory_used.value_fn = lambda d: d.perf.memory_used_mb if d.perf else None`; etc. `foreground_app.value_fn = lambda d: d.foreground.image_name if d.foreground else "Nenhum"` com `extra_state_attributes` trazendo PackageFullName e memória.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_sensor.py tests/test_binary_sensor.py -v`
Expected: passam.

- [ ] **Step 5: Commit**

```bash
cd ~/Github/ha-xbox-dev-mode && git add -A
git commit -m "feat: base entity, sensores e binary_sensor"
```

---

### Task B5: Select (app + settings) + Switch

**Files:**
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/select.py`
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/switch.py`
- Test: `~/Github/ha-xbox-dev-mode/tests/test_select.py`
- Test: `~/Github/ha-xbox-dev-mode/tests/test_switch.py`

**Interfaces:**
- Consumes: `XboxData.sideloaded`, `XboxData.settings`, `coordinator.client.set_setting`, `coordinator.selected_app`.
- Produces:
  - `select.app` — `options` = nomes dos sideloaded; `current_option` = `coordinator.selected_app`; `async_select_option` seta `coordinator.selected_app`.
  - selects de settings (`SETTING_SELECTS = [("tv_resolution","TVResolution"), ("power_mode","PowerMode"), ("hdmi_audio","HDMIAudio"), ("color_space","ColorSpace"), ("headset_format","HeadsetFormat"), ("default_app","DefaultApp")]`) — `options` do `Setting.options`; `async_select_option` → `client.set_setting(NAME, value)` + `async_request_refresh`; `available=False` se a setting ainda não foi buscada.
  - switches (`SETTING_SWITCHES = [("allow_hdr","AllowHDR"), ("allow_4k","Allow4K"), ("allow_vrr","AllowVRR"), ("allow_allm","AllowALLM")]`) — `is_on = value == "true"`; `turn_on/off` → `set_setting(NAME, "true"/"false")` + refresh.

- [ ] **Step 1: Escrever os testes**

```python
# tests/test_select.py
async def test_app_select_lists_sideloaded(hass, setup_integration):
    assert "RetroArch" in hass.states.get("select.xbox_app").attributes["options"]


async def test_tv_resolution_calls_set_setting(hass, setup_integration, mock_devportal):
    await hass.services.async_call("select", "select_option",
        {"entity_id": "select.xbox_tv_resolution", "option": "2160p"}, blocking=True)
    mock_devportal.set_setting.assert_awaited_with("TVResolution", "2160p")
```

```python
# tests/test_switch.py
async def test_allow_hdr_toggle_off(hass, setup_integration, mock_devportal):
    await hass.services.async_call("switch", "turn_off",
        {"entity_id": "switch.xbox_allow_hdr"}, blocking=True)
    mock_devportal.set_setting.assert_awaited_with("AllowHDR", "false")
```

Garantir que `mock_devportal.settings.return_value` traga `TVResolution` (com options `("720p","1080p","2160p")`) e `AllowHDR` (value "true"). O `setup_integration` deve usar `settings_iv` que dispare o fetch de settings no primeiro refresh (ex.: `settings_iv = scan`, para `_due` ser True no tick 1).

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_select.py tests/test_switch.py -v`
Expected: FAIL.

- [ ] **Step 3: Implementar select.py e switch.py**

Entidades declarativas conforme Interfaces, herdando `XboxEntity` (`_dev_only=True` por padrão, o que já as deixa `unavailable` fora do dev_mode). Cada setting-entity lê `coordinator.data.settings.get(NAME)`; `available` extra = setting presente. Após qualquer `set_setting`, `await coordinator.async_request_refresh()`.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_select.py tests/test_switch.py -v`
Expected: passam.

- [ ] **Step 5: Commit**

```bash
cd ~/Github/ha-xbox-dev-mode && git add -A
git commit -m "feat: selects (app + settings) e switches"
```

---

### Task B6: Button + Image

**Files:**
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/button.py`
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/image.py`
- Test: `~/Github/ha-xbox-dev-mode/tests/test_button.py`
- Test: `~/Github/ha-xbox-dev-mode/tests/test_image.py`

**Interfaces:**
- Consumes: `coordinator.client.launch/terminate/restart/shutdown`, `coordinator.selected_app`, `XboxData.foreground`, `XboxData.screenshot`.
- Produces:
  - buttons: `launch_app` (`await client.launch(coordinator.selected_app)` — via resolução por nome→Package feita no client; passar o `package_full_name` do sideloaded cujo `name == selected_app`), `terminate_foreground` (guard se `foreground` None), `restart`, `shutdown` (`device_class=restart`, categoria config).
  - `image.screen` (`XboxScreenImage(XboxEntity, ImageEntity)`): `async_image()` retorna `data.screenshot`; `_attr_image_last_updated` avança quando os bytes mudam; `available=False` se screenshot desabilitado/`None`.

- [ ] **Step 1: Escrever os testes**

```python
# tests/test_button.py
async def test_launch_button_launches(hass, setup_integration, mock_devportal):
    await hass.services.async_call("button", "press",
        {"entity_id": "button.xbox_launch_app"}, blocking=True)
    assert mock_devportal.launch.await_count == 1


async def test_restart_button_calls_restart(hass, setup_integration, mock_devportal):
    await hass.services.async_call("button", "press",
        {"entity_id": "button.xbox_restart"}, blocking=True)
    mock_devportal.restart.assert_awaited_once()
```

```python
# tests/test_image.py
async def test_image_available_with_screenshot(hass, setup_integration_with_shot):
    assert hass.states.get("image.xbox_screen").state != "unavailable"
```

Adicionar `setup_integration_with_shot` (como `setup_integration`, mas `shot` > 0 e `mock_devportal.screenshot.return_value = b"\x89PNG..."`).

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_button.py tests/test_image.py -v`
Expected: FAIL.

- [ ] **Step 3: Implementar button.py e image.py**

`button.py`: `XboxButtonDescription(ButtonEntityDescription)` com `press_fn: Callable[[XboxDevModeCoordinator], Awaitable]`. `launch_app.press_fn` resolve o `package_full_name` pelo `selected_app` em `data.sideloaded` e chama `client.launch(pfn)`. `restart`/`shutdown` chamam o client diretamente (única origem dessas chamadas). `terminate_foreground` só age se `data.foreground`.

`image.py`: herda `XboxEntity` + `ImageEntity`; `async_image()` retorna os bytes; controla `_attr_image_last_updated` comparando com o último hash/len; `available` respeita `screenshot is not None`.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_button.py tests/test_image.py -v`
Expected: passam.

- [ ] **Step 5: Commit**

```bash
cd ~/Github/ha-xbox-dev-mode && git add -A
git commit -m "feat: buttons e image (screenshot)"
```

---

### Task B7: Serviços + diagnostics + README/HACS, release 0.1.0

**Files:**
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/services.yaml`
- Modify: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/__init__.py` (registra serviços)
- Create: `~/Github/ha-xbox-dev-mode/custom_components/xbox_dev_mode/diagnostics.py`
- Create: `~/Github/ha-xbox-dev-mode/hacs.json`
- Create: `~/Github/ha-xbox-dev-mode/README.md`
- Test: `~/Github/ha-xbox-dev-mode/tests/test_services.py`
- Test: `~/Github/ha-xbox-dev-mode/tests/test_diagnostics.py`

**Interfaces:**
- Consumes: `coordinator.client.install/uninstall/launch/terminate/upload_file/set_setting`.
- Produces: serviços `install_package(path)`, `uninstall_package(package_full_name)`, `launch(package_full_name)`, `terminate(package_full_name)`, `upload_file(package_full_name, subdir, path)`, `set_setting(name, value)` (schemas em `services.yaml`; handlers em `__init__.py` resolvendo o coordinator: se houver um só entry, usa ele; senão exige `device_id`). `diagnostics.py`: `async_get_config_entry_diagnostics` dumpando info/perf/packages/settings com `async_redact_data(..., {"password"})` na entry e na credencial SMB.

- [ ] **Step 1: Escrever os testes**

```python
# tests/test_services.py
async def test_install_service_calls_client(hass, setup_integration, mock_devportal, tmp_path):
    f = tmp_path / "x.appx"; f.write_bytes(b"d")
    await hass.services.async_call("xbox_dev_mode", "install_package",
        {"path": str(f)}, blocking=True)
    mock_devportal.install.assert_awaited_once()
```

```python
# tests/test_diagnostics.py
async def test_diagnostics_redacts_password(hass, setup_integration):
    from custom_components.xbox_dev_mode.diagnostics import async_get_config_entry_diagnostics
    entry = hass.config_entries.async_entries("xbox_dev_mode")[0]
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["data"]["password"] == "**REDACTED**"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest tests/test_services.py tests/test_diagnostics.py -v`
Expected: FAIL.

- [ ] **Step 3: Implementar services.yaml, handlers, diagnostics.py, hacs.json, README**

`services.yaml` com os 6 serviços e campos. Registro em `async_setup_entry` via `hass.services.async_register(DOMAIN, "install_package", handler, schema=...)`; handler localiza o coordinator (único entry, ou por `device_id`) e chama o client. `diagnostics.py` usa `homeassistant.helpers.redact.async_redact_data` com `{"password"}`. `hacs.json`: `{"name": "Xbox Dev Mode", "render_readme": true}`. `README.md`: instalação HACS, tabela de entidades/serviços, screenshot, nota de segurança (Basic Auth + cert autoassinado, só LAN).

- [ ] **Step 4: Rodar a suíte inteira**

Run: `cd ~/Github/ha-xbox-dev-mode && uv run pytest -v`
Expected: todos passam.

- [ ] **Step 5: Commit + tag**

```bash
cd ~/Github/ha-xbox-dev-mode && git add -A
git commit -m "feat: serviços, diagnostics e empacotamento HACS (0.1.0)"
git tag v0.1.0
```

---

## Validação final (manual, com o usuário — fora do fluxo TDD)

Exige o console real e presença do usuário:

- [ ] Publicar `xbox-devportal` no PyPI (ou apontar o `requirements` do manifest para o repo git enquanto não publica).
- [ ] Instalar a integração via HACS custom repo, reiniciar o HA.
- [ ] Confirmar que o console aparece em **Descoberto** (SSDP) e concluir o config flow.
- [ ] Ver as entidades povoando em `dev_mode`; conferir a `image.xbox_screen`.
- [ ] **Com o usuário assistindo à TV:** acionar `button.xbox_restart` uma vez e confirmar que `/api/control/restart` existe e reinicia. Se retornar 404, remover os botões restart/shutdown e cortar `restart()`/`shutdown()` da lib numa 0.1.1 (e ajustar o teste `test_restart_button_calls_restart`).
