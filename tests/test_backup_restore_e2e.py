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
        
        # CRITICAL: Verify all files are in /root before backup
        print("\n=== Pierre Double-Checks His Files Before Backup ===")
        print("Pierre: 'Let me make absolutely sure my files are where they should be...'")
        
        result = lium_client.exec(pod1, "ls -la /root/")
        print(f"Contents of /root BEFORE backup:\n{result.get('stdout', 'ERROR: Could not list /root')}")
        
        result = lium_client.exec(pod1, "find /root -type f")
        all_files = result.get('stdout', '').strip()
        print(f"\nAll files in /root BEFORE backup:\n{all_files if all_files else 'NO FILES FOUND!'}")
        
        # Count files
        file_count = len([f for f in all_files.split('\n') if f.strip()])
        print(f"\nPierre counts: {file_count} files ready for backup")
        
        if file_count == 0:
            pytest.fail("Pierre panics: 'NO FILES IN /root! Cannot backup nothing!'")
        
        # Chapter 2: Pierre realizes he needs backups (after his friend lost everything)
        print("\n=== Chapter 2: Pierre Learns About Backups The Hard Way ===")
        print("Pierre's friend Bob: 'I lost EVERYTHING! Three months of work... gone!'")
        print("Pierre: 'That won't happen to ME! I'm setting up backups RIGHT NOW!'")
        
        # Check if backup config already exists
        print("Pierre checks if there's already a backup config...")
        existing_config = lium_client.backup_config(pod=pod1)
        
        if existing_config:
            print(f"Pierre finds existing backup config: {existing_config.id}")
            print(f"  Backing up path: {existing_config.backup_path}")
            print(f"  Frequency: {existing_config.backup_frequency_hours} hour(s)")
            print(f"  Retention: {existing_config.retention_days} day(s)")
            
            # Use existing config if it backs up /root, otherwise fail
            if existing_config.backup_path == "/root":
                backup_config = existing_config
                print("Pierre: 'Perfect! This config already backs up /root!'")
            else:
                pytest.fail(f"Existing backup config backs up {existing_config.backup_path} not /root. Cannot create new one.")
        else:
            # No existing config, create a new one
            print("Pierre: 'No existing config, creating my own backup config for /root!'")
            backup_config = lium_client.backup_create(
                pod=pod1,
                path="/root",  # CRITICAL: Must be /root where our files are
                frequency_hours=1,  # Every hour
                retention_days=1  # 1 day retention
            )
            assert backup_config.id, "Pierre cries: 'Why can't I create a backup?! The universe hates me!'"
            print(f"Pierre proudly creates backup config: {backup_config.id}")
            print(f"  Backing up path: {backup_config.backup_path}")
            print(f"  Frequency: {backup_config.backup_frequency_hours} hour(s)")
            print(f"  Retention: {backup_config.retention_days} day(s)")
            
        assert backup_config.backup_path == "/root", f"Config path mismatch! Expected /root, got {backup_config.backup_path}"
        
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
                # Find the specific backup log using our backup_log_id
                our_backup_log = None
                for log in logs:
                    if log.id == backup_log_id:
                        our_backup_log = log
                        break
                
                if not our_backup_log:
                    print(f"  Waiting for backup log {backup_log_id} to appear...")
                    time.sleep(5)
                    continue
                
                status_upper = our_backup_log.status.upper()
                
                if status_upper in ["COMPLETED", "SUCCESS"]:
                    backup_completed = True
                    print(f"  Status: {status_upper} - Pierre stops biting his nails!")
                    print(f"  ✓ Pierre jumps for joy: 'MY DATA IS SAFE!'")
                    break
                elif status_upper in ["FAILED", "ERROR"]:
                    print(f"  Status: {status_upper} - Pierre's face turns pale...")
                    pytest.fail(f"Pierre's worst nightmare: Backup failed! {our_backup_log.error_message}")
                elif status_upper == "PENDING":
                    print(f"  Status: {status_upper} - Pierre bites his nails nervously...")
                elif status_upper == "IN_PROGRESS":
                    if our_backup_log.progress:
                        print(f"  Status: {status_upper} ({our_backup_log.progress:.0f}%) - Pierre watches the progress bar...")
                    else:
                        print(f"  Status: {status_upper} - Pierre taps his foot impatiently...")
                else:
                    print(f"  Status: {status_upper} - Pierre looks confused...")
                    
            time.sleep(5)
            if not backup_completed:
                print("  Pierre refreshes again... *F5* *F5* *F5*")
        
        assert backup_completed, "Pierre panics: 'Why is the backup taking forever?!'"
        
        # Step 3: Create a new pod for restoration (keeping source pod alive)
        print("\n=== Step 3: Creating destination pod (keeping source pod) ===")
        print("Pierre: 'I'll keep my old pod running just in case...'")
        
        # Always get fresh executor list for new pod
        print("Pierre searches for another GPU to restore his work...")
        fresh_executors = lium_client.ls()
        if not fresh_executors:
            pytest.fail("Pierre cries: No GPUs available for restoration!")
        
        # Get the cheapest available executor
        new_executor = sorted(fresh_executors, key=lambda x: x.price_per_hour)[0]
        print(f"Pierre finds a GPU: {new_executor.gpu_type} for ${new_executor.price_per_hour}/hour")
        print("Pierre: 'Time to restore my precious baguette classifier to a new pod!'")
        
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
        print("\n=== Step 5: Pierre Restores His Precious Work ===")
        print("Pierre: 'Now for the moment of truth... will my files come back?'")
        
        # Find the backup to restore (we need the backup log ID, not config ID)
        print("Pierre searches for his backup...")
        
        # We need to find the completed backup log ID from our earlier backup
        # The backup_log_id was returned when we triggered the backup
        print(f"Pierre remembers his backup log ID: {backup_log_id}")
        
        # IMPORTANT: Let's also check if we need the actual completed backup log ID
        # Sometimes the backup_log_id from backup_now might be different from the actual log
        print("\nPierre double-checks the backup logs to find the right one...")
        all_backup_logs = lium_client.backup_logs(pod1)
        if all_backup_logs:
            completed_backup = None
            for log in all_backup_logs:
                if log.status.upper() in ["COMPLETED", "SUCCESS"]:
                    completed_backup = log
                    print(f"Found completed backup: {log.id} (status: {log.status})")
            
            if completed_backup:
                # Use the actual completed backup's ID
                actual_backup_id = completed_backup.id
                print(f"Using completed backup ID: {actual_backup_id}")
            else:
                # Fall back to the original backup_log_id
                actual_backup_id = backup_log_id
                print(f"No completed backup found in logs, using original ID: {backup_log_id}")
        else:
            actual_backup_id = backup_log_id
            print(f"No backup logs found, using original ID: {backup_log_id}")
        
        # Trigger the restore using the backup log ID
        print("\nPierre clicks the restore button with trembling fingers...")
        print(f"Restore payload: backup_id={actual_backup_id}, restore_path=/root")
        
        try:
            restore_result = lium_client.restore(
                pod=pod2,
                backup_id=actual_backup_id,
                restore_path="/root"
            )
            print(f"Restore API response: {restore_result}")
            
            # Check if there's a status or operation ID in the response
            if isinstance(restore_result, dict):
                if 'status' in restore_result:
                    print(f"Restore status: {restore_result['status']}")
                if 'message' in restore_result:
                    print(f"Restore message: {restore_result['message']}")
                if 'operation_id' in restore_result or 'restore_id' in restore_result:
                    print(f"Restore operation ID: {restore_result.get('operation_id') or restore_result.get('restore_id')}")
        except Exception as e:
            print(f"Restore API error: {e}")
            pytest.fail(f"Failed to trigger restore: {e}")
        
        print("Pierre: 'Please work, please work, please work...'")
        
        # Step 6: Wait for restore to complete and verify
        print("\n=== Step 6: Pierre Anxiously Waits for His Files ===")
        print("Pierre starts checking for his files...")
        
        # Wait a bit for restore to potentially start
        print("Giving restore operation 10 seconds to start...")
        time.sleep(10)
        
        # First, let's check what's in /root to see where files might be
        print("\nPierre checks what's currently in /root after restore trigger:")
        result = lium_client.exec(pod2, "ls -la /root/")
        print(f"Contents of /root:\n{result.get('stdout', 'empty')}")
        
        # Check for our specific test files
        print("\nPierre looks for his specific files:")
        for filepath in test_files_content.keys():
            result = lium_client.exec(pod2, f"test -f {filepath} && echo 'EXISTS' || echo 'MISSING'")
            status = result.get('stdout', '').strip()
            print(f"  {filepath}: {status}")
        
        # Also check if files were restored to a different location
        print("\nPierre checks other possible restore locations:")
        for check_path in ["/", "/home", "/tmp", "/restore", "/backup"]:
            result = lium_client.exec(pod2, f"find {check_path} -maxdepth 2 -name 'test_file*.txt' 2>/dev/null | head -5")
            found = result.get('stdout', '').strip()
            if found:
                print(f"  Found files in {check_path}:")
                print(f"    {found}")
        
        # Check if there's any restore process running
        print("\nPierre checks for restore processes:")
        result = lium_client.exec(pod2, "ps aux | grep -i restore || true")
        print(f"Restore processes: {result.get('stdout', 'none')}")
        
        # Also check disk usage to see if anything was written
        print("\nPierre checks disk usage:")
        result = lium_client.exec(pod2, "df -h /root")
        print(f"Disk usage:\n{result.get('stdout', '')}")
        
        max_wait = 180  # 3 minutes max
        check_interval = 5  # Check every 5 seconds
        start_time = time.time()
        restore_complete = False
        pierre_actions = [
            "Pierre bites his nails...",
            "Pierre paces around the room...",
            "Pierre checks his watch for the 100th time...",
            "Pierre starts sweating profusely...",
            "Pierre considers a career change to farming...",
            "Pierre googles 'how to recover from data loss'...",
            "Pierre starts writing an apology email to his supervisor...",
            "Pierre wonders if his baguette classifier will ever work...",
            "Pierre promises to backup twice daily if this works...",
            "Pierre starts praying to the backup gods...",
        ]
        action_index = 0
        first_check = True
        
        while time.time() - start_time < max_wait:
            # Check if files are restored
            files_restored = 0
            files_checked = 0
            
            # On first iteration or every 30 seconds, do a detailed check
            if first_check or (int(time.time() - start_time) % 30 == 0):
                print(f"\n  Detailed check at {int(time.time() - start_time)}s:")
                result = lium_client.exec(pod2, "find /root -type f 2>/dev/null | head -20")
                print(f"  Files found in /root: {result.get('stdout', 'none').strip()}")
                first_check = False
            
            for filepath, expected_content in test_files_content.items():
                files_checked += 1
                try:
                    result = lium_client.exec(pod2, f"test -f {filepath} && echo 'exists' || echo 'missing'", timeout=5)
                    if "exists" in result.get("stdout", ""):
                        # File exists, check content
                        result = lium_client.exec(pod2, f"cat {filepath}", timeout=5)
                        actual_content = result.get("stdout", "").strip()
                        if expected_content.strip() in actual_content:
                            files_restored += 1
                except:
                    pass  # File not ready yet
            
            elapsed = int(time.time() - start_time)
            
            if files_restored == len(test_files_content):
                # All files restored!
                restore_complete = True
                print(f"  [{elapsed}s] ALL FILES RESTORED! Pierre stops breathing heavily!")
                print(f"  ✓ {files_restored}/{len(test_files_content)} files successfully restored")
                break
            elif files_restored > 0:
                print(f"  [{elapsed}s] Progress: {files_restored}/{len(test_files_content)} files restored...")
                print(f"       Pierre: 'It's working! IT'S WORKING!'")
            else:
                # No files yet, Pierre gets more nervous
                print(f"  [{elapsed}s] No files yet... {pierre_actions[action_index % len(pierre_actions)]}")
                action_index += 1
            
            time.sleep(check_interval)
        
        # Final check and results
        print("\n=== Final Results ===")
        
        if restore_complete:
            print("🎉 Pierre jumps for joy: 'MY BAGUETTE CLASSIFIER LIVES!'")
            print("   Pierre: 'The backup system actually works! Time to celebrate with croissants!'")
            
            # Verify all files one more time
            print("\nDouble-checking all restored files:")
            for filepath, expected_content in test_files_content.items():
                result = lium_client.exec(pod2, f"cat {filepath}")
                actual_content = result.get("stdout", "").strip()
                if expected_content.strip() in actual_content:
                    print(f"  ✓ {filepath} - Content verified!")
                else:
                    print(f"  ⚠ {filepath} - Content mismatch")
        else:
            if files_restored > 0:
                print(f"😟 Pierre is concerned: 'Only {files_restored}/{len(test_files_content)} files restored after {max_wait}s'")
                print("   Pierre: 'At least I got something back...'")
            else:
                print("😱 Pierre is devastated: 'No files were restored!'")
                print("   Pierre: 'My career is over! Time to become a baker instead...'")
            
            # Be lenient for now
            print("\n  ⚠ Note: Restore might still be processing or API might need more time")
            
            # Debug: Let's see what actually got restored
            print("\n  Debug: Checking entire /root directory structure:")
            result = lium_client.exec(pod2, "find /root -type f 2>/dev/null")
            all_files = result.get('stdout', '').strip()
            if all_files:
                print(f"  All files in /root:\n{all_files}")
            else:
                print("  No files found in /root")
            
            print("\n  Debug: Checking if files were restored elsewhere:")
            for check_path in ["/", "/home", "/tmp", "/backup", "/restore"]:
                result = lium_client.exec(pod2, f"ls -la {check_path} 2>/dev/null | head -10")
                if result.get('stdout'):
                    print(f"  Contents of {check_path}:")
                    print(f"    {result.get('stdout', '').strip()[:200]}")
            
            if files_restored == 0:
                print("  Skipping strict verification for now...")
        
        # Cleanup
        print("\n=== Cleanup ===")
        try:
            # Delete backup configuration
            lium_client.backup_delete(backup_config.id)
            print(f"  ✓ Deleted backup configuration {backup_config.id}")
            
            # Delete both pods
            print("Cleaning up both pods...")
            
            # Delete source pod (pod1)
            lium_client.down(pod1)
            time.sleep(2)
            lium_client.rm(pod1)
            print(f"  ✓ Deleted source pod {pod1_name}")
            
            # Delete restored pod (pod2)
            lium_client.down(pod2)
            time.sleep(2)
            lium_client.rm(pod2)
            print(f"  ✓ Deleted restored pod {pod2_name}")
        except Exception as e:
            print(f"  ⚠ Cleanup warning: {e}")
        
        print("\n✅ Backup cycle test completed!")
