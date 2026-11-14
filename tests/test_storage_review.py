"""Optional PostgreSQL integration tests; never run destructive operations on the app DB."""
import os
from pathlib import Path
import tempfile
import unittest

try:
    from sqlalchemy import event, select, text, func
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import IntegrityError
    from fastapi.testclient import TestClient
    from brca_review.storage.database import get_engine
    from brca_review.storage.models import Variant, SubmissionSnapshot, ConditionContext
    from brca_review.storage.review import parse_ids
    from brca_review.storage.importer import import_artifacts
    from brca_review.web.app import create_app
    AVAILABLE=True
except ImportError:
    AVAILABLE=False


@unittest.skipUnless(AVAILABLE,'Install optional web/test dependencies')
class IdentifierTests(unittest.TestCase):
    def test_public_identifiers_duplicates_versions_and_invalid_only(self):
        ids,invalid,duplicates=parse_ids('91425,VCV000091425;bad VCV000091425.9 0')
        self.assertEqual(ids,[91425]);self.assertEqual(duplicates,['91425'])
        self.assertEqual([x['reason'] for x in invalid],['invalid_public_identifier','vcv_version_not_available','invalid_public_identifier'])
        self.assertEqual(parse_ids('bad')[0],[])
        self.assertIsNone(parse_ids(' ')[0])
        with self.assertRaises(ValueError):parse_ids(','.join(['1']*201))


@unittest.skipUnless(AVAILABLE and os.environ.get('BRCA_TEST_DATABASE'),'Set BRCA_TEST_DATABASE to an isolated migrated/imported test database')
class PostgreSQLReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ['BRCA_TEST_DATABASE'].startswith('brca_review_test_'):
            raise RuntimeError('Refuse non-test database')
        cls.engine=get_engine()
        if cls.engine.url.database!=os.environ['BRCA_TEST_DATABASE']:
            raise RuntimeError('Test database URL/name mismatch')
        cls.client=TestClient(create_app(cls.engine));cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None,None,None);cls.engine.dispose()

    def test_health_pair_and_read_only_http(self):
        self.assertEqual(self.client.get('/api/v1/health').json()['postgres_major'],17)
        self.assertEqual(len(self.client.get('/api/v1/comparisons').json()),1)
        self.assertEqual(self.client.post('/api/v1/comparison',json={}).status_code,405)
        self.assertEqual(self.client.get('/api/v1/no-such-endpoint').status_code,404)
        self.assertEqual(self.client.get('/api/v1/comparison?comparison_id=missing').status_code,404)
        observed=[]
        def trace(conn,cursor,statement,parameters,context,executemany):observed.append(statement)
        event.listen(self.engine,'before_cursor_execute',trace)
        try:self.client.get('/api/v1/comparison?ids=91425')
        finally:event.remove(self.engine,'before_cursor_execute',trace)
        self.assertIn('SET TRANSACTION READ ONLY',observed)

    def test_gene_counts_and_explicit_watchlist_errors(self):
        r=self.client.get('/api/v1/comparison?gene=BRCA2&ids=91425,VCV000091425,bad,999999999').json()
        self.assertEqual([x['variation_id'] for x in r['rows']],['91425'])
        self.assertEqual(r['watchlist']['duplicates'],['91425'])
        self.assertEqual(r['watchlist']['invalid'][0]['input'],'bad')
        self.assertEqual(r['watchlist']['unresolved'][0]['input'],'999999999')
        self.assertEqual(self.client.get('/api/v1/comparison?ids=bad').json()['rows'],[])
        r=self.client.get('/api/v1/comparison?gene=BRCA1&ids=91425').json()
        self.assertEqual(r['rows'],[]);self.assertTrue(r['watchlist']['unresolved'])
        self.assertEqual(self.client.get('/api/v1/comparison?gene=OTHER').status_code,422)
        self.assertEqual(self.client.get('/api/v1/comparison?gene=BRCA2').json()['counts']['changed'],67)
        self.assertEqual(self.client.get('/api/v1/comparison?gene=BRCA1').json()['counts']['changed'],46)

    def test_verified_scv_details_and_filters(self):
        r=self.client.get('/api/v1/variants/91425').json()
        self.assertEqual(r['aggregate']['status'],'unchanged')
        e=r['submissions']['rows'][0]
        self.assertEqual(e['status'],'classification_changed')
        self.assertEqual(e['previous'][0]['scv'],'SCV000184021.8')
        self.assertEqual(e['current'][0]['classification'],'Likely benign')
        self.assertEqual(e['previous'][0]['last_evaluated'],'Oct 18, 2022')
        self.assertEqual(e['previous'][0]['reported_condition'],'C0027672:Hereditary cancer-predisposing syndrome')
        self.assertIsNone(e['current'][0]['submitter_id'])
        self.assertEqual(r['coverage']['submission_coverage'],'verified_subset')
        self.assertEqual(self.client.get('/api/v1/submissions?submitter=Ambry&condition=C0027672&status=classification_changed').json()['rows'].__len__(),2)
        self.assertEqual(self.client.get('/api/v1/submissions?submitter=unknown').json()['rows'],[])
        self.assertEqual(self.client.get('/api/v1/variants/999999999').status_code,404)

    def test_postgres_constraints_enforce_identity_and_snapshot_links(self):
        statements=[
          "INSERT INTO variants (variation_id, genes) VALUES (-1, '[]'::jsonb)",
          "INSERT INTO variants (variation_id, genes) VALUES (91425, '[]'::jsonb)",
          "INSERT INTO aggregate_snapshots (release_id, variation_id, classifications, review_statuses, genes, source_lines) VALUES (-99,91425,'[]','[]','[]','[]')",
        ]
        for statement in statements:
            with self.assertRaises(IntegrityError), self.engine.begin() as connection:
                connection.execute(text(statement))

    def test_import_idempotency_and_failed_checksum_no_writes(self):
        with Session(self.engine) as s:before=s.scalar(select(func.count()).select_from(Variant))
        self.assertEqual(import_artifacts(self.engine,Path('outputs/brca1-brca2.csv'),Path('outputs/submissions-final.jsonl')),'already_imported')
        with tempfile.TemporaryDirectory() as folder:
            bad=Path(folder)/'bad.csv';bad.write_text('not a verified artifact')
            with self.assertRaises(ValueError):import_artifacts(self.engine,bad,Path('outputs/submissions-final.jsonl'))
        with Session(self.engine) as s:
            self.assertEqual(s.scalar(select(func.count()).select_from(Variant)),before)
            self.assertEqual(s.scalar(select(func.count()).select_from(SubmissionSnapshot)),9)
            self.assertGreater(s.scalar(select(func.count()).select_from(ConditionContext)),0)
