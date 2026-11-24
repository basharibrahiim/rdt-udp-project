import hashlib
import json


def compute_checksum(seq_num: int, pkt_type: str, payload_hex: str) -> str:
    data = f"{seq_num}|{pkt_type}|{payload_hex}".encode("utf-8")
    return hashlib.md5(data).hexdigest()


def make_packet(seq_num: int, pkt_type: str, payload: bytes = b"") -> bytes:
    payload_hex = payload.hex()
    checksum = compute_checksum(seq_num, pkt_type, payload_hex)
    packet_obj = {
        "seq": seq_num,
        "type": pkt_type,
        "payload": payload_hex,
        "checksum": checksum,
    }
    return json.dumps(packet_obj).encode("utf-8")


def parse_packet(raw_data: bytes):
    try:
        packet_obj = json.loads(raw_data.decode("utf-8"))
        seq_num = packet_obj["seq"]
        pkt_type = packet_obj["type"]
        payload_hex = packet_obj["payload"]
        checksum = packet_obj["checksum"]

        expected_checksum = compute_checksum(seq_num, pkt_type, payload_hex)
        is_corrupt = checksum != expected_checksum

        payload = bytes.fromhex(payload_hex)
        return {
            "seq": seq_num,
            "type": pkt_type,
            "payload": payload,
            "corrupt": is_corrupt,
        }
    except Exception:
        return None