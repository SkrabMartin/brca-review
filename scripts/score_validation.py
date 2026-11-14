"""Score supplied observations only; empty templates produce no invented outcomes."""
import argparse
import csv
import json
from pathlib import Path
from brca_review.validation import score


def read_csv(path):
    with path.open(newline='',encoding='utf-8-sig') as stream:
        rows=list(csv.DictReader(stream))
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError('CSV row/column count mismatch')
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--benchmark',type=Path,default=Path('docs/validation/benchmark.json'))
    p.add_argument('--responses',type=Path,required=True)
    p.add_argument('--sessions',type=Path)
    p.add_argument('--baseline',choices=['clinvar_web','clinvar_archive'],default='clinvar_web')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.resolve() in {p.resolve() for p in [a.benchmark,a.responses]+([a.sessions] if a.sessions else [])}:
        p.error('Output cannot overwrite inputs')
    try:
        benchmark=json.loads(a.benchmark.read_text())
        responses=read_csv(a.responses)
        sessions=[]
        if a.sessions:
            sessions=read_csv(a.sessions)
        result=score(benchmark,responses,sessions,a.baseline)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(result['status'],'; human participants:',result['human_participant_count'])
    except (ValueError,KeyError,OSError) as error:p.exit(2,f'Validation scoring failed: {error}\n')


if __name__=='__main__':main()
