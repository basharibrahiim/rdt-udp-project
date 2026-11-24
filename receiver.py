import socket
import sys
from rdt_packet import make_packet, parse_packet


def run_receiver(
    listen_ip: str = "0.0.0.0",
    listen_port: int = 9001,
    output_file: str = "received_output.txt",
):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((listen_ip, listen_port))

    expected_seq = 0
    received_chunks = []
    last_valid_seq = None

    print(f"[LISTENING] Receiver started on {listen_ip}:{listen_port}")
    print(f"[OUTPUT] Reconstructed file will be saved to '{output_file}'\n")

    while True:
        raw_data, addr = sock.recvfrom(8192)
        pkt = parse_packet(raw_data)

        if pkt is None or pkt["corrupt"]:
            print(f"[CORRUPT PKT] Corrupted packet received from {addr} -> Discarded (no new ACK)")
            if last_valid_seq is not None:
                dup_ack = make_packet(last_valid_seq, "ACK", b"")
                sock.sendto(dup_ack, addr)
                print(f"[ACK SENT] Re-sent duplicate ACK for seq={last_valid_seq}")
            continue

        pkt_type = pkt["type"]
        seq = pkt["seq"]

        if pkt_type == "DATA":
            if seq == expected_seq:
                print(f"[RECV] Valid DATA packet seq={seq} ({len(pkt['payload'])}B) from {addr}")
                received_chunks.append(pkt["payload"])
                ack_pkt = make_packet(seq, "ACK", b"")
                sock.sendto(ack_pkt, addr)
                print(f"[ACK SENT] ACK sent for seq={seq}")
                last_valid_seq = seq
                expected_seq = 1 - expected_seq
            else:
                print(f"[DUPLICATE] Expected seq={expected_seq}, got seq={seq} -> Dropping payload & re-sending ACK")
                if last_valid_seq is not None:
                    ack_pkt = make_packet(last_valid_seq, "ACK", b"")
                    sock.sendto(ack_pkt, addr)
                    print(f"[ACK SENT] Duplicate ACK sent for seq={last_valid_seq}")

        elif pkt_type == "FIN":
            print(f"[FIN RECV] End-of-transfer signal received (seq={seq}) from {addr}")
            ack_pkt = make_packet(seq, "ACK", b"")
            sock.sendto(ack_pkt, addr)
            print(f"[ACK SENT] Final ACK sent for FIN seq={seq}")
            break

    with open(output_file, "wb") as out:
        for part in received_chunks:
            out.write(part)

    sock.close()
    print(f"\n[SAVED] File reconstructed successfully into '{output_file}' ({sum(len(c) for c in received_chunks)} bytes).")


if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else "received_output.txt"
    run_receiver(output_file=out_path)