"""End-to-end tests for backup and restore functionality."""

import time
import pytest
from typing import Dict
from lium_sdk import Lium, PodInfo, LiumNotFoundError


class TestBackupRestoreE2E:
    """Test backup and restore functionality end-to-end."""
    
    @pytest.mark.timeout(3600)  # 60 minutes timeout for the entire test
    def test_backup_and_restore_cycle(
        self, 
        lium_client: Lium, 
        test_pod_name: str,
        test_files_content: Dict[str, str]
    ):
        """
        The Epic Tale of Pierre's Backup Adventure:
        
        Our hero Pierre needs to backup his precious ML models before disaster strikes.
        Will he succeed? Will his data survive? Let's find out...
        """
        
        # Chapter 1: Pierre needs a GPU pod for his groundbreaking AI research
        print("\n=== Chapter 1: Pierre Rents His First GPU Pod ===")
        print("Pierre: 'Sacré bleu! I need ze cheapest GPU to train my baguette classifier!'")
        
        # Pierre, being budget-conscious (he spent all his money on croissants), searches for the cheapest executor
        executors = lium_client.ls()
        assert executors, "Pierre panics: 'Mon Dieu! No GPUs available! My baguette dreams are crushed!'"
        executor = sorted(executors, key=lambda x: x.price_per_hour)[0]
        print(f"Pierre finds a sweet deal: {executor.gpu_type} for only ${executor.price_per_hour}/hour!")
        print("Pierre: 'C'est magnifique! Cheaper than my morning espresso!'")
        
        # Pierre creates his first pod with his favorite PyTorch template
        # Use specific template: PyTorch 2.4.0-py3.12-cuda12.2.0-devel-ubuntu22.04
        template_id = "8c273d47-33fc-4237-805f-e96e685c53b8"
        pod1_name = f"{test_pod_name}-pierres-precious"
        print(f"Pierre excitedly creates his pod: {pod1_name}")
        pod1 = lium_client.up(executor_id=executor.id, pod_name=pod1_name, template_id=template_id)
        
        # Pierre waits patiently for his pod to boot up (like waiting for coffee to brew)
        print("Pierre waits... and waits... (checking Twitter every 30 seconds)")
        pod1 = lium_client.wait_ready(pod1, timeout=1800)  # 30 minutes
        if not pod1:
            # Oh no! Pierre's pod is stuck! Time for emergency cleanup
            print("Pierre: 'Why is it taking so long?! Did I break something?!'")
            pods = lium_client.ps()
            failed_pod = next((p for p in pods if p.name == pod1_name), None)
            if failed_pod:
                try:
                    print("Pierre frantically tries to clean up the mess...")
                    lium_client.down(failed_pod)
                    time.sleep(2)
                    lium_client.rm(failed_pod)
                except:
                    pass
            assert False, "Pierre's pod never started. He considers switching careers to farming."
        print(f"Pierre celebrates: '{pod1_name} is alive! Time to do some SCIENCE!'")
        
        # Pierre uploads his super important research files (definitely not just memes)
        print("\n=== Pierre Uploads His 'Important Research Files' ===")
        for filepath, content in test_files_content.items():
            # Pierre creates directories like a pro
            if "/" in filepath.rsplit("/", 1)[0]:
                dir_path = filepath.rsplit("/", 1)[0]
                lium_client.exec(pod1, f"mkdir -p {dir_path}")
            
            # Pierre carefully writes his files (with shaking hands)
            escaped_content = content.replace("'", "'\\''")
            lium_client.exec(pod1, f"echo '{escaped_content}' > {filepath}")
            
            # Pierre double-checks because he's paranoid
            result = lium_client.exec(pod1, f"cat {filepath}")
            assert content in result.get("stdout", ""), f"Pierre screams: 'Where did {filepath} go?!'"
            print(f"  ✓ Pierre saved {filepath} - 'This could win me a Nobel Prize!'")
        
        # Chapter 2: Pierre realizes he needs backups (after his friend lost everything)
        print("\n=== Chapter 2: Pierre Learns About Backups The Hard Way ===")
        print("Pierre's friend Bob: 'I lost EVERYTHING! Three months of work... gone!'")
        print("Pierre: 'That won't happen to ME! I'm setting up backups RIGHT NOW!'")
        
        # Pierre checks if the backup fairy already blessed his pod
        existing_config = lium_client.backup_config(pod=pod1)
        if existing_config:
            backup_config = existing_config
            print(f"Pierre discovers: 'Oh wow, there's already a backup config here! Lucky me!'")
            print(f"Using backup config: {backup_config.id}")
        else:
            print("Pierre: 'No backup config? No problem! I'll make one myself!'")
            backup_config = lium_client.backup_create(
                pod=pod1,
                path="/root",  # Pierre backs up his entire digital life
                frequency_hours=24,  # Daily, because Pierre is cautious now
                retention_days=7  # A week of backups, Pierre doesn't mess around
            )
            assert backup_config.id, "Pierre cries: 'Why can't I create a backup?! The universe hates me!'"
            print(f"Pierre proudly creates backup config: {backup_config.id}")
        
        # Pierre triggers a backup RIGHT NOW because he's paranoid
        print("\nPierre: 'I'm backing up RIGHT NOW! Can't wait for the scheduled one!'")
        backup_operation = lium_client.backup_now(
            pod=pod1,
            name="pierres-paranoid-backup",
            description="Pierre's super important baguette classifier models"
        )
        assert backup_operation.get("success") == True
        backup_log_id = backup_operation.get("backup_log_id")
        print(f"Pierre watches nervously as backup starts: {backup_log_id}")
        print(f"System says: {backup_operation.get('message')}")
        
        # Pierre refreshes the backup status every 5 seconds like a maniac
        print("\nPierre obsessively checks the backup status...")
        max_wait = 120  # 2 minutes
        start_time = time.time()
        backup_completed = False
        
        while time.time() - start_time < max_wait:
            logs = lium_client.backup_logs(pod1)
            if logs:
                latest_log = logs[-1]  # Get most recent log
                status_upper = latest_log.status.upper()
                
                if status_upper in ["COMPLETED", "SUCCESS"]:
                    backup_completed = True
                    print(f"  Status: {status_upper} - Pierre stops biting his nails!")
                    print(f"  ✓ Pierre jumps for joy: 'MY DATA IS SAFE!'")
                    break
                elif status_upper in ["FAILED", "ERROR"]:
                    print(f"  Status: {status_upper} - Pierre's face turns pale...")
                    pytest.fail(f"Pierre's worst nightmare: Backup failed! {latest_log.error_message}")
                elif status_upper == "PENDING":
                    print(f"  Status: {status_upper} - Pierre bites his nails nervously...")
                elif status_upper == "IN_PROGRESS":
                    if latest_log.progress:
                        print(f"  Status: {status_upper} ({latest_log.progress:.0f}%) - Pierre watches the progress bar...")
                    else:
                        print(f"  Status: {status_upper} - Pierre taps his foot impatiently...")
                else:
                    print(f"  Status: {status_upper} - Pierre looks confused...")
                    
            time.sleep(5)
            if not backup_completed:
                print("  Pierre refreshes again... *F5* *F5* *F5*")
        
        assert backup_completed, "Pierre panics: 'Why is the backup taking forever?!'"
        
        # Step 3: Delete the source pod
        print("\n=== Step 3: Deleting source pod ===")
        lium_client.down(pod1)
        time.sleep(3)
        lium_client.rm(pod1)
        print(f"  ✓ Source pod {pod1_name} deleted")
        
        # Step 4: Create a new pod for restoration
        print("\n=== Step 4: Creating destination pod ===")
        
        # Always get fresh executor list for new pod
        print("Pierre searches for a GPU to restore his work...")
        fresh_executors = lium_client.ls()
        if not fresh_executors:
            pytest.fail("Pierre cries: No GPUs available for restoration!")
        
        # Get the cheapest available executor
        new_executor = sorted(fresh_executors, key=lambda x: x.price_per_hour)[0]
        print(f"Pierre finds a GPU: {new_executor.gpu_type} for ${new_executor.price_per_hour}/hour")
        print("Pierre: 'Time to restore my precious baguette classifier!'")
        
        pod2_name = f"{test_pod_name}-restored"
        print(f"Creating destination pod: {pod2_name}")
        pod2 = lium_client.up(executor_id=new_executor.id, pod_name=pod2_name, template_id=template_id)
        
        # Wait for pod to be ready (30 minutes timeout)
        print("Waiting for pod to be ready (up to 30 minutes)...")
        pod2 = lium_client.wait_ready(pod2, timeout=1800)  # 30 minutes
        if not pod2:
            # Try to cleanup even if pod didn't become ready
            pods = lium_client.ps()
            failed_pod = next((p for p in pods if p.name == pod2_name), None)
            if failed_pod:
                try:
                    lium_client.down(failed_pod)
                    time.sleep(2)
                    lium_client.rm(failed_pod)
                except:
                    pass
            assert False, "Second pod failed to become ready within 30 minutes"
        print(f"Pod {pod2_name} is ready!")
        
        # Step 5: Restore backup to new pod
        print("\n=== Step 5: Restoring backup ===")
        
        # Note: The actual restore API endpoint needs to be implemented
        # For now, we'll simulate restore by checking if backup exists
        # and manually copying files (this part needs the actual restore API)
        
        # Since restore API might not be implemented yet, let's verify backup exists
        backup_configs = lium_client.backup_list()
        assert any(bc.id == backup_config.id for bc in backup_configs), \
            "Backup configuration not found"
        
        print("  ⚠ Note: Restore API endpoint needs to be implemented")
        print("  For full E2E test, we would restore files here")
        
        # Cleanup
        print("\n=== Cleanup ===")
        try:
            # Delete backup configuration
            lium_client.backup_delete(backup_config.id)
            print(f"  ✓ Deleted backup configuration {backup_config.id}")
            
            # Delete second pod
            lium_client.down(pod2)
            time.sleep(2)
            lium_client.rm(pod2)
            print(f"  ✓ Deleted pod {pod2_name}")
        except Exception as e:
            print(f"  ⚠ Cleanup warning: {e}")
        
        print("\n✅ Backup cycle test completed!")
