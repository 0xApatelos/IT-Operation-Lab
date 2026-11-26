# Teardown & rollback lab

Dua level pembalikan: **level layanan** (di dalam VM) dan **level VM**
(di hypervisor). Gunakan level terkecil yang cukup.

## Level layanan — di VM

```bash
cd ~/it-operations-ai-lab
sudo bash lab/scripts/uninstall_demo_service.sh
bash lab/scripts/baseline.sh    # service check → FAIL "unit tidak ditemukan" (ekspektasi benar)
```

Yang dihapus: unit `/etc/systemd/system/demo-http.service`, aplikasi
`/opt/demo-http/`, user sistem `demo-http`. **Repo di `$HOME` tidak dihapus**
— hapus manual (`rm -rf ~/it-operations-ai-lab`) jika ingin bersih total.

Bukti teardown teruji: `docs/evidence/E09-teardown-uninstall.txt`.

## Level VM — di VMware Workstation

1. **Rollback ke kondisi terakhir sehat:** *VM → Snapshot Manager →
   `02-lab-ready` → Revert*. Semua perubahan setelah snapshot hilang.
2. **Hapus VM penuh:** pastikan VM off → klik kanan VM → *Remove from
   Virtual Machine List* → hapus folder disk VM dari disk host (biasanya di
   folder Documents/Virtual Machines).
3. Snapshot dan disk VM tidak tersentuh oleh skrip repo — semua rollback
   level VM manual via hypervisor.

## Windows host

- Hapus folder repo di host (jika ada salinan).
- Uninstall VMware Workstation hanya jika benar-benar ingin berhenti — VMnet
  host-only/NAT bisa dibiarkan (tidak berbahaya) atau di-reset lewat
  *Virtual Network Editor → Restore Default*.

## Checklist teardown terverifikasi

| Aksi | Status |
|---|---|
| uninstall_demo_service.sh di sandbox | tested (E09) |
| uninstall_demo_service.sh di VM Anda | requires manual verification |
| revert snapshot | requires manual verification |
| penghapusan VM + disk | requires manual verification |
