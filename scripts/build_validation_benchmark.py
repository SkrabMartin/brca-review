"""Independently inspect pinned raw sources to prepare a public, non-clinical benchmark.

Does not import the application's extractors, comparison code, database or UI.
Only selected public summary fields are exported; free-text submission evidence
is deliberately excluded. A reviewer must approve the resulting reference set
before a human pilot. Complete files are scanned to verify stated absences.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

SELECTED=[('37422','BRCA1','changed'),('17660','BRCA1','unchanged'),
 ('141093','BRCA1','unchanged'),('37574','BRCA1','unchanged'),('125714','BRCA1','changed'),
 ('3393452','BRCA1','newly_observed'),('54119','BRCA1','unavailable'),('17661','BRCA1','unchanged'),
 ('91425','BRCA2','unchanged'),('9317','BRCA2','unchanged'),('38235','BRCA2','unchanged'),
 ('38181','BRCA2','changed'),('41539','BRCA2','changed'),('3481928','BRCA2','newly_observed'),
 ('51037','BRCA2','unavailable'),('9318','BRCA2','unchanged')]
STATUS={'SCV000030123':'unchanged','SCV000184021':'classification_changed',
        'SCV000184222':'classification_changed','SCV000296299':'context_changed','SCV005437124':'newly_observed'}
VARIANT_FIELDS=['VariationID','GeneSymbol','Name','Assembly','ClinicalSignificance','ReviewStatus',
                'PhenotypeIDS','PhenotypeList','RCVaccession']
SUBMISSION_FIELDS=['#VariationID','SCV','ClinicalSignificance','DateLastEvaluated',
                  'SubmittedPhenotypeInfo','ReportedPhenotypeInfo','Submitter','ReviewStatus']
POSITIVE={'changed','newly_observed','classification_changed','context_changed','missing'}


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def inspect_source(path,release,kind):
    if digest(path)!=release['sha256']:raise ValueError(f'Raw-source hash mismatch: {path}')
    wanted={i for i,_,_ in SELECTED} if kind=='variant' else set(STATUS)
    found={key:[] for key in wanted}
    with gzip.open(path,'rt',encoding='utf-8',newline='') as stream:
        headers=None
        for line,raw in enumerate(stream,1):
            if headers is None:
                if kind=='variant' or raw.startswith('#VariationID\t'):
                    headers=raw.rstrip('\r\n').split('\t')
                    if headers!=release['headers']:raise ValueError('Header differs from pinned manifest')
                    index=headers.index('VariationID' if kind=='variant' else 'SCV')
                continue
            parts=raw.rstrip('\r\n').split('\t',index+1)
            if len(parts)<=index:raise ValueError(f'Broken source row {line}')
            identity=parts[index] if kind=='variant' else parts[index].split('.')[0]
            if identity not in wanted:continue
            values=next(csv.reader([raw],delimiter='\t'))
            if len(values)!=len(headers):raise ValueError(f'Broken selected row {line}')
            record=dict(zip(headers,values))
            fields=VARIANT_FIELDS if kind=='variant' else SUBMISSION_FIELDS
            found[identity].append({**{k:record[k] for k in fields},'source_line':line,
                'source_url':release['url'],'source_sha256':release['sha256'],
                'release_date':release['release_date']})
        if headers is None:raise ValueError('Missing header')
    return found


def aggregate_values(records):return sorted({r['ClinicalSignificance'] for r in records})


def check_status(old,new):
    if not old:return 'newly_observed'
    if not new:return 'missing'
    if any(len({(r['ClinicalSignificance'],r['ReviewStatus']) for r in rows})!=1 for rows in [old,new]):return 'unresolved'
    before,after=aggregate_values(old),aggregate_values(new)
    if before[0].lower() in {'','-','na','not provided','no classification provided'} or after[0].lower() in {'','-','na','not provided','no classification provided'}:return 'unavailable'
    return 'unchanged' if before==after else 'changed'


def build(data_dir,docs_dir,output_dir):
    sources={kind:json.loads((docs_dir/name).read_text())['releases'] for kind,name in
             [('variant','releases.json'),('submission','submission-releases.json')]}
    inspected={}
    for kind in sources:
        for side,release in zip(('previous','current'),sources[kind]):
            print('Inspecting',release['filename'],flush=True)
            inspected[kind,side]=inspect_source(data_dir/release['filename'],release,kind)
    # Compare inspected SCV fields to the already independently recorded expectations.
    prior=json.loads((docs_dir/'submission-examples.json').read_text())
    for scv,status in STATUS.items():
        for side,month in [('previous','01'),('current','02')]:
            actual=inspected['submission',side][scv];expected=prior['submissions'][month].get(scv,[])
            if len(actual)!=len(expected):raise ValueError('SCV coverage differs from reference')
            for a,e in zip(actual,expected):
                for k,v in e.items():
                    if a['source_line' if k=='line' else k]!=v:raise ValueError(f'SCV reference differs: {scv}:{k}')
    tasks=[];cases=[]
    for n,(identifier,gene,status) in enumerate(SELECTED,1):
        old=inspected['variant','previous'][identifier];new=inspected['variant','current'][identifier]
        if check_status(old,new)!=status:raise ValueError(f'Unexpected aggregate status: {identifier}')
        if any(gene not in r['GeneSymbol'].replace(';',',').split(',') for r in old+new):raise ValueError('Unexpected gene')
        cid=f'C{n:02}'
        case=dict(case_id=cid,variation_id=identifier,gene=gene,current_clinvar_url=f'https://www.ncbi.nlm.nih.gov/clinvar/variation/{identifier}/',
                  aggregate=dict(expected_status=status,previous=old,current=new),submissions=[])
        task=dict(task_id=cid+'-A',case_id=cid,level='aggregate',variation_id=identifier,scv_base='',status=status,
                  previous_classification=json.dumps(aggregate_values(old)),current_classification=json.dumps(aggregate_values(new)),
                  previous_condition='',current_condition='',previous_submitter='',current_submitter='',
                  previous_accession='',current_accession='',previous_evaluated='',current_evaluated='')
        for side,records in [('previous',old),('current',new)]:
            task[side+'_source_lines']=json.dumps([r['source_line'] for r in records])
            task[side+'_sha256']=sources['variant'][0 if side=='previous' else 1]['sha256']
        tasks.append(task)
        for scv,scv_status in sorted(STATUS.items()):
            records=inspected['submission','previous'][scv]+inspected['submission','current'][scv]
            if not any(r['#VariationID']==identifier for r in records):continue
            event=dict(scv_base=scv,expected_status=scv_status,previous=inspected['submission','previous'][scv],current=inspected['submission','current'][scv])
            case['submissions'].append(event)
            t=dict(task_id=cid+'-'+scv,case_id=cid,level='submission',variation_id=identifier,scv_base=scv,status=scv_status)
            for side in ['previous','current']:
                record=event[side][0] if event[side] else None
                for suffix,field in [('classification','ClinicalSignificance'),('condition','ReportedPhenotypeInfo'),('submitter','Submitter'),('accession','SCV'),('evaluated','DateLastEvaluated')]:
                    t[side+'_'+suffix]=record[field] if record else ''
                t[side+'_source_lines']=json.dumps([r['source_line'] for r in event[side]])
                t[side+'_sha256']=sources['submission'][0 if side=='previous' else 1]['sha256']
            tasks.append(t)
        cases.append(case)
    for task in tasks:
        task['previous_release']=sources['variant'][0]['release_date']
        task['current_release']=sources['variant'][1]['release_date']
    output_dir.mkdir(parents=True,exist_ok=True)
    benchmark=dict(schema_version=1,benchmark_id='brca-2025-01-02_2025-02-06-v1',
        publication_dates=[r['release_date'] for r in sources['variant']],sources=sources,
        baseline_eligibility={'clinvar_web':False,'clinvar_archive':False},
        verification=dict(source_check='implementation-agent full-file inspection',source_check_date='2026-11-14',independent_reviewer='pending',
                          clinical_scope='not reviewed',human_pilot='not_run',participants=0),
        cases=cases,scored_tasks=tasks,positive_statuses=sorted(POSITIVE))
    (output_dir/'benchmark.json').write_text(json.dumps(benchmark,ensure_ascii=False,indent=2)+'\n')
    with (output_dir/'reference.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(tasks[0]),lineterminator='\n');writer.writeheader();writer.writerows(tasks)
    with (output_dir/'watchlist.txt').open('w') as f:f.write('\n'.join(i for i,_,_ in SELECTED)+'\n')
    with (output_dir/'tasks.csv').open('w',newline='') as f:
        fields=['task_id','case_id','level','variation_id','scv_base','previous_release','current_release']
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');writer.writeheader();writer.writerows(tasks)
    for name,fields in {
        'sessions-template.csv':['participant_id','method','sequence','batch_elapsed_seconds','excluded_seconds','source_access_verified','exclusion_reason'],
        'review-log-template.csv':['task_id','reviewer_code','reviewer_role','checked_date','source_verified','scope_appropriate','agreement','notes_reference'],
        'assignments-template.csv':['participant_id','sequence','first_method','second_method','washout_hours'],
    }.items():
        with (output_dir/name).open('w',newline='') as f:csv.writer(f,lineterminator='\n').writerow(fields)
    with (output_dir/'scope-review.csv').open('w',newline='') as f:
        fields=['case_id','variation_id','gene','source_condition_context','scope_status','inclusion_decision','notes']
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
        for case in cases:
            context=(case['aggregate']['current'] or case['aggregate']['previous'])[0]['PhenotypeList']
            writer.writerow(dict(case_id=case['case_id'],variation_id=case['variation_id'],gene=case['gene'],
                source_condition_context=context,scope_status='pending_clinical_review',inclusion_decision='',
                notes='Source lists Fanconi anemia only. Explicit technical scope challenge; do not assume hereditary-cancer relevance. Clinician must approve or exclude in a new benchmark version.' if case['case_id']=='C06' else 'Gene overlap and source labels do not establish clinical inclusion.'))
    # No participant IDs, observations, times, or outcomes are invented.
    with (output_dir/'responses-template.csv').open('w',newline='') as f:
        fields=['participant_id','record_kind','method','task_id','variation_id','scv_base','status',
                'previous_classification','current_classification','previous_condition','current_condition',
                'previous_submitter','current_submitter','previous_accession','current_accession',
                'previous_evaluated','current_evaluated','previous_release','current_release',
                'completion','elapsed_seconds','excluded_seconds','exclusion_reason','source_reference']
        csv.writer(f,lineterminator='\n').writerow(fields)
    print('Prepared',len(cases),'cases and',len(tasks),'tasks; independent review/pilot remain pending.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,default=Path('data'))
    p.add_argument('--docs-dir',type=Path,default=Path('docs'))
    p.add_argument('--output-dir',type=Path,default=Path('docs/validation'))
    a=p.parse_args();build(a.data_dir,a.docs_dir,a.output_dir)
