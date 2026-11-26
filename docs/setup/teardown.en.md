# Lab teardown & rollback

English mirror of `docs/setup/teardown.md` (Indonesian original is the source
of truth).

Two levels of reversal: **service level** (inside the VM) and **VM level**
(in the hypervisor). Use the smallest level that suffices.

## Service level — inside the VM

```bash
cd ~/it-operations-ai-lab
sudo bash lab/scripts/uninstall_demo_service.sh
bash lab/scripts/baseline.sh    # service check → FAIL "unit not found" (the correct expectation)
```

Removed: the `/etc/systemd/system/demo-http.service` unit, the
`/opt/demo-http/` application, the `demo-http` system user. **The repo in
`$HOME` is not removed** — delete it manually
(`rm -rf ~/it-operations-ai-lab`) for a total clean-up.

Tested teardown evidence: `docs/evidence/E09-teardown-uninstall.txt`.

## VM level — in VMware Workstation

1. **Roll back to the last healthy state:** *VM → Snapshot Manager →
   `02-lab-ready` → Revert*. All changes after the snapshot are gone.
2. **Delete the VM entirely:** make sure the VM is off → right-click the VM →
   *Remove from Virtual Machine List* → delete the VM disk folder from the
   host disk (usually under Documents/Virtual Machines).
3. Snapshots and VM disks are never touched by repo scripts — all VM-level
   rollback is manual via the hypervisor.

## Windows host

- Delete the repo folder on the host (if a copy exists).
- Uninstall VMware Workstation only if you really want to stop — the
  host-only/NAT VMnets can stay (harmless) or be reset via *Virtual Network
  Editor → Restore Default*.

## Verified teardown checklist

| Action | Status |
|---|---|
| uninstall_demo_service.sh in the sandbox | tested (E09) |
| uninstall_demo_service.sh on your VM | requires manual verification |
| snapshot revert | requires manual verification |
| VM + disk deletion | requires manual verification |
