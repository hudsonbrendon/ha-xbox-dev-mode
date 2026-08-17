# ha-xbox-dev-mode — Design

**Data:** 2026-08-16 · **Status:** aprovado em conversa, aguardando revisão da spec escrita

Integração do Home Assistant para Xbox em **Modo Desenvolvedor**, via Windows
Device Portal (WDP) REST. Complementa (não substitui) a integração `xbox`
oficial, que é cloud e cobre o modo Retail.

## Arquitetura: dois repositórios

Mesmo padrão do `ha-xbox360-aurora` (lib `xbox360-nova` no PyPI + integração fina):

1. **`xbox-devportal`** (PyPI) — cliente async do WDP, sem dependência de HA.
2. **`ha-xbox-dev-mode`** (HACS) — coordinator + entidades, importa a lib.

## Fatos verificados no console real (Series S, OS 26100.9426)

Tudo abaixo foi testado contra um Xbox Series S real em `https://<console>:11443`:

| Endpoint | Verbo | Retorna / faz |
|---|---|---|
| `/api/os/info` | GET | `{ComputerName, OsVersion, Platform: "Xbox Series S"}` |
| `/api/resourcemanager/processes` | GET | processos com `ImageName`, `PackageFullName`, `PrivateWorkingSet` |
| `/api/resourcemanager/systemperf` | GET | `CpuLoad`, `TotalPages/AvailablePages/CommittedPages` (PageSize 4096), IO, `GPUData.DedicatedMemory[Used]` |
| `/api/app/packagemanager/packages` | GET | pacotes; sideloaded = `CanUninstall: true` |
| `/api/app/packagemanager/package?package=<nome>` | POST multipart | instala appx/msix → 202; poll em `/state` |
| `/api/app/packagemanager/state` | GET | resultado da última instalação |
| `/api/taskmanager/app?appid=<b64>&package=<b64>` | POST (`Content-Length: 0`) | lança app |
| `/api/taskmanager/app?package=<b64>` | DELETE | encerra app |
| `/api/filesystem/apps/…` | GET/POST/DELETE | ler/subir/apagar arquivos em `LocalState` de qualquer pacote (sem mkdir) |
| `/ext/screenshot` | GET | PNG da tela atual (~21 KB em menu) |
| `/ext/settings` | GET (PUT por item) | ~40 configurações, várias com lista de opções |
| `/ext/xboxlive/sandbox` | GET | `{"Sandbox": "XDKS.1"}` |
| `/ext/smb/developerfolder` | GET | credenciais do share SMB `D:\DevelopmentFiles` |
| `/api/power/state` | GET | `{"LowPowerStateAvailable": false}` |
| `/api/control/restart`, `/api/control/shutdown` | POST | **não testados** (reiniciariam o console); padrão WDP — implementar e validar no primeiro uso real |

**Autenticação:** Basic Auth + TLS autoassinado (`ssl=False`). Todo verbo
não-GET exige CSRF: capturar cookie `CSRF-Token` num GET e reenviar como
cookie **e** header `X-CSRF-Token` (sem isso → 403). POST sem corpo exige
`Content-Length: 0` (sem isso → 411).

**Settings observados com opções** (viram select/switch): `TVResolution`
(480p…2160p), `PowerMode` (Instant On / Energy Saving), `HDMIAudio`,
`ColorSpace`, `ColorDepth`, `HeadsetFormat`, `DefaultApp` (Dev Home / Retail
Home), `AutoSignInUser`, `ShutdownTimeout`, `WirelessRadioSettings`; booleanos
`AllowHDR`, `Allow4K`, `AllowVRR`, `AllowALLM`, `AllowDolbyVision`, `AutoBoot`.

**Descoberta:** o console anuncia SSDP **nos dois modos** (Retail e Dev):
`manufacturer: Microsoft Corporation`, `modelName: Xbox One`,
`friendlyName: XBOX`, UDN estável (`uuid:08e2300a-…`). O componente `ssdp`
do HA já recebe esses anúncios nesta rede (TV LG entrou por esse caminho).

## Repositório 1 — `xbox-devportal`

Cliente `aiohttp`, Python ≥ 3.12, tipado, zero dependência de HA.

```python
class XboxDevPortal:
    def __init__(host, username, password, port=11443, session=None)
    async def info() -> DeviceInfo
    async def system_perf() -> SystemPerf          # cpu, memória, gpu
    async def processes() -> list[Process]
    async def foreground_app() -> Process | None    # heurística: maior app UWP visível
    async def packages(sideloaded_only=False) -> list[Package]
    async def launch(package: Package | str) -> None
    async def terminate(package: Package | str) -> None
    async def install(path: Path) -> None           # multipart + poll do state
    async def uninstall(package_full_name: str) -> None
    async def screenshot() -> bytes                 # PNG
    async def settings() -> dict[str, Setting]      # Setting(value, options)
    async def set_setting(name: str, value: str) -> None
    async def sandbox() -> str
    async def smb_credentials() -> SmbShare
    async def restart() -> None
    async def shutdown() -> None
    async def list_files(pfn, path) / upload_file(...) / delete_file(...)
```

- CSRF automático e transparente (renova no 403 uma vez).
- Erros: `DevPortalError` (base), `AuthError` (401 → reauth no HA),
  `DevPortalUnreachable` (timeout/conexão).
- Testes com `aioresponses`; fixtures gravadas das respostas reais desta sessão.

## Repositório 2 — `ha-xbox-dev-mode`

`domain: xbox_dev_mode` · `iot_class: local_polling` ·
`integration_type: device` · `requirements: ["xbox-devportal>=0.1.0"]` (pin exato definido a cada release)

### Descoberta e config flow

- **SSDP matcher:** `manufacturer: "Microsoft Corporation"` +
  `st: urn:schemas-upnp-org:device:MediaRenderer:1` refinado por
  `modelName: "Xbox One"`. `unique_id` = UDN do UPnP (estável a troca de IP).
- **DHCP matcher** (fallback): OUI da Microsoft (`38:56:3D` incluso).
- Flow: host pré-preenchido pela descoberta → pede usuário/senha → valida com
  `info()`. Se a 11443 não responde mas o SSDP sim, erro específico:
  "console encontrado, mas em modo Retail ou com Device Portal desativado —
  ative o Dev Mode e o Device Portal em Dev Home → Remote Access".
- Options flow: intervalo de polling (padrão 30 s), intervalo do screenshot
  (padrão 60 s, 0 = desligado), intervalo de settings (padrão 120 s).
- Reauth em `AuthError`.

### Coordinator (tri-estado)

A cada ciclo: ping ICMP (via `icmplib`, como a integração `ping` oficial) +
tentativa HTTP.

| Ping | Porta 11443 | Estado |
|---|---|---|
| ✓ | ✓ | `dev_mode` |
| ✓ | ✗ | `retail` |
| ✗ | ✗ | `off` |

Fora de `dev_mode`, permanecem disponíveis `sensor.console_state` e
`binary_sensor.dev_mode` (a razão de existir deles é justamente reportar
esses estados); o resto fica `unavailable`. Ciclo em `dev_mode` busca: processes + systemperf a cada
intervalo; packages e settings em cadência mais lenta (mudam pouco).

### Entidades

**Sensores** (device_class/unidade onde couber):
- `console_state` — enum `dev_mode | retail | off` (sempre disponível)
- `foreground_app` — nome amigável; atributos: PackageFullName, versão, memória
- `cpu_load` — % (systemperf)
- `memory_used` / `memory_available` — MB (páginas × 4096)
- `gpu_memory_used` — MB (`GPUData`)
- `sideloaded_apps` — contagem; atributo com a lista (nome + versão)
- `sandbox` — diagnóstico
- `os_version` — diagnóstico

**Binary sensor:** `dev_mode` (connectivity).

**Image:** `screen` — screenshot periódico via `/ext/screenshot` (intervalo
nas options; 0 desliga).

**Select:**
- `app` — apps sideloaded (recarrega quando a lista muda)
- `tv_resolution`, `power_mode`, `hdmi_audio`, `color_space`,
  `headset_format`, `default_app` — espelham `/ext/settings`
  (categoria `config`)

**Switch** (categoria `config`): `allow_hdr`, `allow_4k`, `allow_vrr`,
`allow_allm`.

**Button:** `launch_app` (lança o selecionado em `select.app`),
`terminate_foreground`, `restart`, `shutdown` (os dois últimos com
`device_class: restart` e categoria `config`).

**Serviços** (`services.yaml`):
- `xbox_dev_mode.install_package` — `path` local do HA
- `xbox_dev_mode.uninstall_package` — `package_full_name`
- `xbox_dev_mode.launch` / `terminate` — `package_full_name`
- `xbox_dev_mode.upload_file` — `package_full_name`, `subdir`, `path`
- `xbox_dev_mode.set_setting` — `name`, `value` (escape hatch p/ settings sem entidade)

**Diagnostics:** dump de info, perf, packages e settings (senha redigida).

### Erros e resiliência

- `AuthError` → `ConfigEntryAuthFailed` → reauth.
- Timeout num ciclo → mantém último estado por 1 ciclo antes de rebaixar
  (evita flap quando o console está carregando jogo pesado).
- PUT de setting falho → log + refresh do valor real (a UI não mente).
- `restart`/`shutdown` nunca são chamados na validação do flow.

### Testes

Padrão `ha-xbox360-aurora`: `pytest-homeassistant-custom-component`,
`conftest.py` com `XboxDevPortal` mockado (fixtures das respostas reais),
um `test_<plataforma>.py` por plataforma + `test_config_flow` (ssdp, dhcp,
manual, reauth, retail-detectado) + `test_coordinator` (tri-estado) +
`test_diagnostics` (redação de segredos).

### Empacotamento

`hacs.json`, `pyproject.toml` + `uv.lock`, README com screenshots,
GitHub Actions (lint ruff + pytest), versão inicial `0.1.0`.

## Fora de escopo (registrado, não esquecido)

- Sair/entrar do Dev Mode remotamente — o WDP não expõe.
- Controle do console em modo Retail — integração `xbox` oficial cobre.
- Wake-on-LAN do estado `off` — `PowerMode: Energy Saving` não responde
  WoL padrão; investigar depois se virar incômodo.
- Transferência em massa de ROMs via SMB — canal existe
  (`/ext/smb/developerfolder`), fica como serviço futuro se fizer sentido.
