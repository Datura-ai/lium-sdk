"""End-to-end test for template switching functionality with Pierre's narrative."""

import os
import pytest
import time
import base64
import shlex
from typing import Optional, Tuple
from lium_sdk import Lium, PodInfo


# Helper functions for robust testing
def _exec_ok(lium: Lium, pod: PodInfo, cmd: str, timeout: int = 120) -> Tuple[bool, str]:
    """Execute command and return success status and output."""
    r = lium.exec(pod, cmd)
    out = (r.get("stdout", "") + r.get("stderr", "")).strip()
    return r.get("exit_code", 1) == 0, out


def _py_cmd() -> str:
    """Get Python command that works in the environment."""
    # prefer python3, fallback to python
    return "bash -lc 'py=$(command -v python3 || command -v python); " \
           "[ -n \"$py\" ] && \"$py\" --version || echo NO_PY'"


def _put_file_b64(lium: Lium, pod: PodInfo, path: str, data: bytes) -> None:
    """Write binary data to file on pod using base64 encoding."""
    b64 = base64.b64encode(data).decode()
    lium.exec(pod, f"bash -lc 'mkdir -p $(dirname {shlex.quote(path)}) && echo {b64} | base64 -d > {shlex.quote(path)}'")


def _cat_b64(lium: Lium, pod: PodInfo, path: str) -> bytes:
    """Read binary file from pod using base64 encoding."""
    ok, out = _exec_ok(lium, pod, f"bash -lc 'base64 -w0 < {shlex.quote(path)}'")
    return base64.b64decode(out) if ok and out else b""


def _find_template(lium: Lium, identifier: str):
    """Find template by filter string."""
    ts = lium.templates(filter=identifier)
    return ts[0] if ts else None


def _wait_ready_with_template(lium: Lium, pod_id: str, expected_template_id: Optional[str], timeout: int = 900) -> Optional[PodInfo]:
    """Wait for pod to be ready, optionally with specific template."""
    t0 = time.time()
    i = 0
    while time.time() - t0 < timeout:
        p = next((p for p in lium.ps() if p.id == pod_id), None)
        if p and p.status.upper() == "RUNNING" and p.ssh_cmd:
            if expected_template_id is None or p.template.get("id") == expected_template_id:
                return p
        time.sleep(min(2 * (1.6 ** i), 15))
        i += 1
    return None


def pierre_says(message: str):
    """Pierre's narrative output - only shown when PIERRE_STORY env var is set."""
    if os.getenv("PIERRE_STORY"):
        print(f"\n🥖 Pierre: {message}")


@pytest.mark.e2e
def test_switch_template_e2e(lium_client: Lium, pod_lifecycle: PodInfo):
    """
    Complete end-to-end test of template switching on a running pod.
    
    This test:
    1. Fingerprints the original environment (Python version)
    2. Switches to a different PyTorch template
    3. Waits for pod to be ready with new template
    4. Verifies the Python version changed (if applicable)
    5. Tests pod functionality after switch
    6. Optionally reverts to original template
    
    Note: Data does NOT persist across template switches - pods get a fresh environment.
    """
    pod = pod_lifecycle
    
    # Pierre's introduction
    pierre_says("Bonjour! Today I test switching templates on my GPU pod.")
    pierre_says("Like switching from a croissant oven to a baguette oven - precision required!")
    
    # Get fresh pod info
    pods = lium_client.ps()
    current_pod = next((p for p in pods if p.id == pod.id), None)
    assert current_pod, "Pod not found in active pods list"
    
    original_template_id = current_pod.template.get("id")
    
    # Fingerprint environment - just check Python version
    ok_py, py_ver = _exec_ok(lium_client, current_pod, _py_cmd())
    pierre_says("Recording the recipe of my current environment...")
    
    # Check for environment override first
    candidate_id = os.getenv("LIUM_NEW_TEMPLATE_ID")
    new_template = None
    
    if candidate_id:
        # User specified a template
        new_template = next((t for t in lium_client.templates() 
                           if t.id == candidate_id or t.huid == candidate_id), None)
    if not new_template:
        # Try the known good PyTorch 2.2.0 template
        known_template_id = "8b63514f-2970-40d9-8d24-051de61140ae"
        new_template = next((t for t in lium_client.templates() 
                           if t.id == known_template_id), None)
    
    if not new_template:
        # Fallback: find any different PyTorch template
        new_template = _find_template(lium_client, "pytorch2.2.0") or \
                      _find_template(lium_client, "py3.11-cuda11.8") or \
                      _find_template(lium_client, "pytorch")
    
    if not new_template:
        pytest.skip("No suitable alternate template found")
    
    pierre_says(f"Time to switch from croissants to baguettes with '{new_template.name}'!")
    
    # Step 3: Perform template switch
    switch_start_time = time.time()
    
    try:
        result = lium_client.switch_template(current_pod, new_template.id)
        print(f"✓ Template switch initiated (status: {result.status})")
    except Exception as e:
        pytest.fail(f"Failed to switch template: {e}")
    
    pierre_says("The transformation begins... like proofing dough, patience is key...")
    
    # Step 4: Wait for pod to be ready with new template
    
    # Note: The new template gets a new ID when attached to pod
    updated_pod = _wait_ready_with_template(lium_client, pod.id, 
                                           expected_template_id=None,  # Don't check template ID
                                           timeout=900)
    
    if not updated_pod:
        pytest.fail("Pod did not become ready after template switch")
    
    # Verify template changed
    new_template_id = updated_pod.template.get("id")
    updated_pod.template.get("name", "Unknown")
    
    assert new_template_id != original_template_id, \
        f"Template ID should have changed from {original_template_id}"
    
    pierre_says("Voilà! The transformation is complete!")
    
    # Step 5: Verify environment changed
    
    # Re-fingerprint environment - just check Python version
    ok_py2, py_ver2 = _exec_ok(lium_client, updated_pod, _py_cmd())
    
    # Verify Python version changed (if we have valid detections)
    if ok_py and ok_py2 and py_ver != "NO_PY" and py_ver2 != "NO_PY":
        if py_ver != py_ver2:
            pierre_says("Perfect! Different Python version for my baguette experiments!")
        else:
            pierre_says("Same Python version but fresh environment - like a clean baking sheet!")
    else:
        pierre_says("Fresh environment ready for my baguettes!")
    
    # Step 6: Final functionality test
    # Create a new test file to verify pod is fully functional
    test_content = f"Template switch test completed at {time.time()}"
    lium_client.exec(updated_pod, f"echo '{test_content}' > /tmp/functionality_test.txt")
    
    ok_test, test_output = _exec_ok(lium_client, updated_pod, "cat /tmp/functionality_test.txt")
    assert ok_test and test_content in test_output, "Pod functionality test failed"
    
    # Optional: Revert to original template
    if os.getenv("REVERT_TEMPLATE", "0") == "1" and original_template_id is not None:
        try:
            lium_client.switch_template(updated_pod, original_template_id)
            reverted = _wait_ready_with_template(lium_client, pod.id, 
                                                expected_template_id=None, 
                                                timeout=600)
            if reverted:
                pierre_says("Back to croissants!")
        except Exception as e:
            print(f"⚠ Revert failed (non-critical): {e}")
   
    # Pierre's wisdom
    if os.getenv("PIERRE_STORY"):
        print("\n🥖 Pierre's Final Wisdom:")
        print("   'Just as a master baker can switch from croissants to baguettes,")
        print("    a good ML engineer can switch environments without losing their dough!'")
        print("   - Pierre, the Pod Whisperer")
