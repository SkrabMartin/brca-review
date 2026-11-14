import { Fragment, useEffect, useMemo, useState } from 'react';
import { dateLabel, decodeSnapshot, filterRows, labels, statusNotes, type Row, type Snapshot } from './data';
import { Submissions } from './Submissions';

const PAGE_SIZE = 25;
const number = new Intl.NumberFormat('cs-CZ');
const joined = (values: string[], fallback: string) => values.join(' | ') || fallback;

export default function App() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [pairs, setPairs] = useState<{id:string; releases:{release_date:string}[]}[]>([]);
  const [pair, setPair] = useState('');
  const [gene, setGene] = useState('BRCA1');
  const [draftIds, setDraftIds] = useState('');
  const [ids, setIds] = useState('');
  const [pairError, setPairError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setPairError(false);
    fetch('/api/v1/comparisons', {signal:controller.signal})
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then((available) => {
        if (!Array.isArray(available) || !available.length || !available.every(p => typeof p.id==='string' && p.releases?.length===2)) throw new Error();
        setPairs(available); setPair(old => old || available[0].id);
      }).catch(() => {if (!controller.signal.aborted) setPairError(true);});
    return () => controller.abort();
  }, [attempt]);
  const params = new URLSearchParams({comparison_id:pair});
  if (gene) params.set('gene',gene);
  if (ids) params.set('ids',ids);
  const queryString=params.toString();

  useEffect(() => {
    if (!pair) return;
    const controller = new AbortController();
    setError(false);
    setData(null);
    fetch(`/api/v1/comparison?${queryString}`, { signal: controller.signal })
      .then(response => {
        if (!response.ok) throw new Error('Data unavailable');
        return response.json();
      })
      .then(decodeSnapshot)
      .then(setData)
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [attempt, pair, queryString]);

  return (
    <>
      <a className="skip" href="#srovnani">Přejít na srovnání</a>
      <header className="top">
        <a className="wordmark" href="#srovnani">BRCA Review</a>
        <nav aria-label="Hlavní navigace">
          <a href="#srovnani">Srovnání</a>
          <a href="#rozsah">Rozsah a omezení</a>
          <a href="#zdroje">Zdroje</a>
        </nav>
      </header>
      <main>
        <section id="srovnani" aria-labelledby="title">
          <h1 id="title">BRCA1 a BRCA2: revize změn v ClinVar</h1>
          <form className="review-form" onSubmit={e => { e.preventDefault();setIds(draftIds);setAttempt(a=>a+1); }}>
            <div className="toolbar">
              <label className="field"><span>Dvojice vydání</span><select aria-label="Dvojice vydání" value={pair} onChange={e=>setPair(e.target.value)} disabled={!pairs.length}>{pairs.map(p=><option key={p.id} value={p.id}>{p.releases.map(r=>dateLabel(r.release_date)).join(' → ')}</option>)}</select></label>
              <label className="field"><span>Gen</span><select aria-label="Gen" value={gene} onChange={e=>setGene(e.target.value)}><option value="BRCA1">BRCA1</option><option value="BRCA2">BRCA2</option><option value="">Oba geny</option></select></label>
            </div>
            <label className="field"><span>Sledované veřejné identifikátory (nejvýše 200; prázdné = všechny záznamy)</span><textarea rows={2} maxLength={8000} value={draftIds} onChange={e=>setDraftIds(e.target.value)} placeholder="91425, VCV000141093, 37422"/></label>
            <p className="note">Pouze veřejná Variation ID nebo VCV bez verze. Nevkládejte jména ani jiné údaje o pacientech. Seznam se neukládá na server.</p>
            <div className="toolbar"><button className="button" type="submit" disabled={!pair}>Použít seznam</button><button className="button" type="button" onClick={()=>{setGene('');setDraftIds('91425, 141093, 9317, 38235, 37574, 37422');setIds('91425,141093,9317,38235,37574,37422');}}>Ověřené příklady</button><button className="button" type="button" onClick={()=>{setDraftIds('');setIds('');}}>Všechny záznamy</button></div>
          </form>
          {!data && !error && !pairError && (
            <div role="status" className="state">
              <h2>Načítání</h2>
              <p>Načítá se ověřené srovnání dvou vydání ClinVar.</p>
            </div>
          )}
          {(error || pairError) && (
            <div role="alert" className="state">
              <h2>Data se nepodařilo načíst</h2>
              <p>Zkontrolujte připojení nebo dostupnost služby a zkuste to znovu. Žádné náhradní výsledky nezobrazujeme.</p>
              <button className="button" onClick={() => setAttempt(a => a + 1)}>Zkusit znovu</button>
            </div>
          )}
          {data && <>
            {data.watchlist && <WatchlistReport value={data.watchlist}/>}
            <Comparison key={queryString} data={data} csvUrl={`/api/v1/comparison.csv?${queryString}`} />
            <Submissions queryString={queryString}/>
          </>}
        </section>
        <Scope />
        <Sources data={data} />
      </main>
      <footer>
        <span>BRCA Review</span>
        <span>Pomůcka k odborné revizi veřejných dat. Interpretace náleží odborníkovi.</span>
      </footer>
    </>
  );
}

function Comparison({ data, csvUrl }: { data: Snapshot; csvUrl:string }) {
  const [status, setStatus] = useState('changed');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);

  const rows = useMemo(() => filterRows(data.rows, status, query), [data, status, query]);
  const pageCount = Math.ceil(rows.length / PAGE_SIZE);
  const currentRows = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const [previousDate, currentDate] = data.releases.map(release => dateLabel(release.release_date));
  const filters: [string, string, number][] = [
    ['', 'Všechny záznamy', data.rows.length],
    ...Object.entries(labels).map(([key, label]): [string, string, number] => [key, label, data.counts[key] ?? 0]),
  ];
  const changeStatus = (value: string) => { setStatus(value); setPage(0); };
  const changeQuery = (value: string) => { setQuery(value); setPage(0); };

  return (
    <>
      <dl className="meta">
        <div><dt>Starší vydání</dt><dd className="mono">{previousDate}</dd></div>
        <div><dt>Novější vydání</dt><dd className="mono">{currentDate}</dd></div>
        <div><dt>Úroveň</dt><dd>souhrn za variantu</dd></div>
        <div><dt>Data</dt><dd>datované snímky, jen ke čtení</dd></div>
      </dl>
      <p className="caveat">
        Porovnání veřejných záznamů, nikoli pacientů. Změna textu klasifikace není nová diagnóza.
      </p>

      <div className="filters" role="group" aria-label="Typ výsledku">
        {filters.map(([key, label, count]) => (
          <button key={key} type="button" aria-pressed={status === key} onClick={() => changeStatus(key)}>
            <span className="count mono">{number.format(count)}</span>
            <span className="label">{label}</span>
          </button>
        ))}
      </div>

      <div className="toolbar">
        <label className="field">
          <span>Hledat podle Variation ID nebo textu klasifikace</span>
          <input
            type="search"
            className="mono"
            placeholder="37422, Pathogenic"
            value={query}
            onChange={event => changeQuery(event.target.value)}
          />
        </label>
        <a className="button" href={csvUrl} download>Stáhnout CSV</a>
      </div>

      <p className="result-count" role="status">
        <span className="mono">{number.format(rows.length)}</span> z <span className="mono">{number.format(data.rows.length)}</span> záznamů
        {status && <> · {labels[status]}</>}
        {query.trim() && <> · hledání „{query.trim()}“</>}
      </p>

      {rows.length === 0 ? (
        <div className="state">
          <h2>Žádný záznam</h2>
          <p>Žádný záznam neodpovídá filtrům. Zkuste jiný identifikátor nebo všechny záznamy.</p>
          <button className="button" onClick={() => { changeStatus(''); changeQuery(''); }}>Zrušit filtry</button>
        </div>
      ) : (
        <>
          <table>
            <caption className="sr-only">Porovnání souhrnných klasifikací vybraných variant mezi dvěma vydáními ClinVar</caption>
            <thead>
              <tr>
                <th scope="col">Variation ID</th>
                <th scope="col">Klasifikace <span className="mono">{previousDate}</span></th>
                <th scope="col">Klasifikace <span className="mono">{currentDate}</span></th>
                <th scope="col">Výsledek</th>
                <th scope="col">Aktuální záznam</th>
              </tr>
            </thead>
            <tbody>
              {currentRows.map(row => {
                const open = selected === row.variation_id;
                return (
                  <Fragment key={row.variation_id}>
                    <tr className={open ? 'open' : undefined}>
                      <th scope="row" className="c-id">
                        <button
                          type="button"
                          className="id-button mono"
                          aria-label={`Detail varianty ${row.variation_id}`}
                          aria-expanded={open}
                          onClick={() => setSelected(open ? null : row.variation_id)}
                        >
                          <span className="sign" aria-hidden="true">{open ? '−' : '+'}</span><span className="num">{row.variation_id}</span>
                        </button>
                      </th>
                      <td className="c-prev" data-label={previousDate}>{joined(row.previous_classification, '—')}</td>
                      <td className="c-curr" data-label={currentDate}>{joined(row.current_classification, '—')}</td>
                      <td className={`c-status st-${row.status}`}>{labels[row.status]}</td>
                      <td className="c-link">
                        <a href={row.clinvar_url} target="_blank" rel="noreferrer">
                          ClinVar<span className="sr-only"> (aktuální stránka, nové okno)</span>
                        </a>
                      </td>
                    </tr>
                    {open && (
                      <tr className="detail-row">
                        <td colSpan={5}><Detail row={row} dates={[previousDate, currentDate]} /></td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
          <div className="pagination">
            <button className="button" disabled={page === 0} onClick={() => setPage(p => p - 1)}>Předchozí</button>
            <span>Strana <span className="mono">{page + 1}</span> z <span className="mono">{pageCount}</span></span>
            <button className="button" disabled={page + 1 >= pageCount} onClick={() => setPage(p => p + 1)}>Další</button>
          </div>
        </>
      )}
    </>
  );
}

function Detail({ row, dates }: { row: Row; dates: string[] }) {
  return (
    <section className="detail" aria-label={`Detail varianty ${row.variation_id}`}>
      <div className="detail-columns">
        {(['previous', 'current'] as const).map((side, index) => (
          <div key={side}>
            <h3>{index ? 'Novější vydání' : 'Starší vydání'} <span className="mono">{dates[index]}</span></h3>
            <dl>
              <dt>Klasifikace</dt>
              <dd>{joined(row[`${side}_classification`], 'Není v tomto vydání')}</dd>
              <dt>Stav přezkumu</dt>
              <dd>{joined(row[`${side}_review_status`], 'Stav přezkumu nedostupný')}</dd>
              <dt>Řádky v rozbaleném TSV</dt>
              <dd className="mono">{row[`${side}_source_lines`].join(', ') || '—'}</dd>
              <dt>Datovaný soubor ClinVar</dt>
              <dd><a className="mono" href={row[`${side}_source_url`]}>{fileName(row[`${side}_source_url`])}</a></dd>
              <dt>SHA-256 souboru</dt>
              <dd className="mono hash">{row[`${side}_sha256`]}</dd>
            </dl>
          </div>
        ))}
      </div>
      <p className="note">
        Úroveň: souhrn za variantu napříč podmínkami. Níže uvedený pohled na ověřená podání je samostatný; souhrnu nelze přisoudit jedinou podmínku nebo laboratoř. Datum vydání není datum posledního odborného hodnocení.
      </p>
    </section>
  );
}

function Scope() {
  return (
    <section id="rozsah" aria-labelledby="rozsah-title">
      <h2 id="rozsah-title">Rozsah a omezení</h2>
      <dl className="facts">
        <dt>Účel</dt>
        <dd>
          Pro klinické genetiky a kurátory, kteří se vracejí k již posouzeným variantám. Přehled ukazuje, které
          souhrnné germinální klasifikace BRCA1 a BRCA2 se mezi dvěma datovanými vydáními ClinVar liší.
        </dd>
        <dt>Interpretace</dt>
        <dd>
          Změna textu klasifikace není nová diagnóza. Jde o porovnání veřejných záznamů, nikoli pacientů. Zdroj je
          dohledatelný, interpretace zůstává na odborníkovi.
        </dd>
        <dt>Výběr variant</dt>
        <dd>
          Podle příslušnosti ke genu BRCA1 nebo BRCA2. Výběr podle genu zatím není klinicky ověřeným výběrem konkrétních
          onemocnění.
        </dd>
        <dt>Mimo tento pohled</dt>
        <dd>
          Zobrazení podání je omezené na pět zdrojově ověřených SCV. Absence příkladu neznamená, že se žádné podání nezměnilo.
          Vazby SCV–RCV, stabilní ID předkladatelů a verze VCV zdrojové TSV neposkytuje. Živé importy a ukládání uživatelských hodnocení nejsou dostupné.
        </dd>
        <dt>Vztah k ClinVar</dt>
        <dd>
          ClinVar nabízí{' '}
          <a href="https://www.ncbi.nlm.nih.gov/clinvar/docs/alerts/">upozornění na změnu souhrnné klasifikace</a>.
          Přínos dávkového přehledu oproti nim není ověřen; rychlost a přesnost revize se má teprve porovnat s přímou
          prací v ClinVar.
        </dd>
      </dl>
      <h3>Typy výsledku</h3>
      <dl className="facts">
        {Object.entries(labels).map(([key, label]) => (
          <Fragment key={key}>
            <dt>{label}</dt>
            <dd>{statusNotes[key]}</dd>
          </Fragment>
        ))}
      </dl>
    </section>
  );
}

function Sources({ data }: { data: Snapshot | null }) {
  return (
    <section id="zdroje" aria-labelledby="zdroje-title">
      <h2 id="zdroje-title">Zdroje</h2>
      <p className="note">
        Zdroj: NCBI ClinVar. Řetězce klasifikací zachováváme v původním znění. Odkaz „ClinVar“ v tabulce otevírá
        aktuální stránku záznamu; historickým důkazem jsou datované soubory.
      </p>
      <dl className="facts">
        {data?.releases.map((release, index) => (
          <Fragment key={release.release_date}>
            <dt>{index ? 'Novější vydání' : 'Starší vydání'} <span className="mono">{dateLabel(release.release_date)}</span></dt>
            <dd>
              <a className="mono" href={release.url}>{release.filename ?? fileName(release.url)}</a>
              {release.sha256 && <span className="mono hash">SHA-256 {release.sha256}</span>}
            </dd>
          </Fragment>
        ))}
        {data && (
          <>
            <dt>Otisk srovnání</dt>
            <dd><span className="mono hash">SHA-256 {data.comparison_sha256}</span></dd>
          </>
        )}
        <dt>Manifest zdrojů</dt>
        <dd><a className="mono" href="/api/releases.json">/api/releases.json</a> — URL, data vydání, hlavičky a kontrolní otisky obou původních variantových souborů.</dd>
        <dt>Archivní srovnání BRCA1</dt>
        <dd><a className="mono" href="/api/comparison.csv" download>/api/comparison.csv</a> — původní CSV Fáze 1. Aktuální výběr stáhnete tlačítkem nad tabulkou.</dd>
      </dl>
    </section>
  );
}

function fileName(url: string | undefined) {
  return url?.split('/').pop() || '—';
}

function WatchlistReport({value}:{value:NonNullable<Snapshot['watchlist']>}) {
  if (!value.invalid.length && !value.duplicates.length && !value.unresolved.length) return null;
  return <div className="state" role="status"><h2>Kontrola seznamu</h2>
    {value.invalid.map((entry,index)=><p key={index}><span className="mono">{entry.input}</span>: {entry.reason==='vcv_version_not_available'?'Historická verze VCV není v tomto zdroji podporována.':'Neplatný veřejný identifikátor.'}</p>)}
    {value.duplicates.length>0 && <p>Duplicitní ID byla sloučena: {value.duplicates.join(', ')}.</p>}
    {value.unresolved.map(entry=><p key={entry.input}><span className="mono">{entry.input}</span>: není ve zvoleném genu nebo načtených vydáních. Může jít i o nepodporovanou variantu.</p>)}
  </div>;
}
