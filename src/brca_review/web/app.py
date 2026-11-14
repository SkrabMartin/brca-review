"""Same-origin, read-only API backed by migrated PostgreSQL snapshots."""
from contextlib import asynccontextmanager
import csv
import io
import json
from typing import Literal
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from brca_review.storage.database import get_engine
from brca_review.storage import review

DEFAULT_COMPARISON='2025-01-02_2025-02-06'


def create_app(engine=None):
    @asynccontextmanager
    async def lifespan(app):
        if engine is None:app.state.engine=get_engine()
        try:yield
        finally:
            if engine is None:app.state.engine.dispose()

    app=FastAPI(title='BRCA Review read-only API',version='0.1.0',lifespan=lifespan,
                docs_url=None,redoc_url=None,openapi_url=None)
    if engine is not None:app.state.engine=engine

    def session(request:Request):
        with Session(request.app.state.engine) as database:
            database.execute(text('SET TRANSACTION READ ONLY'))
            yield database

    @app.exception_handler(SQLAlchemyError)
    async def unavailable(request,error):
        return JSONResponse(status_code=503,content={'detail':'Database unavailable or schema not ready'})

    @app.exception_handler(ValueError)
    async def invalid(request,error):
        return JSONResponse(status_code=422,content={'detail':str(error)})

    @app.exception_handler(KeyError)
    async def not_found(request,error):
        return JSONResponse(status_code=404,content={'detail':'Comparison or variant not available'})

    @app.get('/api/v1/health')
    def health(db:Session=Depends(session)):
        version=db.execute(text("SELECT current_setting('server_version_num')::int")).scalar_one()
        ready=review.list_comparisons(db)
        if not ready:raise HTTPException(503,'No comparison imported')
        return dict(status='ok',mode='postgresql-read-only',postgres_major=version//10000,comparisons=len(ready))

    @app.get('/api/v1/comparisons')
    def comparisons(db:Session=Depends(session)):return review.list_comparisons(db)

    @app.get('/api/v1/comparison')
    def comparison(comparison_id:str=Query(DEFAULT_COMPARISON,max_length=80),
                   gene:Literal['BRCA1','BRCA2']|None=None,ids:str|None=Query(None,max_length=8000),
                   db:Session=Depends(session)):
        return review.snapshot(db,comparison_id,gene,ids)

    @app.get('/api/v1/comparison.csv')
    def comparison_csv(comparison_id:str=Query(DEFAULT_COMPARISON,max_length=80),
                       gene:Literal['BRCA1','BRCA2']|None=None,ids:str|None=Query(None,max_length=8000),
                       db:Session=Depends(session)):
        result=review.snapshot(db,comparison_id,gene,ids)
        stream=io.StringIO(newline='')
        fields=['variation_id','status','clinvar_url']+[f'{side}_{field}' for side in ('previous','current')
            for field in ('release_date','classification','review_status','genes','source_lines','source_url','sha256')]
        writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n',extrasaction='ignore')
        writer.writeheader()
        for row in result['rows']:
            writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
        return Response(stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="brca-review.csv"'})

    @app.get('/api/v1/submissions')
    def submissions(comparison_id:str=Query(DEFAULT_COMPARISON,max_length=80),
                    gene:Literal['BRCA1','BRCA2']|None=None,ids:str|None=Query(None,max_length=8000),
                    status:Literal['classification_changed','context_changed','newly_observed','missing','unchanged','unavailable','unresolved']|None=None,
                    condition:str=Query('',max_length=200),submitter:str=Query('',max_length=200),
                    db:Session=Depends(session)):
        return review.submission_events(db,comparison_id,gene,ids,status,condition,submitter)

    @app.get('/api/v1/variants/{variation_id}')
    def variant(variation_id:str,comparison_id:str=Query(DEFAULT_COMPARISON,max_length=80),db:Session=Depends(session)):
        result=review.snapshot(db,comparison_id,raw_ids=variation_id)
        if not result['rows']:raise HTTPException(404,'Variant not in loaded releases')
        if len(result['rows'])!=1 or result['watchlist']['invalid']:raise HTTPException(422,'Expected one supported public identifier')
        return dict(aggregate=result['rows'][0],releases=result['releases'],
                    submissions=review.submission_events(db,comparison_id,raw_ids=variation_id),coverage=result['coverage'])
    return app


app=create_app()
