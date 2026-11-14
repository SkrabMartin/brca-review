"""Condition-preserving SCV snapshots from pinned submission_summary TSV files."""
import csv
import gzip
from pathlib import Path
import re

from brca_review.ingestion.tsv import sha256

FIELDS = {'variation_id': '#VariationID', 'classification': 'ClinicalSignificance',
          'last_evaluated': 'DateLastEvaluated', 'submitted_condition': 'SubmittedPhenotypeInfo',
          'reported_condition': 'ReportedPhenotypeInfo', 'review_status': 'ReviewStatus',
          'submitter_name': 'Submitter', 'scv': 'SCV', 'submitted_gene': 'SubmittedGeneSymbol',
          'collection_method': 'CollectionMethod', 'origin_counts': 'OriginCounts',
          'somatic_clinical_impact': 'SomaticClinicalImpact', 'oncogenicity': 'Oncogenicity'}


def extract_submissions(path: Path, release: dict, variant_ids: set[str]) -> dict:
    if sha256(path) != release['sha256']:
        raise ValueError(f'Checksum mismatch: {path}')
    records: dict = {}
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as stream:
        headers = None
        for line, raw in enumerate(stream, 1):
            if headers is None:
                if raw.startswith('#VariationID\t'):
                    headers = raw.rstrip('\r\n').split('\t')
                    if headers != release['headers'] or not set(FIELDS.values()) <= set(headers):
                        raise ValueError(f'Unsupported submission headers: {path}')
                continue
            # Membership comes from aggregate gene annotations, not optional submitted gene.
            if raw.split('\t', 1)[0] not in variant_ids:
                continue
            values = next(csv.reader([raw], delimiter='\t'))
            if len(values) != len(headers):
                raise ValueError(f'Malformed submission: {path}:{line}')
            row = dict(zip(headers, values))
            item = {key: row[value] for key, value in FIELDS.items()}
            match = re.fullmatch(r'(SCV[0-9]+)\.([0-9]+)', item['scv'])
            if not match:
                raise ValueError(f'Unversioned/invalid SCV: {path}:{line}')
            base, version = match.groups()
            item['scv_base'] = base
            item['scv_version'] = int(version)
            item['classification_type'] = ('germline' if item['classification'] not in {'', '-', 'na'} else
                'somatic' if any(item[k] not in {'', '-', 'na'} for k in ('somatic_clinical_impact', 'oncogenicity')) else 'unclassified')
            # Raw conditions stay authoritative. IDs below are explicit MedGen references only.
            item['condition_medgen_ids'] = sorted(set(re.findall(r'(?<![A-Za-z0-9])(C(?:N)?[0-9]+)(?=:)', item['reported_condition'])))
            item.update(submitter_id=None, rcv_accessions=None, vcv_accession_version=None,
                        source_url=release['url'], source_sha256=release['sha256'],
                        release_date=release['release_date'], source_filename=path.name)
            alternatives = records.setdefault(base, [])
            duplicate = next((old for old in alternatives if {k:v for k,v in old.items() if k != 'source_lines'} == item), None)
            if duplicate is not None:
                duplicate['source_lines'].append(line)
            else:
                item['source_lines'] = [line]
                alternatives.append(item)
        if headers is None:
            raise ValueError(f'Missing submission header: {path}')
    return records
