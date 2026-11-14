export const labels: Record<string, string> = {
  changed: 'Změněná klasifikace', unchanged: 'Beze změny', newly_observed: 'Nově pozorovaný záznam',
  unavailable: 'Nedostupná klasifikace', missing: 'Chybějící záznam', unresolved: 'Nevyřešený rozpor',
};
/** What each comparison status means; mirrors src/brca_review/comparison/aggregate.py. */
export const statusNotes: Record<string, string> = {
  changed: 'Záznam je v obou vydáních a text souhrnné klasifikace se liší.',
  unchanged: 'Záznam je v obou vydáních se stejným textem souhrnné klasifikace.',
  newly_observed: 'Variation ID je jen v novějším vydání. Nejde o změnu klasifikace.',
  unavailable: 'Aspoň jedno vydání nemá klasifikaci uvedenou (prázdná hodnota, „-“, „not provided“, „no classification provided“). Nepočítá se jako změna.',
  missing: 'Variation ID je jen ve starším vydání. Nepřítomnost nedokládá stažení ani reklasifikaci.',
  unresolved: 'Řádky téhož Variation ID si v jednom vydání odporují; hodnota nebyla vybrána.',
};
export interface Row {
  variation_id: string; status: string; clinvar_url: string;
  previous_classification: string[]; current_classification: string[];
  previous_review_status: string[]; current_review_status: string[];
  previous_source_lines: number[]; current_source_lines: number[];
  previous_source_url: string; current_source_url: string;
  previous_sha256: string; current_sha256: string;
}
export interface Snapshot {
  comparison_id?: string;
  coverage?: { submission_coverage: string; verified_scvs: string[] };
  watchlist?: { invalid: { input: string; reason: string }[]; duplicates: string[]; unresolved: {input: string; reason: string}[]; canonical_ids: string[] | null };
  schema_version: number; gene: string; comparison_sha256: string;
  counts: Record<string, number>;
  releases: { release_date: string; url: string; sha256: string; filename?: string }[];
  rows: Row[];
}
export function decodeSnapshot(value: unknown): Snapshot {
  const data = value as Snapshot;
  if (!data || data.schema_version !== 1 || !['BRCA1','BRCA2','BRCA1+BRCA2'].includes(data.gene) ||
      !Array.isArray(data.rows) || !Array.isArray(data.releases) || data.releases.length !== 2 ||
      !data.counts || typeof data.comparison_sha256 !== 'string' ||
      !data.releases.every(r => typeof r.release_date === 'string') ||
      !data.rows.every(r => typeof r.variation_id === 'string' && r.status in labels &&
        ['previous', 'current'].every(side => {
          const record = r as unknown as Record<string, unknown>;
          return ['classification', 'review_status', 'source_lines'].every(field => Array.isArray(record[`${side}_${field}`]));
        }))) throw new Error('Neočekávaný formát dat.');
  return data;
}
export function filterRows(rows: Row[], status: string, query: string) {
  const search = query.trim().toLowerCase();
  return rows.filter(row => (!status || row.status === status) &&
    (!search || [row.variation_id, ...row.previous_classification, ...row.current_classification]
      .some(value => value.toLowerCase().includes(search))));
}
export const dateLabel = (date: string) => new Intl.DateTimeFormat('cs-CZ', { timeZone: 'UTC' }).format(new Date(`${date}T00:00:00Z`));

export interface Assertion {
  variation_id: string; scv: string; classification: string; classification_type: string;
  submitted_condition: string; reported_condition: string; submitter_name: string;
  last_evaluated: string; review_status: string; release_date: string;
  source_url: string; source_filename: string; source_sha256: string; source_lines: number[];
}
export interface SubmissionEvent {
  scv_base: string; status: string; flags: string[]; previous: Assertion[]; current: Assertion[];
  observed_between: string[]; aggregate_status: Record<string,string>;
}
export interface SubmissionResult {
  rows: SubmissionEvent[];
  coverage: { submission_coverage: string; verified_scvs: string[] };
}
export const submissionLabels: Record<string,string> = {
  classification_changed:'Změněná klasifikace podání', context_changed:'Změněný kontext',
  newly_observed:'Nově pozorované podání', missing:'Chybějící podání', unchanged:'Klasifikace beze změny',
  unavailable:'Nedostupná klasifikace', unresolved:'Nevyřešený rozpor',
};

export const submissionFlagLabels: Record<string,string> = {
  variation_id_changed:'přiřazení varianty', submitted_condition_changed:'podmínka podání',
  reported_condition_changed:'mapovaná podmínka', submitter_name_changed:'název předkladatele',
  classification_type_changed:'typ klasifikace', review_status_changed:'stav přezkumu',
  last_evaluated_changed:'datum posledního hodnocení', collection_method_changed:'metoda sběru',
  origin_counts_changed:'uváděný původ', submitted_gene_changed:'uváděný gen',
  scv_version_changed:'verze SCV', classification_changed:'text klasifikace',
};
