"""Extract variant-level germline snapshots from verified ClinVar TSV releases."""

import csv
import gzip
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass
class Record:
    values: set[str] = field(default_factory=set)
    review_statuses: set[str] = field(default_factory=set)
    genes: set[str] = field(default_factory=set)
    lines: list[int] = field(default_factory=list)

    @property
    def unresolved(self) -> bool:
        return len(self.values) != 1 or len(self.review_statuses) != 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def extract(path: Path, release: dict, selected_genes: frozenset[str] = frozenset({"BRCA1"})) -> dict[str, Record]:
    if sha256(path) != release['sha256']:
        raise ValueError(f'Checksum mismatch: {path}')
    records: dict[str, Record] = {}
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as stream:
        headers = stream.readline().rstrip('\r\n').split('\t')
        if headers != release['headers']:
            raise ValueError(f'Unexpected headers: {path}')
        required = {'VariationID', 'GeneSymbol', 'ClinicalSignificance', 'ReviewStatus'}
        if not required <= set(headers):
            raise ValueError(f'Missing required columns: {path}')
        for line, raw in enumerate(stream, start=2):
            # Cheap prefilter; exact gene-token membership is still checked below.
            if not any(gene in raw for gene in selected_genes):
                continue
            values = next(csv.reader([raw], delimiter='\t'))
            if len(values) != len(headers):
                raise ValueError(f'Malformed TSV row: {path}:{line}')
            row = dict(zip(headers, values))
            genes = set(re.split(r'[,;]', row['GeneSymbol']))
            if not selected_genes.intersection(genes):
                continue
            identifier = row['VariationID']
            if not identifier.isdecimal() or int(identifier) <= 0:
                raise ValueError(f'Invalid Variation ID: {path}:{line}')
            record = records.setdefault(identifier, Record())
            record.values.add(row['ClinicalSignificance'])
            record.review_statuses.add(row['ReviewStatus'])
            record.genes.update(genes)
            record.lines.append(line)
    if not records:
        raise ValueError(f'No selected-gene records: {path}')
    return records
