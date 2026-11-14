"""Read models for public-ID review, with explicit dataset and submission coverage."""
from collections import Counter
import re
from sqlalchemy import select, false
from .models import Comparison, Release, Variant, AggregateChange, AggregateSnapshot, SubmissionChange


def parse_ids(raw):
    if raw is None or not raw.strip():return None,[],[]
    tokens=[x for x in re.split(r'[\s,;]+',raw.strip()) if x]
    if len(tokens)>200:raise ValueError('At most 200 public identifiers per watchlist')
    identifiers=[];invalid=[];duplicates=[]
    for token in tokens:
        upper=token.upper()
        if re.fullmatch(r'VCV[0-9]{9}\.[0-9]+',upper):
            invalid.append({'input':token,'reason':'vcv_version_not_available'});continue
        value=upper[3:] if re.fullmatch(r'VCV[0-9]{9}',upper) else upper
        if not re.fullmatch(r'[0-9]{1,18}',value) or not 0<int(value)<2**63:
            invalid.append({'input':token,'reason':'invalid_public_identifier'});continue
        canonical=int(value)
        if canonical in identifiers:duplicates.append(str(canonical))
        else:identifiers.append(canonical)
    return identifiers,invalid,duplicates


def get_comparison(session,identifier):
    comparison=session.get(Comparison,identifier)
    if comparison is None:raise KeyError('Comparison not loaded')
    return comparison


def release_info(release):
    return dict(release_date=release.release_date.isoformat(),filename=release.filename,url=release.url,
                sha256=release.sha256,retrieved_date=release.retrieved_date.isoformat(),headers=release.headers)


def list_comparisons(session):
    result=[]
    for comparison in session.scalars(select(Comparison).order_by(Comparison.id)):
        result.append(dict(id=comparison.id,scope=comparison.scope,releases=[release_info(session.get(Release,r))
            for r in (comparison.previous_variant_release_id,comparison.current_variant_release_id)]))
    return result


def snapshot(session,identifier,gene=None,raw_ids=None):
    comparison=get_comparison(session,identifier)
    identifiers,invalid,duplicates=parse_ids(raw_ids)
    query=select(AggregateChange,Variant).join(Variant).where(AggregateChange.comparison_id==identifier)
    if gene:query=query.where(Variant.genes.contains([gene]))
    if identifiers is not None:query=query.where(Variant.variation_id.in_(identifiers) if identifiers else false())
    matches=list(session.execute(query.order_by(Variant.variation_id)))
    ids=[variant.variation_id for _,variant in matches]
    releases=[session.get(Release,r) for r in (comparison.previous_variant_release_id,comparison.current_variant_release_id)]
    snapshots={}
    if ids:
        for item in session.scalars(select(AggregateSnapshot).where(
            AggregateSnapshot.release_id.in_([r.id for r in releases]),AggregateSnapshot.variation_id.in_(ids))):
            snapshots[item.release_id,item.variation_id]=item
    rows=[]
    for change,variant in matches:
        row=dict(variation_id=str(variant.variation_id),status=change.status,genes=variant.genes,
                 clinvar_url=f'https://www.ncbi.nlm.nih.gov/clinvar/variation/{variant.variation_id}/')
        for side,release in zip(('previous','current'),releases):
            item=snapshots.get((release.id,variant.variation_id))
            row.update({f'{side}_classification':item.classifications if item else [],
                        f'{side}_review_status':item.review_statuses if item else [],
                        f'{side}_source_lines':item.source_lines if item else [],
                        f'{side}_genes':item.genes if item else [],
                        f'{side}_source_url':release.url,f'{side}_sha256':release.sha256,
                        f'{side}_release_date':release.release_date.isoformat()})
        rows.append(row)
    unresolved=[{'input':str(i),'reason':'not_in_selected_gene_or_loaded_releases'} for i in (identifiers or []) if i not in set(ids)]
    return dict(schema_version=1,comparison_id=identifier,gene=gene or 'BRCA1+BRCA2',
                comparison_sha256=comparison.aggregate_sha256,releases=[release_info(r) for r in releases],
                counts=dict(Counter(r['status'] for r in rows)),rows=rows,coverage=comparison.scope,
                watchlist=dict(invalid=invalid,duplicates=duplicates,unresolved=unresolved,canonical_ids=[str(i) for i in identifiers] if identifiers is not None else None))


def submission_events(session,identifier,gene=None,raw_ids=None,status=None,condition='',submitter=''):
    comparison=get_comparison(session,identifier)
    ids,invalid,duplicates=parse_ids(raw_ids)
    allowed=None
    if gene or ids is not None:
        q=select(Variant.variation_id)
        if gene:q=q.where(Variant.genes.contains([gene]))
        if ids is not None:q=q.where(Variant.variation_id.in_(ids) if ids else false())
        allowed=set(session.scalars(q))
    query=select(SubmissionChange).where(SubmissionChange.comparison_id==identifier)
    if status:query=query.where(SubmissionChange.status==status)
    rows=[]
    for event in session.scalars(query.order_by(SubmissionChange.scv_base)):
        payload=event.payload;records=payload['previous']+payload['current']
        if allowed is not None and not any(int(r['variation_id']) in allowed for r in records):continue
        if condition and not any(condition.casefold() in (r['submitted_condition']+' '+r['reported_condition']).casefold() for r in records):continue
        if submitter and not any(submitter.casefold() in r['submitter_name'].casefold() for r in records):continue
        rows.append(payload)
    return dict(rows=rows,coverage=comparison.scope,invalid=invalid,duplicates=duplicates,
                note='No matching verified SCV is not evidence that all submissions are unchanged.')
