"""Download the two pinned public releases; keep raw data outside Git."""

import argparse
import json
from pathlib import Path
from urllib.request import urlopen

from brca_review.ingestion.tsv import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('docs/releases.json'))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    directory = Path('data')
    directory.mkdir(exist_ok=True)
    for release in manifest['releases']:
        path = directory / release['filename']
        if path.exists() and sha256(path) == release['sha256']:
            print(f'Already verified: {path.name}')
            continue
        temporary = path.with_suffix(path.suffix + '.part')
        try:
            with urlopen(release['url'], timeout=60) as response, temporary.open('wb') as output:
                for block in iter(lambda: response.read(1024 * 1024), b''):
                    output.write(block)
            if sha256(temporary) != release['sha256']:
                raise ValueError(f'Checksum mismatch: {path.name}')
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        print(f'Downloaded and verified: {path.name}')


if __name__ == '__main__':
    main()
