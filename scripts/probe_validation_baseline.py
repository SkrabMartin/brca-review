"""Record source reachability without claiming that historical web review is usable."""
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import time
from urllib.request import Request,urlopen
from urllib.error import URLError,HTTPError


def probe():
    sources=[]
    for name in ['releases.json','submission-releases.json']:
        sources+=json.loads((Path('docs')/name).read_text())['releases']
    checks=[]
    for source in sources:
        item={'url':source['url'],'method':'HEAD','pinned_bytes':source['bytes']}
        try:
            with urlopen(Request(source['url'],method='HEAD'),timeout=30) as r:
                item.update(http_status=r.status,content_length=r.headers.get('Content-Length'),reachable=r.status==200)
        except (URLError,HTTPError,TimeoutError) as error:item.update(reachable=False,error_type=type(error).__name__)
        checks.append(item);time.sleep(.4)
    url='https://www.ncbi.nlm.nih.gov/clinvar/variation/91425/'
    web={'url':url,'scope':'one automated current-page probe; not a history audit'}
    try:
        with urlopen(url,timeout=30) as r:
            body=r.read().decode('utf-8','replace')
            challenge=bool(re.search(r'recaptcha|checking your browser',body,re.I))
            web.update(http_status=r.status,challenge_detected=challenge,
                       historical_values_verified=False)
    except (URLError,HTTPError,TimeoutError) as error:web.update(error_type=type(error).__name__,historical_values_verified=False)
    report={'checked_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'archive_checks':checks,'web_probe':web,
            'clinvar_web_baseline_ready':False,
            'archive_assisted_baseline_reachability':all(c.get('reachable') for c in checks),
            'interpretation':'HTTP availability does not verify historical task coverage. Qualified reviewers must navigate and verify both dated values for every timed task before enabling a direct-ClinVar web comparison. An archive-assisted baseline is a separate comparison, not evidence against direct web review.',
            'participant_observations':0}
    Path('outputs').mkdir(exist_ok=True)
    target=Path('outputs/validation-baseline-probe.json');target.write_text(json.dumps(report,indent=2)+'\n')
    print(target);print('Direct ClinVar web baseline: NOT VERIFIED; challenge:',web.get('challenge_detected'))


if __name__=='__main__':probe()
