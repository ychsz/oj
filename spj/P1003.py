import sys

def main():
    output_path = sys.argv[2]
    with open(output_path) as f:
        content = f.read().strip()
    parts = content.split()
    if len(parts) != 2:
        sys.exit(1)
    try:
        a = int(parts[0])
        b = int(parts[1])
    except ValueError:
        sys.exit(1)
    if a > 0 and b > 0 and a + b == 10:
        sys.exit(0)
    sys.exit(1)

main()