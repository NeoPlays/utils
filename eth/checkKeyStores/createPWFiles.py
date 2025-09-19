from pathlib import Path
import argparse

def create_pw_file(keystores_path: Path, password: str) -> Path:
    """
    Creates a password file for each keystore file in given path.
    The password file will have the same name as the keystore file with a .txt extension.
    """
    if not keystores_path.is_dir():
        raise NotADirectoryError(f"Keystore directory not found: {keystores_path}")

    for p in sorted(keystores_path.glob("*.json")):
        if not p.is_file():
            continue
        pw_file = p.with_suffix('.txt')
        try:
            with pw_file.open("w", encoding="utf-8") as f:
                f.write(password)
            print(f"Created password file: {pw_file}")
        except Exception as e:
            print(f"Error creating password file for {p}: {e}")
    return keystores_path

def main():
    ap = argparse.ArgumentParser(description="Takes directory of keystore files and creates password files")
    ap.add_argument("keystores_dir", type=Path, help="Directory containing keystore files")
    ap.add_argument("password", type=str, help="Password to use for all keystore files")
    args = ap.parse_args()

    create_pw_file(args.keystores_dir, args.password)
    print("Password files created successfully.")

main()