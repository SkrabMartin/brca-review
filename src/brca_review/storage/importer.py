"""Transactionally import pinned public artifacts, exposing only verified SCV examples."""
import argparse
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
from sqlalchemy import insert, select, text
from sqlalchemy.orm import Session
from brca_review.ingestion.tsv import sha256
from .database import get_engine
from .models import (Release, Variant, AggregateSnapshot, ConditionContext, SubmissionSnapshot,
                     Comparison, AggregateChange, SubmissionChange)


def load_artifacts(aggregate, submissions, docs):
    artifacts=json.loads((docs/'comparison-artifacts.json').read_text())
    for path,kind in [(aggregate,'aggregate'),(submissions,'submissions')]:
        if sha256(path)!=artifacts[kind]['sha256']:
            raise ValueError(f'Unverified {kind} artifact; import refused')
    with aggregate.open(encoding='utf-8',newline='') as stream:
        rows=list(csv.DictReader(stream))
    expected=json.loads((docs/'submission-examples.json').read_text())
    events={}
    with submissions.open(encoding='utf-8') as stream:
        for line in stream:
            event=json.loads(line)
            if event['scv_base'] in expected['expected_events']:
                if event['scv_base'] in events:raise ValueError('Duplicate SCV event')
                events[event['scv_base']]=event
    if events.keys()!=expected['expected_events'].keys():raise ValueError('Incomplete verified SCV subset')
    columns={'variation_id':'#VariationID','scv':'SCV','classification':'ClinicalSignificance',
             'submitted_condition':'SubmittedPhenotypeInfo','reported_condition':'ReportedPhenotypeInfo',
             'last_evaluated':'DateLastEvaluated','submitter_name':'Submitter'}
    for scv,event in events.items():
        if event['status']!=expected['expected_events'][scv]:raise ValueError('Unexpected example status')
        for side,month in [('previous','01'),('current','02')]:
            evidence=expected['submissions'][month].get(scv,[])
            if len(evidence)!=len(event[side]):raise ValueError('Unexpected example coverage')
            for source,record in zip(evidence,event[side]):
                if any(record[k]!=source[v] for k,v in columns.items()):raise ValueError('Unverified example fields')
    return artifacts,rows,events


def bulk(session, model, rows):
    for start in range(0,len(rows),1000):session.execute(insert(model),rows[start:start+1000])


def import_artifacts(engine, aggregate:Path, submissions:Path, docs=Path('docs')):
    artifacts,rows,events=load_artifacts(aggregate,submissions,docs)
    manifests={kind:json.loads((docs/name).read_text())['releases'] for kind,name in
               [('variant','releases.json'),('submission','submission-releases.json')]}
    with Session(engine) as session,session.begin():
        session.execute(text('SELECT pg_advisory_xact_lock(731603)'))
        existing=session.get(Comparison,artifacts['comparison_id'])
        if existing:
            if existing.aggregate_sha256!=artifacts['aggregate']['sha256'] or existing.submission_sha256!=artifacts['submissions']['sha256']:
                raise ValueError('Existing immutable comparison differs')
            return 'already_imported'
        releases={}
        for kind,sources in manifests.items():
            for side,source in zip(('previous','current'),sources):
                release=session.scalar(select(Release).where(Release.sha256==source['sha256']))
                if release is None:
                    release=Release(kind=kind, release_date=date.fromisoformat(source['release_date']),
                        retrieved_date=date.fromisoformat(source['retrieved_date']),filename=source['filename'],
                        url=source['url'],sha256=source['sha256'],byte_size=source['bytes'],headers=source['headers'])
                    session.add(release);session.flush()
                releases[kind,side]=release
        session.add(Comparison(id=artifacts['comparison_id'],
            previous_variant_release_id=releases['variant','previous'].id,
            current_variant_release_id=releases['variant','current'].id,
            previous_submission_release_id=releases['submission','previous'].id,
            current_submission_release_id=releases['submission','current'].id,
            aggregate_sha256=artifacts['aggregate']['sha256'],submission_sha256=artifacts['submissions']['sha256'],
            scope={'genes':['BRCA1','BRCA2'],'condition_filter':'none; clinical scope not reviewed',
                   'submission_coverage':'verified_subset','verified_scvs':sorted(events),
                   'verification':'implementation-agent source check; not independent clinical validation'}))
        session.flush()
        variants=[];snapshots=[];changes=[]
        for row in rows:
            identifier=int(row['variation_id'])
            variants.append(dict(variation_id=identifier,genes=sorted(set(json.loads(row['previous_genes'])+json.loads(row['current_genes'])))))
            changes.append(dict(comparison_id=artifacts['comparison_id'],variation_id=identifier,status=row['status']))
            for side in ('previous','current'):
                if json.loads(row[f'{side}_source_lines']):
                    snapshots.append(dict(release_id=releases['variant',side].id,variation_id=identifier,
                        classifications=json.loads(row[f'{side}_classification']),review_statuses=json.loads(row[f'{side}_review_status']),
                        genes=json.loads(row[f'{side}_genes']),source_lines=json.loads(row[f'{side}_source_lines'])))
        bulk(session,Variant,variants);bulk(session,AggregateSnapshot,snapshots);bulk(session,AggregateChange,changes)
        for scv,event in sorted(events.items()):
            links={}
            for side in ('previous','current'):
                links[side]=None
                for record in event[side]:
                    raw=[record['submitted_condition'],record['reported_condition']]
                    fingerprint=hashlib.sha256(json.dumps(raw,ensure_ascii=False).encode()).hexdigest()
                    if session.get(ConditionContext,fingerprint) is None:
                        session.add(ConditionContext(context_hash=fingerprint,submitted=raw[0],reported=raw[1],medgen_ids=record['condition_medgen_ids']))
                        session.flush()
                    snapshot=SubmissionSnapshot(release_id=releases['submission',side].id,
                        variation_id=int(record['variation_id']),scv_base=scv,scv_version=record['scv_version'],
                        condition_hash=fingerprint,submitter_name=record['submitter_name'],submitter_id=record['submitter_id'],
                        classification=record['classification'],classification_type=record['classification_type'],
                        last_evaluated_raw=record['last_evaluated'],review_status=record['review_status'],
                        rcv_accessions=record['rcv_accessions'],vcv_accession_version=record['vcv_accession_version'],payload=record)
                    session.add(snapshot);session.flush();links[side]=snapshot.id
            session.add(SubmissionChange(comparison_id=artifacts['comparison_id'],scv_base=scv,
                previous_snapshot_id=links['previous'],current_snapshot_id=links['current'],status=event['status'],flags=event['flags'],payload=event))
    return 'imported'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--aggregate',type=Path,default=Path('outputs/brca1-brca2.csv'))
    p.add_argument('--submissions',type=Path,default=Path('outputs/submissions-final.jsonl'))
    p.add_argument('--docs',type=Path,default=Path('docs'))
    args=p.parse_args();engine=get_engine()
    try:print(import_artifacts(engine,args.aggregate,args.submissions,args.docs))
    finally:engine.dispose()


if __name__=='__main__':main()
