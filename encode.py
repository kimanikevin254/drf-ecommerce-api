#!/usr/bin/env python3
import sys
import base64

def encode_base64(s: str) -> str:
    """Encode a string to Base64 and return the result."""
    return base64.b64encode(s.encode()).decode()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <string-to-encode>")
        sys.exit(1)

    string_to_encode = sys.argv[1]
    encoded = encode_base64(string_to_encode)
    print(encoded)
