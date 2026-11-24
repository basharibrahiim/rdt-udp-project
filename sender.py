import os
import random
import socket
import sys
from rdt_packet import make_packet, parse_packet


def corrupt_bytes(data: bytes) -> bytes:
    if not data:
        return b"\xff"
    arr = bytearray(data)
    idx = random.randint(0, len(arr) - 1)
    bit = 1 << random.randint(0, 7)
    arr[idx] ^= bit
    return bytes(arr)


def run_sender(
    file_path: str,
    receiver_ip: str = "127.0.0.1",
    receiver_port: int = 9001,
    chunk_size: int = 512,
    timeout: float = 1.0,
    loss_prob: float = 0.15,
    corrupt_prob: float = 0.10,
):
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    chunks = [file_bytes[i : i + chunk_size] for i in range(0, len(file_bytes), chunk_size)]
    if not chunks:
        chunks = [b""]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    seq_num = 0
    total_retransmissions = 0
    total_losses = 0

    print(f"[START] Sending '{file_path}' ({len(file_bytes)} bytes, {len(chunks)} packets) to {receiver_ip}:{receiver_port}")
    print(f"[CONFIG] timeout={timeout}s | loss_prob={loss_prob} | corrupt_prob={corrupt_prob}\n")

    for idx, chunk in enumerate(chunks):
        pkt = make_packet(seq_num, "DATA", chunk)
        acked = False

        while not acked:
            if random.random() < loss_prob:
                total_losses += 1
                print(f"[LOSS] Simulated drop for DATA packet seq={seq_num} (chunk {idx + 1}/{len(chunks)})")
            else:
                wire_pkt = pkt
                if random.random() < corrupt_prob:
                    wire_pkt = corrupt_bytes(pkt)
                    print(f"[CORRUPT] Simulated bit flip on DATA packet seq={seq_num}")

                sock.sendto(wire_pkt, (receiver_ip, receiver_port))
                print(f"[SENT] DATA packet seq={seq_num} (chunk {idx + 1}/{len(chunks)}, size={len(chunk)}B)")

            try:
                ack_raw, _ = sock.recvfrom(4096)
                ack_pkt = parse_packet(ack_raw)

                if ack_pkt is None or ack_pkt["corrupt"]:
                    print(f"[CORRUPT ACK] Received corrupted ACK, waiting/retransmitting...")
                    total_retransmissions += 1
                    continue

                if ack_pkt["type"] == "ACK" and ack_pkt["seq"] == seq_num:
                    print(f"[ACK RECV] Valid ACK received for seq={seq_num}")
                    acked = True
                    seq_num = 1 - seq_num
                else:
                    print(f"[MISMATCH ACK] Expected ACK seq={seq_num}, got seq={ack_pkt['seq']}")

            except socket.timeout:
                total_retransmissions += 1
                print(f"[TIMEOUT] No ACK for seq={seq_num} within {timeout}s -> Retransmitting...")

    fin_pkt = make_packet(seq_num, "FIN", b"")
    while True:
        sock.sendto(fin_pkt, (receiver_ip, receiver_port))
        print(f"[SENT] FIN packet seq={seq_num}")
        try:
            ack_raw, _ = sock.recvfrom(4096)
            ack_pkt = parse_packet(ack_raw)
            if ack_pkt and not ack_pkt["corrupt"] and ack_pkt["type"] == "ACK" and ack_pkt["seq"] == seq_num:
                print(f"[ACK RECV] Final ACK received for FIN seq={seq_num}")
                break
        except socket.timeout:
            total_retransmissions += 1
            print(f"[TIMEOUT] FIN ACK timeout -> Retransmitting FIN...")

    sock.close()
    print("\n[DONE] File transfer completed.")
    print(f"[SUMMARY] Total packet losses simulated: {total_losses} | Total retransmissions: {total_retransmissions}")


if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "sample_input.txt"
    t_out = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    l_prob = float(sys.argv[3]) if len(sys.argv) > 3 else 0.15
    c_prob = float(sys.argv[4]) if len(sys.argv) > 4 else 0.10
    run_sender(target_file, timeout=t_out, loss_prob=l_prob, corrupt_prob=c_prob)