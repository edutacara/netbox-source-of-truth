# netbox-source-of-truth

Using **NetBox as the single source of truth** for network automation:
Ansible reads devices, platforms, interfaces and IPs straight from NetBox,
renders each device's **intended configuration** from templates, and pushes
it — no static inventory files, no hand-edited configs.

```
┌─────────┐  dynamic inventory   ┌─────────┐  render    ┌──────────────────┐
│ NetBox  │ ───────────────────► │ Ansible │ ─────────► │ intended_configs/ │
│ (SoT)   │  devices, IPs,       │         │  deploy    │ <host>.cfg        │
└─────────┘  interfaces          └─────────┘ ─────────► │ Cisco / Juniper   │
                                                        └──────────────────┘
```

## How it works

- `inventory/netbox.yml` — the `netbox.netbox.nb_inventory` plugin builds
  the inventory at runtime: groups by platform/site/role, `ansible_host`
  from the device's primary IP, `ansible_network_os` derived from the
  NetBox platform slug, and interfaces (with IPs) exposed as host vars.
- `templates/` — Jinja2 templates render the intended config per platform
  (Cisco IOS native syntax, Junos `set` syntax) from NetBox data only.
- `playbooks/render_intended_configs.yml` — writes
  `intended_configs/<host>.cfg` for every device.
- `playbooks/deploy_intended_configs.yml` — pushes the rendered configs
  (`ios_config` / `junos_config`), with `--check --diff` support to review
  before applying.
- `scripts/seed_netbox.py` — idempotent pynetbox script that populates a
  fresh NetBox with a demo lab (site, types, roles, platforms, devices,
  interfaces, primary IPs).

## Quick start

```bash
# 1. Run NetBox locally (https://github.com/netbox-community/netbox-docker)
git clone https://github.com/netbox-community/netbox-docker
cd netbox-docker && docker compose up -d
# create an API token in the NetBox UI (admin → API tokens)

# 2. Install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install "ansible>=10" -r requirements.txt
ansible-galaxy collection install -r requirements.yml

# 3. Point at NetBox and seed the demo lab
export NETBOX_API=http://localhost:8000
export NETBOX_TOKEN=<your-token>
python3 scripts/seed_netbox.py

# 4. The inventory now comes from NetBox
ansible-inventory --list

# 5. Render and (optionally) deploy intended configs
ansible-playbook playbooks/render_intended_configs.yml
export NET_USER=admin NET_PASSWORD='your-password'
ansible-playbook playbooks/deploy_intended_configs.yml --check --diff
```

## Why this pattern matters

Documentation that drives automation can't drift: if it's not in NetBox,
it doesn't exist on the network. Renaming an interface description or
re-addressing a link becomes a NetBox change + a pipeline run, and the
rendered `intended_configs/` directory doubles as a reviewable artifact
for change management.

## License

MIT
