"""End-to-end tests for backup and restore functionality."""

import os, time, base64, hashlib, pytest
from typing import Dict
from lium_sdk import Lium

POLL_MAX = 900          # 15 min max for each phase
POLL_MIN = 2.0
POLL_MAX_STEP = 20.0
DEFAULT_TEMPLATE_ID = "1948937e-5049-47ad-8e26-bcf1a4549d70"  # Default PyTorch template

def _backoff(i:int)->float:
    return min(POLL_MIN * (1.6 ** i), POLL_MAX_STEP)

def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _put_file(lium: Lium, pod, path: str, content: bytes):
    b64 = base64.b64encode(content).decode()
    # avoids quoting/newline issues
    lium.exec(pod, f"mkdir -p $(dirname {path}) && echo {b64} | base64 -d > {path}")

def _read_file(lium: Lium, pod, path: str) -> bytes:
    r = lium.exec(pod, f"cat {path} | base64 -w0")
    return base64.b64decode(r["stdout"].strip())

def _wait_until(fn, desc: str, max_s=POLL_MAX):
    t0 = time.time()
    i = 0
    while True:
        ok, data = fn()
        if ok: return data
        dt = _backoff(i); i += 1
        if time.time() - t0 + dt > max_s:
            pytest.fail(f"timeout waiting for {desc}")
        time.sleep(dt)

def _get_best_executor(lium_client, gpu_preference, purpose="use"):
    """Find best available executor from GPU preference list. Pierre wants the best!"""
    for gpu_type in gpu_preference:
        exes = [e for e in lium_client.ls() if gpu_type.strip() in (e.gpu_type or "")]
        if exes:
            exe = sorted(exes, key=lambda x: x.price_per_hour, reverse=True)[0]
            return exe, gpu_type
    pytest.fail(f"Pierre panics: No GPUs available for {purpose} from {gpu_preference}!")

class TestBackupRestoreE2E:
    """Test backup and restore functionality end-to-end."""
    
    @pytest.mark.timeout(3600)  # 60 minutes timeout for the entire test
    @pytest.mark.e2e
    def test_backup_and_restore_cycle(
        self, 
        lium_client: Lium, 
        test_pod_name: str,
        test_files_content: Dict[str, bytes]
    ):
        """Test complete backup and restore cycle.
        
        Pierre's epic journey to protect his baguette classifier from disaster.
        """
        verbose = os.getenv("PIERRE_STORY") == "1"
        created = {"pods": [], "backup_config_id": None}
        
        def log(msg): 
            print(msg) if verbose else None
        
        try:
            # Pierre needs the best GPU money can buy for his revolutionary AI
            log("=== Pierre rents premium GPUs ===")
            gpu_preference = os.getenv("LIUM_GPU_TYPE", "A100,H100,H200").split(",")
            
            # Pierre tries to get his preferred GPU type
            exe, gpu_type = _get_best_executor(lium_client, gpu_preference, "backup")
            log(f"Pierre found {gpu_type}: ${exe.price_per_hour}/hour")
            
            # Pierre creates his first pod with his favorite PyTorch template
            template_id = os.getenv("LIUM_TEMPLATE_ID", DEFAULT_TEMPLATE_ID)
            pod1 = lium_client.up(executor_id=exe.id, pod_name=f"{test_pod_name}-src", template_id=template_id)
            created["pods"].append(pod1)
            
            # Pierre waits patiently for his pod to boot up
            pod1 = lium_client.wait_ready(pod1, timeout=1800)
            assert pod1, "Pierre's pod never started - considers switching careers to farming"
            log(f"Pod {pod1.name} is ready!")
            
            # Pierre uploads his super important research files (definitely not just memes)
            expected = {}
            for path, content in test_files_content.items():
                data = content if isinstance(content, bytes) else content.encode()
                _put_file(lium_client, pod1, path, data)
                roundtrip = _read_file(lium_client, pod1, path)
                assert roundtrip == data, f"Pierre screams: File corruption at {path}!"
                expected[path] = _sha256(data)
            log(f"Uploaded {len(expected)} files with SHA256 verification")
            
            # Pierre learns from Bob's data loss disaster and sets up backups
            cfg = lium_client.backup_config(pod=pod1)
            if cfg and cfg.backup_path != "/root":
                lium_client.backup_delete(cfg.id)  # Pierre needs /root backed up specifically
                cfg = None
            if not cfg:
                cfg = lium_client.backup_create(pod=pod1, path="/root", frequency_hours=1, retention_days=1)
            created["backup_config_id"] = cfg.id
            assert cfg.backup_path == "/root", f"Pierre needs /root backed up, not {cfg.backup_path}!"
            
            # Pierre triggers an immediate backup because he's paranoid
            op = lium_client.backup_now(pod=pod1, name="pierres-paranoid-backup", description="Pierre's baguette classifier")
            assert op.get("success") is True, "Pierre cries: Backup trigger failed!"
            backup_log_id = op["backup_log_id"]
            log(f"Backup started: {backup_log_id}")
            
            # Pierre obsessively checks backup status every few seconds
            def check_backup():
                logs = lium_client.backup_logs(pod1) or []
                for lg in logs:
                    if lg.id == backup_log_id:
                        status = (lg.status or "").upper()
                        if status in {"COMPLETED", "SUCCESS"}:
                            return True, lg
                        if status in {"FAILED", "ERROR"}:
                            pytest.fail(f"Pierre's nightmare: Backup failed! {lg.error_message}")
                        log(f"Backup status: {status}")
                return False, None
            
            _wait_until(check_backup, "backup completion")
            log("Backup completed - Pierre stops biting his nails")
            
            # Pierre gets another premium GPU for restoration testing
            exe2, gpu_type2 = _get_best_executor(lium_client, gpu_preference, "restore")
            log(f"Pierre found another {gpu_type2} for restore: ${exe2.price_per_hour}/hour")
            pod2 = lium_client.up(executor_id=exe2.id, pod_name=f"{test_pod_name}-dst", template_id=template_id)
            created["pods"].append(pod2)
            
            # Pierre waits for the second pod while drinking champagne
            pod2 = lium_client.wait_ready(pod2, timeout=1800)
            assert pod2, "Pierre's restoration pod failed - time to become a baker"
            log(f"Pod {pod2.name} is ready for restore!")
            
            # Pierre clicks restore with trembling fingers
            restore = lium_client.restore(pod=pod2, backup_id=backup_log_id, restore_path="/root")
            op_id = restore.get("operation_id") or restore.get("restore_id")
            log(f"Restore initiated: {op_id or 'async'}")
            
            # Pierre anxiously checks if his files are coming back
            def check_restored():
                ok = 0
                for path, expected_hash in expected.items():
                    try:
                        data = _read_file(lium_client, pod2, path)
                        if _sha256(data) == expected_hash:
                            ok += 1
                            log(f"✓ {path} restored with correct SHA256")
                    except Exception:
                        pass  # File not ready yet
                return (ok == len(expected)), ok
            
            restored_count = _wait_until(check_restored, "files restored")
            assert restored_count == len(expected), f"Pierre devastated: Only {restored_count}/{len(expected)} files restored!"
            log("🎉 All files restored perfectly - Pierre celebrates with croissants!")
            
        finally:
            # Pierre cleans up to save his champagne budget
            log("=== Cleanup ===")
            try:
                if created["backup_config_id"]:
                    lium_client.backup_delete(created["backup_config_id"])
                    log(f"Deleted backup config: {created['backup_config_id']}")
            except Exception as e:
                print(f"Cleanup warning (backup): {e}")
            
            for pod in created["pods"]:
                try:
                    # We know it's a dict from up() return value
                    pod_id = pod['id']
                    pod_name = pod.get('name', pod_id)
                    
                    lium_client.down(pod_id)
                    time.sleep(2)
                    lium_client.rm(pod_id)
                    log(f"Deleted pod: {pod_name}")
                except Exception as e:
                    print(f"Cleanup warning (pod): {e}")
            
            log("✅ Test completed - Pierre's data is safe!")
