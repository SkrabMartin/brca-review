import { useEffect, useMemo, useState } from 'react';
import { dateLabel, submissionLabels, submissionFlagLabels, type Assertion, type SubmissionResult } from './data';

export function Submissions({queryString}:{queryString:string}) {
  const [data,setData]=useState<SubmissionResult|null>(null);
  const [error,setError]=useState(false);
  const [retry,setRetry]=useState(0);
  const [status,setStatus]=useState('');
  const [condition,setCondition]=useState('');
  const [submitter,setSubmitter]=useState('');
  useEffect(()=>{
    const controller=new AbortController();setData(null);setError(false);
    fetch(`/api/v1/submissions?${queryString}`,{signal:controller.signal})
      .then(r=>{if(!r.ok)throw new Error();return r.json();})
      .then(value=>{if(!Array.isArray(value.rows)||!value.coverage?.verified_scvs)throw new Error();setData(value);})
      .catch(()=>{if(!controller.signal.aborted)setError(true);});
    return()=>controller.abort();
  },[queryString,retry]);
  const rows=useMemo(()=>data?.rows.filter(event=>{
    const records=event.previous.concat(event.current);
    return (!status||event.status===status)&&records.some(r=>(r.reported_condition+' '+r.submitted_condition).toLowerCase().includes(condition.toLowerCase()))&&records.some(r=>r.submitter_name.toLowerCase().includes(submitter.toLowerCase()));
  })??[],[data,status,condition,submitter]);
  return <section className="submission-section" aria-labelledby="submissions-title">
    <h2 id="submissions-title">Jednotlivá podání — ověřený výběr</h2>
    <p className="note">Tento pohled pokrývá pouze pět zdrojově ověřených SCV, nikoli všechna podání BRCA1/BRCA2. Kontrolu provedl implementační agent; klinická validace neproběhla. Pokud se příklad nenajde, neznamená to, že jsou všechna podání beze změny.</p>
    {error?<div className="state" role="alert"><p>Podání se nepodařilo načíst.</p><button className="button" onClick={()=>setRetry(n=>n+1)}>Znovu načíst podání</button></div>:!data?<p role="status">Načítání podání…</p>:<>
      <div className="toolbar"><label className="field"><span>Typ události podání</span><select aria-label="Typ události podání" value={status} onChange={e=>setStatus(e.target.value)}><option value="">Všechny události</option>{Object.entries(submissionLabels).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><label className="field"><span>Podmínka / onemocnění</span><input value={condition} onChange={e=>setCondition(e.target.value)} placeholder="C0027672"/></label><label className="field"><span>Předkladatel</span><input value={submitter} onChange={e=>setSubmitter(e.target.value)} placeholder="Ambry"/></label></div>
      <p className="result-count" role="status">{rows.length} podání ve vybraném rozsahu. Celkové pokrytí: {data.coverage.verified_scvs.length} ověřených SCV.</p>
      {!rows.length&&<div className="state"><p>Žádné ověřené podání neodpovídá výběru. Nelze z toho vyvodit nepřítomnost změn ostatních podání.</p></div>}
      {rows.map(event=><details className="scv-event" key={event.scv_base}>
        <summary><span className="mono">{event.scv_base}</span> · {submissionLabels[event.status]??event.status} · varianta {(event.current[0]??event.previous[0]).variation_id}</summary>
        <p className="note">Pozorováno mezi vydáními {event.observed_between.map(dateLabel).join(' → ')}. Souhrn varianty: {Object.entries(event.aggregate_status).map(([id,value])=>`${id}: ${value==='unchanged'?'beze změny':value}`).join('; ')}.</p>
        <div className="detail-columns"><AssertionSide title="Starší vydání" record={event.previous[0]}/><AssertionSide title="Novější vydání" record={event.current[0]}/></div>
        <p className="note">Verze podání ani datum posledního hodnocení neurčují přesný okamžik zveřejnění změny. Odlišný kontext může znamenat i přejmenování; chybějící vazby SCV–RCV a ID předkladatele nejsou doplněny odhadem.</p>
        {event.flags.length>0&&<p className="note">Změněná pole ve zdroji: {event.flags.map(flag=>submissionFlagLabels[flag]??flag).join(', ')}</p>}
      </details>)}
    </>}
  </section>;
}

function AssertionSide({record,title}:{record?:Assertion;title:string}) {
  if(!record)return <div><h3>{title}</h3><p>Podání v tomto vydání nebylo pozorováno.</p></div>;
  return <div className="detail"><h3>{title} · {dateLabel(record.release_date)}</h3><dl>
    <dt>SCV a verze</dt><dd className="mono">{record.scv}</dd>
    <dt>Klasifikace</dt><dd>{record.classification}</dd>
    <dt>Předkladatel</dt><dd>{record.submitter_name}</dd>
    <dt>Podmínka podání</dt><dd>{record.submitted_condition}</dd>
    <dt>Mapovaná podmínka</dt><dd>{record.reported_condition}</dd>
    <dt>Naposledy hodnoceno</dt><dd>{record.last_evaluated}</dd>
    <dt>Stav přezkumu</dt><dd>{record.review_status}</dd>
    <dt>Zdroj</dt><dd><a href={record.source_url}>{record.source_filename}</a> · řádky {record.source_lines.join(', ')}</dd>
    <dt>SHA-256</dt><dd className="hash mono">{record.source_sha256}</dd>
  </dl></div>;
}
