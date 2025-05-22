MACHINE_PRICES = {
    # Latest Gen NVIDIA GPUs (Averaged if applicable)
    "NVIDIA B200": 12.99 / 2,
    "NVIDIA H200": 9.79 / 2,
    "NVIDIA H100 80GB HBM3": 6.50 / 2,
    "NVIDIA H100 NVL": 5.20 / 2,
    "NVIDIA H100 PCIe": 5.00 / 2,
    "NVIDIA H800 80GB HBM3": 2.61 / 2,
    "NVIDIA H800 NVL": 2.09 / 2,
    "NVIDIA H800 PCIe": 2.01 / 2,
    "NVIDIA GeForce RTX 5090": 0.98 / 2,
    "NVIDIA GeForce RTX 4090": 0.38 / 2,
    "NVIDIA GeForce RTX 4090 D": 0.26 / 2,
    "NVIDIA RTX 4000 Ada Generation": 0.38 / 2,
    "NVIDIA RTX 6000 Ada Generation": 1.03 / 2,
    "NVIDIA L4": 0.43 / 2,
    "NVIDIA L40S": 1.03 / 2,
    "NVIDIA L40": 0.99 / 2,
    "NVIDIA RTX 2000 Ada Generation": 0.28 / 2,
    # Previous Gen NVIDIA GPUs (Averaged if applicable)
    "NVIDIA A100 80GB PCIe": 1.64 / 2,
    "NVIDIA A100-SXM4-80GB": 1.89 / 2,
    "NVIDIA RTX A6000": 0.87 / 2,
    "NVIDIA RTX A5000": 0.43 / 2,
    "NVIDIA RTX A4500": 0.35 / 2,
    "NVIDIA RTX A4000": 0.32 / 2,
    "NVIDIA A40": 0.39 / 2,
    "NVIDIA GeForce RTX 3090": 0.21 / 2,
}


def get_corrected_machine_names(machines: list[str]) -> list[str]:
    """
    Corrects the machine names to match the ones in the MACHINE_PRICES dictionary.
    """
    corrected_machines = []
    for machine in machines:
        for key in MACHINE_PRICES.keys():
            if machine.lower() in key.lower():
                corrected_machines.append(key)
                break
    return corrected_machines
