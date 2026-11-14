import { readFileSync } from 'node:fs';
const data = JSON.parse(readFileSync('public/api/comparison.json', 'utf8'));
if (data.schema_version !== 1 || data.rows.length !== 14970) throw new Error('Export the verified Phase 1 snapshot before building.');
for (const file of ['health', 'releases.json', 'comparison.csv']) readFileSync(`public/api/${file}`);
