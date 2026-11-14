"""Provisional-reference scoring only; never infers clinical benefit or invents observations."""
from collections import defaultdict
import json
import math
import statistics
import re

METHODS={'app','clinvar_web','clinvar_archive'}
STATUSES={'changed','newly_observed','missing','unchanged','unavailable','unresolved','classification_changed','context_changed'}
FIELDS=['previous_classification','current_classification','previous_condition','current_condition',
        'previous_submitter','current_submitter','previous_accession','current_accession',
        'previous_evaluated','current_evaluated','previous_release','current_release']


def normalize(value):return ' '.join(str(value).split()).casefold()


def field_equal(field,actual,expected):
    if not str(actual).strip():return False
    if field.endswith('condition'):
        ids=lambda value:set(re.findall(r'\bC(?:N)?[0-9]+\b',value))
        if ids(expected):return ids(actual)==ids(expected)
    if field.endswith('classification'):
        def values(value):
            if value.startswith('['):
                parsed=json.loads(value)
                if not isinstance(parsed,list) or not all(isinstance(x,str) for x in parsed):raise ValueError('Classification must be a string or string array')
                return sorted(normalize(x) for x in parsed)
            return [normalize(value)]
        return values(actual.strip())==values(expected)
    return normalize(actual)==normalize(expected)


def seconds(value,allow_blank=False):
    if allow_blank and not str(value).strip():return None
    try:number=float(value)
    except (ValueError,TypeError):raise ValueError('Invalid time value')
    if not math.isfinite(number) or number<0:raise ValueError('Times must be finite and nonnegative')
    return number


def score(benchmark,responses,sessions=(),baseline='clinvar_web'):
    if baseline not in METHODS-{'app'}:raise ValueError('Choose one explicitly named baseline')
    reference={task['task_id']:task for task in benchmark['scored_tasks']}
    if len(reference)!=len(benchmark['scored_tasks']):raise ValueError('Duplicate reference task')
    positive=set(benchmark['positive_statuses'])
    groups=defaultdict(dict);kinds={}
    for row in responses:
        if not any(str(v).strip() for v in row.values()):continue
        participant=row.get('participant_id','').strip();method=row.get('method','').strip();task=row.get('task_id','').strip()
        kind=row.get('record_kind','').strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,32}',participant) or method not in METHODS or kind not in {'human','synthetic'}:raise ValueError('Declare participant code, known method, and human/synthetic record_kind')
        if task not in reference:raise ValueError('Response contains unknown task_id')
        key=(participant,method)
        if task in groups[key]:raise ValueError('Duplicate task response; adjudicate before scoring')
        if key in kinds and kinds[key]!=kind:raise ValueError('Mixed human/synthetic observations in one session')
        kinds[key]=kind
        completion=row.get('completion','').strip()
        status=row.get('status','').strip()
        if completion not in {'complete','timeout','not_assessable'}:raise ValueError('Declare completion state')
        if completion=='complete' and status not in STATUSES:raise ValueError('Invalid completed status')
        if completion!='complete' and status:raise ValueError('Incomplete tasks must not declare an inferred status')
        elapsed=seconds(row.get('elapsed_seconds',''),True)
        excluded=seconds(row.get('excluded_seconds','') or 0)
        if elapsed is None and excluded:raise ValueError('Cannot exclude time without an elapsed value')
        if elapsed is not None and excluded>elapsed:raise ValueError('Excluded time exceeds elapsed time')
        if excluded and not row.get('exclusion_reason','').strip():raise ValueError('Document any excluded task time')
        groups[key][task]=row
    timing={}
    for row in sessions:
        if not any(str(v).strip() for v in row.values()):continue
        key=(row.get('participant_id','').strip(),row.get('method','').strip())
        if key not in groups:raise ValueError('Session timing has no corresponding responses')
        if key in timing:raise ValueError('Duplicate session timing')
        elapsed=seconds(row.get('batch_elapsed_seconds',''));excluded=seconds(row.get('excluded_seconds','') or 0)
        if excluded>elapsed or elapsed<=0:raise ValueError('Invalid batch/excluded timing')
        if excluded and not row.get('exclusion_reason','').strip():raise ValueError('Document any excluded batch time')
        if row.get('source_access_verified') not in {'yes','no'}:raise ValueError('Declare session source-access verification')
        if row.get('sequence') not in {'app_first','baseline_first'}:raise ValueError('Declare assigned sequence')
        timing[key]=dict(gross_seconds=elapsed,excluded_seconds=excluded,net_seconds=elapsed-excluded,
                         source_access_verified=row['source_access_verified']=='yes',sequence=row['sequence'])
    results=[]
    expected_events=sum(task['status'] in positive for task in reference.values())
    for key,answers in sorted(groups.items()):
        tp=fp=correct_status=not_assessable=timeouts=0;attributes=defaultdict(lambda:{'correct':0,'expected':0})
        per_task=[]
        for task_id,task in reference.items():
            row=answers.get(task_id)
            complete=bool(row and row['completion']=='complete')
            identity=bool(complete and row.get('variation_id','').lstrip('0')==task['variation_id'] and
                          (task['level']=='aggregate' or row.get('scv_base','').upper()==task['scv_base']))
            matches=bool(identity and row['status']==task['status'])
            correct_status+=matches
            predicted_positive=bool(complete and row['status'] in positive)
            if predicted_positive:
                if matches and task['status'] in positive:tp+=1
                else:fp+=1
            if row and row['completion']=='not_assessable':not_assessable+=1
            if row and row['completion']=='timeout':timeouts+=1
            details={}
            for field in FIELDS:
                if task.get(field,'')=='':continue # Not applicable, not an answered field.
                valid=bool(identity and field_equal(field,row.get(field,''),task[field]))
                attributes[field]['expected']+=1;attributes[field]['correct']+=valid;details[field]=valid
            elapsed=seconds(row.get('elapsed_seconds',''),True) if row else None
            excluded=seconds(row.get('excluded_seconds','') or 0) if row else 0
            per_task.append(dict(task_id=task_id,status_correct=matches,fields_correct=details,
                                 completion=row['completion'] if row else 'missing_response',elapsed_seconds=elapsed,
                                 excluded_seconds=excluded,net_elapsed_seconds=elapsed-excluded if elapsed is not None else None))
        fn=expected_events-tp
        results.append(dict(participant_id=key[0],method=key[1],record_kind=kinds[key],
            expected_tasks=len(reference),answered_tasks=len(answers),missing_responses=len(reference)-len(answers),
            status_correct=correct_status,status_accuracy=correct_status/len(reference) if reference else None,
            true_positive=tp,false_positive=fp,false_negative=fn,
            precision=tp/(tp+fp) if tp+fp else None,recall=tp/expected_events if expected_events else None,
            not_assessable=not_assessable,timeouts=timeouts,
            field_accuracy={k:{**v,'errors':v['expected']-v['correct']} for k,v in attributes.items()},
            batch_timing=timing.get(key),tasks=per_task))
    by_key={(r['participant_id'],r['method']):r for r in results}
    paired=[]
    for participant in sorted({k[0] for k in groups}):
        app=by_key.get((participant,'app'));control=by_key.get((participant,baseline))
        if not app or not control or app['record_kind']!=control['record_kind']:continue
        a,b=app['batch_timing'],control['batch_timing']
        gate=benchmark.get('baseline_eligibility',{}).get(baseline) is True and benchmark['verification']['independent_reviewer']=='approved'
        eligible=bool(gate and a and b and a['source_access_verified'] and b['source_access_verified'] and a['sequence']==b['sequence'] and
                      not app['missing_responses'] and not control['missing_responses'] and
                      not any(r[key] for r in (app,control) for key in ('timeouts','not_assessable')))
        paired.append(dict(participant_id=participant,record_kind=app['record_kind'],baseline=baseline,
            timing_eligible=eligible,net_seconds_saved=(b['net_seconds']-a['net_seconds']) if eligible else None,
            status_accuracy_difference=app['status_accuracy']-control['status_accuracy'],
            precision_difference=app['precision']-control['precision'] if app['precision'] is not None and control['precision'] is not None else None,
            recall_difference=app['recall']-control['recall'] if app['recall'] is not None and control['recall'] is not None else None))
    human={r['participant_id'] for r in results if r['record_kind']=='human'}
    eligible_times=[p['net_seconds_saved'] for p in paired if p['record_kind']=='human' and p['timing_eligible']]
    return dict(benchmark_id=benchmark['benchmark_id'],status='no_participant_data' if not groups else 'provisional_reference_scoring_only',
        baseline=baseline,human_participant_count=len(human),
        synthetic_participant_count=len({r['participant_id'] for r in results if r['record_kind']=='synthetic'}),
        independent_reference_review=benchmark['verification']['independent_reviewer'],
        usefulness_conclusion=None,results=results,paired=paired,
        median_net_seconds_saved=statistics.median(eligible_times) if eligible_times else None,
        warning='Descriptive scoring against an agent-prepared reference; no clinical or reviewer-benefit conclusion. Do not mix direct-web and archive-assisted baselines. Missing/not-assessable tasks stay in accuracy/recall denominators.')
