"""Check a running read-only app against the provisional raw-source benchmark."""
import argparse
import csv
from datetime import datetime,timezone
import io
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


def verify(benchmark,base):
    def get(path):
        with urlopen(base.rstrip('/')+path,timeout=45) as response:
            if response.status!=200:raise ValueError(f'HTTP {response.status}: {path}')
            return response.read()
    health=json.loads(get('/api/v1/health'))
    if health.get('mode')!='postgresql-read-only' or health.get('postgres_major')!=17:raise ValueError('Expected real PostgreSQL17 read-only API')
    ids=','.join(case['variation_id'] for case in benchmark['cases']);query=urlencode({'ids':ids})
    snapshot=json.loads(get('/api/v1/comparison?'+query))
    if snapshot.get('coverage',{}).get('submission_coverage')!='verified_subset':raise ValueError('Unexpected submission coverage contract')
    rows={row['variation_id']:row for row in snapshot['rows']}
    if len(rows)!=len(benchmark['cases']):raise ValueError('Incomplete benchmark aggregate coverage')
    for case in benchmark['cases']:
        row=rows[case['variation_id']];expected=case['aggregate']
        if row['status']!=expected['expected_status']:raise ValueError(f'Status mismatch: {case["case_id"]}')
        for n,side in enumerate(['previous','current']):
            evidence=expected[side];release=benchmark['sources']['variant'][n]
            checks={f'{side}_classification':sorted({r['ClinicalSignificance'] for r in evidence}),
                    f'{side}_review_status':sorted({r['ReviewStatus'] for r in evidence}),
                    f'{side}_source_lines':[r['source_line'] for r in evidence],
                    f'{side}_source_url':release['url'],f'{side}_sha256':release['sha256'],
                    f'{side}_release_date':release['release_date']}
            for field,value in checks.items():
                if row[field]!=value:raise ValueError(f'Aggregate evidence mismatch: {case["case_id"]}:{field}')
    submission=json.loads(get('/api/v1/submissions?'+query))
    if submission['coverage']['submission_coverage']!='verified_subset':raise ValueError('Unclear SCV coverage')
    events={event['scv_base']:event for event in submission['rows']}
    expected_scvs={item['scv_base']:item for case in benchmark['cases'] for item in case['submissions']}
    if events.keys()!=expected_scvs.keys():raise ValueError('SCV coverage mismatch')
    mapping={'scv':'SCV','variation_id':'#VariationID','classification':'ClinicalSignificance',
             'last_evaluated':'DateLastEvaluated','submitter_name':'Submitter','reported_condition':'ReportedPhenotypeInfo',
             'submitted_condition':'SubmittedPhenotypeInfo','review_status':'ReviewStatus'}
    for scv,expected in expected_scvs.items():
        event=events[scv]
        if event['status']!=expected['expected_status'] or event['observed_between']!=benchmark['publication_dates']:raise ValueError('SCV event mismatch')
        for n,side in enumerate(['previous','current']):
            if len(event[side])!=len(expected[side]):raise ValueError('SCV presence mismatch')
            for record,source in zip(event[side],expected[side]):
                if any(record[k]!=source[v] for k,v in mapping.items()):raise ValueError('SCV context mismatch')
                if record['source_lines']!=[source['source_line']] or record['source_sha256']!=benchmark['sources']['submission'][n]['sha256']:raise ValueError('SCV provenance mismatch')
    export=list(csv.DictReader(io.StringIO(get('/api/v1/comparison.csv?'+query).decode())))
    if {r['variation_id'] for r in export}!=rows.keys():raise ValueError('CSV selection mismatch')
    for row in export:
        if row['status']!=rows[row['variation_id']]['status']:raise ValueError('CSV status mismatch')
    return dict(status='technical_checks_passed',checked_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                base_url=base,aggregate_cases=len(rows),scv_cases=len(events),human_participants=0,
                clinical_validation=False,usefulness_conclusion=None)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url',default='http://127.0.0.1:8091')
    p.add_argument('--benchmark',type=Path,default=Path('docs/validation/benchmark.json'))
    p.add_argument('--output',type=Path,default=Path('outputs/validation/app-check.json'))
    a=p.parse_args()
    if a.output.resolve()==a.benchmark.resolve():p.error('Output cannot overwrite benchmark')
    result=verify(json.loads(a.benchmark.read_text()),a.base_url)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],':',result['aggregate_cases'],'aggregate cases,',result['scv_cases'],'SCVs; not a human pilot')
