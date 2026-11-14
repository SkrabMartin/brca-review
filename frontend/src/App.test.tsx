import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';
import { decodeSnapshot, filterRows, type Row } from './data';
const row = {
  variation_id:'37422',status:'changed',clinvar_url:'https://www.ncbi.nlm.nih.gov/clinvar/variation/37422/',
  previous_classification:['Uncertain significance'],current_classification:['Conflicting classifications of pathogenicity'],
  previous_review_status:['criteria provided'],current_review_status:['conflicting'],
  previous_source_lines:[43739],current_source_lines:[43758],
  previous_source_url:'https://example.org/old',current_source_url:'https://example.org/new',
  previous_sha256:'oldhash',current_sha256:'newhash',
} satisfies Row;
const releases=[{release_date:'2025-01-02'},{release_date:'2025-02-06'}];
const snapshot={schema_version:1,gene:'BRCA1',comparison_sha256:'hash',counts:{changed:1},releases,rows:[row]};
const coverage={submission_coverage:'verified_subset',verified_scvs:['SCV000184021']};
const assertion={variation_id:'91425',scv:'SCV000184021.8',classification:'Uncertain significance',classification_type:'germline',submitted_condition:'MedGen:C0027672',reported_condition:'C0027672:Hereditary cancer-predisposing syndrome',submitter_name:'Ambry Genetics',last_evaluated:'Oct 18, 2022',review_status:'criteria provided',release_date:'2025-01-02',source_url:'https://example.org/old',source_filename:'submission_old.gz',source_sha256:'oldscvhash',source_lines:[250350]};
const event={scv_base:'SCV000184021',status:'classification_changed',flags:['classification_changed'],previous:[assertion],current:[{...assertion,scv:'SCV000184021.9',classification:'Likely benign',release_date:'2025-02-06',last_evaluated:'Nov 26, 2024'}],observed_between:['2025-01-02','2025-02-06'],aggregate_status:{'91425':'unchanged'}};
function mockApi(options:{fail?:boolean;watchlist?:boolean}={}) {
  let failed=false;
  const fetcher=vi.fn(async(input:string)=>{
    if(input==='/api/v1/comparisons')return{ok:true,json:async()=>[{id:'2025-01-02_2025-02-06',releases}]};
    if(input.startsWith('/api/v1/submissions?'))return{ok:true,json:async()=>({rows:[event],coverage})};
    if(options.fail&&!failed){failed=true;return{ok:false};}
    const params=new URL(input,'http://localhost').searchParams;
    return{ok:true,json:async()=>({...snapshot,gene:params.get('gene')||'BRCA1+BRCA2',
      ...(options.watchlist&&params.has('ids')?{watchlist:{invalid:[{input:'bad',reason:'invalid_public_identifier'}],duplicates:['37422'],unresolved:[{input:'999',reason:'not_in_selected_gene_or_loaded_releases'}],canonical_ids:['37422','999']}}:{})})};
  });
  vi.stubGlobal('fetch',fetcher);return fetcher;
}
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('uses same-origin API and preserves redesigned aggregate table/detail/search',async()=>{
  const fetcher=mockApi();render(<App/>);
  fireEvent.click(await screen.findByRole('button',{name:'Detail varianty 37422'}));
  expect(fetcher.mock.calls.some(([url])=>url.startsWith('/api/v1/comparison?'))).toBe(true);
  expect(screen.getByText('oldhash')).toBeTruthy();expect(screen.getByText('newhash')).toBeTruthy();
  fireEvent.change(screen.getByRole('searchbox'),{target:{value:'999999'}});
  expect(screen.queryByRole('button',{name:'Detail varianty 37422'})).toBeNull();
  expect(screen.getByText(/Žádný záznam neodpovídá/)).toBeTruthy();
});
it('reports backend failure and retries without fabricated data',async()=>{
  mockApi({fail:true});render(<App/>);await screen.findByRole('alert');
  expect(screen.queryByRole('table')).toBeNull();fireEvent.click(screen.getByRole('button',{name:'Zkusit znovu'}));
  expect(await screen.findByRole('button',{name:'Detail varianty 37422'})).toBeTruthy();
});
it('selects genes and canonical watchlists with explicit invalid/duplicate/absent feedback',async()=>{
  const fetcher=mockApi({watchlist:true});render(<App/>);
  await screen.findByRole('button',{name:'Detail varianty 37422'});
  fireEvent.change(screen.getByLabelText('Gen'),{target:{value:'BRCA2'}});
  fireEvent.change(screen.getByLabelText(/Sledované veřejné identifikátory/),{target:{value:'VCV000037422,37422,bad,999'}});
  fireEvent.click(screen.getByRole('button',{name:'Použít seznam'}));
  expect(await screen.findByText(/Duplicitní ID byla sloučena/)).toBeTruthy();
  expect(screen.getByText(/Neplatný veřejný identifikátor/)).toBeTruthy();
  expect(screen.getByText(/není ve zvoleném genu/)).toBeTruthy();
  expect(fetcher.mock.calls.some(([url])=>url.includes('gene=BRCA2')&&url.includes('ids='))).toBe(true);
});
it('shows actual SCV conditions/submitter/version/evaluation dates and filters verified subset',async()=>{
  mockApi();render(<App/>);
  const summary=await screen.findByText(/SCV000184021/,{selector:'summary span'});
  fireEvent.click(summary);
  expect(screen.getByText('SCV000184021.8')).toBeTruthy();expect(screen.getByText('SCV000184021.9')).toBeTruthy();
  expect(screen.getByText('Oct 18, 2022')).toBeTruthy();
  expect(screen.getAllByText('Ambry Genetics')).toHaveLength(2);
  expect(screen.getByText(/91425: beze změny/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Předkladatel'),{target:{value:'unknown lab'}});
  await waitFor(()=>expect(screen.getByText(/Žádné ověřené podání neodpovídá/)).toBeTruthy());
});
it('rejects malformed data and retains classification search',()=>{
  expect(()=>decodeSnapshot({rows:[]})).toThrow();
  expect(filterRows([row],'changed','37422')).toEqual([row]);
  expect(filterRows([row],'unchanged','')).toEqual([]);
  expect(filterRows([row],'','uncertain')).toEqual([row]);
});
