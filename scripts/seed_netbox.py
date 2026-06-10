#!/usr/bin/env python3
"""Seed a NetBox instance with a small demo lab.

Creates a site, manufacturers, device types, roles, platforms, two
devices (one Cisco ISR, one Juniper MX) with interfaces, management IPs
and primary-IP assignment — enough for the dynamic inventory and the
intended-config templates to work end to end.

Idempotent: existing objects are reused, so the script can be re-run.

Usage:
    export NETBOX_API=http://localhost:8000
    export NETBOX_TOKEN=<api-token>
    python3 scripts/seed_netbox.py
"""

import os
import sys

import pynetbox


def ensure(endpoint, lookup, defaults=None):
    """Return the object matching `lookup`, creating it if needed."""
    obj = endpoint.get(**lookup)
    if obj:
        print(f"  exists: {endpoint.name} {lookup}")
        return obj
    obj = endpoint.create({**lookup, **(defaults or {})})
    print(f"  created: {endpoint.name} {lookup}")
    return obj


def main() -> int:
    try:
        api_url = os.environ["NETBOX_API"]
        token = os.environ["NETBOX_TOKEN"]
    except KeyError as missing:
        print(f"error: environment variable {missing} is not set", file=sys.stderr)
        return 1

    nb = pynetbox.api(api_url, token=token)

    print("Organizational objects:")
    site = ensure(nb.dcim.sites, {"slug": "lab-sp"}, {"name": "Lab Sao Paulo", "status": "active"})
    cisco = ensure(nb.dcim.manufacturers, {"slug": "cisco"}, {"name": "Cisco"})
    juniper = ensure(nb.dcim.manufacturers, {"slug": "juniper"}, {"name": "Juniper"})

    print("Device types, roles and platforms:")
    isr = ensure(
        nb.dcim.device_types,
        {"slug": "isr4451"},
        {"model": "ISR4451", "manufacturer": cisco.id},
    )
    mx = ensure(
        nb.dcim.device_types,
        {"slug": "mx204"},
        {"model": "MX204", "manufacturer": juniper.id},
    )
    core_role = ensure(
        nb.dcim.device_roles, {"slug": "core-router"}, {"name": "Core Router", "color": "2196f3"}
    )
    edge_role = ensure(
        nb.dcim.device_roles, {"slug": "edge-router"}, {"name": "Edge Router", "color": "4caf50"}
    )
    ios = ensure(nb.dcim.platforms, {"slug": "ios"}, {"name": "Cisco IOS"})
    junos = ensure(nb.dcim.platforms, {"slug": "junos"}, {"name": "Juniper Junos"})

    lab_devices = [
        # (name, device_type, role, platform, mgmt interface, mgmt IP)
        ("rtr-core-01", isr, core_role, ios, "GigabitEthernet0/0/0", "192.0.2.11/24"),
        ("mx-edge-01", mx, edge_role, junos, "ge-0/0/0", "192.0.2.31/24"),
    ]

    print("Devices, interfaces and IPs:")
    for name, dev_type, role, platform, intf_name, address in lab_devices:
        device = ensure(
            nb.dcim.devices,
            {"name": name},
            {
                "device_type": dev_type.id,
                "role": role.id,
                "platform": platform.id,
                "site": site.id,
                "status": "active",
            },
        )
        interface = ensure(
            nb.dcim.interfaces,
            {"device_id": device.id, "name": intf_name},
            {"device": device.id, "type": "1000base-t", "description": "uplink / management"},
        )
        ip = ensure(
            nb.ipam.ip_addresses,
            {"address": address},
            {
                "assigned_object_type": "dcim.interface",
                "assigned_object_id": interface.id,
                "status": "active",
            },
        )
        if not device.primary_ip4:
            device.primary_ip4 = ip.id
            device.save()
            print(f"  set primary IP of {name} to {address}")

    print("\nDone. Verify the dynamic inventory with:")
    print("  ansible-inventory --list")
    return 0


if __name__ == "__main__":
    sys.exit(main())
